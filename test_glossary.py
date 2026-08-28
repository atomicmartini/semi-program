"""glossary.py 의 용어 찾기·링크 로직만 테스트한다. 네트워크를 쓰지 않는다.

프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 glossary.py 를 고친다
(docs/slices/08-개념-사전-채우기.md).
"""

import unittest

from glossary import link_terms, parse_source, render_entries


def term(name: str, *aliases: str) -> dict:
    """link_terms 가 쓰는 최소한의 모양. 긴 것부터 찾도록 정렬해 둔다."""
    return {
        "id": name.lower(),
        # read_terms 가 만드는 것과 같은 정렬
        "patterns": sorted({name, *aliases}, key=len, reverse=True),
    }


class TestLinkTermsWordBoundary(unittest.TestCase):
    """영문 용어는 낱말 경계를 요구한다.

    companies.py 가 이미 고친 버그와 같은 것이다 — `intel` 이 `intelligent` 안에서
    잡혀 인텔 기사 23건 중 7건이 거짓이었다. ASIC·SoC·SiP 는 더 짧아서 더 위험하다.
    """

    def test_asic_not_matched_inside_basic(self):
        out = link_terms("This is a basic test", [term("ASIC")])
        self.assertEqual(out, "This is a basic test")

    def test_soc_not_matched_inside_association(self):
        out = link_terms("the association said", [term("SoC")])
        self.assertEqual(out, "the association said")

    def test_sip_not_matched_inside_gossip(self):
        out = link_terms("just gossip", [term("SiP")])
        self.assertEqual(out, "just gossip")

    def test_english_term_matched_as_whole_word(self):
        out = link_terms("a new ASIC design", [term("ASIC")])
        self.assertIn('href="concepts.html#asic"', out)
        self.assertIn(">ASIC</a>", out)

    def test_matching_ignores_case(self):
        out = link_terms("a new asic design", [term("ASIC")])
        self.assertIn('href="concepts.html#asic"', out)

    def test_term_matched_next_to_punctuation(self):
        out = link_terms("uses an ASIC, not a GPU", [term("ASIC")])
        self.assertIn(">ASIC</a>", out)


class TestLinkTermsKorean(unittest.TestCase):
    """한국어는 조사가 붙으므로 낱말 경계를 걸면 못 찾는다."""

    def test_korean_term_matched_with_particle(self):
        out = link_terms("패키징을 맡는다", [term("패키징")])
        self.assertIn('href="concepts.html#패키징"', out)

    def test_korean_term_matched_bare(self):
        out = link_terms("패키징 공정", [term("패키징")])
        self.assertIn(">패키징</a>", out)


class TestLinkTermsSelection(unittest.TestCase):
    def test_longer_term_wins_over_shorter(self):
        """HBM4 가 HBM 보다 먼저 잡혀야 한다."""
        out = link_terms("HBM4 양산", [term("HBM4"), term("HBM")])
        self.assertIn(">HBM4</a>", out)
        self.assertNotIn(">HBM</a>", out)

    def test_links_only_first_occurrence(self):
        out = link_terms("ASIC and ASIC again", [term("ASIC")])
        self.assertEqual(out.count("<a class=\"term\""), 1)

    def test_page_prefix_is_applied(self):
        out = link_terms("an ASIC", [term("ASIC")], page_prefix="../")
        self.assertIn('href="../concepts.html#asic"', out)

    def test_no_terms_returns_text_unchanged(self):
        self.assertEqual(link_terms("아무것도 없다", []), "아무것도 없다")


class TestParseSource(unittest.TestCase):
    """출처 칸에서 링크와 꼬리표를 함께 읽는다.

    꼬리표가 데이터에만 있고 화면에 안 나오면 `[공식]` 과 `[2차]` 를 가른 의미가 없다.
    """

    def test_reads_label_and_url(self):
        label, url, tag = parse_source("[JEDEC JESD235D](https://example.com/a) `[공식]`")
        self.assertEqual(label, "JEDEC JESD235D")
        self.assertEqual(url, "https://example.com/a")

    def test_reads_official_tag(self):
        _, _, tag = parse_source("[삼성 용어사전](https://example.com/a) `[공식]`")
        self.assertEqual(tag, "공식")

    def test_reads_secondary_tag(self):
        _, _, tag = parse_source("[Synopsys 해설](https://example.com/b) `[2차]`")
        self.assertEqual(tag, "2차")

    def test_missing_tag_is_empty(self):
        _, _, tag = parse_source("[출처만 있음](https://example.com/c)")
        self.assertEqual(tag, "")

    def test_no_link_returns_empty(self):
        self.assertEqual(parse_source("출처 없음"), ("", "", ""))


class TestRenderEntries(unittest.TestCase):
    def entry(self, tag: str) -> str:
        return render_entries(
            [
                {
                    "id": "hbm",
                    "term": "HBM",
                    "english": "HBM",
                    "category": "메모리",
                    "definition": "광폭 인터페이스 D램.",
                    "source_label": "JEDEC",
                    "source_url": "https://example.com/a",
                    "source_tag": tag,
                    "checked": "2026-08-29",
                }
            ]
        )

    def test_shows_official_tag(self):
        self.assertIn("공식", self.entry("공식"))

    def test_shows_secondary_tag(self):
        self.assertIn("2차", self.entry("2차"))

    def test_no_tag_renders_without_crashing(self):
        out = self.entry("")
        self.assertIn("JEDEC", out)
        self.assertNotIn("[]", out)


if __name__ == "__main__":
    unittest.main()
