"""오늘 기사와 정말 이어지는 과거 기사를 잇는다. 모델을 부르지 않는다.

    이어짐 = (기업이 직접 겹침 OR 관계로 이어진 기업) AND 키워드가 겹침

기업 하나만으로는 잇지 않는다 — 삼성전자는 거의 모든 한국어 기사에 나와서 증거가 못 된다
(docs/slices/06-연결고리-기준.md). 회사가 달라도 extract.py 가 뽑은 관계로 이어져 있으면 잇는다.
억지로 잇지 않는다 — 조건을 못 채우면 '이어지는 흐름 없음'.
과거 범위는 제한 없음(있는 전체)이고, 정규화는 companies.md 사전에 있는 것만 한다.
"""

import json
import sys
from pathlib import Path

from filter import filter_articles, read_keywords

HERE = Path(__file__).parent
ARTICLE_DIR = HERE / "data" / "articles"
COMPANIES_FILE = HERE / "data" / "companies.md"

MIN_KEYWORDS = 1  # 키워드가 몇 개 겹쳐야 잇는가. 헐거우면 올린다
MAX_RELATED = 10  # 기사 하나당 최대 몇 건까지 보여주는가


def read_company_map() -> dict[str, str]:
    """별칭·정식명을 소문자로 낮춰 정식명에 매핑한다. 사전에 없는 이름은 다루지 않는다."""
    mapping: dict[str, str] = {}
    in_table = False
    for line in COMPANIES_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_table = s.startswith("## 정식명")
            continue
        if not in_table or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("정식명", "---"):
            continue
        canonical = cells[0]
        mapping[canonical.lower()] = canonical
        for alias in cells[1].split(","):
            alias = alias.strip()
            if alias:
                mapping[alias.lower()] = canonical
    return mapping


def companies_mentioned(text: str, company_map: dict[str, str]) -> set[str]:
    """글에 등장하는 정식명 집합. 긴 별칭부터 찾아야 짧은 이름이 긴 이름을 잘라먹지 않는다."""
    haystack = text.lower()
    found: set[str] = set()
    for alias in sorted(company_map, key=len, reverse=True):
        if alias in haystack:
            found.add(company_map[alias])
    return found


def read_topic_keywords() -> list[str]:
    """무엇에 관한 기사인지 가릴 말들. `### 카테고리` 아래 것만 쓴다.

    `포함` 목록(`반도체` 등)은 거의 모든 기사에 걸려서 증거가 못 된다 —
    삼성전자가 증거가 못 되는 것과 같은 이유다.
    """
    _, _, categories = read_keywords()
    return sorted({w for words in categories.values() for w in words}, key=len, reverse=True)


def topic_keywords(text: str, vocab: list[str]) -> set[str]:
    """글에 등장하는 카테고리 키워드."""
    haystack = text.lower()
    return {w for w in vocab if w in haystack}


def read_relation_pairs() -> set[frozenset[str]]:
    """extract.py 가 뽑아 둔 기업 짝. 회사가 달라도 이어 주는 다리가 된다.

    사용자 요청 — "엔비디아가 개발한 걸 삼성이 만들기로 했다" 같은 것.
    아직 뽑은 게 없으면 빈 집합. 그러면 직접 겹침만으로 판정한다.
    """
    pairs: set[frozenset[str]] = set()
    for path in ARTICLE_DIR.glob("*.extracted.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for a in data["articles"]:
            for r in a.get("relations") or []:
                names = [c for c in (r.get("companies") or []) if c]
                for i, one in enumerate(names):
                    for other in names[i + 1 :]:
                        pairs.add(frozenset({one, other}))
    return pairs


def bridged(today: set[str], past: set[str], pairs: set[frozenset[str]]) -> bool:
    """회사가 달라도 관계로 이어져 있는가."""
    return any(frozenset({a, b}) in pairs for a in today for b in past if a != b)


def find_related(
    article: dict,
    past_articles: list[dict],
    company_map: dict[str, str],
    vocab: list[str],
    relation_pairs: set[frozenset[str]],
    min_keywords: int = MIN_KEYWORDS,
) -> list[dict]:
    """정말 이어지는 과거 기사를, 최신순 최대 MAX_RELATED 건 돌려준다.

        이어짐 = (기업이 직접 겹침 OR 관계로 이어진 기업) AND 키워드가 겹침

    기업 하나만으로는 잇지 않는다 — 삼성전자는 거의 모든 기사에 나와서 증거가 못 된다.
    """
    today_text = f"{article['title']} {article['summary']}"
    today_companies = companies_mentioned(today_text, company_map)
    today_keywords = topic_keywords(today_text, vocab)
    if not today_companies or not today_keywords:
        return []

    candidates = []
    for past in past_articles:
        past_text = f"{past['title']} {past['summary']}"
        past_companies = companies_mentioned(past_text, company_map)

        shared_companies = today_companies & past_companies
        if not shared_companies and not bridged(today_companies, past_companies, relation_pairs):
            continue

        shared_keywords = today_keywords & topic_keywords(past_text, vocab)
        if len(shared_keywords) < min_keywords:
            continue

        candidates.append(
            {
                "date": (past.get("published") or "")[:10],
                "title": past["title"],
                "url": past["url"],
                "shared_companies": sorted(shared_companies),
                "shared_keywords": sorted(shared_keywords),
            }
        )

    candidates.sort(key=lambda c: c["date"], reverse=True)
    return candidates[:MAX_RELATED]


def _load_all_past(before_day: str) -> list[dict]:
    """<before_day> 이전 날짜의, 반도체로 걸러진 기사를 전부 모은다."""
    past: list[dict] = []
    for path in sorted(ARTICLE_DIR.glob("*.json")):
        if "." in path.stem or path.stem >= before_day:
            continue  # .filtered/.selected/.extracted/.linked 파생 파일과 오늘 이후는 건너뛴다
        raw = json.loads(path.read_text(encoding="utf-8"))["articles"]
        kept, _ = filter_articles(raw)
        past.extend(kept)
    return past


def link_day(day: str) -> list[dict]:
    """오늘 선별된 기사마다 이어지는 흐름을 붙인다."""
    from pick import select_day

    picked, _, _ = select_day(day)
    company_map = read_company_map()
    vocab = read_topic_keywords()
    pairs = read_relation_pairs()
    past = _load_all_past(day)

    linked = []
    for a in picked:
        related = find_related(a, past, company_map, vocab, pairs)
        linked.append({**a, "related": related})
    return linked


def save_day(day: str, linked: list[dict]) -> Path:
    path = ARTICLE_DIR / f"{day}.linked.json"
    path.write_text(
        json.dumps({"date": day, "articles": linked}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    if len(argv) != 1:
        print("사용법: python link.py <날짜>   예: python link.py 2026-08-22", file=sys.stderr)
        return 1

    day = argv[0]
    linked = link_day(day)
    save_day(day, linked)

    with_flow = [a for a in linked if a["related"]]
    print(f"{day} — {len(linked)}건 중 이어지는 흐름 있음 {len(with_flow)}건")
    for a in with_flow:
        names = ", ".join(f"{r['date']} {r['title']}" for r in a["related"])
        print(f"  · {a['title']}")
        print(f"      → {names}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
