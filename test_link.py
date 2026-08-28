"""link.py 의 계산·판단 로직만 테스트한다. 표준 라이브러리 unittest 만 쓴다 (의존성 0개).

프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 link.py 를 구현한다.
"""

import unittest

from companies import companies_mentioned
from link import bridged, find_related, topic_keywords

COMPANIES = {
    "삼성전자": "삼성전자",
    "삼성": "삼성전자",
    "tsmc": "TSMC",
    "엔비디아": "엔비디아",
    "nvidia": "엔비디아",
    "kla": "KLA",
    "qnity": "Qnity",
}
VOCAB = ["주주환원", "패키징", "hbm", "파운드리", "검사장비", "디자인"]


class TestCompaniesMentioned(unittest.TestCase):
    def test_finds_canonical_company_by_alias(self):
        text = "삼성전자가 tsmc 와 경쟁한다"
        self.assertEqual(companies_mentioned(text, COMPANIES), {"삼성전자", "TSMC"})

    def test_no_match_returns_empty_set(self):
        self.assertEqual(companies_mentioned("반도체 뉴스", COMPANIES), set())


class TestTopicKeywords(unittest.TestCase):
    """무엇에 관한 기사인가. 카테고리 키워드만 쓴다 — '반도체' 같은 건 증거가 못 된다."""

    def test_finds_keywords(self):
        self.assertEqual(topic_keywords("HBM 패키징 공정", VOCAB), {"hbm", "패키징"})

    def test_is_case_insensitive(self):
        self.assertEqual(topic_keywords("hbm 소식", VOCAB), {"hbm"})

    def test_no_match_returns_empty_set(self):
        self.assertEqual(topic_keywords("회사가 상을 받았다", VOCAB), set())


class TestBridged(unittest.TestCase):
    """기업이 달라도 관계로 이어져 있으면 잇는다 (사용자 요청)."""

    def setUp(self):
        self.pairs = {frozenset({"엔비디아", "삼성전자"}), frozenset({"Qnity", "KLA"})}

    def test_bridges_two_different_companies(self):
        self.assertTrue(bridged({"엔비디아"}, {"삼성전자"}, self.pairs))

    def test_bridge_works_both_ways(self):
        self.assertTrue(bridged({"KLA"}, {"Qnity"}, self.pairs))

    def test_no_bridge_when_pair_unknown(self):
        self.assertFalse(bridged({"엔비디아"}, {"TSMC"}, self.pairs))

    def test_no_bridge_without_any_relations(self):
        self.assertFalse(bridged({"엔비디아"}, {"삼성전자"}, set()))


class TestFindRelated(unittest.TestCase):
    def _article(self, title, summary, published="2026-08-22"):
        return {"url": title, "title": title, "summary": summary, "published": published}

    def test_links_when_company_and_keyword_both_overlap(self):
        today = self._article("삼성전자 주주환원", "삼성전자가 주주환원을 의결했다")
        past = [self._article("삼성전자 주주환원 검토", "삼성전자 주주환원 계획", "2026-07-01")]
        related = find_related(today, past, COMPANIES, VOCAB, set())
        self.assertEqual(len(related), 1)

    def test_does_not_link_on_company_alone(self):
        # 지금 문제 그 자체 — 삼성전자 하나 겹쳤다고 주주환원과 디자인상이 이어져 있었다
        today = self._article("삼성전자 주주환원", "삼성전자가 주주환원을 의결했다")
        past = [self._article("삼성전자 디자인 수상", "삼성전자가 디자인 상을 받았다", "2026-07-01")]
        self.assertEqual(find_related(today, past, COMPANIES, VOCAB, set()), [])

    def test_does_not_link_on_keyword_alone(self):
        today = self._article("삼성전자 패키징", "삼성전자 패키징 투자")
        past = [self._article("TSMC 패키징", "tsmc 패키징 증설", "2026-07-01")]
        self.assertEqual(find_related(today, past, COMPANIES, VOCAB, set()), [])

    def test_links_across_companies_through_a_relation(self):
        # 엔비디아가 개발한 것을 삼성이 만들기로 했다 — 회사는 다르지만 이어져야 한다
        pairs = {frozenset({"엔비디아", "삼성전자"})}
        today = self._article("삼성전자 HBM 생산", "삼성전자가 HBM 을 만든다")
        past = [self._article("엔비디아 HBM 요구", "nvidia 가 HBM 을 쓴다", "2026-07-01")]
        related = find_related(today, past, COMPANIES, VOCAB, pairs)
        self.assertEqual(len(related), 1)

    def test_records_why_it_was_linked(self):
        today = self._article("삼성전자 주주환원", "삼성전자가 주주환원을 의결했다")
        past = [self._article("삼성전자 주주환원 검토", "삼성전자 주주환원 계획", "2026-07-01")]
        r = find_related(today, past, COMPANIES, VOCAB, set())[0]
        self.assertEqual(r["shared_companies"], ["삼성전자"])
        self.assertEqual(r["shared_keywords"], ["주주환원"])

    def test_caps_at_max_related_most_recent(self):
        from link import MAX_RELATED

        today = self._article("삼성전자 패키징", "삼성전자 패키징 소식")
        past = [
            self._article(f"삼성전자 패키징 {i}", "삼성전자 패키징", f"2026-01-{i:02d}")
            for i in range(1, MAX_RELATED + 6)
        ]
        related = find_related(today, past, COMPANIES, VOCAB, set())
        self.assertEqual(len(related), MAX_RELATED)
        dates = [r["date"] for r in related]
        self.assertEqual(dates, sorted(dates, reverse=True))


if __name__ == "__main__":
    unittest.main()
