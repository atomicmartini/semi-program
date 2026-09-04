"""오늘 기사와 정말 이어지는 과거 기사를 잇는다.

    후보 = TF-IDF 상위 15건        (코드 · 놓치지 않는 일만 한다)
    이어짐 = 모델이 고른 것 AND 근거 인용구가 원문에 실제로 있다

후보 추리기와 판정을 나눈 이유는 docs/slices/11-이어지는흐름-모델판정.md 에 있다 —
유사도 지표는 '놓치지 않기'는 잘하고 '가려내기'는 못한다. 네 번 재보고 확인했다.
억지로 잇지 않는다 — 모델이 하나도 안 고르면 '이어지는 흐름 없음'.
"""

import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

from extract import BACKOFF, PAUSE, RETRIES, _call_model, _load_key, _parse_json, _verify_quote, should_retry
from filter import filter_articles

HERE = Path(__file__).parent
ARTICLE_DIR = HERE / "data" / "articles"

MAX_RELATED = 10      # 기사 하나당 화면에 보여줄 최대 건수. 사용자가 정한 값
SHORTLIST = 15        # 모델에게 넘길 후보 수. 늘리면 프롬프트가 길어진다
SUMMARY_CHARS = 300   # 프롬프트에 넣는 요약 길이. 더 자르면 판정 근거가 얇아진다

# 한글은 2글자 이상 덩어리, 영문·숫자는 낱말 단위. 한 글자는 증거가 못 된다.
_TOKEN = re.compile(r"[가-힣]{2,}|[a-zA-Z][a-zA-Z0-9\-]{1,}")


def tokens(text: str) -> list[str]:
    """TF-IDF 로 셀 말들. 한국어는 조사가 붙어('광연결로') 앞 2~3글자도 함께 본다."""
    out: list[str] = []
    for t in _TOKEN.findall(text.lower()):
        out.append(t)
        if not t.isascii() and len(t) > 2:
            out.extend(t[:n] for n in (2, 3) if len(t) > n)
    return out


def _vector(toks: list[str], idf: dict[str, float], default_idf: float) -> dict[str, float]:
    tf = Counter(toks)
    vec = {w: (1 + math.log(c)) * idf.get(w, default_idf) for w, c in tf.items()}
    norm = math.sqrt(sum(x * x for x in vec.values())) or 1.0
    return {w: x / norm for w, x in vec.items()}


def shortlist(article: dict, past: list[dict], limit: int = SHORTLIST) -> list[dict]:
    """모델에게 넘길 후보를 고른다. 판정이 아니라 '놓치지 않기' 다.

    흔한 말(`메모리`)은 문서빈도가 높아 가중치가 저절로 낮아진다 — 옛 기준이
    `메모리` 하나로 이어 버리던 문제를 수식이 대신 막는다.
    """
    if not past:
        return []

    docs = [tokens(f"{a['title']} {a['summary']}") for a in past]
    n = len(docs)
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    idf = {w: math.log(n / (1 + c)) for w, c in df.items()}
    default_idf = math.log(n) if n else 0.0

    today_vec = _vector(tokens(f"{article['title']} {article['summary']}"), idf, default_idf)
    scored = []
    for a, d in zip(past, docs):
        vec = _vector(d, idf, default_idf)
        score = sum(today_vec[w] * vec[w] for w in today_vec.keys() & vec.keys())
        if score > 0:
            scored.append((score, a))
    scored.sort(key=lambda x: -x[0])
    return [a for _, a in scored[:limit]]


def verify_links(parsed: dict | None, candidates: list[dict], limit: int = MAX_RELATED) -> list[dict]:
    """모델이 고른 연결 중 근거가 진짜인 것만 남긴다.

    인용구가 그 과거 기사 원문에 실제로 있는지 코드가 대조한다.
    없으면 그 연결만 버린다 — 지어낸 연결을 화면에 내지 않는다 (CLAUDE.md).
    """
    if not parsed:
        return []

    by_url = {c["url"]: c for c in candidates}
    out: list[dict] = []
    for item in parsed.get("links") or []:
        past = by_url.get((item.get("url") or "").strip())
        if past is None:
            continue  # 후보에 없던 주소를 지어낸 경우
        quote = (item.get("quote") or "").strip()
        if not _verify_quote(quote, f"{past['title']} {past['summary']}"):
            continue
        out.append(
            {
                "date": (past.get("published") or "")[:10],
                "title": past["title"],
                "url": past["url"],
                "reason": (item.get("reason") or "").strip(),
                "quote": quote,
            }
        )

    out.sort(key=lambda r: r["date"], reverse=True)
    return out[:limit]


