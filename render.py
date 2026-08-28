"""저장한 기사를 목록으로 내고, 개념 페이지와 날짜 링크를 함께 만든다.

기사 글 속의 용어에는 개념 페이지로 가는 링크를 건다.
카테고리 칩을 누르면 그 분야만 남는다.
"""

import html
import json
import sys
from pathlib import Path

import companies
import glossary
from filter import UNCLASSIFIED, filter_articles, read_keywords
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
  .by-ai { font-size:11px; color:#94908a; border:1px solid #e4e2dd; border-radius:99px;
    padding:1px 7px; margin-left:6px; white-space:nowrap; vertical-align:1px; }
  .src { font-size:12px; color:#94908a; margin-top:10px; }
  .src a { color:#63605a; }
  .none { color:#94908a; }
  a.term { color:#0b5fff; text-decoration:none; border-bottom:1px dashed currentColor; }
  a.term:hover { background:#eef3ff; }
  details.thread { border-top:1px solid #e4e2dd; padding-top:10px; margin-top:10px; }
  details.thread summary { cursor:pointer; font-size:13px; color:#0b5fff; list-style:none;
    font-weight:600; display:flex; align-items:center; gap:6px; }
  details.thread summary::-webkit-details-marker { display:none; }
  details.thread summary .arw { transition:transform .15s; display:inline-block; }
  details.thread[open] summary .arw { transform:rotate(90deg); }
  .rail { position:relative; margin:14px 0 0; padding-left:74px; }
  .rail::before { content:""; position:absolute; left:60px; top:8px; bottom:8px;
    width:2px; background:#cfccc4; }
  .step { position:relative; margin-bottom:14px; }
  .step:last-child { margin-bottom:0; }
  .step .when { position:absolute; left:-74px; top:-1px; width:48px; text-align:right;
    font-size:12px; color:#94908a; font-variant-numeric:tabular-nums; line-height:1.5; }
  .step::before { content:""; position:absolute; left:-16px; top:5px; width:9px; height:9px;
    border-radius:50%; background:#b8b4ac; border:2px solid #fff; }
  .step .what a { font-size:13.5px; color:#63605a; line-height:1.5; text-decoration:none; }
  .step .what a:hover { text-decoration:underline; }
  @media (max-width:600px) {
    .rail { padding-left:0; } .rail::before { left:5px; }
    .step { padding-left:22px; }
    .step .when { position:static; width:auto; text-align:left; display:block; margin-bottom:2px; }
    .step::before { left:1px; top:6px; }
  }
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
  .days-head { color:#94908a; margin-bottom:6px; }
  .days .month { display:flex; align-items:baseline; gap:8px; flex-wrap:wrap;
    padding:4px 0; border-top:1px solid #eeece7; }
  .days .ym { color:#94908a; font-variant-numeric:tabular-nums; min-width:62px; }
  .days a { color:#63605a; white-space:nowrap; text-decoration:none; }
  .days a:hover { text-decoration:underline; }
  .days b { color:#1c1b19; }
  .cgroup { margin:0 0 22px; }
  .cgroup h2 { font-size:15px; margin:0 0 8px; padding-bottom:6px;
    border-bottom:1px solid #e4e2dd; }
  .cgroup h2 .n { font-size:12px; color:#94908a; margin-left:7px; font-weight:400; }
  .colist { display:flex; gap:8px; flex-wrap:wrap; }
  a.co { font-size:14px; padding:7px 13px; border-radius:8px; background:#fff;
    border:1px solid #e4e2dd; color:#1c1b19; text-decoration:none; }
  a.co:hover { border-color:#0b5fff; color:#0b5fff; }
  a.co .n { font-size:12px; color:#94908a; margin-left:6px; }
  .profile { background:#fff; border:1px solid #e4e2dd; border-radius:8px;
    padding:18px 20px; margin-bottom:18px; }
  .ctags { display:flex; gap:6px; flex-wrap:wrap; margin:10px 0 0; }
  .ctag { font-size:11px; background:#f2f1ee; color:#63605a; padding:2px 9px;
    border-radius:99px; }
  .colist-articles { background:#fff; border:1px solid #e4e2dd; border-radius:8px;
    padding:6px 18px; }
  .carow { display:flex; gap:14px; align-items:baseline; padding:9px 0;
    border-bottom:1px solid #f0eeea; }
  .carow:last-child { border-bottom:none; }
  .carow .when { font-size:12px; color:#94908a; font-variant-numeric:tabular-nums;
    white-space:nowrap; }
  .carow .what a { color:#1c1b19; text-decoration:none; font-size:14px; }
  .carow .what a:hover { text-decoration:underline; }
  .carow .src { font-size:11px; color:#94908a; margin-left:6px; }
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
  <a class="{company_on}" href="{prefix}companies.html">기업 {company_count}</a>
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
  <p class="sum">{summary}{made_by}</p>
  {thread}
  <div class="src">{source} · 발행 {published} · <a href="{url}">원문</a></div>
</div>
"""

THREAD = """<details class="thread" open>
  <summary><span class="arw">›</span>이어지는 흐름 {n}건</summary>
  <div class="rail">{steps}</div>
</details>
"""

STEP = """<div class="step">
  <span class="when">{when}</span>
  <div class="what"><a href="{url}">{title}</a></div>
</div>
"""


def load_related(day: str) -> dict[str, list[dict]]:
    """<날짜>.linked.json 에서 URL → 이어지는 흐름 목록. 파일이 없으면 빈 dict (에러 아님)."""
    path = ARTICLE_DIR / f"{day}.linked.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {a["url"]: a.get("related", []) for a in data["articles"]}


def load_extracted(day: str) -> dict[str, dict]:
    """<날짜>.extracted.json 에서 URL → 뽑아 둔 결과. 파일이 없으면 빈 dict (에러 아님)."""
    path = ARTICLE_DIR / f"{day}.extracted.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {a["url"]: a for a in data["articles"]}


def choose_summary(article: dict, extracted: dict[str, dict]) -> tuple[str, bool]:
    """카드에 보여줄 요약. 돌려주는 것 — (보여줄 글, 모델이 만든 것인가)

    한국어 요약이 있으면 그것을 쓴다. 없거나 비었으면 원래 요약으로 되돌린다 —
    빈 카드를 만들지 않는다.
    """
    summary_ko = (extracted.get(article["url"]) or {}).get("summary_ko")
    if summary_ko:
        return summary_ko, True
    return article["summary"], False


def render_thread(related: list[dict]) -> str:
    """흐름이 없으면 빈 문자열. link.py 는 최신순으로 주지만 화면은 오래된 것부터 보여준다."""
    if not related:
        return ""
    oldest_first = sorted(related, key=lambda r: r["date"])
    steps = "".join(
        STEP.format(
            when=html.escape(r["date"][5:] or r["date"]),
            title=html.escape(r["title"]),
            url=html.escape(r["url"], quote=True),
        )
        for r in oldest_first
    )
    return THREAD.format(n=len(related), steps=steps)


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


def article_days() -> list[str]:
    """기사가 있는 모든 날짜. 파생 파일(.filtered/.selected/.linked)은 뺀다.

    자르지 않는다 — 14일로 자르면 과거 기사에 갈 길이 아예 없다 (슬라이스 04).
    """
    return sorted(p.stem for p in ARTICLE_DIR.glob("*.json") if "." not in p.stem)


def render_day_links(days: list[str], current: str = "") -> str:
    """지난 날짜 줄. 달별로 묶는다 — 125개를 한 줄에 늘어놓으면 못 읽는다."""
    if not days:
        return ""

    by_month: dict[str, list[str]] = {}
    for d in sorted(days, reverse=True):
        by_month.setdefault(d[:7], []).append(d)

    rows = []
    for month in sorted(by_month, reverse=True):
        items = "".join(
            f"<b>{d[8:]}</b>" if d == current else f'<a href="{d}.html">{d[8:]}</a>'
            for d in by_month[month]
        )
        rows.append(f'<div class="month"><span class="ym">{month}</span>{items}</div>')

    return f'<div class="days"><div class="days-head">지난 날짜</div>{"".join(rows)}</div>'


def day_links(current: str = "") -> str:
    return render_day_links(article_days(), current)


COMPANY_ROW = """<div class="carow">
  <span class="when">{date}</span>
  <div class="what"><a href="{url}">{title}</a> <span class="src">{source}</span></div>
</div>
"""

MAX_COMPANY_ARTICLES = 50


def _page(*, title: str, tab: str, terms: list[dict], meta: str, body: str,
          chips: str = "", days: str = "", prefix: str = "", companies_total: int = 0) -> str:
    """페이지 껍데기. 탭이 늘어도 호출부를 하나씩 안 고치게 기본값을 둔다."""
    return PAGE.format(
        title=title,
        style=STYLE,
        news_on="on" if tab == "news" else "",
        concept_on="on" if tab == "concept" else "",
        company_on="on" if tab == "company" else "",
        prefix=prefix,
        term_count=len(terms),
        company_count=companies_total or len(companies.read_companies()),
        meta=meta,
        body=body,
        chips=chips,
        days=days,
    )


def _render_card(a: dict, terms: list[dict], related_map: dict, extracted: dict) -> str:
    """기사 카드 하나."""
    summary, by_model = choose_summary(a, extracted)
    # 뽑아 둔 분류가 있으면 그것을 쓴다 — extract.py 가 모델 답을 코드로 걸러 둔 값이다.
    category = (extracted.get(a["url"]) or {}).get("category") or a.get("category", UNCLASSIFIED)

    return CARD.format(
        category=html.escape(category),
        tier=html.escape(a.get("tier", "")),
        title=glossary.link_terms(html.escape(a["title"]), terms),
        summary=glossary.link_terms(html.escape(summary[:300]), terms),
        # 모델이 쓴 문장이다. 기자가 쓴 것처럼 보이지 않게 밝힌다.
        made_by=' <span class="by-ai">AI 요약</span>' if by_model else "",
        thread=render_thread(related_map.get(a["url"], [])),
        source=html.escape(a["source"]),
        published=html.escape((a.get("published") or "—")[:16].replace("T", " ")),
        url=html.escape(a["url"], quote=True),
    )


def render_news(day: str, terms: list[dict]) -> str:
    """하루치 목록 HTML."""
    picked, _, _ = select_day(day)
    ok, total = _status()
    related_map = load_related(day)
    extracted = load_extracted(day)

    if picked:
        body = "".join(
            _render_card(a, terms, related_map, extracted) for a in picked
        )
    else:
        # '기사 없음' 과 '수집 실패' 는 다르다 (CLAUDE.md).
        body = '<p class="none">이 날은 반도체 관련 기사가 없습니다. (수집은 정상이었습니다)</p>'

    return _page(
        title=f"반도체 뉴스 데일리 — {day}",
        tab="news",
        terms=terms,
        meta=f"{day} · {len(picked)}건 · 수집 {ok}곳 중 {total}곳 정상",
        body=body,
        chips=category_chips(picked) if picked else "",
        days=day_links(day),
    )


def render_concepts(terms: list[dict]) -> str:
    """개념 페이지 HTML."""
    body = glossary.render_entries(terms) if terms else '<p class="none">등재된 개념이 없습니다.</p>'
    return _page(
        title="개념 — 반도체 뉴스 데일리",
        tab="concept",
        terms=terms,
        meta=f"{len(terms)}개 · 설명마다 출처와 확인일이 붙어 있습니다",
        body=body,
    )


def render_companies(terms: list[dict], rows: list[dict], counts: dict[str, int]) -> str:
    """기업 목록 페이지. 분류별로 회사를 늘어놓는다."""
    body = companies.render_groups(companies.by_category(rows), counts)
    with_desc = sum(1 for c in rows if c["description"])
    return _page(
        title="기업 — 반도체 뉴스 데일리",
        tab="company",
        terms=terms,
        companies_total=len(rows),
        meta=f"{len(rows)}곳 · 설명이 붙은 곳 {with_desc}곳 · 숫자는 그 회사가 나온 기사 수입니다",
        body=body,
    )


def render_company(terms: list[dict], company: dict, articles: list[dict],
                   companies_total: int) -> str:
    """회사 하나의 페이지. 그 회사가 나온 기사만 최신순으로 모은다."""
    shown = articles[:MAX_COMPANY_ARTICLES]
    if shown:
        rows = "".join(
            COMPANY_ROW.format(
                date=html.escape((a.get("published") or "")[:10]),
                title=glossary.link_terms(html.escape(a["title"]), terms, page_prefix="../"),
                source=html.escape(a["source"]),
                url=html.escape(a["url"], quote=True),
            )
            for a in shown
        )
        listing = f'<div class="colist-articles">{rows}</div>'
    else:
        listing = '<p class="none">아직 이 회사가 나온 기사가 없습니다.</p>'

    more = (
        f'<p class="none">기사 {len(articles)}건 중 최근 {len(shown)}건만 보여줍니다.</p>'
        if len(articles) > len(shown)
        else ""
    )
    return _page(
        title=f"{company['name']} — 반도체 뉴스 데일리",
        tab="company",
        terms=terms,
        companies_total=companies_total,
        prefix="../",
        meta=f"기사 {len(articles)}건",
        body=companies.render_profile(company) + listing + more,
    )


def collect_company_articles(rows: list[dict]) -> dict[str, list[dict]]:
    """회사마다 그 회사가 나온 기사를 최신순으로 모은다.

    거른 것(반도체 관련) 기준이다 — 전체 수집분은 채용·가전이 섞이고,
    하루 10건 선별분만 보면 회사 페이지가 비어 보인다 (슬라이스 07).
    """
    company_map = companies.read_company_map()
    found: dict[str, list[dict]] = {c["name"]: [] for c in rows}

    for day in article_days():
        raw = json.loads((ARTICLE_DIR / f"{day}.json").read_text(encoding="utf-8"))["articles"]
        kept, _ = filter_articles(raw)
        for a in kept:
            for name in companies.companies_mentioned(f"{a['title']} {a['summary']}", company_map):
                if name in found:
                    found[name].append(a)

    for arts in found.values():
        arts.sort(key=lambda a: a.get("published") or "", reverse=True)
    return found


def latest_day() -> str:
    days = article_days()
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
        days = sorted(article_days(), reverse=True)  # 자르지 않는다 (슬라이스 04)
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

    rows = companies.read_companies()
    by_company = collect_company_articles(rows)
    counts = {name: len(arts) for name, arts in by_company.items()}

    (DOCS_DIR / "companies.html").write_text(
        render_companies(terms, rows, counts), encoding="utf-8"
    )
    company_dir = DOCS_DIR / "company"
    company_dir.mkdir(exist_ok=True)
    for c in rows:
        (company_dir / f"{c['slug']}.html").write_text(
            render_company(terms, c, by_company.get(c["name"], []), len(rows)),
            encoding="utf-8",
        )
    print(f"기업 {len(rows)}곳 → docs/companies.html · docs/company/*.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
