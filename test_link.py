"""link.py 의 계산·판단 로직만 테스트한다. 표준 라이브러리 unittest 만 쓴다 (의존성 0개).

프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 link.py 를 구현한다.
"""

import unittest

from link import companies_mentioned, find_related

COMPANIES = {"삼성전자": "삼성전자", "삼성": "삼성전자", "tsmc": "TSMC", "엔비디아": "엔비디아"}


class TestCompaniesMentioned(unittest.TestCase):
    def test_finds_canonical_company_by_alias(self):
        text = "삼성전자가 tsmc 와 경쟁한다"
        self.assertEqual(companies_mentioned(text, COMPANIES), {"삼성전자", "TSMC"})

    def test_no_match_returns_empty_set(self):
        self.assertEqual(companies_mentioned("반도체 뉴스", COMPANIES), set())


class TestFindRelated(unittest.TestCase):
    def setUp(self):
        self.today = {"url": "today", "title": "오늘", "summary": "삼성전자 소식", "published": "2026-08-22"}
        self.past = [
            {"url": "past1", "title": "지난달 삼성전자", "summary": "삼성전자 실적", "published": "2026-07-01"},
            {"url": "past2", "title": "무관 기사", "summary": "엔비디아 소식", "published": "2026-07-05"},
        ]

    def test_links_article_sharing_one_company(self):
        related = find_related(self.today, self.past, COMPANIES, threshold=1)
        urls = [r["url"] for r in related]
        self.assertIn("past1", urls)
        self.assertNotIn("past2", urls)

    def test_below_threshold_returns_empty(self):
        related = find_related(self.today, self.past, COMPANIES, threshold=2)
        self.assertEqual(related, [])

    def test_caps_at_three_most_recent(self):
        many_past = [
            {"url": f"p{i}", "title": "삼성전자", "summary": "삼성전자", "published": f"2026-0{i}-01"}
            for i in range(1, 6)
        ]
        related = find_related(self.today, many_past, COMPANIES, threshold=1)
        self.assertEqual(len(related), 3)
        dates = [r["date"] for r in related]
        self.assertEqual(dates, sorted(dates, reverse=True))


if __name__ == "__main__":
    unittest.main()
