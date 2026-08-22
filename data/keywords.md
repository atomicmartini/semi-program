# 키워드

> 코드에 박지 않는다. 늘리고 줄이는 일은 이 파일에서 한다.
> 제목과 요약을 소문자로 바꿔 **부분 문자열**로 맞춘다.
> 판정 순서 — ① 제외에 걸리면 버린다 ② 포함에 하나도 안 걸리면 버린다 ③ 카테고리를 붙인다.

## 포함 — 하나라도 있으면 반도체 관련으로 본다

반도체, 파운드리, 웨이퍼, 디램, d램, dram, 낸드, nand, hbm, 메모리, 패키징, 노광, euv,
팹리스, 파운드리, 수율, 미세공정, 전공정, 후공정, 인터포저, 본딩, 포토레지스트, 식각, 증착,
소부장, 시스템반도체, 이미지센서, 파워반도체, 화합물반도체, 칩셋, 프로세서, 반도체장비,
semiconductor, foundry, wafer, chipmaker, chip, dram, nand, hbm, memory, packaging,
lithography, euv, fab, yield, transistor, interposer, tsv, photoresist, etch, deposition,
die, substrate, mems, soc, asic, cmos, gpu, npu, tpu, node, silicon, microled, photonic

## 제외 — 하나라도 있으면 버린다 (포함에 걸려도 버린다)

기업 뉴스룸에는 가전·모바일·사회공헌 소식이 섞여 온다.

갤럭시, 비스포크, 냉장고, 세탁기, 에어컨, 청소기, 스마트싱스, 스마트폰 신제품,
tv 신제품, 사회공헌, 봉사활동, 기부, 사내동호회, 임직원 행사,
채용설명회, 구직자, 채용 상담, 인턴십 모집, 신입사원 공채, 취업박람회, 잡페어,
galaxy, refrigerator, washing machine, air conditioner, vacuum cleaner,
sustainability report, csr, scholarship, volunteer, career fair, job fair, hiring event

## 카테고리 — 먼저 걸린 것을 쓴다. 하나도 안 걸리면 `미분류`

카테고리는 6개 + 미분류로 고정이다 (`PLAN.md`). 임의로 늘리지 않는다.

### 파운드리·공정
파운드리, 공정, 노광, 수율, 미세공정, 전공정, 후공정, 패키징, 인터포저, 본딩, 팹,
2.5d, 3d 적층, 나노, tsmc, 파운드리사, 트랜지스터, 게이트,
foundry, lithography, yield, fab, packaging, interposer, bonding, tsv, node, euv,
advanced packaging, cowos, hybrid bonding, wafer-level, chiplet, transistor, cfet,
gate-all-around, gaa, backside power, production, manufacturing

### 메모리
디램, d램, dram, 낸드, nand, hbm, 메모리, 적층, ssd, 낸드플래시, 디디알,
memory, ddr, flash storage, stacking

### AI·가속기
인공지능, 가속기, 데이터센터, 추론, 학습용, 신경망, 지능형, agi, cpo, 광연결,
ai chip, accelerator, data center, inference, gpu, npu, tpu, neural, llm,
ai computing, co-packaged optics, silicon photonics, photonic

### 장비·소재
장비, 소재, 부품, 웨이퍼, 포토레지스트, 식각, 증착, 세정, 검사장비, 소부장, asml,
equipment, material, wafer, photoresist, etch, deposition, metrology, inspection,
cleaning, precursor, substrate

### 정책·규제
수출통제, 규제, 관세, 보조금, 제재, 반독점, 국가안보, 통상, 특허소송, 무역,
export control, tariff, subsidy, sanction, chips act, antitrust, regulation, ban

### 투자·실적
투자, 실적, 매출, 영업이익, 인수, 합병, 증설, 설비투자, 주주환원, 상장, 유상증자,
분기 실적, 수주,
investment, earnings, revenue, acquisition, merger, ipo, capex, funding, purchase order,
expansion, stake

## 확인 필요

- [ ] 패키징을 `파운드리·공정` 에 넣었다. 수집처 8곳 중 2곳이 패키징 전문이라
      이 카테고리가 커질 수 있다. 실제 분포를 보고 판단한다
- [ ] 제외 목록이 기업 뉴스룸 잡음을 충분히 거르는지
- [ ] `chip` 처럼 짧은 말이 엉뚱한 기사를 끌어오는지
- [ ] 기업명은 이 파일이 아니라 `data/companies.md` 를 읽어 포함 판정에 쓴다.
      두 곳에 적으면 어긋나기 때문이다
