"""반도체와 무관한 기사를 걸러내고 카테고리를 붙인다. 모델을 부르지 않는다.

키워드를 코드에 박지 않는다 (CLAUDE.md). 늘리고 줄이는 일은 data/keywords.md 에서 한다.
이 단계의 카테고리는 키워드로만 정한다. 애매하면 `미분류` 로 둔다.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
KEYWORDS_FILE = HERE / "data" / "keywords.md"
COMPANIES_FILE = HERE / "data" / "companies.md"
ARTICLE_DIR = HERE / "data" / "articles"

UNCLASSIFIED = "미분류"


def read_keywords() -> tuple[list[str], list[str], dict[str, list[str]]]:
    """data/keywords.md 에서 포함·제외·카테고리 키워드를 읽는다.

    '##' 아래 본문은 포함/제외 목록, '###' 아래 본문은 그 카테고리의 키워드다.
    """
    include: list[str] = []
    exclude: list[str] = []
    categories: dict[str, list[str]] = {}
    bucket: list[str] | None = None

    for line in KEYWORDS_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()

        if stripped.startswith("### "):
            bucket = categories.setdefault(stripped[4:].strip(), [])
            continue
        if stripped.startswith("## "):
            head = stripped[3:]
            if head.startswith("포함"):
                bucket = include
            elif head.startswith("제외"):
                bucket = exclude
            else:
                bucket = None  # 카테고리 절의 설명문, '확인 필요' 등은 담지 않는다
            continue

        if bucket is None or not stripped or stripped.startswith((">", "-", "|")):
            continue
        bucket.extend(w.strip().lower() for w in stripped.split(",") if w.strip())

    return include, exclude, categories


def read_companies() -> list[str]:
    """data/companies.md 의 정식명과 별칭. 기업명이 나오면 반도체 기사로 본다.

    기업 목록을 keywords.md 에 또 적지 않는다 — 두 곳에 적으면 어긋난다.
    """
    names: list[str] = []
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
        names.append(cells[0].lower())
        names.extend(a.strip().lower() for a in cells[1].split(",") if a.strip())
    return names


def _haystack(article: dict) -> str:
    return f"{article['title']} {article['summary']}".lower()


def classify(text: str, categories: dict[str, list[str]]) -> str:
    """먼저 걸린 카테고리를 쓴다. 하나도 안 걸리면 미분류."""
    for name, words in categories.items():
        if any(w in text for w in words):
            return name
    return UNCLASSIFIED


def filter_articles(articles: list[dict]) -> tuple[list[dict], list[tuple[dict, str]]]:
    """남길 기사와 (버린 기사, 이유) 목록을 돌려준다."""
    include, exclude, categories = read_keywords()
    companies = read_companies()
    kept: list[dict] = []
    dropped: list[tuple[dict, str]] = []
    seen_titles: set[str] = set()

    for a in articles:
        text = _haystack(a)

        hit = next((w for w in exclude if w in text), None)
        if hit:
            dropped.append((a, f"제외 키워드 '{hit}'"))
            continue
        if not (any(w in text for w in include) or any(c in text for c in companies)):
            dropped.append((a, "반도체 키워드·기업명 없음"))
            continue

        # 뉴스룸이 한 기사를 여러 페이지로 쪼개 올리는 경우가 있다 (링크는 다르고 제목은 같다).
        # 제목이 완전히 같은 것만 걸러낸다. 비슷한 기사 묶기는 이번 범위 밖이다.
        title_key = " ".join(a["title"].split()).lower()
        if title_key in seen_titles:
            dropped.append((a, "같은 제목이 이미 있음"))
            continue
        seen_titles.add(title_key)

        kept.append({**a, "category": classify(text, categories)})

    return kept, dropped


def load_day(day: str) -> list[dict]:
    path = ARTICLE_DIR / f"{day}.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} 가 없습니다. 먼저 python fetch.py 를 실행하세요.")
    return json.loads(path.read_text(encoding="utf-8"))["articles"]


def save_day(day: str, kept: list[dict]) -> Path:
    path = ARTICLE_DIR / f"{day}.filtered.json"
    path.write_text(
        json.dumps({"date": day, "articles": kept}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    if len(argv) != 1:
        print("사용법: python filter.py <날짜>   예: python filter.py 2026-08-22", file=sys.stderr)
        return 1

    day = argv[0]
    articles = load_day(day)
    kept, dropped = filter_articles(articles)

    print(f"{day} — 받은 기사 {len(articles)}건")
    print(f"  남김 {len(kept)}건 · 버림 {len(dropped)}건")

    if dropped:
        reasons: dict[str, int] = {}
        for _, why in dropped:
            reasons[why] = reasons.get(why, 0) + 1
        print("\n버린 이유")
        for why, n in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"  {n:>3}건  {why}")

    if kept:
        counts: dict[str, int] = {}
        for a in kept:
            counts[a["category"]] = counts.get(a["category"], 0) + 1
        print("\n카테고리")
        for name, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {n:>3}건  {name}")

    print(f"\n저장 {save_day(day, kept)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
