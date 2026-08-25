# Silent Exit Redteam — lg.com 화면 단위 As-Is / To-Be 진단

AI 가상 고객(레드팀)이 **lg.com UK · DE · TH · BR** 에 실제 진입해 페르소나별 구매 과업을 수행하고,
막힌 지점을 화면 구성 요소 단위로 특정한 뒤 캡처한 진단 리포트입니다.

**리포트 보기 → https://hazajous-code.github.io/lgcom-redteam-audit/**

## 무엇이 실측이고 무엇이 시뮬레이션인가

| 구분 | 성격 |
|---|---|
| 화면 실태 · 스펙 문자열 · 캡처 21장 | **실측** — 2026-08-25/26 lg.com·samsung.com 직접 관측 |
| 이탈률 · 도달 모수 · 마찰 지수 · VOC | **시뮬레이션** — AI 가상 고객 생성. 실제 GA 트래픽이나 고객 발언이 아님 |

## 주요 실측 결과

- PDP 아코디언 **초기 확장 0개** — UK 36개 / TH 37개 / BR 35개, **4개국 전수 동일** → 템플릿 문제
- UK PDP `See All Specs` 를 펼치면 스펙 텍스트 **674자 → 4,531자**. 클릭 없이 보이는 건 **14.9%**
- 치수 단위 표기는 **태국에만 `mm` 이 있음**. UK·DE·BR 은 `1441 x 826 x 45.1` 처럼 단위 없음 → 로컬 설정 문제
- 같은 PDP 가 상단은 `Up to 165Hz in 4K`, 스펙표는 `120Hz Native (VRR 165Hz)` — 4개국 공통
- **`/br/tvs/` 가 404** (UK·TH 는 동일 패턴이 정상) / BR 은 PLP·PDP 모두 **할부·Pix 표기 없음**
- Buying Guide 허브에서 **PLP·PDP 로 나가는 링크 0개** (TH·UK 공통)
- TH 프로모션 허브의 Terms & Conditions 링크가 `href="null"` 로 깨져 있음
- **경쟁 비교** — 삼성 UK 는 `120Hz Motion and above` 필터로 주사율 선별이 되지만, LG 는 4개국 모두 불가

## 구성

```
index.html      리포트 본문 (단일 파일, 캡처는 WebP data URI 임베드)
shots/          원본 캡처 PNG
runner.py       레드팀 러너 — snapshot / evaluate / report 3단계
targets.json    수집 대상 화면 12개 (UK·DE·TH·BR + 삼성 비교)
personas.json   페르소나 P01–P12
capture.py      초기 캡처 스크립트
cap2~6.py       회차별 추가 캡처
```

## runner.py — 화면은 1번, 페르소나는 N개

회의에서 나온 "수천 개 에이전트를 동시에 뿌린다"는 그대로는 성립하지 않습니다.
lg.com 은 엣지에서 headless 브라우저를 **403** 으로 막기 때문에,
브라우저를 N번 띄우는 순간 그게 병목이자 비용이 됩니다.

그래서 두 단계로 나눕니다.

```bash
pip install playwright anthropic && playwright install chromium
export ANTHROPIC_API_KEY=...

python runner.py snapshot --config targets.json    # headed 브라우저로 화면 1회 수집
python runner.py evaluate --personas personas.json --workers 8   # 스냅샷 위에서 병렬 평가
python runner.py report                            # 마찰·이탈처·결핍 콘텐츠 집계
```

`snapshot` 은 접힌 아코디언을 펼친 뒤 DOM·캡처를 저장합니다(펼치지 않으면 스펙의 15%만 관측됨).
`evaluate` 는 브라우저가 필요 없으므로 페르소나를 100개에서 1,000개로 늘려도 **브라우저는 그대로 1대**입니다.
쿠키 동의·거부 버튼은 **클릭하지 않고** 화면을 덮는 오버레이만 CSS 로 숨깁니다.

## 재현 시 주의

- **headless 는 동작하지 않습니다.** `headless=False` 필수
- 스펙·리뷰가 지연 로딩되고 아코디언이 전부 접힌 채 시작하므로, 펼침 동작 후 판독해야 합니다
- 가격·재고·프로모션은 수시로 바뀌므로 캡처 시각·URL·뷰포트를 함께 보관하십시오 (본 회차 1280×900)

## 고지

본 저장소는 공개 웹페이지를 관찰한 UX 진단 자료입니다.
캡처된 화면의 저작권과 상표권은 각 사(LG전자·삼성전자)에 있으며, 각 캡처에 출처 URL을 병기했습니다.
LG전자의 공식 자료가 아니며 회사의 입장을 대변하지 않습니다.
