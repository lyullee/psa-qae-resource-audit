# PSA–QAE CCE 투고 준비도와 최소 완료선

작성일: 2026-10-09

최종 갱신: 2026-10-10

## 권고 포지셔닝

현실적인 CCE 경로는 **양자 우위 논문**이 아니라 **PSA 확률제약 평가에서 QAE의 유효 조건과 실패 경계를 공정모델 오차, 강한 고전 기준선, 실제 게이트 비용, 하드웨어 잡음으로 분해한 자원 인식형 방법론 논문**이다. 이 경로에서는 확장 가능한 양자 loader를 완성하지 않아도 되지만, 완성하지 못한 비용을 숨기거나 QAE가 RQMC보다 우수하다고 주장해서는 안 된다.

## 현재 근거

| 항목 | 상태 | 확보된 근거 | 남은 위험 |
|---|---|---|---|
| 주 의사결정 문제 | 조건부 완료 | recycle 0.420/0.427/0.430, 공동사건, 목표확률 0.50 동결; 가장 가까운 실패정책 0.427의 shortfall은 RQMC RMSE의 11.91배·residual-stress 반폭의 7.57배; prospective audit의 조건부 p=0.50 crossing은 0.42659 | 주 surrogate에서 순도 제약이 비활성이라 사건이 회수율 단일제약으로 축소되며, 전체 훈련 support도 독립 H2 오차의 5x 분리를 못함 |
| 고전 기준선 | 완료 | 200회 반복, MC/RQMC/IS/MLAE 동일 사건 비교 | 현 주 사례에서 RQMC가 최선이므로 양자 우위 주장은 불가 |
| 공정 오라클 자원 | 부분 완료(큰 진전) | response oracle 99 논리 큐빗·35,160 CX/call; calibrated phase-map clean 계상 186 논리 큐빗·8,367,972 CX; integrated policy stream-to-event oracle 최대 510 논리 큐빗·1,286,021 clean CX; 물리모델 joint horizon 68·보수적 horizon 85·out-of-place state/stream 2,880 qubits; finite-support controller는 440 qubits·166,189 CX, controller-to-coefficient 회로는 495 qubits·353,441 CX; 세 raw 5성분 기체재고에서 조성 정규화·압력 3개·방향성 내부면 2개·run/stage controller·동적 Langmuir response·q*/LDF/loading conversion·보존수지를 직접 연결한 성분별 경로는 2,696–2,885 qubits·55,337,688–56,289,028 CX; 압력유도 포화/비포화 탱크 배분 회로는 647 qubits·705,194 CX이며 관측 포화 128건과 제한된 비포화 counterfactual 224건의 label을 보존 | raw aggregate map은 CSS 2/32이고 spectral 안정화는 명시적 보정이다. 비포화 counterfactual은 산술 시험이며 물리적 비포화 trajectory, out-of-support normalization/flow reversal, monolithic five-component transpilation, adaptive integration, 완전 phase/cycle unitary는 미합성 |
| 상태준비 | 음성 대조군 완료 | 1비트 502 CX, 2비트 262,125 CX; 7비트 dense 표는 64 EiB | scalable reversible copula/quantile loader는 미완성 |
| QPU | 단일 실행 완료 | ibm_marrakesh, 5 s charge, exact 0.625 대비 0.566940 | 단일 backend·단일 run이며 noise-aware interval 없음 |
| 외부 공정 검증 | 부분 완료(경계 교정) | 공개 CO2/N2 동적 PSA에서 purity 방향 4/4, recovery 방향 3/4; Thelen VA-10의 독립 H2 matched pair에서 균압압력 4.50→4.75 bara 시 회수율이 두 측정법 모두 감소(-2.30/-1.31 %-point); pyAPEP wrapper의 제품단 연결·외부 H2 회수율 경계를 교정하고 3정책 15-cycle screen과 450-cycle stress control을 실행; Voigt 13-run H2 자료로 동결 후보간격 분해능 감사; toPSAil/Yang 공개 H2/CO 70/30·2-bed·6-step·zeolite-5A 모델과 99.99% purity/75.87% recovery 실험 앵커; 공개자료 10개 감사에서 strict raw-data gate 0/10 | 교정 pyAPEP 450-cycle control도 purity 0.991666, recovery 0.044166, tank supply 0.03164, CSS 1.2538e-3로 네 gate를 모두 실패; synchronized H2 historian과 0.420 선택 검증은 열림 |
| 재현성 | 로컬 패키지 완료 | 전체 주장 감사 113/113 PASS; 전용 원고 감사 45/45 PASS; scientific/Qiskit 환경 freeze; 본문·SI·코드 318개 manifest artifact 검증 PASS; 공개저장소 staging 326 files·325 checksum entries; 패키징 중 QPU 제출 0건 | GitHub 공개와 DOI 발급은 과학적 외부 게이트와 저자 검토 뒤 필요 |
| 원고 | CCE 심사용 원고·title page·Figures 1–6·Tables 1–4·SI·편집자료 완료 | 본문 10,493단어, 초록 219단어, 참고문헌 18개; 6개 키워드; 5개 highlights; graphical abstract와 Figures 1–6의 PNG/vector PDF; 제한적 신규성 검색 프로토콜; AI 사용 공개문; blinded review DOCX, title page, SI DOCX; 4인 저자·ORCID·이메일·소속·CRediT 기록; 본문 Table 3·4는 각각 핵심 8개 행이며 전체 29개 resource tier와 30개 evidence tier는 SI Tables S1·S2에 수록 | 공동저자 최종 승인, COI·funding과 AI 공개문 최종 승인, 실제 Editorial Manager 입력 필요 |

