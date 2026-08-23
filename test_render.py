"""render.py 의 흐름 블록 정렬 로직만 테스트한다. 표준 라이브러리 unittest 만 쓴다.

프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 render.py 를 구현한다.
"""

import unittest

from render import render_thread


class TestRenderThread(unittest.TestCase):
    def test_empty_returns_empty_string(self):
        self.assertEqual(render_thread([]), "")

    def test_orders_oldest_first(self):
        # link.py 는 최신순으로 준다 — 화면에서는 타임라인이라 오래된 것부터 보여야 한다
        related = [
            {"date": "2026-08-21", "title": "B", "url": "u2"},
            {"date": "2026-08-19", "title": "A", "url": "u1"},
        ]
        html = render_thread(related)
        self.assertLess(html.index("08-19"), html.index("08-21"))

    def test_links_to_original_article(self):
        related = [{"date": "2026-08-19", "title": "A", "url": "https://example.com/a"}]
        html = render_thread(related)
        self.assertIn('href="https://example.com/a"', html)

    def test_shows_count(self):
        related = [
            {"date": "2026-08-19", "title": "A", "url": "u1"},
            {"date": "2026-08-20", "title": "B", "url": "u2"},
        ]
        html = render_thread(related)
        self.assertIn("2건", html)


if __name__ == "__main__":
    unittest.main()
