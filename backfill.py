"""여러 날의 '이어지는 흐름' 판정을, 하루 무료 모델 한도에 걸쳐 이어서 돌린다.

link.py <날짜> 는 한 번에 하루치만 판정한다. 그런데 OpenRouter 무료 모델은
하루 50회 한도라, 과거 136일치를 다시 돌리려면 여러 날에 나눠 이어서 실행해야 한다.
손으로 어디까지 했는지 챙기면 실수하기 쉬워 이 러너를 만든다.

진행 상황을 따로 기록하지 않는다 — data/articles/<날짜>.linked.json 자체가 기록이다.
그 파일의 기사마다 새 파이프라인이 붙이는 `judged` 표시가 있고, 근거(reason) 있는
연결이 있거나 흐름이 진짜로 없어서(오류 없이) 빈 것이면 끝난 것이다.
link_error 가 남아 있거나 `judged` 표시가 없으면(옛 키워드 규칙이 남긴 파일 포함)
아직 안 끝난 것으로 본다.

새 날짜부터 처리한다 — 첫 화면에 뜨는 게 최신 날짜라 거기부터 고쳐야 눈에 먼저 띈다.
오늘 한도를 다 쓰면(무료 모델 하루 50회 초과) 남은 날짜를 텅 빈 결과로 밀어붙이지 않고
그 자리에서 멈춘다 — 내일 다시 실행하면 이어서 한다.
"""

import json
import re
import sys
from pathlib import Path

import link

HERE = Path(__file__).parent
ARTICLE_DIR = HERE / "data" / "articles"

# OpenRouter 무료 모델이 하루 한도에 걸리면 이 문구와 함께 HTTP 429 를 준다.
# 하지만 extract._call_model 은 urllib.request.urlopen 을 그대로 쓰는데, 이 함수는
# 429 응답이 오면 본문을 읽기도 전에 HTTPError 를 던진다 — 그래서 이 본문 문구는
# link.judge() 가 남기는 link_error 문자열에 실제로는 절대 안 실린다.
# 실제 link_error 는 str(HTTPError) 그대로인 "HTTP Error 429: Too Many Requests" 뿐이다
# (data/articles/*.linked.json 에 남은 45건 전부 이 형태 하나다).
QUOTA_PHRASE = "Rate limit exceeded: free-models-per-day"
# link.judge() 가 실제로 남기는 모양(f"{type(e).__name__} {e}")에 맞춰 "HTTP Error 429"
# 를 앵커로 잡는다. 그냥 "429" 를 아무 데서나 찾으면 기사 제목에 우연히 429 가 있어도
# 멈추게 되니, HTTPError 의 문자열 형태에 붙여서만 본다.
_HTTP_429 = re.compile(r"HTTP Error 429\b")


def base_dates(article_dir: Path = ARTICLE_DIR) -> list[str]:
    """<날짜>.json 형태의 원본 파일만 고른다. 파생 파일(.selected/.extracted/.linked)은
    stem 에 점이 있어 걸러진다 — link.py 의 _load_all_past 와 같은 규칙이다."""
    return sorted(p.stem for p in article_dir.glob("*.json") if "." not in p.stem)


def needs_judging(day: str, article_dir: Path = ARTICLE_DIR) -> bool:
    """이 날짜를 다시 판정해야 하는가.

    .linked.json 이 없으면 당연히 필요하다.
    있어도 link_error 가 하나라도 남아 있으면 그 판정은 실패한 채 저장된 것 — 다시 해야 한다.
    새 파이프라인이 실제로 판정한 기사에는 `judged` 표시가 붙는다(link.link_day 참조).
    이 표시가 없는 기사가 하나라도 있으면 다시 한다 — 옛 키워드 규칙도 '링크 0건·오류 0건'과
    똑같은 모양을 만들기 때문에, 표시 없이는 "옛 데이터"와 "모델이 진짜 흐름 없음이라 답한 것"을
    구분할 방법이 없다 (item 3). 표시만으로는 안 걸러지는 옛 형식(연결은 있는데 reason 이
    하나도 없는 경우)도 다시 한다.
    셋 다 아니면 — 모델이 정말로 '이어지는 흐름 없음' 이라 답했거나 근거 있는 연결이 있는
    것이니 끝난 것으로 본다. 억지로 다시 돌리지 않는다 (CLAUDE.md).
    """
    path = article_dir / f"{day}.linked.json"
    if not path.exists():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True  # 읽을 수 없는 파일은 다시 만든다

    articles = data.get("articles") or []
    if any(a.get("link_error") for a in articles):
        return True

    if not all(a.get("judged") for a in articles):
        return True  # 옛 규칙이 남긴 파일이거나 아직 새로 판정 못 받은 기사가 있다

    related = [r for a in articles for r in (a.get("related") or [])]
    if related and not any("reason" in r for r in related):
        return True

    return False


