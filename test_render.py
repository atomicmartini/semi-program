"""render.py 의 흐름 블록 정렬 로직만 테스트한다. 표준 라이브러리 unittest 만 쓴다.

프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 render.py 를 구현한다.
"""

import unittest

from render import choose_summary, render_day_links, render_thread


class TestRenderThread(unittest.TestCase):
    def test_empty_returns_empty_string(self):
        self.assertEqual(render_thread([]), "")

    def test_orders_oldest_first(self):
        # link.py 는 최신순으로 준다 — 화면에서는 타임라인이라 오래된 것부터 보여야 한다
        related = [
            {"date": "2026-08-21", "title": "B", "url": "u2"},
            {"date": "2026-08-19", "title": "A", "url": "u1"},
        ]
        html = render_thread(related)
        self.assertLess(html.index("08-19"), html.index("08-21"))

    def test_links_to_original_article(self):
        related = [{"date": "2026-08-19", "title": "A", "url": "https://example.com/a"}]
        html = render_thread(related)
        self.assertIn('href="https://example.com/a"', html)

    def test_shows_count(self):
        related = [
            {"date": "2026-08-19", "title": "A", "url": "u1"},
            {"date": "2026-08-20", "title": "B", "url": "u2"},
        ]
        html = render_thread(related)
        self.assertIn("2건", html)


class TestRenderDayLinks(unittest.TestCase):
    """날짜 줄. 14일로 자르면 과거 기사에 갈 길이 아예 없다 (슬라이스 04)."""

    def _days(self) -> list[str]:
        return ["2025-11-10", "2025-11-24", "2025-12-03", "2026-08-21", "2026-08-22"]

    def test_does_not_truncate_old_days(self):
        html = render_day_links(self._days())
        self.assertIn("2025-11-10", html)

    def test_links_to_each_day_page(self):
        html = render_day_links(self._days())
        self.assertIn('href="2025-11-10.html"', html)

    def test_marks_current_day_without_link(self):
        html = render_day_links(self._days(), current="2026-08-22")
        self.assertNotIn('href="2026-08-22.html"', html)

    def test_groups_by_month(self):
        # 125개를 한 줄에 늘어놓으면 못 읽는다. 달별로 묶는다
        html = render_day_links(self._days())
        for month in ("2025-11", "2025-12", "2026-08"):
            self.assertIn(month, html)

    def test_empty_days_gives_empty_string(self):
        self.assertEqual(render_day_links([]), "")


class TestChooseSummary(unittest.TestCase):
    """카드에 보여줄 요약 고르기 (슬라이스 05).

    돌려주는 것 — (보여줄 글, 모델이 만든 것인가)
    """

    def setUp(self):
        self.article = {"url": "u1", "summary": "The global IC industry is confronting..."}

    def test_prefers_korean_summary(self):
        text, by_model = choose_summary(self.article, {"u1": {"summary_ko": "한국어 요약이다."}})
        self.assertEqual(text, "한국어 요약이다.")
        self.assertTrue(by_model)

    def test_falls_back_when_no_extracted_file(self):
        text, by_model = choose_summary(self.article, {})
        self.assertEqual(text, self.article["summary"])
        self.assertFalse(by_model)

    def test_falls_back_when_summary_ko_is_empty(self):
        # 빈 카드를 만들지 않는다
        text, by_model = choose_summary(self.article, {"u1": {"summary_ko": ""}})
        self.assertEqual(text, self.article["summary"])
        self.assertFalse(by_model)

    def test_falls_back_when_summary_ko_is_none(self):
        # extract_error 가 난 기사는 summary_ko 가 None 이다
        text, by_model = choose_summary(self.article, {"u1": {"summary_ko": None}})
        self.assertEqual(text, self.article["summary"])
        self.assertFalse(by_model)


if __name__ == "__main__":
    unittest.main()
