"""기사를 모델로 분류·한국어 요약하고, 기업 간 관계를 인용구와 함께 뽑는다.

판정은 코드가 한다. 모델은 분류·요약·관계 추출만 한다 (CLAUDE.md).
카테고리가 정해진 목록에 없으면 코드가 미분류로 강제하고,
원문에 없는 인용구가 붙은 관계는 코드가 버린다.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from filter import UNCLASSIFIED, read_keywords
from pick import select_day

HERE = Path(__file__).parent
ARTICLE_DIR = HERE / "data" / "articles"
ENV_FILE = HERE / ".env"

API_URL = "https://openrouter.ai/api/v1/chat/completions"
# 무료 모델은 언제든 막힌다. 이 한 줄만 바꾸면 갈아탈 수 있게 둔다.
# google/gemma-4-* 는 2026-08-23 기준 상위 제공자(Google AI Studio) 공유 풀이 429 로 계속 막혔다.
# 다른 후보 — nvidia/nemotron-3-nano-30b-a3b:free (빠름) · dots-studio/dots-3-note-preview:free
MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

PROMPT = """다음 반도체 뉴스 기사를 분석해 아래 JSON 형식으로만 답하라. 다른 말은 하지 마라.

카테고리는 반드시 이 중 하나를 그대로 써라: {categories}
summary_ko 는 기사 내용을 한국어 두 문장으로 요약한다. 기사에 없는 내용은 쓰지 않는다.
relations 는 기사에 **명시적으로 등장하는** 기업 간 관계(경쟁·협력·공급·투자·인수 등)만 담는다.
없으면 빈 배열로 둔다. quote 는 그 관계를 뒷받침하는 문장을 원문에서 **그대로** 옮긴다. 지어내지 마라.

{{"category": "...", "summary_ko": "...", "relations": [{{"companies": ["...", "..."], "description": "...", "quote": "..."}}]}}

제목: {title}
본문: {body}
"""

_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


class ModelError(RuntimeError):
    """모델이 답을 못 준 경우. 그 기사만 실패로 두고 나머지는 계속한다."""


def _load_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("OPENROUTER_API_KEY 가 없습니다. .env 를 확인하세요.")


def _call_model(prompt: str, key: str) -> str:
    body = json.dumps(
        {"model": MODEL, "messages": [{"role": "user", "content": prompt}]}
    ).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    # HTTP 200 인데 choices 가 없을 때가 있다 (제공자가 중간에 실패하면 error 만 온다).
    # 여기서 KeyError 로 터지면 앞서 처리한 기사까지 통째로 날아간다. 한 건만 실패로 넘긴다.
    if "choices" not in data:
        raise ModelError(json.dumps(data, ensure_ascii=False)[:200])
    return data["choices"][0]["message"]["content"]


def _parse_json(text: str) -> dict | None:
    m = _JSON_BLOCK.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _verify_quote(quote: str, haystack: str) -> bool:
    """인용구가 원문에 실제로 있는지 대조한다. 없으면 그 관계를 버린다 (CLAUDE.md)."""
    return bool(quote) and _norm(quote) in _norm(haystack)


def resolve_category(model_answer: str | None, keyword_answer: str, categories: list[str]) -> str:
    """카테고리는 코드가 정한다 (CLAUDE.md).

    모델이 목록에 없는 것을 지어내거나 `미분류` 로 답하면 키워드 분류를 그대로 쓴다.
    모델을 바꿔도 이 규칙은 안 흔들린다.
    """
    if model_answer in categories and model_answer != UNCLASSIFIED:
        return model_answer
    return keyword_answer


def extract_one(article: dict, categories: list[str], key: str) -> dict:
    """기사 한 건을 모델에 보내고, 결과를 코드로 검산해 돌려준다."""
    haystack = f"{article['title']} {article['summary']}"
    prompt = PROMPT.format(
        categories="/".join(categories), title=article["title"], body=article["summary"]
    )

    try:
        raw = _call_model(prompt, key)
    except (urllib.error.URLError, urllib.error.HTTPError, ModelError, TimeoutError) as e:
        return {**article, "summary_ko": None, "relations": [], "extract_error": str(e)}

    parsed = _parse_json(raw)
    if parsed is None:
        return {
            **article,
            "summary_ko": None,
            "relations": [],
            "extract_error": "모델 출력을 JSON 으로 못 읽음",
        }

    # filter.py 가 키워드로 매긴 분류를 되돌릴 자리로 쓴다. 모델이 틀려도 정보를 안 잃는다.
    category = resolve_category(
        parsed.get("category"), article.get("category", UNCLASSIFIED), categories
    )

    relations = []
    for r in parsed.get("relations", []) or []:
        quote = (r.get("quote") or "").strip()
        if _verify_quote(quote, haystack):
            relations.append(
                {
                    "companies": r.get("companies", []),
                    "description": r.get("description", ""),
                    "quote": quote,
                }
            )
        # 인용구가 원문에 없으면 그 관계는 조용히 버린다 — 지어낸 관계를 화면에 내지 않는다.

    return {
        **article,
        "category": category,
        "summary_ko": parsed.get("summary_ko", ""),
        "relations": relations,
        "extract_error": None,
    }


def load_done(day: str) -> dict[str, dict]:
    """이미 뽑아 둔 결과. 실패한 것은 다시 하도록 빼고 돌려준다."""
    path = ARTICLE_DIR / f"{day}.extracted.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        a["url"]: a
        for a in data["articles"]
        if not a.get("extract_error") and a.get("summary_ko")
    }


def extract_day(day: str) -> tuple[list[dict], int, int]:
    """선별된 하루치 기사를 처리한다. (결과, 실패 건수, 건너뛴 건수)

    이미 뽑아 둔 기사는 모델을 다시 부르지 않는다 — 125일치를 돌리면 수백 번이라
    중간에 끊기면 처음부터 다시 하게 된다.
    """
    picked, _, _ = select_day(day)
    _, _, categories = read_keywords()
    cat_names = [*categories, UNCLASSIFIED]
    key = _load_key()
    done = load_done(day)

    out: list[dict] = []
    errors = skipped = 0
    for a in picked:
        if a["url"] in done:
            out.append(done[a["url"]])
            skipped += 1
            continue
        result = extract_one(a, cat_names, key)
        if result.get("extract_error"):
            errors += 1
        out.append(result)
    return out, errors, skipped


def save_day(day: str, extracted: list[dict]) -> Path:
    path = ARTICLE_DIR / f"{day}.extracted.json"
    path.write_text(
        json.dumps({"date": day, "articles": extracted}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    if len(argv) != 1:
        print("사용법: python extract.py <날짜>   예: python extract.py 2026-08-22", file=sys.stderr)
        return 1

    day = argv[0]
    extracted, errors, skipped = extract_day(day)
    save_day(day, extracted)

    n_relations = sum(len(a.get("relations") or []) for a in extracted)
    print(
        f"{day} — {len(extracted)}건 처리 · 새로 부름 {len(extracted) - skipped}건"
        f" · 이미 있어 건너뜀 {skipped}건 · 관계 {n_relations}건 · 실패 {errors}건"
    )
    if errors:
        print("실패한 기사는 summary_ko 가 비어 있습니다. extract_error 필드를 확인하세요.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
