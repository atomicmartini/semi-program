"""link.py 의 계산·판단 로직만 테스트한다. 표준 라이브러리 unittest 만 쓴다 (의존성 0개).

프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 link.py 를 구현한다.
"""

import unittest

from companies import companies_mentioned
from link import build_prompt, judge, shortlist, tokens, verify_links

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


class TestVerifyLinks(unittest.TestCase):
    """지어낸 연결을 막는 방어선. 인용구가 원문에 없으면 그 연결은 버린다 (CLAUDE.md)."""

    def _candidate(self, url, summary, published="2026-05-05"):
        return {"url": url, "title": f"제목 {url}", "summary": summary, "published": published}

    def test_keeps_link_whose_quote_is_in_the_source(self):
        cands = [self._candidate("a", "GlobalFoundries 가 co-packaged optics 채택을 가속한다")]
        parsed = {"links": [{"url": "a", "reason": "같은 CPO 채택 흐름", "quote": "co-packaged optics 채택을 가속"}]}
        got = verify_links(parsed, cands)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["reason"], "같은 CPO 채택 흐름")

    def test_drops_link_whose_quote_is_invented(self):
        cands = [self._candidate("a", "GlobalFoundries 가 co-packaged optics 채택을 가속한다")]
        parsed = {"links": [{"url": "a", "reason": "그럴듯한 이유", "quote": "원문에 없는 문장이다"}]}
        self.assertEqual(verify_links(parsed, cands), [])

    def test_drops_link_to_url_not_in_candidates(self):
        cands = [self._candidate("a", "본문")]
        parsed = {"links": [{"url": "없는주소", "reason": "이유", "quote": "본문"}]}
        self.assertEqual(verify_links(parsed, cands), [])

    def test_broken_answer_gives_empty_list(self):
        self.assertEqual(verify_links(None, [self._candidate("a", "본문")]), [])

    def test_respects_limit(self):
        cands = [self._candidate(str(i), "같은 본문 문장") for i in range(15)]
        parsed = {"links": [{"url": str(i), "reason": "이유", "quote": "같은 본문"} for i in range(15)]}
        self.assertEqual(len(verify_links(parsed, cands, limit=10)), 10)


class TestBuildPrompt(unittest.TestCase):
    def test_includes_candidate_urls_and_trims_summary(self):
        today = {"url": "t", "title": "오늘", "summary": "오늘 요약", "published": "2026-08-20"}
        cands = [{"url": "a", "title": "과거", "summary": "가" * 500, "published": "2026-05-05"}]
        prompt = build_prompt(today, cands)
        self.assertIn("a", prompt)
        self.assertIn("오늘", prompt)
        self.assertNotIn("가" * 400, prompt)   # 앞 300자만 넣는다


class TestJudge(unittest.TestCase):
    """모델을 진짜로 부르지 않는다 — 호출 함수를 바꿔 끼운다."""

    def setUp(self):
        self.cands = [{"url": "a", "title": "과거", "summary": "co-packaged optics 채택", "published": "2026-05-05"}]
        self.today = {"url": "t", "title": "오늘", "summary": "CPO 청사진", "published": "2026-08-20"}

    def test_returns_verified_links_on_good_answer(self):
        answer = '{"links": [{"url": "a", "reason": "같은 CPO 흐름", "quote": "co-packaged optics 채택"}]}'
        links, err = judge(self.today, self.cands, "열쇠", call=lambda p, k: answer)
        self.assertIsNone(err)
        self.assertEqual(len(links), 1)

    def test_reports_error_when_model_fails(self):
        def boom(prompt, key):
            raise RuntimeError("모델이 죽었다")
        links, err = judge(self.today, self.cands, "열쇠", call=boom)
        self.assertEqual(links, [])
        self.assertIn("모델이 죽었다", err)   # 실패를 조용히 넘기지 않는다 (CLAUDE.md)

    def test_broken_json_is_an_error_not_a_crash(self):
        links, err = judge(self.today, self.cands, "열쇠", call=lambda p, k: "말이 안 되는 답")
        self.assertEqual(links, [])
        self.assertIsNotNone(err)

    def test_no_candidates_means_no_model_call(self):
        called = []
        links, err = judge(self.today, [], "열쇠", call=lambda p, k: called.append(1) or "{}")
        self.assertEqual((links, err, called), ([], None, []))

    def test_candidate_missing_key_is_an_error_not_a_crash(self):
        # 중간에 끊긴 이전 실행이 남긴 레코드처럼, 후보에 summary 가 빠진 경우 —
        # build_prompt 가 KeyError 를 내도 그 기사만 비우고 넘어가야 한다 (CLAUDE.md).
        broken = [{"url": "a", "title": "과거"}]  # summary 없음
        called = []
        links, err = judge(self.today, broken, "열쇠", call=lambda p, k: called.append(1) or "{}")
        self.assertEqual(links, [])
        self.assertIsNotNone(err)
        self.assertEqual(called, [])  # 프롬프트를 못 만들었으니 모델을 부르지 않는다


if __name__ == "__main__":
    unittest.main()
