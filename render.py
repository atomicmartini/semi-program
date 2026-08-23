"""저장한 기사를 목록으로 내고, 개념 페이지와 날짜 링크를 함께 만든다.

기사 글 속의 용어에는 개념 페이지로 가는 링크를 건다.
카테고리 칩을 누르면 그 분야만 남는다.
"""

import html
import json
import sys
from pathlib import Path

import glossary
from filter import UNCLASSIFIED, read_keywords
from pick import select_day

HERE = Path(__file__).parent
ARTICLE_DIR = HERE / "data" / "articles"
DOCS_DIR = HERE / "docs"
STATUS_FILE = HERE / "data" / "fetch_status.json"

STYLE = """
  body { margin:0 auto; padding:24px; max-width:900px; background:#fbfbfa; color:#1c1b19;
    font-family:"Pretendard","Apple SD Gothic Neo",system-ui,sans-serif; line-height:1.6;
    word-break:keep-all; }
  h1 { font-size:24px; margin:0; }
  nav { display:flex; gap:20px; margin:14px 0 20px; padding-bottom:8px;
    border-bottom:1px solid #cfccc4; }
  nav a { color:#94908a; text-decoration:none; padding-bottom:8px; margin-bottom:-9px; }
  nav a.on { color:#1c1b19; font-weight:700; border-bottom:2px solid #1c1b19; }
  .meta { color:#63605a; font-size:14px; margin:6px 0 20px; }
  .card { background:#fff; border:1px solid #e4e2dd; border-radius:8px;
    padding:16px 18px; margin-bottom:12px; }
  .cat { font-size:12px; color:#94908a; }
  .tier { font-size:12px; color:#0a7d3c; }
  .card h2 { font-size:17px; margin:4px 0 6px; }
  .sum { color:#63605a; font-size:14px; margin:0; }
  .src { font-size:12px; color:#94908a; margin-top:10px; }
  .src a { color:#63605a; }
  .none { color:#94908a; }
  a.term { color:#0b5fff; text-decoration:none; border-bottom:1px dashed currentColor; }
  a.term:hover { background:#eef3ff; }
  .entry { background:#fff; border:1px solid #e4e2dd; border-radius:8px;
    padding:18px 20px; margin-bottom:12px; scroll-margin-top:16px; }
  .entry:target { border-color:#0b5fff; box-shadow:0 0 0 3px #eef3ff; }
  .ehead { display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; }
  .entry h2 { font-size:19px; margin:0; }
  .en { font-size:13px; color:#94908a; }
  .entry .cat { font-size:11px; background:#f2f1ee; padding:2px 8px; border-radius:99px; }
  .def { color:#63605a; font-size:14px; margin:8px 0 0; }
  .entry .meta { font-size:12px; color:#94908a; margin:12px 0 0;
    padding-top:10px; border-top:1px solid #e4e2dd; }
  .entry .meta a { color:#63605a; }
  footer { margin-top:32px; padding-top:14px; border-top:1px solid #e4e2dd;
    font-size:12px; color:#94908a; }
  .chips { display:flex; gap:7px; flex-wrap:wrap; margin:0 0 18px; }
  .chip { font-size:13px; padding:5px 12px; border-radius:99px; background:#fff;
    border:1px solid #cfccc4; color:#63605a; cursor:pointer; }
  .chip.on { background:#1c1b19; color:#fff; border-color:#1c1b19; font-weight:600; }
  .chip.empty { color:#c4c1ba; cursor:default; }
  .chip .n { opacity:.55; margin-left:5px; }
  .days { margin:22px 0 0; font-size:13px; }
  .days a { color:#63605a; margin-right:10px; white-space:nowrap; }
  .days b { color:#1c1b19; margin-right:10px; }
"""

PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{style}</style>
</head>
<body>
<h1>반도체 뉴스 데일리</h1>
<nav>
  <a class="{news_on}" href="{prefix}index.html">뉴스</a>
  <a class="{concept_on}" href="{prefix}concepts.html">개념 {term_count}</a>
</nav>
<div class="meta">{meta}</div>
{chips}
{body}
{days}
<footer>출처 data/sources.md · 개념 설명은 출처를 확인해 넣습니다.<br>
이 페이지는 투자 조언이 아닙니다.</footer>
<script>
document.addEventListener('click', function (e) {{
  var chip = e.target.closest('.chip:not(.empty)');
  if (!chip) return;
  var want = chip.dataset.cat;
  document.querySelectorAll('.chip').forEach(function (c) {{
    c.classList.toggle('on', c === chip);
  }});
  document.querySelectorAll('.card').forEach(function (card) {{
    card.hidden = want !== '' && card.dataset.cat !== want;
  }});
}});
</script>
</body>
</html>
"""

CARD = """<div class="card" data-cat="{category}">
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