PROMPT = """오늘 기사와 정말로 이어지는 과거 기사만 고르라. 다른 말은 하지 말고 JSON 으로만 답하라.

이어진다 = 같은 사안·같은 기술 흐름이 실제로 이어진다는 뜻이다.
같은 회사가 나온다거나 같은 분야라는 이유로 고르지 마라. 그건 이어지는 것이 아니다.
하나도 없으면 links 를 빈 배열로 둬라. 억지로 고르지 마라.
quote 는 그 과거 기사 본문에서 **그대로** 옮긴다. 지어내면 코드가 대조해서 버린다.
reason 은 과거 기사가 영어든 무엇이든 항상 한국어로 쓴다. quote 는 번역하지 말고 원문 언어 그대로 둔다.

{{"links": [{{"url": "과거 기사 주소", "reason": "왜 이어지는지 한 줄", "quote": "과거 기사 원문 문장"}}]}}

[오늘 기사]
제목: {title}
본문: {body}

[과거 기사 후보]
{candidates}
"""


def build_prompt(article: dict, candidates: list[dict]) -> str:
    """오늘 기사와 후보 목록을 모델에 넘길 프롬프트로 엮는다."""
    lines = []
    for c in candidates:
        date = (c.get("published") or "")[:10]
        lines.append(f"- url: {c['url']}\n  날짜: {date}\n  제목: {c['title']}\n  본문: {c['summary'][:SUMMARY_CHARS]}")
    return PROMPT.format(
        title=article["title"],
        body=article["summary"][:SUMMARY_CHARS],
        candidates="\n".join(lines),
    )


def judge(article: dict, candidates: list[dict], key: str, call=None) -> tuple[list[dict], str | None]:
    """후보를 모델에 한 번 넘겨 판정받는다. (연결 목록, 오류 원문)

    실패를 삼키지 않는다 — 실패하면 흐름을 비우고 이유를 돌려준다 (CLAUDE.md).
    """
    if not candidates:
        return [], None

    call = call or _call_model
    try:
        prompt = build_prompt(article, candidates)
    except Exception as e:  # noqa: BLE001 — 프롬프트를 못 만들면 재시도해도 소용없다. 그 기사만 비운다
        return [], f"{type(e).__name__} {e}"

    raw = None
    for attempt in range(RETRIES):
        try:
            raw = call(prompt, key)
            break
        except Exception as e:  # noqa: BLE001 — 어떤 실패든 그 기사만 비우고 넘어간다
            if attempt == RETRIES - 1 or not should_retry(e):
                return [], f"{type(e).__name__} {e}"
            time.sleep(BACKOFF * (attempt + 1))

    parsed = _parse_json(raw)
    if parsed is None:
        return [], "모델 출력을 JSON 으로 못 읽음"
    return verify_links(parsed, candidates), None


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
    past = _load_all_past(day)
    key = _load_key()

    linked = []
    for a in picked:
        candidates = shortlist(a, past)
        related, error = judge(a, candidates, key)
        entry = {**a, "related": related}
        if error:
            entry["link_error"] = error
        linked.append(entry)
        time.sleep(PAUSE)  # 몰아치면 429 가 난다
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

    failed = [a for a in linked if a.get("link_error")]
    for a in failed:
        # 판정 실패를 조용히 넘기지 않는다 (CLAUDE.md).
        print(f"  ! {a['title'][:40]} — 판정 실패: {a['link_error']}", file=sys.stderr)

    for a in with_flow:
        print(f"  · {a['title']}")
        for r in a["related"]:
            print(f"      → {r['date']} {r['title']}")
            print(f"        이유: {r['reason']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
