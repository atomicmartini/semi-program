"""link.py 의 계산·판단 로직만 테스트한다. 표준 라이브러리 unittest 만 쓴다 (의존성 0개).

프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 link.py 를 구현한다.
"""

import unittest

from companies import companies_mentioned
from link import shortlist, tokens

COMPANIES = {
    "삼성전자": "삼성전자",
    "삼성": "삼성전자",
    "tsmc": "TSMC",
    "엔비디아": "엔비디아",
    "nvidia": "엔비디아",
    "kla": "KLA",
    "qnity": "Qnity",
}


class TestCompaniesMentioned(unittest.TestCase):
    def test_finds_canonical_company_by_alias(self):
        text = "삼성전자가 tsmc 와 경쟁한다"
        self.assertEqual(companies_mentioned(text, COMPANIES), {"삼성전자", "TSMC"})

    def test_no_match_returns_empty_set(self):
        self.assertEqual(companies_mentioned("반도체 뉴스", COMPANIES), set())


class TestTokens(unittest.TestCase):
    def test_splits_korean_and_english(self):
        got = tokens("HBM 패키징 co-packaged optics")
        self.assertIn("hbm", got)
        self.assertIn("패키징", got)
        self.assertIn("co-packaged", got)

    def test_ignores_single_letter_noise(self):
        self.assertEqual(tokens("a b c"), [])


class TestShortlist(unittest.TestCase):
    """후보 추리기는 '놓치지 않는 일'만 한다. 가려내는 것은 모델이 한다."""

    def _article(self, title, summary, published="2026-08-20"):
        return {"url": title, "title": title, "summary": summary, "published": published}

    def test_rare_word_beats_common_word(self):
        # 지금 문제 그 자체 — '메모리'만 겹치는 기사가 CPO 기사를 밀어내면 안 된다
        today = self._article("CPO 청사진", "co-packaged optics 로 메모리를 빛으로 잇는다")
        cpo = self._article("GlobalFoundries co-packaged optics", "co-packaged optics 채택", "2026-05-05")
        common = self._article("DDR4 가격", "메모리 가격이 올랐다", "2026-07-01")
        filler = [self._article(f"메모리 소식 {i}", "메모리 이야기", "2026-06-01") for i in range(8)]
        got = shortlist(today, [common, cpo, *filler], limit=15)
        self.assertEqual(got[0]["url"], cpo["url"])

    def test_respects_limit(self):
        today = self._article("HBM", "HBM 이야기")
        past = [self._article(f"HBM {i}", "HBM 이야기", "2026-07-01") for i in range(30)]
        self.assertEqual(len(shortlist(today, past, limit=15)), 15)

    def test_empty_past_gives_empty_list(self):
        self.assertEqual(shortlist(self._article("제목", "요약"), [], limit=15), [])


if __name__ == "__main__":
    unittest.main()
