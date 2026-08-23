"""extract.py 의 판정 로직만 테스트한다. 모델을 부르지 않는다.

판정은 코드가 한다 (CLAUDE.md). 모델이 틀려도 코드가 막아야 한다.
"""

import unittest

from extract import resolve_category
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


if __name__ == "__main__":
    unittest.main()