def dates_to_process(article_dir: Path = ARTICLE_DIR) -> list[str]:
    """판정이 필요한 날짜를 새 날짜부터 순서대로 돌려준다."""
    pending = [d for d in base_dates(article_dir) if needs_judging(d, article_dir)]
    return sorted(pending, reverse=True)


def is_quota_error(msg: str | None) -> bool:
    """이 오류에 멈춰야 하는지 가린다 — 안전한 쪽으로 판단이 기운다.

    본래는 '하루 한도(daily cap)' 와 '순간적으로 몰아쳐서 걸린 429' 를 구분하려
    했지만, 몸통(본문) 문구는 link_error 문자열에 실제로 절대 안 실린다 (위 주석).
    그래서 두 가지를 구분하지 않고 **HTTP 429 면 무조건 멈춘다.**
    안 멈춰도 됐는데 멈추면 다음 실행 한 번 더 도는 비용이지만, 멈춰야 하는데
    안 멈추면 89일치 .linked.json 을 빈 결과로 덮어써 복구 불가능한 손실이 난다 —
    싼 쪽(재실행)으로 넘어지게 만든다.
    본문 문구가 나중에 실제로 실리게 되면(QUOTA_PHRASE) 그것도 그대로 인정한다.
    """
    if not msg:
        return False
    return bool(_HTTP_429.search(msg)) or QUOTA_PHRASE in msg


def run(limit: int | None = None, article_dir: Path = ARTICLE_DIR, link_day=None, save_day=None) -> dict:
    """대상 날짜를 새것부터 하나씩 판정한다. 한도에 걸리면 그 자리에서 멈춘다.

    여기서는 출력하지 않는다 — main() 이 sys.stdout 을 utf-8 로 맞춘 뒤에 찍는다
    (link.py 의 link_day/extract.py 의 extract_day 와 같은 관례: 계산은 조용히,
    출력은 main() 에서만).

    link_day/save_day 를 인자로 받는 이유는 테스트에서 진짜 모델 호출 없이
    가짜 함수를 끼워 넣기 위해서다 — link.py 자체는 손대지 않는다.
    """
    link_day = link_day or link.link_day
    save_day = save_day or link.save_day

    pending = dates_to_process(article_dir)
    processed: list[dict] = []
    quota_hit = False

    for day in pending:
        if limit is not None and len(processed) >= limit:
            break

        linked = link_day(day)
        save_day(day, linked)

        errors = [a["link_error"] for a in linked if a.get("link_error")]
        quota_errors = [e for e in errors if is_quota_error(e)]
        other_errors = [e for e in errors if not is_quota_error(e)]
        with_flow = sum(1 for a in linked if a.get("related"))
        processed.append(
            {
                "day": day,
                "total": len(linked),
                "with_flow": with_flow,
                "errors": other_errors,
                "quota_error": quota_errors[0] if quota_errors else None,
            }
        )

        if quota_errors:
            quota_hit = True
            break

    remaining = dates_to_process(article_dir)
    return {"processed": processed, "quota_hit": quota_hit, "remaining": remaining}


USAGE = "사용법: python backfill.py [--limit N]   예: python backfill.py --limit 3"


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    # 인자 검사를 먼저 끝낸다 — 이후에야 모델 호출이 시작된다.
    if argv and argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0

    limit = None
    if argv:
        if len(argv) != 2 or argv[0] != "--limit":
            print(USAGE, file=sys.stderr)
            return 1
        try:
            limit = int(argv[1])
        except ValueError:
            print(USAGE, file=sys.stderr)
            return 1
        if limit < 1:
            print("--limit 은 1 이상이어야 합니다.", file=sys.stderr)
            return 1

    result = run(limit=limit)

    for item in result["processed"]:
        print(f"{item['day']} — {item['total']}건 중 이어지는 흐름 있음 {item['with_flow']}건")
        for e in item["errors"]:
            # 한도 초과가 아닌 실패는 조용히 넘기지 않는다 (CLAUDE.md).
            print(f"  ! 판정 실패: {e}", file=sys.stderr)
        if item["quota_error"]:
            print(f"  ! 오늘 무료 모델 한도에 도달했습니다 ({item['quota_error']}) — 여기서 멈춥니다.")

    print(f"\n처리한 날짜 {len(result['processed'])}건")
    print(f"판정이 아직 필요한 날짜 {len(result['remaining'])}건")
    if result["quota_hit"]:
        print("오늘 무료 모델 한도를 다 썼습니다 — 내일 다시 python backfill.py 를 실행하세요.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
