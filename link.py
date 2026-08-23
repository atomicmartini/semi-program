"""오늘 기사와 공통 기업이 있는 과거 기사를 잇는다. 모델을 부르지 않는다.

extract.py 의 관계·인용구는 아직 검증 전이라 쓰지 않는다 (docs/slices/01-이어지는-흐름.md).
공통 기업 언급만으로 잇는다. 억지로 잇지 않는다 — 임계값 미만이면 '이어지는 흐름 없음'.
과거 범위는 제한 없음(있는 전체)이고, 정규화는 companies.md 사전에 있는 것만 한다.
"""

import json
import sys
from pathlib import Path

from filter import filter_articles

HERE = Path(__file__).parent
ARTICLE_DIR = HERE / "data" / "articles"
COMPANIES_FILE = HERE / "data" / "companies.md"

THRESHOLD = 1  # 공통 기업 몇 개부터 잇는가
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


def find_related(
    article: dict, past_articles: list[dict], company_map: dict[str, str], threshold: int = THRESHOLD
) -> list[dict]:
    """공통 기업이 임계값 이상인 과거 기사를, 최신순 최대 MAX_RELATED 건 돌려준다."""
    today_companies = companies_mentioned(f"{article['title']} {article['summary']}", company_map)
    if not today_companies:
        return []

    candidates = []
    for past in past_articles:
        past_companies = companies_mentioned(f"{past['title']} {past['summary']}", company_map)
        shared = today_companies & past_companies
        if len(shared) >= threshold:
            candidates.append(
                {
                    "date": (past.get("published") or "")[:10],
                    "title": past["title"],
                    "url": past["url"],
                    "shared_companies": sorted(shared),
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
    past = _load_all_past(day)

    linked = []
    for a in picked:
        related = find_related(a, past, company_map)
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
