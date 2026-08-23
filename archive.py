"""RSS 가 못 주는 과거 기사를 목록 페이지에서 가져온다. 모델을 부르지 않는다.

fetch.py(RSS)는 최근분만 준다. 몇 달 전 사건을 '이어지는 흐름' 재료로 쓰려면
목록 페이지를 거슬러 올라가야 한다 (docs/slices/03-과거-기사-수집.md).

기사별 원문 페이지는 열지 않는다 — 목록에 제목·요약·날짜가 다 있다.
목록에는 시각이 없어 published 는 T00:00:00 으로 두고 원문 표기를 published_raw 에 남긴다.
"""

import html as html_mod
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from fetch import HEADERS
from filter import filter_articles

HERE = Path(__file__).parent
ARTICLE_DIR = HERE / "data" / "articles"

PER_MONTH = 5
PAUSE = 1.5  # 목록 페이지 사이 쉬는 시간(초). 남의 서버다
# 한 사이트에서 넘길 목록 페이지 수 상한.
# 더일렉은 쪽당 6~9일치라 6개월(약 180일)을 보려면 최소 25쪽이 필요하다.
MAX_PAGES = 30

THELEC_LIST = (
    "https://www.thelec.kr/news/articleList.html"
    "?page={page}&sc_section_code=S1N2&view_type=sm"
)
DIGEST_LIST = "https://www.semiconductor-digest.com/category/packaging/page/{page}/"

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def _clean(raw: str) -> str:
    return _SPACE.sub(" ", html_mod.unescape(_TAG.sub(" ", raw))).strip()


# --- 파싱 (네트워크 없이 검사 가능한 부분) ---------------------------------

_THELEC_ITEM = re.compile(r'<li class="altlist-webzine-item".*?</li>', re.S)
_THELEC_LINK = re.compile(
    r'<H2 class="altlist-subject".*?<a href="([^"]+)".*?>(.*?)</a>', re.S | re.I
)
_THELEC_SUM = re.compile(r'<p class="altlist-summary">(.*?)</p>', re.S)
# 과거 쪽은 '2025-02-06', 최근 쪽은 '08-21 18:08' — 최근 것에는 연도가 없다.
_THELEC_FULL_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_THELEC_SHORT_DATE = re.compile(r"\b(\d{2})-(\d{2}) \d{2}:\d{2}\b")


def _thelec_date(block: str) -> tuple[str, str] | None:
    """(저장할 날짜, 원문 표기). 못 읽으면 None — 추측해서 채우지 않는다."""
    full = _THELEC_FULL_DATE.search(block)
    if full:
        return full.group(0), full.group(0)

    short = _THELEC_SHORT_DATE.search(block)
    if not short:
        return None

    # 연도가 없다. 올해로 보되, 그러면 미래가 되는 경우는 작년으로 본다.
    today = datetime.now()
    month, day = int(short.group(1)), int(short.group(2))
    year = today.year
    try:
        if datetime(year, month, day).date() > today.date():
            year -= 1
    except ValueError:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}", short.group(0)


def parse_thelec_list(page_html: str) -> list[dict]:
    """더일렉 목록 페이지에서 기사를 뽑는다."""
    out = []
    for block in _THELEC_ITEM.findall(page_html):
        link = _THELEC_LINK.search(block)
        date = _thelec_date(block)
        if not link or not date:
            continue
        day, raw_date = date
        summary = _THELEC_SUM.search(block)
        out.append(
            _article(
                url=link.group(1),
                title=_clean(link.group(2)),
                summary=_clean(summary.group(1)) if summary else "",
                day=day,
                raw_date=raw_date,
                source="더일렉 반도체",
                lang="한국어",
                offset="+09:00",
            )
        )
    return out


