"""backfill.py 의 날짜 선별·한도 중단 로직만 테스트한다. 네트워크를 쓰지 않는다.

link_day/save_day 는 전부 가짜로 끼워 넣는다 — 진짜 모델을 부르면 안 된다
(오늘 무료 모델 한도가 이미 다 찬 상태라 실제로 부르면 실패하거나 기존 결과를 망가뜨린다).
"""

import json
import tempfile
import unittest
from pathlib import Path

from backfill import base_dates, dates_to_process, is_quota_error, needs_judging, run


def _write(dir_: Path, name: str, data: dict) -> None:
    (dir_ / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class TestBaseDates(unittest.TestCase):
    def test_only_dates_without_dots_count(self):
        with tempfile.TemporaryDirectory() as d:
            dir_ = Path(d)
            for name in ("2026-08-20.json", "2026-08-20.selected.json", "2026-08-20.linked.json"):
                _write(dir_, name, {})
            self.assertEqual(base_dates(dir_), ["2026-08-20"])


class TestNeedsJudging(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir_ = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_linked_file_needs_judging(self):
        self.assertTrue(needs_judging("2026-08-20", self.dir_))

    def test_link_error_needs_judging(self):
        _write(self.dir_, "2026-08-20.linked.json", {
            "articles": [{"related": [], "link_error": "HTTPError HTTP Error 429: Too Many Requests"}]
        })
        self.assertTrue(needs_judging("2026-08-20", self.dir_))

    def test_genuinely_empty_flows_without_errors_is_done(self):
        # 모델이 정말 '이어지는 흐름 없음' 이라 답한 경우 — 억지로 다시 돌리지 않는다 (CLAUDE.md).
        _write(self.dir_, "2026-08-20.linked.json", {"articles": [{"related": []}]})
        self.assertFalse(needs_judging("2026-08-20", self.dir_))

    def test_links_present_with_reason_is_done(self):
        _write(self.dir_, "2026-08-20.linked.json", {
            "articles": [{"related": [{"date": "2026-05-01", "reason": "같은 흐름", "quote": "q"}]}]
        })
        self.assertFalse(needs_judging("2026-08-20", self.dir_))

    def test_links_present_without_reason_needs_judging(self):
        # 옛 형식이거나 깨진 결과 — reason 이 하나도 없다.
        _write(self.dir_, "2026-08-20.linked.json", {
            "articles": [{"related": [{"date": "2026-05-01", "quote": "q"}]}]
        })
        self.assertTrue(needs_judging("2026-08-20", self.dir_))

    def test_unreadable_file_needs_judging(self):
        (self.dir_ / "2026-08-20.linked.json").write_text("이건 JSON 이 아니다", encoding="utf-8")
        self.assertTrue(needs_judging("2026-08-20", self.dir_))


class TestDatesToProcess(unittest.TestCase):
    def test_orders_newest_first_and_skips_done_dates(self):
        with tempfile.TemporaryDirectory() as d:
            dir_ = Path(d)
            for day in ("2026-08-18", "2026-08-19", "2026-08-20"):
                _write(dir_, f"{day}.json", {})
            # 08-19 만 이미 끝난 것으로 둔다.
            _write(dir_, "2026-08-19.linked.json", {"articles": [{"related": []}]})

            self.assertEqual(dates_to_process(dir_), ["2026-08-20", "2026-08-18"])


class TestIsQuotaError(unittest.TestCase):
    def test_matches_daily_quota_message_with_429(self):
        msg = "ModelError HTTP 429: Rate limit exceeded: free-models-per-day, please try again later"
        self.assertTrue(is_quota_error(msg))

    def test_plain_429_without_quota_phrase_is_not_quota(self):
        self.assertFalse(is_quota_error("HTTPError HTTP Error 429: Too Many Requests"))

    def test_quota_phrase_without_429_is_not_quota(self):
        self.assertFalse(is_quota_error("Rate limit exceeded: free-models-per-day"))

    def test_none_is_not_quota(self):
        self.assertFalse(is_quota_error(None))


class TestRun(unittest.TestCase):
    """진짜 link.link_day/save_day 대신 가짜를 끼운다 — 네트워크를 절대 타지 않는다."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir_ = Path(self._tmp.name)
        for day in ("2026-08-18", "2026-08-19", "2026-08-20"):
            _write(self.dir_, f"{day}.json", {})
        self.saved: dict[str, list[dict]] = {}

    def tearDown(self):
        self._tmp.cleanup()

    def _save_day(self, day, linked):
        # link.save_day 처럼 실제로 파일을 써야 needs_judging() 이 다음 판단을 제대로 한다.
        self.saved[day] = linked
        _write(self.dir_, f"{day}.linked.json", {"date": day, "articles": linked})

    def test_stops_on_quota_error_and_leaves_earlier_dates_pending(self):
        calls = []

        def fake_link_day(day):
            calls.append(day)
            if day == "2026-08-19":
                return [{"url": "a", "related": [], "link_error": "HTTP 429: Rate limit exceeded: free-models-per-day"}]
            return [{"url": "b", "related": []}]

        result = run(article_dir=self.dir_, link_day=fake_link_day, save_day=self._save_day)

        # 새 날짜부터: 08-20 은 성공, 08-19 에서 한도에 걸려 멈추고 08-18 은 손대지 않는다.
        self.assertEqual(calls, ["2026-08-20", "2026-08-19"])
        self.assertTrue(result["quota_hit"])
        self.assertEqual([p["day"] for p in result["processed"]], ["2026-08-20", "2026-08-19"])
        self.assertIsNotNone(result["processed"][-1]["quota_error"])
        self.assertIn("2026-08-18", result["remaining"])
        self.assertIn("2026-08-19", result["remaining"])  # 한도 걸린 날짜는 다음에 다시 시도해야 한다

    def test_non_quota_error_reports_and_continues(self):
        def fake_link_day(day):
            if day == "2026-08-20":
                return [{"url": "a", "related": [], "link_error": "ModelError 모델이 이상한 답을 줌"}]
            return [{"url": "b", "related": []}]

        result = run(article_dir=self.dir_, link_day=fake_link_day, save_day=self._save_day)

        self.assertFalse(result["quota_hit"])
        self.assertEqual({p["day"] for p in result["processed"]}, {"2026-08-18", "2026-08-19", "2026-08-20"})
        found = next(p for p in result["processed"] if p["day"] == "2026-08-20")
        self.assertTrue(found["errors"])
        self.assertIsNone(found["quota_error"])
        # 08-20 은 오류가 남아 있으니 다음 실행에서도 다시 판정 대상이다.
        self.assertEqual(result["remaining"], ["2026-08-20"])

    def test_limit_caps_dates_processed_this_run(self):
        def fake_link_day(day):
            return [{"url": day, "related": []}]

        result = run(limit=1, article_dir=self.dir_, link_day=fake_link_day, save_day=self._save_day)

        self.assertEqual([p["day"] for p in result["processed"]], ["2026-08-20"])
        self.assertFalse(result["quota_hit"])
        self.assertEqual(set(result["remaining"]), {"2026-08-18", "2026-08-19"})

    def test_no_pending_dates_does_nothing(self):
        for day in ("2026-08-18", "2026-08-19", "2026-08-20"):
            _write(self.dir_, f"{day}.linked.json", {"articles": [{"related": []}]})
        called = []
        result = run(article_dir=self.dir_, link_day=lambda d: called.append(d), save_day=self._save_day)
        self.assertEqual(called, [])
        self.assertEqual(result, {"processed": [], "quota_hit": False, "remaining": []})


if __name__ == "__main__":
    unittest.main()
