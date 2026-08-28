"""companies.py 의 읽기·묶기 로직만 테스트한다. 네트워크를 쓰지 않는다.

프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 companies.py 를 구현한다.
"""

import unittest

from companies import (
    CATEGORY_ORDER,
    by_category,
    companies_mentioned,
    parse_companies,
    slug,
)

TABLE = """
## 정식명과 별칭

| 정식명 | 별칭 | 분류 | 영문 | 국가 | 설명 | 출처 | 확인일 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 삼성전자 | Samsung Electronics, Samsung, 삼성 | 메모리, 파운드리 | Samsung Electronics | 한국 | 메모리·시스템LSI·파운드리를 모두 한다. | [삼성 사업영역](https://example.com/a) `[공식]` | 2026-08-24 |
| SK하이닉스 | SK Hynix, 하이닉스 | 메모리 | SK hynix | 한국 |  |  |  |
| TSMC | Taiwan Semiconductor | 파운드리 | TSMC | 대만 | 순수 위탁생산 모델을 개척했다. | [TSMC 회사소개](https://example.com/b) `[공식]` | 2026-08-24 |

## 미확인

(아직 없음)
"""


class TestParseCompanies(unittest.TestCase):
    def setUp(self):
        self.rows = parse_companies(TABLE)
        self.by_name = {c["name"]: c for c in self.rows}

    def test_reads_every_row(self):
        self.assertEqual(len(self.rows), 3)

    def test_splits_aliases(self):
        self.assertIn("samsung", self.by_name["삼성전자"]["aliases"])

    def test_splits_multiple_categories(self):
        # 삼성전자는 메모리이자 파운드리다 — 양쪽에 나와야 한다
        self.assertEqual(self.by_name["삼성전자"]["categories"], ["메모리", "파운드리"])

    def test_reads_single_category_as_list(self):
        self.assertEqual(self.by_name["TSMC"]["categories"], ["파운드리"])

    def test_keeps_english_and_country(self):
        self.assertEqual(self.by_name["TSMC"]["english"], "TSMC")
        self.assertEqual(self.by_name["TSMC"]["country"], "대만")

    def test_reads_source_link_and_checked_date(self):
        c = self.by_name["삼성전자"]
        self.assertEqual(c["source_url"], "https://example.com/a")
        self.assertEqual(c["source_label"], "삼성 사업영역")
        self.assertEqual(c["checked"], "2026-08-24")


class TestMissingSource(unittest.TestCase):
    """개념 사전과 다르게 간다 — 회사는 항목을 빼지 않고 설명만 비운다.

    목록 자체가 값이라, 출처가 없다고 회사를 감추면 분류표가 망가진다
    (docs/slices/07-기업-탭.md).
    """

    def setUp(self):
        self.by_name = {c["name"]: c for c in parse_companies(TABLE)}

    def test_company_without_source_is_still_listed(self):
        self.assertIn("SK하이닉스", self.by_name)

    def test_its_description_is_empty(self):
        self.assertEqual(self.by_name["SK하이닉스"]["description"], "")

    def test_description_is_dropped_when_source_is_missing(self):
        # 설명만 있고 출처가 없으면 설명을 싣지 않는다
        table = TABLE.replace(
            "| SK하이닉스 | SK Hynix, 하이닉스 | 메모리 | SK hynix | 한국 |  |  |  |",
            "| SK하이닉스 | SK Hynix | 메모리 | SK hynix | 한국 | 출처 없는 설명 |  |  |",
        )
        rows = {c["name"]: c for c in parse_companies(table)}
        self.assertEqual(rows["SK하이닉스"]["description"], "")


class TestSlug(unittest.TestCase):
    """주소에 한글이 안 들어가게 영문으로 만든다 (glossary.py 와 같은 방식)."""

    def test_lowercases_and_hyphenates(self):
        self.assertEqual(slug("Samsung Electronics"), "samsung-electronics")

    def test_handles_single_word(self):
        self.assertEqual(slug("TSMC"), "tsmc")

    def test_strips_punctuation(self):
        self.assertEqual(slug("SK hynix, Inc."), "sk-hynix-inc")


class TestByCategory(unittest.TestCase):
    def setUp(self):
        self.grouped = by_category(parse_companies(TABLE))

    def test_company_appears_in_every_category_it_belongs_to(self):
        self.assertIn("삼성전자", [c["name"] for c in self.grouped["메모리"]])
        self.assertIn("삼성전자", [c["name"] for c in self.grouped["파운드리"]])

    def test_keeps_declared_category_order(self):
        self.assertEqual(list(self.grouped), [c for c in CATEGORY_ORDER])

    def test_empty_category_is_kept_as_empty_list(self):
        # 빈 칸도 보여준다 — 무엇이 비었는지가 정보다 (칩 필터와 같은 판단)
        self.assertEqual(self.grouped["OSAT·후공정"], [])


class TestCompaniesMentioned(unittest.TestCase):
    """link.py 에서 옮겨 온 함수. 회사 로직은 회사 파일에 둔다."""

    def test_finds_by_alias(self):
        cmap = {"삼성전자": "삼성전자", "삼성": "삼성전자", "tsmc": "TSMC"}
        self.assertEqual(companies_mentioned("삼성이 tsmc 와", cmap), {"삼성전자", "TSMC"})


if __name__ == "__main__":
    unittest.main()