_DIGEST_ITEM = re.compile(r'<div class="post style3 post-\d+.*?(?=<div class="post style3|\Z)', re.S)
_DIGEST_LINK = re.compile(r'<h5 class="entry-title".*?<a href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
_DIGEST_DATE = re.compile(r'<div class="time">([^<]+)</div>')
_DIGEST_SUM = re.compile(r'<div class="post-content entry-content[^"]*">(.*?)</div>', re.S)


def parse_digest_list(page_html: str) -> list[dict]:
    """Semiconductor Digest 목록 페이지에서 기사를 뽑는다."""
    out = []
    for block in _DIGEST_ITEM.findall(page_html):
        link = _DIGEST_LINK.search(block)
        date = _DIGEST_DATE.search(block)
        if not link or not date:
            continue
        raw_date = date.group(1).strip()
        try:
            day = datetime.strptime(raw_date, "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            continue  # 날짜를 못 읽으면 버린다. 추측하지 않는다
        summary = _DIGEST_SUM.search(block)
        out.append(
            _article(
                url=link.group(1),
                title=_clean(link.group(2)),
                summary=_clean(summary.group(1)) if summary else "",
                day=day,
                raw_date=raw_date,
                source="Semiconductor Digest (패키징)",
                lang="영어",
                offset="+00:00",
            )
        )
    return out


def _article(*, url, title, summary, day, raw_date, source, lang, offset) -> dict:
    """fetch.py 가 만드는 것과 같은 모양으로 맞춘다."""
    return {
        "url": url,
        "title": title,
        "summary": summary,
        "author": "",
        "published": f"{day}T00:00:00{offset}",
        "published_raw": raw_date,
        "fetched": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": source,
        "tier": "[2차]",
        "lang": lang,
    }


def pick_monthly(articles: list[dict], per_month: int = PER_MONTH) -> list[dict]:
    """달마다 최대 per_month 건. 한 날에 몰리지 않게 고르게 벌려서 고른다.

    5건이 같은 날에 몰리면 '이어지는 흐름' 재료로 쓸모가 없다.
    모자라면 있는 만큼만 — 억지로 채우지 않는다.
    """
    by_month: dict[str, list[dict]] = {}
    for a in articles:
        by_month.setdefault(a["published"][:7], []).append(a)

    picked: list[dict] = []
    for month in sorted(by_month):
        items = sorted(by_month[month], key=lambda a: a["published"])
        if len(items) <= per_month:
            picked.extend(items)
            continue
        step = len(items) / per_month
        picked.extend(items[int(i * step)] for i in range(per_month))
    return picked


# --- 수집 -------------------------------------------------------------------


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _pages_hint(list_url: str, parser, target: str) -> int:
    """목표 달에 닿는 목록 페이지 번호를 이분 탐색으로 찾는다."""
    lo, hi = 1, 400
    while lo < hi:
        mid = (lo + hi) // 2
        try:
            items = parser(_get(list_url.format(page=mid)))
        except Exception:
            return lo
        time.sleep(PAUSE)
        if not items:
            hi = mid
            continue
        newest = max(a["published"][:7] for a in items)
        if newest > target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def collect(start: str, end: str, only: str = "") -> tuple[list[dict], dict[str, str]]:
    """두 사이트에서 start~end 달의 기사를 모은다.

    only 를 주면 이름에 그 말이 든 곳만 돈다 — 한 곳만 다시 받을 때 쓴다.
    """
    status: dict[str, str] = {}
    everything: list[dict] = []

    for label, list_url, parser in (
        ("더일렉 반도체", THELEC_LIST, parse_thelec_list),
        ("Semiconductor Digest (패키징)", DIGEST_LIST, parse_digest_list),
    ):
        if only and only.lower() not in label.lower():
            continue
        print(f"  {label} — 시작 쪽 찾는 중…", flush=True)
        try:
            first = _pages_hint(list_url, parser, end)
        except Exception as e:  # 여기서 막히면 이 사이트만 건너뛴다
            status[label] = f"실패 (시작 쪽 탐색: {e})"
            print(f"  {label:<32} {status[label]}", flush=True)
            continue

        articles, state = _crawl_from(list_url, parser, start, end, first)
        status[label] = state
        everything.extend(articles)
        print(f"  {label:<32} {state}  ({len(articles)}건)", flush=True)

    return everything, status


def _crawl_from(list_url, parser, start, end, first_page) -> tuple[list[dict], str]:
    """찾아낸 시작 쪽부터 과거로 넘기며 모은다."""
    collected: list[dict] = []
    page = first_page
    reached_older = False

    while page < first_page + MAX_PAGES:
        try:
            items = parser(_get(list_url.format(page=page)))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            return collected, f"실패 (page={page}, {e})"

        if not items:
            return collected, f"0건 파싱됨 (page={page}) — 목록 구조가 바뀌었는지 확인할 것"

        months = [a["published"][:7] for a in items]
        collected.extend(a for a, m in zip(items, months) if start <= m <= end)

        if min(months) < start:
            reached_older = True
            break
        page += 1
        time.sleep(PAUSE)

    return collected, "정상" if reached_older else f"상한 도달 ({MAX_PAGES}쪽)"


def save(articles: list[dict]) -> tuple[dict[str, int], int]:
    """발행일별 파일에 합친다. 이미 있는 원문 링크는 건너뛴다 (fetch.py 와 같은 규칙)."""
    ARTICLE_DIR.mkdir(parents=True, exist_ok=True)
    by_day: dict[str, list[dict]] = {}
    for a in articles:
        by_day.setdefault(a["published"][:10], []).append(a)

    added: dict[str, int] = {}
    skipped = 0
    for day, fresh in sorted(by_day.items()):
        path = ARTICLE_DIR / f"{day}.json"
        existing = json.loads(path.read_text(encoding="utf-8"))["articles"] if path.exists() else []
        seen = {a["url"] for a in existing}

        new = []
        for a in fresh:
            if a["url"] in seen:
                skipped += 1
                continue
            seen.add(a["url"])
            new.append(a)

        if not new:
            continue
        merged = existing + new
        merged.sort(key=lambda a: a["published"] or "", reverse=True)
        path.write_text(
            json.dumps({"date": day, "articles": merged}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        added[day] = len(new)
    return added, skipped


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    if len(argv) not in (2, 3):
        print("사용법: python archive.py <시작달> <끝달> [사이트]"
              "   예: python archive.py 2025-11 2026-04 더일렉", file=sys.stderr)
        return 1

    start, end = argv[0], argv[1]
    only = argv[2] if len(argv) == 3 else ""
    print(f"{start} ~ {end} 과거 기사 수집 (달마다 최대 {PER_MONTH}건)"
          + (f" · {only} 만" if only else ""))

    raw, status = collect(start, end, only)
    print(f"\n받은 기사 {len(raw)}건")

    kept, dropped = filter_articles(raw)
    print(f"  반도체 관련 {len(kept)}건 · 버림 {len(dropped)}건")

    picked = pick_monthly(kept)
    added, skipped = save(picked)

    print(f"\n달별 확보 건수 (요청 {PER_MONTH}건)")
    months: dict[str, int] = {}
    for a in picked:
        months[a["published"][:7]] = months.get(a["published"][:7], 0) + 1
    month = start
    while month <= end:
        n = months.get(month, 0)
        mark = "" if n >= PER_MONTH else "   ← 못 채움"
        print(f"  {month}  {n}건{mark}")
        y, m = int(month[:4]), int(month[5:])
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        month = f"{y:04d}-{m:02d}"

    print(f"\n새로 저장 {sum(added.values())}건 ({len(added)}일치) · 이미 있어 건너뜀 {skipped}건")
    failed = {k: v for k, v in status.items() if v != "정상"}
    if failed:
        print("\n수집 실패·미완:")
        for k, v in failed.items():
            print(f"  {k} — {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
