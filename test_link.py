"""link.py 의 계산·판단 로직만 테스트한다. 표준 라이브러리 unittest 만 쓴다 (의존성 0개).

프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 link.py 를 구현한다.
"""

import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import link
from link import build_prompt, judge, load_done, shortlist, tokens, verify_links


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
        cands = [self._candidate(str(i), "같은 본문 문장이 이어진다") for i in range(15)]
        parsed = {
            "links": [{"url": str(i), "reason": "이유", "quote": "같은 본문 문장이 이어진다"} for i in range(15)]
        }
        self.assertEqual(len(verify_links(parsed, cands, limit=10)), 10)

    def test_drops_link_with_empty_reason(self):
        # 이유 없는 연결은 render.py 가 숨기던 것 그대로 두면 안 된다 — 코드가 먼저 버린다 (item 4).
        cands = [self._candidate("a", "GlobalFoundries 가 co-packaged optics 채택을 가속한다")]
        parsed = {"links": [{"url": "a", "reason": "", "quote": "co-packaged optics 채택을 가속"}]}
        self.assertEqual(verify_links(parsed, cands), [])

    def test_dedupes_same_url_keeps_first_occurrence(self):
        # 모델이 같은 과거 기사를 두 번 고르면 화면에 두 번 뜬다 — 처음 것만 남긴다 (item 5).
        cands = [self._candidate("a", "GlobalFoundries 가 co-packaged optics 채택을 가속한다")]
        parsed = {
            "links": [
                {"url": "a", "reason": "첫 번째 이유", "quote": "co-packaged optics 채택을 가속"},
                {"url": "a", "reason": "두 번째 이유", "quote": "co-packaged optics 채택을 가속"},
            ]
        }
        got = verify_links(parsed, cands)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["reason"], "첫 번째 이유")

    def test_drops_quote_shorter_than_min_length(self):
        # "CPO" 같은 2~3글자 인용구는 아무 문장에나 들어맞아 증거가 못 된다 (item 7).
        cands = [self._candidate("a", "CPO 기술을 도입한다고 밝혔다")]
        parsed = {"links": [{"url": "a", "reason": "이유", "quote": "CPO"}]}
        self.assertEqual(verify_links(parsed, cands), [])

    def test_keeps_quote_at_min_length_boundary(self):
        quote = "가나다라마바사아자차"  # 정확히 10글자, 원문에 그대로 있다
        cands = [self._candidate("a", f"{quote} 이런 이야기다")]
        parsed = {"links": [{"url": "a", "reason": "이유", "quote": quote}]}
        got = verify_links(parsed, cands)
        self.assertEqual(len(got), 1)


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

    def test_none_content_is_an_error_not_a_crash(self):
        # 제공자가 choices[0].message.content 로 null 을 주면 raw 가 None 이 된다.
        # _parse_json(None) 은 정규식이 문자열이 아닌 값을 받아 TypeError 를 낸다 —
        # 이게 judge() 밖으로 새 나가면 backfill 전체가 멈춘다. 그 기사만 비워야 한다 (item 6).
        links, err = judge(self.today, self.cands, "열쇠", call=lambda p, k: None)
        self.assertEqual(links, [])
        self.assertIsNotNone(err)


class TestLoadDone(unittest.TestCase):
    """한도가 도중에 끊긴 뒤 다시 실행해도 이미 검증된 연결을 잃지 않는다 (item 2·3)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir_ = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, day: str, articles: list[dict]) -> None:
        (self.dir_ / f"{day}.linked.json").write_text(
            json.dumps({"date": day, "articles": articles}, ensure_ascii=False), encoding="utf-8"
        )

    def test_missing_file_gives_empty_dict(self):
        self.assertEqual(load_done("2026-08-20", self.dir_), {})

    def test_reuses_judged_article_without_error(self):
        self._write("2026-08-20", [{"url": "a", "related": [{"date": "2026-05-01"}], "judged": True}])
        done = load_done("2026-08-20", self.dir_)
        self.assertIn("a", done)
        self.assertEqual(done["a"]["related"], [{"date": "2026-05-01"}])

    def test_excludes_article_with_link_error_even_if_judged(self):
        self._write("2026-08-20", [{"url": "a", "related": [], "judged": True, "link_error": "HTTP Error 429"}])
        self.assertEqual(load_done("2026-08-20", self.dir_), {})

    def test_excludes_old_data_without_judged_marker(self):
        # 옛 키워드 규칙이 남긴 파일은 judged 표시가 없다 — 다시 판정해야 한다 (item 3).
        self._write("2026-08-20", [{"url": "a", "related": []}])
        self.assertEqual(load_done("2026-08-20", self.dir_), {})


class TestLinkDayResume(unittest.TestCase):
    """link_day() 가 이미 끝난 기사는 모델을 다시 안 부르고, 안 끝난 것만 부른다 (item 2)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir_ = Path(self._tmp.name)
        self._orig_dir = link.ARTICLE_DIR
        link.ARTICLE_DIR = self.dir_

    def tearDown(self):
        link.ARTICLE_DIR = self._orig_dir
        self._tmp.cleanup()

    def test_only_unjudged_or_failed_articles_call_the_model(self):
        day = "2026-08-20"
        existing = {
            "date": day,
            "articles": [
                {
                    "url": "done", "title": "이미 끝난 기사", "summary": "s", "published": day,
                    "related": [
                        {"date": "2026-05-01", "title": "과거", "url": "p", "reason": "이유", "quote": "인용구10자이상"}
                    ],
                    "judged": True,
                },
                {
                    "url": "failed", "title": "실패했던 기사", "summary": "s", "published": day,
                    "related": [], "link_error": "HTTP Error 429: Too Many Requests",
                },
            ],
        }
        (self.dir_ / f"{day}.linked.json").write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

        picked = [
            {"url": "done", "title": "이미 끝난 기사", "summary": "s", "published": day},
            {"url": "failed", "title": "실패했던 기사", "summary": "s", "published": day},
        ]
        calls: list[str] = []

        def fake_judge(article, candidates, key, call=None):
            calls.append(article["url"])
            return [], None

        with unittest.mock.patch("pick.select_day", return_value=(picked, [], [])), \
                unittest.mock.patch.object(link, "_load_key", return_value="k"), \
                unittest.mock.patch.object(link, "_load_all_past", return_value=[]), \
                unittest.mock.patch.object(link, "judge", fake_judge), \
                unittest.mock.patch.object(link.time, "sleep", lambda s: None):
            linked = link.link_day(day)

        # 이미 끝난 기사("done")는 다시 모델을 부르지 않고 저장된 related 를 그대로 쓴다.
        self.assertEqual(calls, ["failed"])
        done_entry = next(a for a in linked if a["url"] == "done")
        self.assertEqual(done_entry["related"][0]["reason"], "이유")
        failed_entry = next(a for a in linked if a["url"] == "failed")
        self.assertTrue(failed_entry["judged"])  # 재판정 성공 — 새 judged 표시가 붙는다


if __name__ == "__main__":
    unittest.main()
