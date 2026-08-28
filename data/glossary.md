# 개념 사전

> 기사에 나오는 용어의 설명. **뉴스와 성격이 다른 자료다.**
> 뉴스 사실은 기사에서만 가져오지만, 용어 설명은 기사에 없는 지식이다.
> 그래서 **사람이 출처를 확인해 넣는다. 모델이 즉석에서 만들지 않는다.**
>
> **출처와 확인일이 없는 항목은 화면에 싣지 않는다** (`CLAUDE.md`).

## 출처 꼬리표

| 꼬리표 | 무엇 | 예 |
| --- | --- | --- |
| `[공식]` | 표준화 기구, 또는 **그 기술을 실제로 만드는 회사**의 공식 용어사전·제품 페이지 | JEDEC 규격, 삼성반도체 용어사전, SK하이닉스 제품 페이지, 앰코 패키징 페이지 |
| `[2차]` | 그 밖의 통용 출처 — 업체가 쓴 해설 글, 외부 전문가 칼럼 | Synopsys 용어 해설, 뉴스룸에 실린 교수 칼럼, 퀄컴 블로그 |

**공식이 없다고 항목을 빼지는 않는다.** 대신 어디서 온 설명인지 화면에 드러낸다.
칼럼·블로그는 글쓴이 개인 의견이라고 스스로 밝히는 경우가 있어 `[공식]` 으로 올리지 않는다.

## 등재된 개념

