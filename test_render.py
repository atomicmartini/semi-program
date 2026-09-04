"""render.py 의 흐름 블록 정렬 로직만 테스트한다. 표준 라이브러리 unittest 만 쓴다.

프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 render.py 를 구현한다.
"""

import unittest

from render import choose_summary, render_day_links, render_thread, search_entry


class TestRenderThread(unittest.TestCase):
    def test_empty_returns_empty_string(self):
        self.assertEqual(render_thread([]), "")

    def _ev(self, **kw):
        # 근거(reason·quote) 없는 연결은 이제 통째로 걸러진다(item 1) — 정렬·링크·건수처럼
        # 이 필터와 무관한 걸 테스트할 때는 근거를 채워 준다.
        base = {"reason": "같은 흐름", "quote": "원문 인용구"}
        return {**base, **kw}

    def test_orders_oldest_first(self):
        # link.py 는 최신순으로 준다 — 화면에서는 타임라인이라 오래된 것부터 보여야 한다
        related = [
            self._ev(date="2026-08-21", title="B", url="u2"),
            self._ev(date="2026-08-19", title="A", url="u1"),
        ]
        html = render_thread(related)
        self.assertLess(html.index("08-19"), html.index("08-21"))

    def test_links_to_original_article(self):
        related = [self._ev(date="2026-08-19", title="A", url="https://example.com/a")]
        html = render_thread(related)
        self.assertIn('href="https://example.com/a"', html)

    def test_shows_count(self):
        related = [
            self._ev(date="2026-08-19", title="A", url="u1"),
            self._ev(date="2026-08-20", title="B", url="u2"),
        ]
        html = render_thread(related)
        self.assertIn("2건", html)


class TestRenderThreadEvidence(unittest.TestCase):
    """왜 이어지는지를 화면에 드러낸다 — 저장만 하고 안 보여주면 가른 의미가 없다."""

    def _related(self, **kw):
        base = {"date": "2026-05-05", "title": "과거 기사", "url": "http://a",
                "reason": "같은 CPO 채택 흐름", "quote": "co-packaged optics 채택을 가속"}
        return [{**base, **kw}]

    def test_shows_reason_and_quote(self):
        html = render_thread(self._related())
        self.assertIn("같은 CPO 채택 흐름", html)
        self.assertIn("co-packaged optics 채택을 가속", html)

    def test_drops_old_data_without_reason(self):
        # 옛 .linked.json(06-연결고리-기준) 에는 reason·quote 가 없다. 인용구 없는 관계는
        # 쓰지 않는다는 규칙(CLAUDE.md) 이 render_thread 에도 그대로 적용된다 — 예전에는
        # 링크만 남기고 근거 줄만 숨겼지만, 이제는 연결 자체를 화면에 안 낸다 (item 1).
        html = render_thread([{"date": "2026-05-05", "title": "과거", "url": "http://a"}])
        self.assertEqual(html, "")
        self.assertNotIn("과거", html)

    def test_drops_reason_without_quote_and_quote_without_reason(self):
        # 반쪽만 있는 것도 안 된다 — 둘 다 있어야 근거로 인정한다.
        only_reason = [{"date": "2026-05-05", "title": "과거", "url": "http://a", "reason": "이유"}]
        only_quote = [{"date": "2026-05-05", "title": "과거", "url": "http://a", "quote": "인용구"}]
        self.assertEqual(render_thread(only_reason), "")
        self.assertEqual(render_thread(only_quote), "")

    def test_count_reflects_only_verified_entries(self):
        # 근거 없는 항목은 건수에서도 빠진다 — 화면에 안 보이는데 "2건"이라 하면 거짓말이다.
        related = [
            self._related()[0],
            {"date": "2026-05-01", "title": "근거 없음", "url": "http://b"},
        ]
        html = render_thread(related)
        self.assertIn("1건", html)
        self.assertNotIn("2건", html)

    def test_escapes_html_in_quote(self):
        html = render_thread(self._related(quote="<script>x</script>"))
        self.assertNotIn("<script>", html)


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


class TestSearchEntry(unittest.TestCase):
    """검색 인덱스 한 줄. choose_summary 와 같은 우선순위로 요약·분류를 고른다."""

    def setUp(self):
        self.article = {
            "title": "T",
            "summary": "원래 영문 요약",
            "category": "패키징",
            "source": "EE Times",
            "url": "https://example.com/a",
        }

    def test_prefers_korean_summary(self):
        entry = search_entry(self.article, "2026-08-24", {"https://example.com/a": {"summary_ko": "한국어 요약"}})
        self.assertEqual(entry["summary"], "한국어 요약")

    def test_falls_back_to_original_summary(self):
        entry = search_entry(self.article, "2026-08-24", {})
        self.assertEqual(entry["summary"], "원래 영문 요약")

    def test_prefers_extracted_category_over_keyword_category(self):
        extracted = {"https://example.com/a": {"category": "메모리", "summary_ko": "요약"}}
        entry = search_entry(self.article, "2026-08-24", extracted)
        self.assertEqual(entry["category"], "메모리")

    def test_includes_date_source_url(self):
        entry = search_entry(self.article, "2026-08-24", {})
        self.assertEqual(entry["date"], "2026-08-24")
        self.assertEqual(entry["source"], "EE Times")
        self.assertEqual(entry["url"], "https://example.com/a")

    def test_truncates_long_summary(self):
        long_article = {**self.article, "summary": "가" * 500}
        entry = search_entry(long_article, "2026-08-24", {})
        self.assertLessEqual(len(entry["summary"]), 200)


if __name__ == "__main__":
    unittest.main()
