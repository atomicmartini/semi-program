"""화면에 올릴 기사를 고른다. 모델을 부르지 않는다.

파일 이름이 pick.py 인 이유 — select 는 파이썬 표준 라이브러리 이름이라
같은 이름을 쓰면 리눅스에서 subprocess·asyncio 가 이 파일을 불러 깨진다.

10건은 상한이다. 모자라면 있는 만큼만 쓴다 — 억지로 채우지 않는다.
자른 건수를 반드시 드러낸다 (CLAUDE.md).
"""

import json
import sys
from pathlib import Path

from filter import filter_articles, load_day, read_companies

HERE = Path(__file__).parent
ARTICLE_DIR = HERE / "data" / "articles"

MAX_TOTAL = 10
MAX_PER_CATEGORY = 3

SCORE_OFFICIAL = 3  # [공식] 출처 — 기업 발표는 확정 사실이다
SCORE_COMPANY = 1  # 관심 기업이 언급됨


def score(article: dict, companies: list[str]) -> int:
    """점수는 코드가 매긴다. 모델을 쓰지 않는다 (CLAUDE.md)."""
    points = 0
    if article.get("tier") == "[공식]":
        points += SCORE_OFFICIAL
    text = f"{article['title']} {article['summary']}".lower()
    if any(c in text for c in companies):
        points += SCORE_COMPANY
    return points


def select_top(articles: list[dict]) -> tuple[list[dict], list[dict]]:
    """고른 기사와 자른 기사를 돌려준다.

    카테고리당 최대 3건을 먼저 채우고, 10건이 안 차면 남은 자리를 점수 순으로 메운다.
    """
    companies = read_companies()
    # 점수 내림차순 · 같은 점수면 최신순
    ranked = sorted(
        articles,
        key=lambda a: (score(a, companies), a.get("published") or ""),
        reverse=True,
    )

    picked: list[dict] = []
    per_category: dict[str, int] = {}

    for a in ranked:
        cat = a.get("category", "미분류")
        if len(picked) >= MAX_TOTAL:
            break
        if per_category.get(cat, 0) >= MAX_PER_CATEGORY:
            continue
        per_category[cat] = per_category.get(cat, 0) + 1
        picked.append({**a, "score": score(a, companies)})

    # 카테고리 상한 때문에 자리가 남았으면 점수 순으로 채운다.
    if len(picked) < MAX_TOTAL:
        chosen = {a["url"] for a in picked}
        for a in ranked:
            if len(picked) >= MAX_TOTAL:
                break
            if a["url"] not in chosen:
                picked.append({**a, "score": score(a, companies)})
                chosen.add(a["url"])

    chosen = {a["url"] for a in picked}
    cut = [a for a in ranked if a["url"] not in chosen]
    return picked, cut


def select_day(day: str) -> tuple[list[dict], list[dict], int]:
    """하루치를 거르고 고른다. (고른 것, 자른 것, 거르기 전 기사 수)"""
    raw = load_day(day)
    kept, _ = filter_articles(raw)
    picked, cut = select_top(kept)
    return picked, cut, len(raw)


def save_day(day: str, picked: list[dict]) -> Path:
    path = ARTICLE_DIR / f"{day}.selected.json"
    path.write_text(
        json.dumps({"date": day, "articles": picked}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    if len(argv) != 1:
        print("사용법: python pick.py <날짜>   예: python pick.py 2026-08-20", file=sys.stderr)
        return 1

    day = argv[0]
    picked, cut, raw_count = select_day(day)

    print(f"{day} — 받은 기사 {raw_count}건 → 거른 뒤 {len(picked) + len(cut)}건")
    if len(picked) < MAX_TOTAL:
        print(f"  고름 {len(picked)}건 (상한 {MAX_TOTAL}건에 못 미침 — 있는 만큼만)")
    else:
        print(f"  고름 {len(picked)}건")
    # 자른 수를 숨기지 않는다 (CLAUDE.md).
    print(f"  자름 {len(cut)}건")

    if picked:
        counts: dict[str, int] = {}
        for a in picked:
            counts[a["category"]] = counts.get(a["category"], 0) + 1
        print("\n카테고리")
        for name, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {n}건  {name}")

        print("\n고른 기사")
        for a in picked:
            print(f"  [{a['score']}점] [{a['category']}] {a['title'][:56]}")

    if cut:
        print("\n자른 기사")
        for a in cut[:5]:
            print(f"  [{a.get('category', '미분류')}] {a['title'][:56]}")
        if len(cut) > 5:
            print(f"  … 외 {len(cut) - 5}건")

    print(f"\n저장 {save_day(day, picked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
