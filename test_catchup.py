"""catchup.py 의 '무엇을 먼저 할지' 판단만 테스트한다. 네트워크·모델을 쓰지 않는다.

사용자가 매일 접속하지 못한다. 가끔 들어왔을 때 하루 50건을 어디에 쓸지가
이 파일이 정하는 것이고, 그 판단이 틀리면 첫 화면이 비어 보인다.
"""

import unittest

from catchup import plan_work


class TestPlanWork(unittest.TestCase):
    def _need(self, mapping):
        """날짜 → (요약 필요, 판정 필요) 를 돌려주는 가짜 조사 함수."""
        return lambda day: mapping.get(day, (0, 0))

    def test_newest_date_comes_first(self):
        """첫 화면이 최신 날짜다. 과거가 비는 것보다 오늘이 비는 게 나쁘다."""
        plan = plan_work(["2026-09-01", "2026-10-03", "2026-09-15"],
                         self._need({"2026-09-01": (1, 1), "2026-10-03": (2, 2), "2026-09-15": (1, 1)}),
                         budget=50)
        self.assertEqual([d for d, _, _ in plan], ["2026-10-03", "2026-09-15", "2026-09-01"])

    def test_stops_at_budget(self):
        plan = plan_work(["2026-10-03", "2026-10-02", "2026-10-01"],
                         self._need({"2026-10-03": (10, 10), "2026-10-02": (10, 10),
                                     "2026-10-01": (10, 10)}),
                         budget=25)
        self.assertEqual([d for d, _, _ in plan], ["2026-10-03"])

    def test_skips_dates_with_nothing_to_do(self):
        plan = plan_work(["2026-10-03", "2026-10-02"],
                         self._need({"2026-10-02": (1, 1)}), budget=50)
        self.assertEqual([d for d, _, _ in plan], ["2026-10-02"])

    def test_fills_leftover_budget_with_a_smaller_day(self):
        """큰 날짜가 예산을 넘기면 건너뛰고, 남는 예산에 들어가는 작은 날짜를 채운다.

        날짜를 반쪽만 처리하면 그 날 화면에 요약 없는 기사가 섞인다 (HANDOFF).
        """
        plan = plan_work(
            ["2026-10-03", "2026-10-02", "2026-10-01"],
            self._need({"2026-10-03": (10, 10), "2026-10-02": (9, 9), "2026-10-01": (2, 2)}),
            budget=24,
        )
        self.assertEqual([d for d, _, _ in plan], ["2026-10-03", "2026-10-01"])

    def test_reports_cost_per_date(self):
        plan = plan_work(["2026-10-03"], self._need({"2026-10-03": (3, 4)}), budget=50)
        self.assertEqual(plan, [("2026-10-03", 3, 4)])

    def test_empty_when_nothing_pending(self):
        self.assertEqual(plan_work(["2026-10-03"], self._need({}), budget=50), [])

    def test_zero_budget_plans_nothing(self):
        plan = plan_work(["2026-10-03"], self._need({"2026-10-03": (1, 1)}), budget=0)
        self.assertEqual(plan, [])


if __name__ == "__main__":
    unittest.main()