## 투고 전에 닫아야 하는 최소 네 작업

### P0. 같은 정책·사건의 독립 H2 검증

가장 큰 심사 위험이다. Thelen VA-10으로 같은 화학계의 균압압력-회수율 방향은 확보했지만, 이는 제품가스 recycle이 아니고 동결 순도사건도 통과하지 못한다. 현재 CO2/N2 공개모델 역시 화학계 analog이며 정책 선택을 재현하지 못했다. pyAPEP wrapper를 감사해 기존 feed-end pressurisation과 adsorption-feed-only recovery 결과를 철회하고, product-end 연결·전체 외부 H2 경계·tank self-sufficiency로 교정했다. 15-cycle screen은 pre-CSS이고, 450-cycle 0.420 control도 purity `0.991666`, external-boundary recovery `0.044166`, tank supply `0.03164`, CSS residual `1.2538e-3`로 네 gate를 모두 실패했다. 따라서 pyAPEP 결과는 CSS 음성 대조군이 아니라 topology-feasibility stress test다. 다음 중 하나가 추가로 필요하다.

1. 공개 H2 PSA 모델에서 동일한 세 정책과 동일한 purity/recovery 사건을 계산한다.
2. 독립 H2 운전자료에서 정책에 대응하는 단계 또는 recycle 변화를 구성하고 held-out 순위를 검증한다.
3. 독립 구현의 H2 PSA solver를 사용하고, 기존 32-run surrogate를 보지 않은 운전조건으로 검증한다.

권고 판정 기준은 정책효과가 solver 수치오차의 최소 5배이고, 세 정책의 순위가 독립 반복 또는 격자 정련에서 유지되며, 0.420 선택 또는 그 실패가 사전에 정한 규칙으로 결정되는 것이다. 이를 확보하지 못하면 제목과 결론을 공개자료 기반 계산 프레임워크로 제한하고 산업 H2 실증 표현을 삭제한다.

### 완료. CCE 형식의 심사용 원고