| 용어 | 영문 | 별칭 | 분류 | 설명 | 출처 | 확인일 |
| --- | --- | --- | --- | --- | --- | --- |
| 패키징 | Packaging | packaging, 후공정 | 패키징 | 칩을 외부 환경으로부터 보호하고 단자 간 연결을 위해 전기적으로 포장하는 공정. 반도체 제조의 마지막 단계로 상호배선·전력 공급·방열을 담당한다. | [삼성반도체 용어사전 — 패키징](https://semiconductor.samsung.com/kr/support/tools-resources/dictionary/semiconductor-glossary-packaging/) `[공식]` | 2026-08-23 |
| 웨이퍼 | Wafer | wafer, wafers | 장비·소재 | 실리콘 등의 단결정 기둥을 얇게 자른 원판. 그 위에 전자회로를 새겨 칩을 만든다. 직경이 클수록 버리는 부분이 적어 효율이 높다. | [삼성반도체 용어사전 — 웨이퍼](https://semiconductor.samsung.com/kr/support/tools-resources/dictionary/semiconductor-glossary-wafer/) `[공식]` | 2026-08-23 |
| 파운드리 | Foundry | foundry, foundries | 파운드리·공정 | 반도체 제조 과정만 전담하는 위탁 생산업체. 직접 설계하지 않고 외부 기업의 설계를 받아 생산한다. 설계 전문 기업(팹리스)이 생산시설 투자를 피하려고 활용한다. | [삼성반도체 용어사전 — 파운드리](https://semiconductor.samsung.com/kr/support/tools-resources/dictionary/semiconductor-glossary-foundry/) `[공식]` | 2026-08-23 |
| D램 | DRAM | dram, 디램 | 메모리 | 용량이 크고 속도가 빨라 컴퓨터의 주력 메모리로 쓰이는 휘발성 메모리. 커패시터의 전하가 새기 때문에 일정 시간마다 데이터를 되살리는 '리프레시'가 필요하다. | [삼성반도체 용어사전 — D램](https://semiconductor.samsung.com/kr/support/tools-resources/dictionary/semiconductor-glossary-dram/) `[공식]` | 2026-08-23 |
| 수율 | Yield | yield | 파운드리·공정 | 웨이퍼 한 장에 설계된 최대 칩 개수 대비 실제로 나온 정상 칩 개수의 백분율. 높을수록 생산성이 좋아 공정장비 정확도·클린룸 청정도 등을 관리해 끌어올린다. | [삼성반도체 용어사전 — 수율](https://semiconductor.samsung.com/kr/support/tools-resources/dictionary/semiconductor-glossary-yield/) `[공식]` | 2026-08-23 |
| 낸드플래시 | NAND Flash | NAND Flash, NAND, 낸드플래시, 낸드 | 메모리 | 전원이 꺼져도 데이터가 남는 비휘발성 플래시 메모리 가운데 데이터 저장용으로 쓰는 형태. 코드 저장용인 노어(NOR)형과 달리 용량을 늘리기 쉬워 대용량 저장에 쓴다. | [삼성반도체 용어사전 — 플래시 메모리](https://semiconductor.samsung.com/kr/support/tools-resources/dictionary/semiconductor-glossary-flash-memory/) `[공식]` | 2026-08-29 |
| HBM | HBM | High Bandwidth Memory, HBM, 고대역폭 메모리 | 메모리 | 연산 칩 바로 옆에 밀착시켜 쓰는 광폭 인터페이스 D램. 인터페이스를 서로 독립된 채널로 나누고 채널마다 128비트 데이터 버스를 DDR 속도로 돌려 빠르면서도 전력을 덜 쓴다. | [JEDEC JESD235D — High Bandwidth Memory DRAM](https://www.jedec.org/standards-documents/docs/jesd235a) `[공식]` | 2026-08-29 |
| HBM2 | HBM2 | HBM2 | 메모리 | HBM 의 2세대. SK하이닉스는 HBM 세대를 1세대(HBM)·2세대(HBM2)·3세대(HBM2E)·4세대(HBM3)·5세대(HBM3E)·6세대(HBM4) 순으로 정리한다. | [SK하이닉스 뉴스룸 — 하이브리드 본딩 Tech Note](https://news.skhynix.co.kr/tech-note-series-ep2/) `[2차]` | 2026-08-29 |
| HBM2E | HBM2E | HBM2E | 메모리 | HBM 의 3세대. 실리콘관통전극(TSV)으로 D램을 수직으로 쌓아 410~460GB/s 대역폭을 내며, 용량 8~16GB 에 4단·8단으로 쌓는다. | [SK하이닉스 HBM 제품](https://product.skhynix.com/products/dram/hbm.go) `[공식]` | 2026-08-29 |
| HBM3 | HBM3 | HBM3 | 메모리 | HBM 의 4세대. 채널을 서로 독립적으로 두는 광폭 인터페이스 구조는 그대로이고, 채널마다 64비트 데이터 버스를 DDR 속도로 쓴다. | [JEDEC JESD238B.01 — High Bandwidth Memory (HBM3) DRAM](https://www.jedec.org/standards-documents/docs/jesd238b01) `[공식]` | 2026-08-29 |
| HBM3E | HBM3E | HBM3E | 메모리 | HBM 의 5세대. 용량 24~36GB 에 핀당 9.6Gbps 이상, 스택당 1.23TB/s 이상 대역폭을 내며 8단·12단으로 쌓는다. | [SK하이닉스 HBM 제품](https://product.skhynix.com/products/dram/hbm.go) `[공식]` | 2026-08-29 |
| HBM4 | HBM4 | HBM4 | 메모리 | HBM 의 6세대. 2025년 12월 공개된 JESD270-4A 규격이며, 채널마다 64비트 데이터 버스를 DDR 속도로 쓰는 광폭 인터페이스 구조다. | [JEDEC JESD270-4A — High Bandwidth Memory (HBM4) DRAM](https://www.jedec.org/standards-documents/docs/jesd270-4a) `[공식]` | 2026-08-29 |
| 칩렛 | Chiplet | chiplets, chiplet, 칩렛 | 패키징 | 기능을 나눠 따로 만든 작은 모듈형 다이. 큰 단일 다이 하나에 전부 담는 대신 여러 개를 한 패키지 안에서 이어 붙여 수율·비용·확장성을 얻는다. | [Synopsys — What are Chiplets?](https://www.synopsys.com/glossary/what-are-chiplets.html) `[2차]` | 2026-08-29 |
| 하이브리드 본딩 | Hybrid Bonding | hybrid bonding, 하이브리드 본딩, 하이브리드본딩 | 패키징 | 칩을 쌓을 때 범프를 두지 않고 구리와 구리를 직접 붙이는 접합 기술. 칩 사이 피치가 1㎛ 이하까지 좁아져 연결 밀도가 오르고 두께와 발열이 줄어든다. | [SK하이닉스 뉴스룸 — 하이브리드 본딩 Tech Note](https://news.skhynix.co.kr/tech-note-series-ep2/) `[2차]` | 2026-08-29 |
| SiP | SiP | System in Package, SiP, 시스템 인 패키지 | 패키징 | 여러 칩과 부품을 한 패키지 안에 통합하는 방식. 크기는 줄이면서 기능은 늘릴 수 있어 모바일·RF·웨어러블처럼 공간이 좁은 제품에 쓴다. | [Amkor — System in Package (SiP)](https://amkor.com/packaging/system-in-package/) `[공식]` | 2026-08-29 |
| SoC | SoC | System on Chip, SoCs, SoC, 시스템 온 칩 | AI·가속기 | 전체 시스템을 칩 하나에 담은 반도체. 연산 소자(CPU), 메모리 소자, 디지털신호처리 소자 등을 한 칩에 모아 크기와 제조비용을 줄인다. | [삼성반도체 용어사전 — SoC](https://semiconductor.samsung.com/kr/support/tools-resources/dictionary/semiconductor-glossary-soc/) `[공식]` | 2026-08-29 |
| ASIC | ASIC | Application-Specific Integrated Circuit, ASICs, ASIC | AI·가속기 | 특정 용도에 맞춰 맞춤 제작한 집적회로. 범용 프로세서나 FPGA 와 달리 정해진 기능만 하도록 최적화해 성능과 전력 효율을 끌어올린다. | [Synopsys — What is ASIC Design?](https://www.synopsys.com/glossary/what-is-asic-design.html) `[2차]` | 2026-08-29 |
| NPU | NPU | Neural Processing Unit, NPUs, NPU, 신경망처리장치 | AI·가속기 | AI 추론을 낮은 전력으로 처리하려고 밑바닥부터 새로 설계한 연산 장치. 신경망 계층의 스칼라·벡터·텐서 연산을 맡아 CPU·GPU 와 일을 나눈다. | [Qualcomm OnQ — What is an NPU?](https://www.qualcomm.com/news/onq/2024/02/what-is-an-npu-and-why-is-it-key-to-unlocking-on-device-generative-ai) `[2차]` | 2026-08-29 |

> **별칭**은 기사 본문에서 이 용어를 찾을 때 쓴다. 영문 기사가 많아 영어 표기가 필요하다.
> **영문 별칭은 낱말 경계를 요구한다** — 안 그러면 `ASIC` 이 `basic`, `SoC` 가 `association`,
> `SiP` 가 `gossip` 안에서 잡힌다 (`glossary.py`). 한국어는 조사가 붙어 그대로 포함으로 본다.
> 그래서 복수형(`wafers` `chiplets` `ASICs`)은 별칭에 따로 적어야 한다.
> 설명은 출처 내용을 짧게 옮긴 것이며 원문을 통째로 복제하지 않는다 (`CLAUDE.md`).

## 고른 이유

무작위로 고르지 않는다. **기사가 실제로 요구한 것부터** 넣는다.

### 처음 5개 (세션 3) — 143건에서 셈

| 용어 | 등장 | 출처 |
| --- | --- | --- |
| 패키징 | 30건 | 확보 |
| 웨이퍼 | 9건 | 확보 |
| 파운드리 | 6건 | 확보 |
| D램 | 6건 | 확보 |
| 수율 | 5건 | 확보 |

당시 `HBM`(4건)·`하이브리드 본딩`(4건)·`칩렛`(3건)은 **삼성 용어사전에 없어** 미뤘다.

### 다음 13개 (세션 8) — 214건에서 셈

**출처를 공식으로만 한정하지 않기로 하면서 미뤄 뒀던 것들이 풀렸다.**

| 용어 | 등장 | | 용어 | 등장 |
| --- | --- | --- | --- | --- |
| HBM | 10 | | 낸드플래시 | 4 |
| 칩렛 | 8 | | ASIC | 3 |
| 하이브리드 본딩 | 6 | | NPU | 3 |
| SoC | 5 | | SiP | 1 |
| HBM4 | 3 | | | |

**뺀 것** — `첨단 패키징`(24건)은 너무 포괄적이라 개념으로 세우면 아무 기사나 다 걸린다.
`데이터센터`(11건)는 반도체 개념이 아니다. `리소그래피`·`팹리스`는 이번엔 넣지 않았다.

**HBM2·HBM2E·HBM3·HBM3E 는 기사에 0건이다.** 그래도 넣었다 —
계보의 중간이 비면 개념 탭에서 오히려 이상해 보인다. 대신 **기사 본문 링크는 안 걸린다.**

## 채우는 순서

1. 아래 '미등재' 목록에서 **자주 나온 순으로** 사람이 출처를 확인해 옮긴다
2. 공식 출처가 없으면 통용 출처를 쓰되 `[2차]` 로 단다. **추측해서 쓰지 않는다**

## 미등재 — 기사에 나왔지만 사전에 없는 말

> 코드가 여기에 쌓는다. **추측해서 채우지 않는다.**
> 용어가 아닌 것(회사명·행사명·제품명)이 섞이므로 사람이 걸러야 한다.

(자동 수집은 아직 만들지 않았다 — 다음 슬라이스. 지금의 대기 목록은 아래다)

| 용어 | 등장 | 왜 아직 안 넣었나 |
| --- | --- | --- |
| 패키지 기판 (substrate) | 7 | `substrate` 문자열이 `glass substrate` 등과 겹쳐 셈이 부정확하다 |
| 전력반도체 | 5 | 출처 미확인 |
| 유리기판 | 3 | 출처 미확인 |
| 식각 · 증착 | 3 · 2 | 출처 미확인 |
| SiC · OSAT · GPU · CXL | 3 · 3 · 3 · 3 | 출처 미확인 |
| EUV · CMP · 인터포저 | 2 · 2 · 2 | 출처 미확인 |
| HBM4E | 3 | 아직 규격 문서를 못 찾았다. `HBM4` 와 별개 항목이어야 한다 |

## 분류

`패키징` `파운드리·공정` `메모리` `AI·가속기` `장비·소재` `정책·규제` `투자·실적`
카테고리와 같은 이름을 쓴다 (`PLAN.md`).