def category_chips(picked: list[dict]) -> str:
    """카테고리 칩. 0건인 것도 보여준다 — 오늘 무엇이 비었는지가 정보다."""
    counts: dict[str, int] = {}
    for a in picked:
        counts[a.get("category", UNCLASSIFIED)] = counts.get(a.get("category", UNCLASSIFIED), 0) + 1

    names = [*read_keywords()[2], UNCLASSIFIED]  # keywords.md 의 순서를 그대로 쓴다
    chips = [f'<span class="chip on" data-cat="">전체<span class="n">{len(picked)}</span></span>']
    for name in names:
        n = counts.get(name, 0)
        empty = "" if n else " empty"
        chips.append(
            f'<span class="chip{empty}" data-cat="{html.escape(name, quote=True)}">'
            f'{html.escape(name)}<span class="n">{n}</span></span>'
        )
    return f'<div class="chips">{"".join(chips)}</div>'


def day_links(current: str = "") -> str:
    """지난 날짜 줄. 오늘 기사가 적은 날 다른 날로 갈 길이 필요하다."""
    days = sorted((p.stem for p in ARTICLE_DIR.glob("*.json") if "." not in p.stem), reverse=True)[:14]
    items = "".join(
        f"<b>{d[5:]}</b>" if d == current else f'<a href="{d}.html">{d[5:]}</a>'
        for d in days
    )
    return f'<div class="days">지난 날짜 {items}</div>' if items else ""


def render_news(day: str, terms: list[dict]) -> str:
    """하루치 목록 HTML."""
    picked, _, _ = select_day(day)
    ok, total = _status()

    if picked:
        body = "".join(
            CARD.format(
                category=html.escape(a.get("category", "미분류")),
                tier=html.escape(a.get("tier", "")),
                title=glossary.link_terms(html.escape(a["title"]), terms),
                summary=glossary.link_terms(html.escape(a["summary"][:200]), terms),
                source=html.escape(a["source"]),
                published=html.escape((a.get("published") or "—")[:16].replace("T", " ")),
                url=html.escape(a["url"], quote=True),
            )
            for a in picked
        )
    else:
        # '기사 없음' 과 '수집 실패' 는 다르다 (CLAUDE.md).
        body = '<p class="none">이 날은 반도체 관련 기사가 없습니다. (수집은 정상이었습니다)</p>'

    return PAGE.format(
        title=f"반도체 뉴스 데일리 — {day}",
        style=STYLE,
        news_on="on",
        concept_on="",
        prefix="",
        term_count=len(terms),
        meta=f"{day} · {len(picked)}건 · 수집 {ok}곳 중 {total}곳 정상",
        body=body,
        chips=category_chips(picked) if picked else "",
        days=day_links(day),
    )


def render_concepts(terms: list[dict]) -> str:
    """개념 페이지 HTML."""
    body = glossary.render_entries(terms) if terms else '<p class="none">등재된 개념이 없습니다.</p>'
    return PAGE.format(
        title="개념 — 반도체 뉴스 데일리",
        style=STYLE,
        news_on="",
        concept_on="on",
        prefix="",
        term_count=len(terms),
        meta=f"{len(terms)}개 · 설명마다 출처와 확인일이 붙어 있습니다",
        body=body,
        chips="",
        days="",
    )


def latest_day() -> str:
    days = sorted(p.stem for p in ARTICLE_DIR.glob("*.json") if "." not in p.stem)
    if not days:
        raise FileNotFoundError("data/articles/ 가 비었습니다. 먼저 python fetch.py 를 실행하세요.")
    return days[-1]


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    DOCS_DIR.mkdir(exist_ok=True)
    terms = glossary.read_terms()
    print(f"개념 {len(terms)}개 — {', '.join(t['term'] for t in terms)}")

    if argv and argv[0] == "--all":
        days = sorted((p.stem for p in ARTICLE_DIR.glob("*.json") if "." not in p.stem), reverse=True)[:14]
    else:
        days = [argv[0] if argv else latest_day()]

    for d in days:
        (DOCS_DIR / f"{d}.html").write_text(render_news(d, terms), encoding="utf-8")
    print(f"뉴스 {len(days)}일치 → docs/*.html")

    newest = latest_day()
    if newest in days:
        (DOCS_DIR / "index.html").write_text(render_news(newest, terms), encoding="utf-8")
        print(f"{newest} → docs/index.html")

    (DOCS_DIR / "concepts.html").write_text(render_concepts(terms), encoding="utf-8")
    print("     → docs/concepts.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
