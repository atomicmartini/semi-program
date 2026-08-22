"""RSS 수집. data/sources.md 에 적힌 곳에서 기사를 받아 발행일별로 저장한다.

주소를 코드에 박지 않는다 (CLAUDE.md). 늘리고 줄이는 일은 data/sources.md 에서 한다.
표준 라이브러리만 쓴다.
"""

import html
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).parent
SOURCES_FILE = HERE / "data" / "sources.md"
ARTICLE_DIR = HERE / "data" / "articles"
STATUS_FILE = HERE / "data" / "fetch_status.json"

# 이 표들에 적힌 곳만 수집한다. '후보'·'안 쓰는 곳'은 건너뛴다.
USED_SECTIONS = ("## 쓰는 곳", "## 기업 뉴스룸")

# 헤더를 채우지 않으면 403 으로 막는 곳이 있다 (3D InCites, Intel Newsroom).
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "ko,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "close",
}
TIMEOUT = 25


def read_sources() -> list[dict]:
    """data/sources.md 의 '쓰는 곳'·'기업 뉴스룸' 표에서 수집처를 읽는다."""
    text = SOURCES_FILE.read_text(encoding="utf-8")
    sources, section = [], None

    for line in text.splitlines():
        if line.startswith("## "):
            section = line.strip()
            continue
        # 제목에 설명이 붙는 경우가 있어 앞부분만 맞춰 본다 ('## 기업 뉴스룸 — [공식] 등급').
        if not section or not section.startswith(USED_SECTIONS) or not line.startswith("|"):
            continue

        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in ("이름", "---"):
            continue

        url = cells[1].strip("`")
        if not url.startswith("http"):
            continue
        sources.append({"name": cells[0], "url": url, "lang": cells[2], "tier": cells[3].strip("`")})

    return sources


_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
# 워드프레스가 요약 끝에 붙이는 꼬리표. 내용이 아니라 사이트 광고다.
_WP_TAIL = re.compile(r"\s*The post .*? appeared first on .*?\.?\s*$", re.I)


def _clean(raw: str) -> str:
    """피드가 담아 보내는 HTML 과 꼬리표를 걷어낸다."""
    text = html.unescape(_TAG.sub(" ", raw))
    text = _WP_TAIL.sub("", text)
    return _SPACE.sub(" ", text).strip()


def _text(item: ET.Element, tag: str) -> str:
    el = item.find(tag)
    return _clean(el.text) if el is not None and el.text else ""


def parse_published(raw: str) -> str | None:
    """발행시각을 ISO 문자열로. 못 읽으면 None — 추측해서 채우지 않는다."""
    raw = raw.strip()
    if not raw:
        return None
    try:  # RFC 822 — 8곳 중 7곳
        return parsedate_to_datetime(raw).astimezone().isoformat(timespec="seconds")
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):  # 더일렉
        try:
            return datetime.strptime(raw, fmt).isoformat(timespec="seconds")
        except ValueError:
            continue
    return None


def fetch_feed(source: dict) -> tuple[list[dict], str]:
    """피드 하나를 받아 기사 목록과 상태를 돌려준다."""
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        req = urllib.request.Request(source["url"], headers=HEADERS)
        raw = urllib.request.urlopen(req, timeout=TIMEOUT).read()
        root = ET.fromstring(raw)
    except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError, OSError) as err:
        return [], f"실패: {type(err).__name__} {err}"

    items = root.findall(".//item")
    if not items:
        # HTTP 200 인데 기사가 0건인 피드가 있다. 정상으로 보이지만 죽은 것이다.
        return [], "응답은 왔으나 기사 0건"

    articles = []
    for it in items:
        link = _text(it, "link")
        if not link:
            continue
        raw_date = _text(it, "pubDate")
        articles.append(
            {
                "url": link,  # 고유 열쇠
                "title": _text(it, "title"),
                "summary": _text(it, "description"),
                "author": _text(it, "author"),
                "published": parse_published(raw_date),
                "published_raw": raw_date,
                "fetched": now,
                "source": source["name"],
                "tier": source["tier"],
                "lang": source["lang"],
            }
        )
    return articles, "정상"


def _day_of(article: dict) -> str:
    """저장할 날짜. 발행일이 없으면 수집일로 두고 published 는 None 으로 남긴다."""
    stamp = article["published"] or article["fetched"]
    return stamp[:10]


def fetch_articles(sources: list[dict] | None = None) -> tuple[dict[str, int], dict[str, str]]:
    """수집처를 돌며 기사를 발행일별 파일에 합친다.

    돌려주는 것 — (날짜별 새 기사 수, 출처별 상태)
    이미 있는 기사(원문 링크가 같은 것)는 건너뛴다.
    """
    sources = sources if sources is not None else read_sources()
    ARTICLE_DIR.mkdir(parents=True, exist_ok=True)

    by_day: dict[str, list[dict]] = {}
    status: dict[str, str] = {}

    for src in sources:
        articles, state = fetch_feed(src)
        status[src["name"]] = state
        print(f"  {src['name']:<24} {state}  ({len(articles)}건)", flush=True)
        for a in articles:
            by_day.setdefault(_day_of(a), []).append(a)

    added: dict[str, int] = {}
    for day, fresh in sorted(by_day.items()):
        path = ARTICLE_DIR / f"{day}.json"
        existing = json.loads(path.read_text(encoding="utf-8"))["articles"] if path.exists() else []
        seen = {a["url"] for a in existing}

        new = [a for a in fresh if a["url"] not in seen and not seen.add(a["url"])]
        if not new and path.exists():
            continue

        merged = existing + new
        merged.sort(key=lambda a: a["published"] or "", reverse=True)
        path.write_text(
            json.dumps({"date": day, "articles": merged}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        added[day] = len(new)

    STATUS_FILE.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "sources": status,
                "ok": sum(1 for s in status.values() if s == "정상"),
                "total": len(status),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return added, status


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    sources = read_sources()
    print(f"수집처 {len(sources)}곳")
    added, status = fetch_articles(sources)

    failed = {n: s for n, s in status.items() if s != "정상"}
    print(f"\n출처 {len(status)}곳 중 {len(status) - len(failed)}곳 정상")
    for name, state in failed.items():
        # 수집 실패를 조용히 넘기지 않는다 (CLAUDE.md).
        print(f"  ! {name} — {state}", file=sys.stderr)

    total_new = sum(added.values())
    if total_new == 0:
        print("새 기사 0건")
    else:
        print(f"새 기사 {total_new}건 — 날짜 {len(added)}개")
        for day, n in sorted(added.items(), reverse=True)[:8]:
            print(f"  {day}  +{n}")
    return 1 if len(failed) == len(status) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