core draft와 번호형 참고문헌 18개, Tables 1–4, Figures 1–6을 묶은 blinded review DOCX를 생성했고 Word PDF 출력으로 전 페이지를 검수했다. 저자 4인의 순서, ORCID, 이메일, 소속, KGS 공식 본사 우편주소와 CRediT를 별도 1-page title page에 기록하고 렌더링 검수했다. 공정모델·CSS·prior/copula·surrogate 검증, matched estimator budget, reversible oracle와 uncomputation, QPU metadata, 독립 검증의 성공과 실패가 포함되며, OpenAI Codex의 코드·분석·원고 지원 범위를 Methods와 참고문헌 직전 공개문에 기록했다. 남은 편집 작업은 공동저자 승인, COI·funding 및 AI 공개문 최종 승인, 투고 시스템 파일 유형 지정이다.

### P1. 다중 QPU 반복과 noise-aware interval

준비된 3-backend × 3-seed 행렬은 9 jobs, 27 circuits이다. 기존 5 s job과 같은 charge라고 단순 가정하면 약 45 s로 Open plan 600 s rolling allowance의 7.5%지만 실제 charge는 보장되지 않는다. 실행 전 다른 세션의 사용량을 확인한다.

최소 결과는 backend/run별 p estimate, amplified-depth별 bias, calibration timestamp, layout, two-qubit count, raw counts, QPU charge와 readout mitigation 전후 비교다. 이상적 binomial likelihood interval과 run/backend 변동을 포함한 bootstrap 또는 hierarchical interval을 분리해 보고한다.

### P1. 공정 단계와 가역 산술의 마지막 연결 — 전 성분 reciprocal/LDF microstep까지 합성, full phase는 미합성

reduced-H2 ledger와 72개 calibrated affine block에 더해, 주 32-run spatial/tank 모델의 final cycle을 다시 추적했다. 8개 phase, 2개 equalization, 4개 tank withdrawal, 2개 product/recycle split의 성분별 stream으로 source purity/recovery 사건을 수치오차 내에서 전부 재생했다. 8개 phase-specific ridge map을 outer leave-one-run-out으로 평가하고 held-out run의 실제 phase-start state를 조건으로 넣었을 때 순도/회수율 MAE는 `3.79e-8/7.27e-5`, 사건 label은 `32/32`였다. event-active 두 adsorption phase의 12개 stream output block은 input 12 bit/output 16 bit에서 최대 `272` logical qubits, `1,101,233` forward CX, `2,202,466` clean CX로 컴파일됐다.

