"""저장한 기사를 목록 한 장으로 낸다. 스켈레톤 — 목록 말고는 아무것도 없다.

개념 링크 · 칩 필터 · 날짜 목록은 아직 만들지 않는다 (PLAN.md).
"""

import html
import json
import sys
from pathlib import Path

from pick import select_day

HERE = Path(__file__).parent
ARTICLE_DIR = HERE / "data" / "articles"
DOCS_DIR = HERE / "docs"
STATUS_FILE = HERE / "data" / "fetch_status.json"

PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>반도체 뉴스 데일리 — {date}</title>
<style>
  body {{ margin:0 auto; padding:24px; max-width:900px; background:#fbfbfa; color:#1c1b19;
    font-family:"Pretendard","Apple SD Gothic Neo",system-ui,sans-serif; line-height:1.6;
    word-break:keep-all; }}
  h1 {{ font-size:24px; margin:0; }}
  .meta {{ color:#63605a; font-size:14px; margin:6px 0 24px; }}
  .card {{ background:#fff; border:1px solid #e4e2dd; border-radius:8px;
    padding:16px 18px; margin-bottom:12px; }}
  .cat {{ font-size:12px; color:#94908a; }}
  .tier {{ font-size:12px; color:#0a7d3c; }}
  h2 {{ font-size:17px; margin:4px 0 6px; }}
  .sum {{ color:#63605a; font-size:14px; margin:0; }}
  .src {{ font-size:12px; color:#94908a; margin-top:10px; }}
  .none {{ color:#94908a; }}
  footer {{ margin-top:32px; padding-top:14px; border-top:1px solid #e4e2dd;
    font-size:12px; color:#94908a; }}
</style>
</head>
<body>
<h1>반도체 뉴스 데일리</h1>
<div class="meta">{date} · {count}건 · 수집 {ok}곳 중 {total}곳 정상</div>
{cards}
<footer>출처 data/sources.md · 이 페이지는 투자 조언이 아닙니다.</footer>
</body>
</html>
"""

CARD = """<div class="card">
  <span class="cat">{category}</span> <span class="tier">{tier}</span>
  <h2>{title}</h2>
  <p class="sum">{summary}</p>
  <div class="src">{source} · 발행 {published} · <a href="{url}">원문</a></div>
</div>
"""


def _status() -> tuple[int, int]:
    if not STATUS_FILE.exists():
        return 0, 0
    data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    return data.get("ok", 0), data.get("total", 0)


def render_page(day: str) -> str:
    """하루치 목록 HTML 을 문자열로 만든다."""
    picked, _, _ = select_day(day)
    ok, total = _status()

    if picked:
        cards = "".join(
            CARD.format(
                category=html.escape(a.get("category", "미분류")),
                tier=html.escape(a.get("tier", "")),
                title=html.escape(a["title"]),
                summary=html.escape(a["summary"][:200]),
                source=html.escape(a["source"]),
                published=html.escape((a.get("published") or "—")[:16].replace("T", " ")),
                url=html.escape(a["url"], quote=True),
            )
            for a in picked
        )
    else:
        cards = '<p class="none">이 날은 반도체 관련 기사가 없습니다.</p>'

    return PAGE.format(date=day, count=len(picked), ok=ok, total=total, cards=cards)


def write_page(day: str) -> Path:
    DOCS_DIR.mkdir(exist_ok=True)
    path = DOCS_DIR / f"{day}.html"
    path.write_text(render_page(day), encoding="utf-8")
    return path


def latest_day() -> str:
    """기사가 있는 가장 최근 날짜."""
    days = sorted(p.stem for p in ARTICLE_DIR.glob("*.json") if "." not in p.stem)
    if not days:
        raise FileNotFoundError("data/articles/ 가 비었습니다. 먼저 python fetch.py 를 실행하세요.")
    return days[-1]


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    day = argv[0] if argv else latest_day()
    path = write_page(day)
    print(f"{day} → {path}")

    # index.html 은 가장 최근 날짜와 같은 내용으로 둔다.
    if day == latest_day():
        index = DOCS_DIR / "index.html"
        index.write_text(render_page(day), encoding="utf-8")
        print(f"{day} → {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
