"""가끔 접속해도 밀린 일이 순서대로 처리되게 한다. 한 번에 하나씩, 한도까지만.

사용자가 매일 접속하지 못한다. 며칠씩 밀리면 할 일이 하루 한도(무료 모델 50건)를
넘기 때문에 **무엇을 먼저 할지** 가 매번 문제가 된다. 그 판단을 손으로 하지 않게 여기 담았다.

    python catchup.py            # 받기 → 최신 날짜부터 요약·판정 → 남으면 과거 재판정 → 화면 생성

순서를 이렇게 정한 이유 —
  1. `fetch.py` 는 공짜이고 **미룰 수 없다.** RSS 는 최근 10~20건만 들고 있어서
     며칠 지나면 그 날짜 기사가 피드에서 사라진다. 접속했으면 일단 받아 둔다.
  2. 요약·판정은 **최신 날짜부터.** 첫 화면이 최신 날짜라 거기가 비면 바로 보인다.
  3. 날짜를 반쪽만 하지 않는다. 예산을 넘기는 날짜는 건너뛰고 들어가는 작은 날짜를 채운다 —
     반쪽만 하면 그 날 화면에 한국어 요약 없는 기사가 섞인다.
  4. 남으면 `backfill.py` 로 과거 날짜를 새 기준으로 다시 판정한다.

배포는 하지 않는다 — `git push` 는 사람이 판단한다.
"""

import sys

import extract
import link
import render
from backfill import base_dates, is_quota_error
from backfill import run as backfill_run
from pick import select_day

DAILY_BUDGET = 50  # 무료 모델 하루 상한. 크레딧을 충전하면 올라간다


def needs(day: str) -> tuple[int, int]:
    """그 날짜에 남은 (요약 건수, 판정 건수). 이미 끝난 기사는 세지 않는다."""
    picked, _, _ = select_day(day)
    done_summary = extract.load_done(day)
    to_extract = sum(1 for a in picked if a["url"] not in done_summary)

    judged = link.load_done(day)  # judged 표시가 있고 실패하지 않은 기사만 들어 있다
    to_link = sum(1 for a in picked if a["url"] not in judged)
    return to_extract, to_link


def plan_work(days: list[str], need_of, budget: int) -> list[tuple[str, int, int]]:
    """예산 안에서 처리할 날짜를 정한다. 새 날짜부터, 반쪽은 만들지 않는다.

    돌려주는 것 — [(날짜, 요약 건수, 판정 건수)]
    """
    plan: list[tuple[str, int, int]] = []
    left = budget
    for day in sorted(days, reverse=True):
        ex, lk = need_of(day)
        cost = ex + lk
        if cost == 0:
            continue
        if cost > left:
            continue  # 이 날짜는 통째로 다음 기회에 — 반쪽으로 남기지 않는다
        plan.append((day, ex, lk))
        left -= cost
    return plan


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    budget = DAILY_BUDGET
    if argv and argv[0].startswith("--budget="):
        budget = int(argv[0].split("=", 1)[1])

    print("1) 기사 받기 — 미루면 피드에서 사라진다")
    import fetch

    added, status = fetch.fetch_articles()
    failed = {n: s for n, s in status.items() if s != "정상"}
    print(f"   출처 {len(status)}곳 중 {len(status) - len(failed)}곳 정상 · 새 기사 {sum(added.values())}건")
    for name, state in failed.items():
        print(f"   ! {name} — {state}", file=sys.stderr)  # 조용히 넘기지 않는다 (CLAUDE.md)

    print(f"\n2) 요약·판정 — 오늘 예산 {budget}건, 최신 날짜부터")
    plan = plan_work(base_dates(), needs, budget)
    if not plan:
        print("   할 것 없음 (최근 날짜는 다 끝났다)")
    spent = 0
    stopped = False
    for day, ex, lk in plan:
        print(f"   {day} — 요약 {ex}건 · 판정 {lk}건", flush=True)
        if ex:
            extracted, errors, _ = extract.extract_day(day)
            extract.save_day(day, extracted)
            if any(is_quota_error(a.get("extract_error") or "") for a in extracted):
                stopped = True
        linked = link.link_day(day)
        link.save_day(day, linked)
        spent += ex + lk
        if any(is_quota_error(a.get("link_error") or "") for a in linked):
            stopped = True
        if stopped:
            print("   ! 오늘 한도에 도달했다 — 여기서 멈춘다. 받아 둔 기사는 남아 있다")
            break

    left = budget - spent
    if not stopped and left > 0:
        print(f"\n3) 과거 재판정 — 예산 {left}건 남음")
        result = backfill_run(limit=max(1, left // 5))
        print(f"   처리한 날짜 {len(result['processed'])}건 · 남은 날짜 {len(result['remaining'])}일")
    else:
        print("\n3) 과거 재판정 — 건너뜀 (예산 없음)")

    print("\n4) 화면 생성")
    render.main(["--all"])

    print("\n끝. 배포하려면 — git add docs && git commit && git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