- 주 purity/recovery event에 대한 conditional threshold-label 오차(완료: 32/32)
- branch/cap flag 보존
- parameter-only free-running phase-start state 생성은 one-cycle 범위에서 완료; 16-bit modular final-event block은 125 qubits/182,981 clean CX, 19-bit integrated policy stream-to-event oracle은 최대 510 qubits/1,286,021 clean CX로 완료
- 원 tank/spatial 모델은 32/32 조건에서 joint horizon 68 cycle로 수렴하며, 16-bit screen을 포함한 fixed horizon은 85 cycle로 정량화 완료
- 단일 physical state 1,360 qubits, clean out-of-place current/next 2,720, ten raw streams 포함 2,880 qubits의 architecture-specific accounting 완료; universal lower bound 주장은 하지 않음
- 25,856개 실제 cell state를 대상으로 five-component denominator와 H2/CO2/CH4/CO/N2의 component-specific reciprocal, q*, 1초 explicit LDF update를 각각 검증
- clean compute-copy-uncompute 회로는 성분별 490–515 logical qubits와 1,118,920–1,965,308 CX; 모든 정밀도·overflow·nonzero-q* erasure gate 통과
- 다섯 loading input/output을 보존하고 arithmetic workspace를 순차 재사용한 modular 계상은 675 logical qubits, 6,547,362 additive CX
- 제품단 valve/5성분 flux는 288 logical qubits·800,762 CX, 별도 고정 `r=0.420` product-split/tank-capacity 계상은 677 logical qubits·1,043,990 additive CX로 합성 완료
- 제품 밸브 법칙에서 생성한 5성분 flux register를 제품 말단 1초 물질수지에 직접 누적하고 valve/flux workspace를 exact reverse한 clean 회로는 842 logical qubits·2,348,388 CX·depth 3,285,605; 6,464개 제품단 상태의 32,320개 성분수지에서 정밀도·erasure·underflow·overflow gate를 모두 통과
- 같은 20-bit 제품 압력·조성 register에서 factor-specialized LDF loading transfer와 high-18-bit valve flux를 함께 생성해 한 성분 경계수지에 직접 누적하고 exact reverse한 경로 완료; 성분별 1,072–1,195 qubits·10,060,060–26,810,396 CX, 보수적 반복공통경로 상한 1,195 peak qubits·88,388,552 additive CX; 6,464개 상태·32,320개 수지에서 p95 3.38e-5–2.13e-4, max 2.31e-4–4.76e-4, erasure·underflow·overflow 0
- 세 셀의 5성분 기체재고에서 압력 3개를 재구성하고 두 내부면의 5성분 flux를 만든 뒤 중앙셀 물질수지에 직접 누적하고 pressure/face workspace를 exact reverse한 clean 회로는 1,508 logical qubits·8,328,622 CX·depth 12,250,291; 12,928개 상태의 64,640개 성분수지에서 전파오차·산술오차·erasure·underflow·overflow gate를 모두 통과
- supplied composition 두 개를 제거하고 각 upwind cell의 18-bit 성분기체 재고를 22-bit 공통량, 8-bit support-adaptive address/256 segments, 22-bit reciprocal QROM으로 20-bit mole fraction에 정규화한 뒤 동일한 pressure/two-face/balance 경로에 직접 합성; 25,856개 normalization state에서 최대 성분 p95/max 절대오차 2.071e-4/3.105e-4, erasure/overflow 0, standalone normalizer 333 qubits·1,340,232 CX, 전체 clean 회로 1,651 qubits·14,667,150 CX·depth 22,143,683, retained I/O 610, cleared workspace 1,041
- 12,928개 interior-cell state의 64,640개 성분 물질수지에서 current gas, 좌·우 face transfer, sign-split LDF transfer를 next gas로 누적하는 5성분 clean 회로를 합성; 성분별 198–209 qubits·68,676–80,800 CX, workspace-reuse 계상 609 qubits·366,802 additive CX, underflow 0
- supplied current/next loading에서 `q_next-q_current`의 부호와 크기를 가역 추출하고 고체질량을 통해 adsorption/desorption gas term으로 변환한 뒤 next-gas cell balance에 직접 합성; H2/CO2/CH4/CO/N2 loading bits는 26/26/32/32/30, 통합 성분 회로는 383–431 qubits·139,600–343,680 CX, 5성분 순차 계상은 934 qubits·1,411,882 additive CX; 3-bit 64-pair 전수 구조검사에서 branch mismatch와 dirty workspace 0
- 기존 standalone LDF를 26/26/32/32/30-bit로 재컴파일해 sign/solid-conversion/cell-balance interface와 직접 합성하고 LDF까지 exact reverse; 성분별 861–929 qubits·3,412,254–4,991,534 CX, 5성분 순차 계상 1,317 qubits·19,082,852 additive CX, measurement/reset 0
- full 20-bit gas-normalized pressure/composition과 두 internal face를 factor-quantized LDF, sign/solid conversion, 동일 conservative component balance에 직접 연결하고 exact reverse한 5개 parameter-specialized path 완료; 성분별 1,944–2,039 qubits·20,670,468–35,947,274 CX, 5성분 common-path-repeating 상한 2,039 peak qubits·128,013,726 additive CX
- 두 product/upstream gas-inventory register에서 제품·상류 조성을 각각 정규화하고 두 압력을 재구성해 inward face를 생성한 뒤 product-cell LDF·valve·loading-sign/solid-conversion·보존수지에 직접 연결한 5개 parameter-specialized path 완료; 성분별 1,803–1,952 qubits·20,253,112–37,020,740 CX, p95 `7.58e-5–2.11e-4`, max `2.19e-4–4.98e-4`, 5성분 common-path-repeating 상한 1,952 peak qubits·139,413,748 additive CX
- 5-qubit run address에서 11개 12-bit parameter word, 3-bit stage address에서 6개 paired-bed valve state, 7-bit run/slot address에서 5성분 18-bit tank withdrawal을 coherent QROM으로 합성했다. 352 parameter value, 8 schedule address, 640 tank record를 전수 검증했고, 통합 회로는 440 logical qubits·depth 324,495·166,189 CX·194,419 u, measurement/reset 0이다. 이 회로는 32-run/final-cycle support에 한정된다.
- 위 controller가 불러온 capacity·affinity·LDF factor를 reversible multiplication/weighted arithmetic으로 5개 equilibrium prefactor, 5개 LDF-alpha coefficient, 2개 adsorption flag에 직접 연결했다. 320 coefficient record와 16 schedule flag를 검증했고 equilibrium/LDF max relative error는 `4.987e-5/4.356e-5`, 회로는 495 logical qubits·depth 526,434·353,441 CX·436,305 u, measurement/reset 0이다.
- 생성된 equilibrium/LDF coefficient를 supplied 20-bit competitive-Langmuir response, adsorption schedule mask, q*, sign-preserving LDF update, loading-sign/solid conversion, conservative gas balance에 직접 소비하는 5개 clean 경로를 합성했다. 64,640개 성분수지에서 q*/LDF-next/next-gas 최대 scale-normalized error는 `4.324e-5/3.165e-5/3.997e-4`, quantized-transfer erasure는 0이다. 성분별 회로는 1,297–1,486 logical qubits·1,855,912–2,807,252 CX; repeated-controller 상한은 1,486 peak qubits·depth 12,387,085·11,911,052 additive CX다.
- controller의 12-bit run-affinity word와 supplied 20-bit pressure·5성분 composition에서 affinity-dependent denominator, 4,096-segment reciprocal, component response를 가역 생성한 뒤 같은 q*/LDF/loading/balance 경로에 직접 소비하는 5개 clean 회로를 합성했다. Denominator p95/max 절대오차는 `1.955e-4/3.530e-4`; 성분별 경로는 1,771–1,960 logical qubits·41,440,216–42,391,556 CX, 공통 depth 67,700,348이다. Repeated-controller 상한은 1,960 peak qubits·depth 338,501,740·209,832,572 additive CX다.
- pressure-derived tank allocation은 18-bit common/5-bit address/16-bit reciprocal 설계에서 관측 포화 128건과 제한된 비포화 counterfactual 224건을 보존했다. Clean circuit은 647 qubits·depth 1,127,046·705,194 CX이고 p95/max component-scale 오차는 `1.687e-4/3.872e-4`다. Counterfactual은 관측 tank composition 위 산술 시험이며 물리적 비포화 trajectory, 5성분 monolithic transpilation, adaptive integration과 완전 phase/cycle workspace는 미완성
- 선형 response-plane oracle 대비 추가 비용

