# 수집처

> **확인일: 2026-08-22** — 아래 주소는 모두 실제로 받아 보고 동작을 확인했다.
> 코드에 주소를 박지 않는다 (`AGENTS.md` D2). 사이트를 더하려면 이 표에 줄을 추가한다.

## 쓰는 곳

| 이름 | 주소 | 언어 | 등급 | 받은 건수 | 확인일 | 비고 |
| --- | --- | --- | --- | --- | --- | --- |
| 더일렉 반도체 | `https://www.thelec.kr/rss/S1N2.xml` | 한국어 | `[2차]` | 20 | 2026-08-22 | 반도체 섹션 전용. 잡음 적음 |
| Semiconductor Digest (패키징) | `https://www.semiconductor-digest.com/category/packaging/feed/` | 영어 | `[2차]` | 100 | 2026-08-22 | 패키징 카테고리 |
| Semi Engineering | `https://semiengineering.com/feed/` | 영어 | `[2차]` | 10 | 2026-08-22 | 전체 피드 (아래 '안 쓰는 곳' 참조) |
| EE Times | `https://www.eetimes.com/feed/` | 영어 | `[2차]` | 10 | 2026-08-22 | 업계 종합 |
| 3D InCites | `https://3dincites.com/feed/` | 영어 | `[2차]` | 10 | 2026-08-22 | 첨단 패키징 전문 |

## 후보 (아직 안 씀)

| 이름 | 주소 | 받은 건수 | 확인일 | 왜 보류인가 |
| --- | --- | --- | --- | --- |
| 더일렉 소재장비 | `https://www.thelec.kr/rss/S1N3.xml` | 20 | 2026-08-22 | 장비·소재 카테고리 보강용 |
| SemiWiki | `https://semiwiki.com/feed/` | 5 | 2026-08-22 | 건수가 적음. 분석 글 위주 |
| Tom's Hardware | `https://www.tomshardware.com/feeds/all` | 50 | 2026-08-22 | 소비자 PC 중심이라 잡음 많음 |

## 안 쓰는 곳 — 확인했으나 동작하지 않음

| 이름 | 주소 | 확인일 | 결과 |
| --- | --- | --- | --- |
| Semi Engineering 패키징 카테고리 | `https://semiengineering.com/category-main-page-packaging-test-electronic-systems/feed/` | 2026-08-22 | HTTP 200 이나 **기사 0건**. 전체 피드 + 키워드 거르기로 대체 |
| TrendForce 보도자료 | `https://www.trendforce.com/presscenter/rss` | 2026-08-22 | HTTP 404 |
| AnandTech | `https://www.anandtech.com/rss/` | 2026-08-22 | 기사 0건 (폐간) |
| ZDNet Korea | `https://zdnet.co.kr/news/news_xml.asp` | 2026-08-22 | HTTP 404 |
| 디지털데일리 | `https://www.ddaily.co.kr/rss/allArticle.xml` | 2026-08-22 | HTML 반환, RSS 아님 |

## 아직 없는 것 — 채워야 할 자리

- [ ] **`[공식]` 등급 출처가 하나도 없다.** 위 5곳은 전부 언론(`[2차]`)이다.
      `AGENTS.md` R1 상 `[2차]` 만으로는 관계를 `확정` 으로 올릴 수 없으므로,
      기업 IR·보도자료 피드를 최소 한 곳 넣어야 한다.
      후보: 삼성전자 뉴스룸, SK하이닉스 뉴스룸, TSMC·Intel·NVIDIA 프레스룸.
- [ ] 각 피드가 하루에 몇 건씩 새로 올라오는지 (며칠 돌려 봐야 안다)
- [ ] 피드가 주는 요약 길이가 관계 추출에 충분한지 (더일렉은 250자 내외 확인)
