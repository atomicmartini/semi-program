"""archive.py 의 파싱·고르기 로직만 테스트한다. 네트워크를 쓰지 않는다.

HTML 조각은 2026-08-23 에 실제 목록 페이지에서 그대로 떼어 온 것이다.
프롬프트 순서: 이 테스트를 먼저 실행해 실패를 확인한 뒤 archive.py 를 구현한다.
"""

import unittest

from archive import parse_digest_list, parse_thelec_list, pick_monthly

THELEC_HTML = """
<ul class="altlist-webzine">
  <li class="altlist-webzine-item">
    <a href="https://www.thelec.kr/news/articleView.html?idxno=32712" class="altlist-image"><img src="x.jpg"/></a>
    <div class="altlist-webzine-content">
      <H2 class="altlist-subject">
        <a href="https://www.thelec.kr/news/articleView.html?idxno=32712" target="_top">
          SK하이닉스, 메모리 업계 최초 자동차산업 정보보안인증 &lsquo;TISAX&rsquo; 획득
        </a>
      </H2>
      <p class="altlist-summary">
        SK하이닉스가 메모리 업계 최초로 글로벌 자동차산업 정보 보안 인증인 TISAX를 획득했다고 6일 밝혔다.
      </p>
      <div class="altlist-info">
        <div class="altlist-info-item">이선행 기자</div>
        <div class="altlist-info-item">2025-02-06 </div>
      </div>
    </div>
  </li>
  <li class="altlist-webzine-item">
    <div class="altlist-webzine-content">
      <H2 class="altlist-subject">
        <a href="https://www.thelec.kr/news/articleView.html?idxno=32711" target="_top">딥엑스, 올해의 제품상 수상</a>
      </H2>
      <p class="altlist-summary">딥엑스가 상을 받았다.</p>
      <div class="altlist-info">
        <div class="altlist-info-item">김기자</div>
        <div class="altlist-info-item">2025-02-05 </div>
      </div>
    </div>
  </li>
</ul>
"""

DIGEST_HTML = """
<div class="post style3 post-30882 type-post status-publish format-standard hentry category-packaging">
  <header class="post-title entry-header">
    <h5 class="entry-title" itemprop="name headline"><a href="https://www.semiconductor-digest.com/nomis-power-unveils/" title="NoMIS Power Unveils Major Advancement">NoMIS Power Unveils Major Advancement</a></h5>
  </header>
  <aside class="post-bottom-meta">
    <strong itemprop="author" class="author vcard"><a href="/author/x/" rel="author">Shannon Davis</a></strong>
    <div class="time">May 1, 2025</div>
  </aside>
  <div class="post-content entry-content small">
    <p>NoMIS Power has announced a key advancement in its next-generation SiC MOSFET platform.</p>
  </div>
</div>
<div class="post style3 post-30880 type-post status-publish format-standard hentry category-packaging">
  <header class="post-title entry-header">
    <h5 class="entry-title" itemprop="name headline"><a href="https://www.semiconductor-digest.com/second-one/" title="Second One">Second One</a></h5>
  </header>
  <aside class="post-bottom-meta">
    <div class="time">April 28, 2025</div>
  </aside>
  <div class="post-content entry-content small">
    <p>Second summary.</p>
  </div>
</div>
"""


class TestParseThelec(unittest.TestCase):
    def setUp(self):
        self.items = parse_thelec_list(THELEC_HTML)

    def test_finds_all_articles(self):
        self.assertEqual(len(self.items), 2)

    def test_extracts_fields(self):
        a = self.items[0]
        self.assertEqual(a["url"], "https://www.thelec.kr/news/articleView.html?idxno=32712")
        self.assertIn("SK하이닉스", a["title"])
        self.assertIn("TISAX", a["summary"])
        self.assertEqual(a["published"][:10], "2025-02-06")

    def test_unescapes_entities_in_title(self):
        # &lsquo; 같은 엔티티가 그대로 남으면 화면에 깨져 보인다
        self.assertNotIn("&lsquo;", self.items[0]["title"])


THELEC_RECENT_HTML = """
<ul class="altlist-webzine">
  <li class="altlist-webzine-item">
    <div class="altlist-webzine-content">
      <H2 class="altlist-subject">
        <a href="https://www.thelec.kr/news/articleView.html?idxno=61226" target="_top">삼성전자, 주주환원</a>
      </H2>
      <p class="altlist-summary">삼성전자가 주주환원을 의결했다.</p>
      <div class="altlist-info">
        <div class="altlist-info-item">이준 기자</div>
        <div class="altlist-info-item">08-21 18:08</div>
      </div>
    </div>
  </li>
</ul>
"""


class TestParseThelecRecentDate(unittest.TestCase):
    """최근 쪽은 날짜를 '08-21 18:08' 로 쓴다 — 연도가 없다.

    이걸 못 읽으면 시작 쪽을 찾는 이분 탐색이 통째로 무너진다 (실제로 겪음).
    """

    def test_parses_year_less_date(self):
        items = parse_thelec_list(THELEC_RECENT_HTML)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["published"][5:10], "08-21")

    def test_keeps_raw_text(self):
        items = parse_thelec_list(THELEC_RECENT_HTML)
        self.assertEqual(items[0]["published_raw"], "08-21 18:08")


class TestParseDigest(unittest.TestCase):
    def setUp(self):
        self.items = parse_digest_list(DIGEST_HTML)

    def test_finds_all_articles(self):
        self.assertEqual(len(self.items), 2)

    def test_extracts_fields(self):
        a = self.items[0]
        self.assertEqual(a["url"], "https://www.semiconductor-digest.com/nomis-power-unveils/")
        self.assertEqual(a["title"], "NoMIS Power Unveils Major Advancement")
        self.assertIn("SiC MOSFET", a["summary"])

    def test_parses_long_month_name_date(self):
        self.assertEqual(self.items[0]["published"][:10], "2025-05-01")
        self.assertEqual(self.items[1]["published"][:10], "2025-04-28")


class TestPickMonthly(unittest.TestCase):
    def _articles(self, month: str, n: int) -> list[dict]:
        return [
            {"url": f"{month}-{i}", "published": f"{month}-{i:02d}T00:00:00+09:00"}
            for i in range(1, n + 1)
        ]

    def test_caps_per_month(self):
        picked = pick_monthly(self._articles("2025-11", 20), per_month=5)
        self.assertEqual(len(picked), 5)

    def test_keeps_all_when_fewer_than_cap(self):
        # 억지로 채우지 않는다 — 있는 만큼만
        picked = pick_monthly(self._articles("2025-11", 3), per_month=5)
        self.assertEqual(len(picked), 3)

    def test_spreads_across_the_month(self):
        # 5건이 같은 날에 몰리면 '이어지는 흐름' 재료로 쓸모가 없다
        picked = pick_monthly(self._articles("2025-11", 20), per_month=5)
        days = sorted(a["published"][8:10] for a in picked)
        self.assertGreater(len(set(days)), 3)

    def test_handles_multiple_months_independently(self):
        articles = self._articles("2025-11", 10) + self._articles("2025-12", 10)
        picked = pick_monthly(articles, per_month=5)
        self.assertEqual(len(picked), 10)


if __name__ == "__main__":
    unittest.main()