현 상태는 process stream에서 사건까지의 관측가능성과 parameter-only one-cycle 경로를 닫았다. Integrated oracle은 stream 합산·recycle scaling·joint phase mark·exact uncomputation을 연결한다. Raw aggregate 50-cycle map은 CSS gate 2/32지만 label-free spectral correction은 32/32로 회복시킨다. 별도 원 물리모델 감사에서는 85개 상태좌표를 100 cycle 동안 보존해 모든 조건의 실제 CSS 수렴과 68-cycle joint horizon을 확인했다. 16-bit 고정소수점은 최종 CSS/event label을 모두 보존하고 conservative horizon을 85로 만든다. Finite-support controller가 run-specific parameter와 valve schedule을 coherent하게 보존하며, 최고 성분별 경로는 세 raw 기체재고에서 normalization·pressure reconstruction·two-face transport·run-affinity denominator/reciprocal/response·q*/LDF/loading conversion·conservative balance를 하나의 clean circuit으로 직접 연결한다. 별도 647-qubit 회로는 압력유도 수요와 탱크 재고를 비교해 포화 인출 또는 비포화 비례배분을 선택한다. 남은 핵심은 실제 phase에서 물리적 비포화 trajectory를 생성하고 다섯 성분 monolithic adaptive phase/cycle로 통합하는 일이다.

