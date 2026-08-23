"""extract.py 의 판정 로직만 테스트한다. 모델을 부르지 않는다.

판정은 코드가 한다 (CLAUDE.md). 모델이 틀려도 코드가 막아야 한다.
"""

import unittest

import urllib.error

from extract import ModelError, resolve_category, should_retry
from filter import UNCLASSIFIED

CATEGORIES = ["패키징", "파운드리·공정", "메모리", "장비·소재", UNCLASSIFIED]


class TestResolveCategory(unittest.TestCase):
    def test_uses_model_answer_when_valid(self):
        self.assertEqual(resolve_category("메모리", "장비·소재", CATEGORIES), "메모리")

    def test_falls_back_to_keyword_when_model_says_unclassified(self):
        # super-120b 가 영어 기사를 미분류로 틀렸는데 filter.py 는 장비·소재로 맞혔다.
        # 모델 답이 키워드 분류를 덮어쓰면 정보를 잃는다.
        self.assertEqual(resolve_category(UNCLASSIFIED, "장비·소재", CATEGORIES), "장비·소재")

    def test_falls_back_when_model_invents_a_category(self):
        # 카테고리를 임의로 늘리지 않는다 (CLAUDE.md)
        self.assertEqual(resolve_category("반도체일반", "메모리", CATEGORIES), "메모리")

    def test_stays_unclassified_when_both_are_unclassified(self):
        self.assertEqual(
            resolve_category(UNCLASSIFIED, UNCLASSIFIED, CATEGORIES), UNCLASSIFIED
        )

    def test_handles_missing_model_answer(self):
        self.assertEqual(resolve_category(None, "패키징", CATEGORIES), "패키징")


class TestShouldRetry(unittest.TestCase):
    """14일치를 돌렸더니 62건 중 22건이 429·502 로 실패했다. 쉬었다 다시 하면 되는 것들이다."""

    def _http(self, code: int) -> urllib.error.HTTPError:
        return urllib.error.HTTPError("u", code, "msg", {}, None)

    def test_retries_on_rate_limit(self):
        self.assertTrue(should_retry(self._http(429)))

    def test_retries_on_upstream_overload(self):
        self.assertTrue(should_retry(self._http(502)))
        self.assertTrue(should_retry(self._http(503)))

    def test_retries_on_error_body_with_200(self):
        # 상위 서버 과부하는 HTTP 200 에 error 본문으로 오기도 한다
        self.assertTrue(should_retry(ModelError('{"error": {"code": 502}}')))

    def test_does_not_retry_on_bad_key(self):
        # 401 은 쉬었다 해도 안 된다. 다시 해 봐야 시간만 쓴다
        self.assertFalse(should_retry(self._http(401)))

    def test_does_not_retry_on_bad_request(self):
        self.assertFalse(should_retry(self._http(400)))


if __name__ == "__main__":
    unittest.main()