## 선택 작업

구조화 Gaussian-copula/empirical-quantile loader는 양자 우위 주장을 하려면 필수지만, 자원 경계 논문에는 선택 작업이다. 단순 dense loader 확대는 가치가 없다. 새 구현을 한다면 analytic normal generator, correlation transform, piecewise-polynomial inverse CDF, error budget을 갖춘 구조화 회로여야 한다.

## 제출 판단

parameter-only initializer, raw 50-cycle 실패, spectral correction, 19-bit integrated policy oracle, 85-cycle register target, 440-qubit finite-support controller, 495-qubit controller-to-kinetics coefficient interface, 647-qubit pressure-derived 포화/비포화 탱크배분 회로, 그리고 2,696–2,885-qubit gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths를 심사용 원고와 함께 제시해 “작은 QPU kernel이 PSA와 분리돼 있다”는 위험은 크게 줄었다. 자원경계 논문 기준 **로컬 원고·재현성 패키지는 약 99%**, 외부검증과 반복 하드웨어 증거까지 포함한 **과학적 투고 준비도는 약 95%**로 판단한다. 여전히 **calibrated 동일 recycle 정책·사건의 H2 검증 부재와 단일 QPU 실행**이 가장 큰 거절 위험이다. 제목·초록에서 완전한 cyclic oracle이나 양자우위를 주장하지 않고, 방법 비교·one-cycle 성공·physical horizon·resource audit를 함께 전면에 두면 CCE 도전은 현실적이다. 양자 우위 문구를 유지하려면 structured loader와 synthesized nonlinear reversible cycle map이 필요하다.

동결 surrogate에서 0.427의 확률 shortfall은 `0.029560`으로 RQMC RMSE의 `11.91x`, noiseless MLAE RMSE의 `10.22x`, residual-stress 반폭의 `7.57x`다. 따라서 현재 후보 간격에서는 RQMC보다 더 정밀한 확률추정이 정책을 바꾸지 않는다. 이 결과는 QAE를 억지로 유리하게 만드는 대신 **공정모델 개선과 후보정책 재설계가 우선**이라는 의사결정 가치를 제공한다.

## 다음 실행 순서

1. 교정된 pyAPEP topology stress test를 넘는 calibrated H2 모델 또는 독립 H2 정책자료에서 동결된 세 정책·사건을 검증한다.
2. 공유 Open quota를 확인한 뒤 준비된 9-job QPU campaign의 실행 여부를 결정한다.
3. Unsaturated proportional tank allocation을 추가하고 다섯 성분을 최소 한 adsorption phase의 monolithic circuit으로 통합해 workspace/CX를 측정한다.
4. 기록된 저자정보·CRediT·AI 공개문에 대한 공동저자 승인을 받고 COI·funding을 확정한다.
5. code/data archive DOI를 발급하고 최종 교차참조·영문 교정을 수행한다.

제출용 작업제목, highlights, cover-letter draft, checklist, graphical abstract는 `PSA_QAE_CCE_EDITORIAL_PACKAGE.json`에 기계 판독 가능한 claim boundary와 함께 정리했다. 이 편집 패키지는 CCE 적합성을 설명하지만 열린 과학적 게이트를 닫았다는 증거로 사용하지 않는다.



