# PSA–QAE 논문의 CCE 최종 격차 해소 계획

작성일: 2026-10-09

최종 갱신: 2026-10-10

## 1. 현재 판단

- **CCE 주제 적합성:** 높음. PSA의 확률제약 의사결정에 새로운 계산 방법을 적용하고, 대체 방법과 정량 비교하며, 계산 한계를 명시하는 구성이 CCE 범위에 들어간다.
- **현재 증거 수준:** 자원경계 방법론 기준 높음. 공개 PSA 자료의 교정·검증, MC/QMC 비교, 주 process-stream/event 연결, primitive-gate 자원계층, 실제 IBM QPU 실행까지 확보했다.
- **현재 투고 준비도:** 자원경계 방법론 원고의 로컬 원고·재현성 패키지는 약 99%, 외부검증과 반복 하드웨어 증거까지 포함한 과학적 투고 준비도는 약 95%로 판단한다. 강한 고전 기준선, 32-run stream ledger, parameter-only one-cycle 사건 재현, aggregate instability 진단, 510-qubit integrated policy oracle, 실제 QPU 경계, toPSAil/Yang H2 앵커, 68-cycle physical horizon과 16-bit/85-cycle target, 440-qubit finite-support coherent interface, 495-qubit controller-to-coefficient interface, 세 raw 기체재고에서 normalization·pressure·two-face transport·run-affinity dynamic Langmuir·LDF·conservative balance를 잇는 2,696–2,885-qubit 성분 경로, 그리고 관측 포화 128건과 제한된 비포화 counterfactual 224건을 보존한 647-qubit pressure-derived tank-allocation interface까지 확보했다. 게재가능성을 실질적으로 올릴 남은 과학적 공백은 동일 product-recycle H2 검증, 다중 QPU 반복, 물리적 비포화 trajectory와 adaptive five-component phase/cycle 통합이다.
- **목표 포지셔닝:** 양자 우위나 산업 H2 실증이 아니라, **PSA 확률제약 평가에서 QAE가 유효해질 조건과 실패하는 조건을 공정 모델 오차까지 포함해 정량화한 자원 인식형 방법론 논문**으로 고정한다.

CCE의 공식 범위는 화학공학 문제에 대한 새로운 계산·시스템 기술, 대안 방법 비교, 모델링·시뮬레이션·최적화·운전 적용을 포함한다. 실제로 Nenno와 Caspari의 CCE 논문은 공정 동적 최적화를 양자 하드웨어에 매핑하고 고전법보다 우월하지 않다는 결과를 정량적으로 보고했다. 따라서 긍정적인 양자 우위보다 **검증 가능한 문제 정식화, 공정 관련성, 공정 비용을 포함한 공정한 비교**가 중요하다.

## 2. 투고 전에 반드시 닫을 네 가지 게이트

### Gate 1. 하나의 공정 의사결정 문제로 고정

주 실험을 다음처럼 고정한다.

- 결정변수: recycle ratio 또는 step time 중 하나
- 불확실성: 공급 조성·압력·유량과 교정 잔차
- 공동 사건: 제품 H2 순도와 회수율의 동시 충족
- 의사결정 규칙: 목표 만족확률의 하한이 기준 이상인 최소비용 정책 선택
- 외부 검증: 보지 않은 운전 단계 또는 별도 공개 PSA 모델에서 정책 순위 유지 여부 확인

현재 여러 파일에 분산된 1D 보간, 16-state 물리 표, 4096-state surrogate, 공간·탱크 proxy를 한 논문의 동등한 주 실험처럼 제시하면 초점이 흐려진다. 주 실험 하나를 본문에 두고 나머지는 민감도 분석이나 보충자료로 이동한다.

**통과 기준:** 모든 방법이 동일한 확률 사건, 동일한 prior, 동일한 정책 집합과 동일한 비용 단위를 사용한다.

### Gate 2. 고전 기준선을 같은 조건에서 다시 비교

필수 비교군은 다음과 같다.

1. crude Monte Carlo
2. randomized Sobol QMC
3. adaptive 또는 weighted importance sampling
4. 가능한 작은 문제의 exact enumeration
5. MLAE/QAE query model

평가지표는 확률 RMSE만으로 끝내지 않는다.

- 공정모델 평가 횟수
- 벽시계 시간
- 정책 오선택률
- 신뢰하한을 사용한 feasible/infeasible 오분류율
- importance sampling의 ESS와 가중치 불안정성
- 동일한 목표 오차에서 요구되는 총비용

현재 QMC는 강하지만 importance sampling은 1차원 대조군 수준이다. 희귀사건이 실제로 생기는 하나의 tail 조건에서 IS를 제대로 튜닝하고, QAE가 crude MC에는 유리해도 QMC/IS에는 불리할 수 있음을 같은 표에서 보여야 한다.

**통과 기준:** 최소 200회 반복에서 방법별 오차·비용·정책오류의 불확실성 구간을 보고하며, 유리한 사례만 고르는 방식이 아니어야 한다.

### Gate 3. QPU 결과를 반복성과 잡음 분석으로 확장

현재 `ibm_marrakesh` 한 번의 결과는 하드웨어 실행 증거이지만 일반화 근거는 아니다. 다음 정도가 적정하다.

- 2~3개 백엔드에서 각 3회 반복
- 동일한 회로·shots·고정 transpiler seed를 주 분석으로 사용
- 별도의 layout/transpiler seed 민감도
- 실행 당시 calibration timestamp, layout, depth, two-qubit gate 수, queue/charge/QPU time 기록
- 최소 한 가지 readout mitigation 또는 잡음 민감도 분석
- run/backend 간 분산과 증폭 차수별 bias 분석

이 실험은 Open 할당량을 대략 30~60초 더 사용할 가능성이 있다. 다른 세션도 같은 월간 할당량을 쓰므로 실행 전에 전체 실행표를 확정해 한 번에 수집한다.

현재의 likelihood interval은 이상적 Bernoulli 모델에 조건부이므로 하드웨어 bias를 포함하는 신뢰구간으로 표현하면 안 된다. 반복 실행 자료를 이용한 hierarchical/binomial overdispersion 모델이나 bootstrap 구간을 별도로 제시한다.

**통과 기준:** 단일 job 결과가 아니라 backend/run 변동을 제시하고, 이상적 통계오차와 하드웨어 bias를 분리한다.

### Gate 4. 공정 오라클의 전체 비용을 연결

3-qubit QPU 회로와 PSA 공정 surrogate 사이의 연결을 자원식으로 명확히 한다.

- 불확실성 state preparation
- 고정소수점 공정 surrogate 계산
- 순도·회수율 comparator
- flag qubit 기록
- uncomputation
- controlled powers 또는 각 MLAE amplification stage
- logical gate 수, depth, ancilla, transpiled two-qubit gate 수

대형 lookup-table 오라클은 negative control로 유지한다. 주장은 “현재 하드웨어에서 PSA QAE를 구현했다”가 아니라, “작은 확률 커널을 실제 하드웨어에서 측정하고, PSA 규모로 확장될 때 loader와 reversible arithmetic가 만드는 비용을 별도로 계상했다”가 되어야 한다.

**통과 기준:** QAE/MC 교차점의 결론이 loader·oracle 비용 범위에 따라 어떻게 바뀌는지 tornado 또는 phase diagram으로 제시한다. QMC를 이기는 구간이 없다면 그대로 보고한다.

## 3. 공정 타당성을 올리는 최소 추가 작업

산업 H2 historian을 반드시 확보할 필요는 없다. 대신 논문의 표현을 공개자료 기반 방법론으로 제한하고 다음을 보강한다.

- TU Wien H2/CH4 운전표로 제품 순도·회수율 및 정책 민감도를 교정
- Otway 1초 로그로 밸브 상태와 압력 transient 부분만 검증
- 서로 다른 설비의 자료를 직접 결합한 것처럼 표현하지 않고, 각각 `separation calibration`과 `dynamic plausibility check`로 구분
- 보지 않은 stage/cycle에 대한 검증 지표 유지
- model discrepancy를 chance-constraint 계산에 전파
- 공개 PSA simulator 또는 별도 문헌 사례 하나에서 정책 순위의 외부 재현성 확인

동기화된 산업 H2 밸브·압력·유량·조성 로그가 확보되면 논문의 등급이 더 올라가지만, 그것이 없다고 CCE 방법론 논문이 불가능해지는 것은 아니다. 다만 industrial validation, valve-Cv identification, 99.99% product guarantee 같은 표현은 사용하지 않는다.

## 4. 권장 본문 구성

### 핵심 그림 5개

1. PSA 정책선택과 chance-constraint/QAE 계산 흐름
2. 공개자료 교정과 held-out 검증
3. 동일 budget에서 MC–QMC–IS–MLAE 오차 및 정책오류 비교
4. 실제 QPU의 amplification stage별 이상값·관측값·backend 변동
5. loader/oracle 비용과 model discrepancy를 포함한 crossover phase diagram

### 핵심 표 3개

1. 데이터·공정모델·불확실성·검증 분할
2. 모든 계산법의 정확도·평가횟수·시간·정책오류
3. QPU backend·calibration·회로자원·실행비용

본문은 약 8,000~9,000단어로 정리하고, 유한 truth-table 전수검증, 상세 bootstrap, 모든 추가 정책·회로는 보충자료로 이동한다.

## 5. 재현성 및 통계 체크

- 하나의 명령으로 주요 표와 그림을 다시 생성
- Python/Qiskit 환경 lock 파일 제공
- 공개 원자료 URL, license, 전처리 checksum 기록
- random seed와 transpiler seed를 모두 기록
- estimand, 정책 선택 규칙, 실패 기준을 분석 전에 고정
- exact enumeration이 가능한 사례에서 각 estimator 구현을 검증
- 코드와 결과 manifest를 DOI 저장소에 보관할 준비

## 6. 하지 않아도 되는 확장

- 더 큰 장식용 toy circuit
- “양자 우위”를 만들기 위한 선택적 budget 비교
- 혐기성 소화 전체 공정까지 범위를 확대하는 작업
- 공개자료가 뒷받침하지 않는 산업 H2 실증 주장
- 복잡한 최적화 알고리즘을 추가해 논문의 중심을 흐리는 작업

## 7. 실행 우선순위

| 순서 | 작업 | CCE 기여도 | 예상 부담 | 결과가 나쁠 때의 가치 |
|---:|---|---|---|---|
| 1 | 주 공정 문제와 claim 고정 | 매우 큼 | 낮음 | 논문 초점 확보 |
| 2 | MC/QMC/IS/MLAE 통합 benchmark | 매우 큼 | 중간 | QAE 적용 한계 규명 |
| 3 | 전체 loader/oracle 비용 phase diagram | 매우 큼 | 중간~높음 | 과장 없는 crossover 결론 |
| 4 | 다중 QPU 반복·잡음 분석 | 큼 | 낮음~중간 | NISQ 한계의 실측 증거 |
| 5 | 외부 PSA 모델 검증 | 큼 | 중간 | 모델 종속성 평가 |
| 6 | 7–8천 단어 CCE 원고 재구성 | 매우 큼 | 중간 | 심사 가능한 이야기 완성 |
| 7 | 재현 패키지와 보충자료 정리 | 중간 | 중간 | 신뢰성과 재현성 향상 |

## 8. Go/No-Go 기준

다음 네 항목이 모두 충족되면 CCE 투고가 현실적이다.

1. 동일 문제에서 MC/QMC/IS/MLAE 비교가 끝난다.
2. QPU 반복 결과가 backend 편차까지 포함한다.
3. 공정모델 오차가 QAE 통계오차보다 큰 현재 결과를 숨기지 않고 의사결정 영향으로 해석한다.
4. loader와 reversible oracle 비용을 포함한 결론을 제시한다.

3번과 4번의 결과가 QAE에 불리해도 투고 가치는 유지된다. 이때 논문의 핵심 결과는 “PSA에서 양자 이득이 확인되었다”가 아니라 “어떤 공정·오차·오라클 조건에서 QAE가 의미가 있고, 현재 조건에서는 무엇이 병목인지 최초로 정량 분리했다”가 된다.

## 9. 2026-10-09 실행 진척

- **Gate 1 조건부 완료:** 주 문제를 recycle `0.420/0.427/0.430`, 공동사건 `H2 product >= 0.9998` 및 `external recovery proxy >= 0.789`, 목표확률 `0.50`으로 고정했다. 기계 판독 가능한 프로토콜은 `PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json`이다.
- **Gate 2 조건부 완료:** 동일 prior와 사건에서 200회 반복한 결과 RMSE는 MC `0.006794`, RQMC `0.002482`, 방어적 mixture IS `0.010170`, 무잡음 MLAE `0.002892`였다. RQMC가 현 주 사례의 우선 방법이고 IS proposal은 열세였다. 산업 공정 검증이 아니라 32-run surrogate 조건부 결과라는 제한은 유지한다.
- **Gate 4 산술 proxy 완료:** 관측된 MLAE RMSE와 같아지는 MC 비용은 약 `19,323`회로 추정됐다. optimistic structured-loader proxy에서 MLAE 비용은 equal-RMSE MC의 `0.362x`이지만 관측 RQMC의 `1.709x`이고 RMSE도 더 크므로, 현재 주 사례에서는 RQMC가 지배한다. 결과는 `PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY.json`에 기록했다.
- **Gate 4 primitive-gate 음성 대조군 완료:** 32개 물리 설계행의 주 사건을 5큐빗 phase oracle로 합성했다. 25개 성공행 대신 7개 실패행을 표지하는 전역위상 동치 최적화 후, 동결된 3,500-query MLAE 스케줄은 완전연결 CX 기준 약 `432,000` 2큐빗 게이트, 선형 ECR 스트레스 테스트에서 약 `883,600` 2큐빗 게이트로 전개됐다. 이는 유한 lookup 제어의 실측 비용이며 연속 prior나 cyclic PSA integrator의 비용은 아니다. 결과는 `PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES.json`에 기록했다.
- **실제 IBM target preflight 완료:** 동일 5큐빗 회로를 Open instance의 `ibm_marrakesh` target에 transpiler seed 3개로 컴파일했다. 3,500-query shot schedule의 중앙 CZ 수는 약 `778,800`이고, `m=8` 회로는 depth `11,437`, CZ `4,157`이었다. sampler와 job은 만들지 않아 QPU 할당량을 사용하지 않았다. 결과는 `PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_IBM_PREFLIGHT_ibm_marrakesh.json`에 기록했다.
- **구조화 선형-surrogate oracle 합성 완료:** 주 prior의 bounded support에서 순도 하한은 `0.9998353`으로 동결 기준 `0.9998`보다 높아 순도 제약이 비활성임을 확인했다. 활성 회수율 반응면은 9개 입력의 고정소수점 weighted-adder/comparator/phase/uncompute 회로로 합성했다. 분류 불일치를 MLAE RMSE보다 낮추는 첫 해상도는 입력당 7비트이며, 99 논리 큐빗, depth `59,012`, `35,160 CX/oracle`이 필요했다. 동결 증폭 스케줄의 phase-oracle 반복만 `52.74 million CX` 하한이고 copula loader는 제외됐다. 결과는 `PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE.json`에 기록했다.
- **상관 prior dense-loader 음성 대조군 완료:** 정책과 상수 좌표를 제외한 9개 활성 변수의 empirical-copula 분포를 실제 `StatePreparation` 회로로 합성했다. 입력당 1비트는 9큐빗·`502 CX`·분류 불일치 `0.154617`, 2비트는 18큐빗·`262,125 CX`·불일치 `0.098045`였다. 오라클 정확도에 필요한 7비트는 loader 63큐빗과 `2^63` 진폭, float64 확률표만 `64 EiB`이므로 dense 경로는 배제된다. 이는 구조화 Gaussian-copula/empirical-quantile loader를 완성한 결과가 아니라 그 필요성을 실측한 결과다. `PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER.json`에 기록했다.
- **공동제약 활성도 감사 완료:** 동결 주 사건은 사실상 회수율 단일제약임을 원고에 명시했다. 주 임계값은 결과를 본 뒤 변경하지 않았다. 별도 `5×5` rounded threshold sensitivity에서 두 제약이 모두 활성이고 0.420 선택이 네 개 scramble에서 유지되는 셀을 8개 확인했다. 결과는 `PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY.json`에 기록했다.
- **게이트 패키지 재현 명령 완료:** Qiskit 환경에서 `run_cce_gate_compilation_package.py`를 실행하면 유한-table 합성, 구조화 선형 oracle, empirical-copula dense-loader 음성 대조군, 임계값 활성도 감사, 최종 joint-event 산술과 integrated policy stream-to-event oracle을 다시 만들고 37개 코드·입력·결과 파일의 SHA-256을 기록한다. 실제 IBM backend preflight는 시변 calibration이므로 다시 실행하지 않고 기존 no-submission artifact만 검증한다. 전체 validation은 PASS이며 QPU 할당량을 사용하지 않는다.
- **독립 공개모델 정책 검증은 부분 통과:** 공개 동적 CO2/N2 PSA solver에서 light-product purge/feed conductance ratio를 `0.420/0.427/0.430`으로 직접 바꾸고 네 물성 시나리오를 CSS까지 계산했다. 순도 양 끝점 방향은 4/4, 회수율은 3/4 시나리오에서 주 모델과 일치했지만, 외부 사건확률은 세 정책 모두 `0.50`이라 외부 선택은 `0.430`이었다. 4,800-point 수치 재검산에서도 정책 신호는 quadrature 변화의 `0.33–1.72%`에 불과했다. 따라서 외부 purity 방향 control은 확보했지만 local `0.420` chance selection 검증은 실패한 것으로 유지한다. 결과는 `PSA_QAE_CCE_EXTERNAL_LIGHT_PRODUCT_POLICY_VALIDATION.json`과 `PSA_QAE_CCE_EXTERNAL_POLICY_NUMERICAL_REFINEMENT.json`에 기록했다.
- **독립 H2 메커니즘 대조군 완료:** Thelen 2023의 자동 4-column VA-10에서 다른 조건은 같고 균압압력만 `4.50→4.75 bara`인 BP1/BP2를 추출했다. H2 회수율은 direct bellows meter에서 `81.45→79.15%`, pulse transmitter에서 `80.78→79.47%`로 두 방법 모두 감소했다. 그러나 순도는 `99.95→99.93%`로 동결 문턱 `99.98%`보다 낮고, 균압압력은 제품가스 recycle과 다른 제어변수다. 따라서 같은 화학계의 방향성 근거는 강화했지만 동일 정책·사건 및 `0.420` 선택 검증은 열어 둔다. 결과는 `PSA_QAE_CCE_INDEPENDENT_H2_EQUALIZATION_CONTROL.json`에 기록했다.
- **독립 H2 정책간격 분해능 감사 완료:** Voigt 13-run H2/CH4 자료의 purge/feed recovery 계수 `-77.97 %-point/unit`과 group-held-out RMSE `5.854 %-point`를 사용해 동결 후보의 숫자 간격만 검사했다. `0.420–0.430`의 가장 넓은 간격도 예상 recovery 효과가 `0.780 %-point`, effect/RMSE `0.1332`에 불과하며 5x 분리 기준을 만족하려면 RMSE를 `37.5x` 줄여야 한다. 연속 purity는 식별 불가하고 purge/feed는 product recycle이 아니므로 외부 선택 검증으로 세지 않는다. 결과는 `PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.json`에 기록했다.
- **독립 pyAPEP 경계 교정 완료:** 기존 wrapper가 제품가스 pressurisation을 feed end에 연결하고 외부 고순도 makeup을 제외한 adsorption-feed-only 회수율을 사용했음을 감사에서 발견했다. 기존 12-run CSS/mesh 결과는 `SUPERSEDED`로 보존하고 증거에서 제외했다. 교정 wrapper는 light-product-end 연결, 전체 외부 H2 회수율 경계, tank self-sufficiency를 사용한다. 15-cycle 세 정책 screen은 pre-CSS이며, 450-cycle `0.420` control도 purity `0.991666`, recovery `0.044166`, tank supply `0.03164`, CSS residual `1.2538e-3`로 purity/recovery/tank/CSS gate를 모두 실패했다. 따라서 이는 CSS 음성 검증이 아니라 topology-feasibility stress test이며 외부 선택 검증으로 세지 않는다.
- **toPSAil/Yang 공개 H2 동적모델·실험 앵커 완료:** 공개 workbooks의 H2/CO `0.70/0.30`, zeolite 5A, 2-bed, 6-step, 25-CSTR, equalization, product tank와 low-pressure purge 구조를 직접 감사했다. Yang 실험의 `99.99%` purity는 동결 `99.98%` 문턱을 넘지만 `75.87%` recovery는 `78.9%` 문턱보다 `3.03 %-point` 낮아 joint event는 false다. Kim과 Scott은 valve를 feed/purge flow와 pressure change에, heat transfer를 experimental recovery에 맞추고 isothermal/nonisothermal/event/Ergun CSS를 `13/42/36/31` cycles로 보고했다. 동일 화학계·공정구조·고순도 실험 앵커는 닫혔지만, P/F와 product-gas recycle은 다른 제어변수이고 공개 cycle-result MAT가 없어 `0.420` 선택 검증으로 세지 않는다. 결과는 `PSA_QAE_CCE_TOPSAIL_YANG_H2_PUBLIC_MODEL_AUDIT.json`에 기록했다.
- **정책 결정마진의 공정적 해석 완료:** 선택정책 `0.420`의 외부제품/총제품 비율은 `0.580`, recycle/외부제품 비는 `0.7241`이다. 가장 가까운 실패정책 `0.427`의 확률 shortfall `0.029560`은 RQMC RMSE의 `11.91x`, noiseless MLAE RMSE의 `10.22x`, residual-stress 반폭의 `7.57x`다. 따라서 동결 surrogate와 현재 후보 간격에서는 추정기를 RQMC보다 더 정밀하게 만들어도 정책 선택이 바뀌지 않으며, 공정모델 개선이나 후보정책 재설계가 우선이다. 결과는 `PSA_QAE_CCE_POLICY_DECISION_MARGIN.json`에 기록했다.
- **prospective 정책설계 요구조건 완료:** 동결 주 사례는 변경하지 않고 조건부 확률곡선을 훈련 recycle support `0.3508–0.4481`에서 다시 계산했다. p=0.50 crossing은 `0.42659`다. 그러나 전체 support의 Voigt계수 기반 recovery 효과도 독립 H2 group-CV RMSE의 `1.296x`뿐이라 5x 기준을 실패한다. 전체 support를 쓰는 새 실험도 recovery group-CV RMSE `<=1.517 %-point`가 필요하며, 현재 0.010 span은 `<=0.156 %-point`가 필요하다. 따라서 필요한 다음 자료는 같은 product-recycle 제어, 연속 purity, 더 낮은 held-out error를 갖춘 H2 campaign이다. 결과는 `PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.json`에 기록했다.
- **재현 명령 완료:** `run_cce_primary_package.py`가 두 계산을 재생성하고 사건·정책·예산·3,600개 estimator record를 검증한 뒤 18개 입력·코드·결과 파일의 SHA-256 manifest를 만든다. 이 명령은 IBM job을 다시 제출하지 않아 QPU 할당량을 사용하지 않는다.
- **QPU 반복 preflight 완료:** `ibm_marrakesh/ibm_fez/ibm_kingston` × transpiler seed 3개의 9-job 계획을 Open instance에서 compile만 했다. 27개 회로의 depth는 `4–135`, 2Q gate는 `0–37`이며 sampler 제출은 없었다. 기존 5초 job을 단순 외삽한 예상 charge는 약 45초지만 보장값은 아니다. 계획은 `PSA_QAE_QPU_REPLICATION_CAMPAIGN_PLAN.json`에 있다.
- **calibrated one-cycle phase-map bridge 완료:** phase ledger를 4개 기체 몰수와 4개 흡착량의 8차원 bed state, 성분별 유입·유출, equalization 전후 두 bed 상태까지 확장했다. 20개 reduced-H2 run을 nested leave-one-run-out으로 평가한 8개 phase map을 실제 순서로 한 cycle 합성한 결과 joint-state 상대 L1 중앙값은 `0.00149`, p95는 `0.00317`, 최종 pressure 오차 중앙값은 bed A/B `0.00734/0.00741 bar`였다. equalization 방향은 40/40 일치하고 음수 clipping은 0건이었다. 이는 held-out one-cycle bridge이며 fixed-point equalization, repeated CSS, 주 chance event, primitive gates는 아직 열려 있다.
- **calibrated affine-map fixed-point/primitive-gate layer 완료:** nested-holdout p95의 10%를 양자화 예산으로 배정해 input/output 정밀도를 함께 스크리닝했다. 두 예산을 만족하는 최소 sequential-register proxy는 input당 `11 bit`, scalar accumulator `16 bit`였고, p95 state/outlet-H2 양자화 오차는 `9.9978e-5/2.2017e-5`였다. 8개 phase × 9개 output의 72개 signed weighted-sum block을 `u/CX`로 전수 컴파일한 결과 workspace 재사용 시 최대 `186` logical qubits, forward `4,183,986 CX`, clean compute-uncompute `8,367,972 CX`였다. constant/state update, reversible equalization, repeated CSS, 주 event comparator, loader와 routing은 제외됐으므로 완전한 cyclic oracle 주장은 여전히 금지한다.
- **소형 coherent end-to-end 연결 control 완료:** 두 3-bit inventory register의 constant/state update, 방향 ancilla를 유지한 보존적 1-unit transfer, 두 integer comparator, joint-event phase mark, exact uncomputation을 하나의 Qiskit 회로로 연결했다. 64개 입력을 한 coherent superposition으로 전수검증한 결과 forward/phase 최대 amplitude 오차는 `1.70e-16/2.78e-16`, phase label `64/64`, work/event qubit clean return을 만족했다. clean oracle은 `15 logical qubits`, depth `405`, `304 CX`다. 이는 모듈 wiring 증거이며 calibrated kinetics, 반복 CSS 또는 주 H2 사건 구현은 아니다.
- **주 final-cycle process-stream ledger 완료:** 동결 32-run spatial/tank model의 마지막 CSS cycle에서 8개 bed phase, 2개 equalization, 4개 tank withdrawal, 2개 product/recycle split을 성분별로 추적했다. source CSV의 purity/recovery 사건을 전부 재생했고, 사건은 `25/32`, CSS는 `32/32`, 최대 purity/recovery 재생 오차는 `2.89e-15/1.33e-10`이었다. 이는 공정–사건 관측 interface이며 plant validation이나 가역 cyclic oracle은 아니다.
- **주 phase-stream event bridge와 primitive-gate layer 완료:** 8개 phase map을 outer leave-one-run-out으로 평가해 held-out run의 실제 phase-start state로부터 adsorption stream을 예측했다. purity/recovery MAE는 `3.79e-8/7.27e-5`, 사건 label은 `32/32`였다. p95 오차의 10%를 양자화 예산으로 둔 최소 구성은 input `12 bit`/scalar output `16 bit`; event-active 12개 block은 최대 `272` logical qubits, `1,101,233` forward CX, `2,202,466` clean CX였다. 이 separate-scalar 결과는 observed phase-start state 조건이며, 아래 integrated policy oracle이 합산·recycle scaling·event 연결을 별도로 닫는다.
- **observed-start one-cycle free-running bridge 완료:** outer-held phase/equalization map을 held-out run의 final-cycle 시작 aggregate A/B bed state에서 중간 관측 상태 없이 1회 합성했다. 사건 label은 `32/32`, purity/recovery MAE는 `8.61e-8/6.43e-5`, p95 cycle-closure 상대 L1은 `1.09e-4`였고 state/stream clipping은 0건이었다. 같은 aggregate map을 50회 반복한 음성 대조군에서는 terminal label `21/32`, tail event constant `26/32`, CSS gate `1/32`에 그쳐 one-cycle 성공이 반복 CSS를 뜻하지 않음을 확인했다.
- **parameter-only CSS initializer와 one-cycle event bridge 완료:** held-out run에서는 11개 동결 공정·불확실성 파라미터만 입력하고, 20개 aggregate A/B cycle-start gas/adsorbed state 좌표를 outer-held ridge map으로 예측했다. held dynamic state를 전혀 공급하지 않은 one-cycle 합성에서도 사건 label은 `32/32`, purity/recovery MAE는 `3.64e-7/3.22e-4`, p95 initializer state L1은 `7.01e-4`, p95 predicted-cycle closure L1은 `1.39e-5`였고 clipping은 0건이었다.
- **parameter-only initializer fixed-point/primitive-gate layer 완료:** 최소 통과 정밀도는 활성 파라미터당 `9 bit`, scalar output `14 bit`였고 p95 CSS-state 양자화 L1은 `5.62e-5`였다. 20개 scalar initializer block을 `u/CX`로 컴파일한 결과 scalar workspace 재사용 시 최대 `118` logical qubits, forward depth `1,139,187`, forward `578,702 CX`, clean compute-uncompute `1,157,404 CX`였다. loader, routing, 가역 state update와 physical CSS는 제외된다.
- **parameter-only 50-cycle 실패경계 완료:** parameter-only initializer에서 시작해 aggregate cycle map을 50회 반복하면 terminal event label `28/32`, tail event constant `30/32`, aggregate CSS gate `2/32`이고 p95 state drift는 `0.2549`였다. 따라서 no-held-state one-cycle leakage는 닫았지만 aggregate surrogate를 반복 physical model로 사용할 수는 없다. 이 음성 결과를 본문과 graphical abstract에 직접 제시한다.
- **label-free spectral 안정화 경계 완료:** outer-held affine phase/equalization block으로 정확한 aggregate cycle Jacobian을 조립하니 raw spectral radius가 `1.040–1.254`로 모두 1을 넘었다. held label이나 held dynamic trajectory를 사용하지 않고 목표 radius `0.9`가 되도록 `0.135–0.282`의 CSS-anchor weight를 계산하면 50-cycle terminal label과 aggregate CSS gate가 모두 `32/32`, p95 terminal residual은 `6.24e-8`, clipping은 0건이었다. 이 결과는 reduced surrogate의 불안정 원인과 필요한 보정량을 닫지만, anchor가 보존식에서 유도되지 않은 명시적 model correction이므로 physical/reversible CSS 주장은 여전히 금지한다.
- **최종 joint-event 가역 산술 완료:** 세 aggregate unsigned register(adsorption-feed H2, external-product H2, external-product impurity)에서 purity와 recovery 조건을 integer cross-multiplication으로 평가했다. 두 nested-holdout p95 오차 예산과 `32/32` label을 처음 만족한 정밀도는 `16 bit`, coefficient fractional precision은 `8 bit`였다. p95 purity/recovery 양자화 오차는 `1.6376e-9/9.8807e-6`; 두 flag를 유지하고 CZ phase mark 뒤 정확히 uncompute한 clean oracle은 `125 logical qubits`, depth `355,454`, `182,981 CX`였다. 이는 세 aggregate register에서 시작하는 modular interface이며, 아래 integrated circuit의 독립 검산 기준으로 유지한다.
- **정책별 stream-to-event 가역 연결 완료:** 두 adsorption affine map을 29개 고유 phase-state/parameter 입력에서 세 aggregate stream으로 직접 축약하고, 고정 recycle 후보 `0.420/0.427/0.430`을 계수에 흡수했다. 두 p95 예산을 처음 만족하는 aggregate 정밀도는 `19 bit`; purity/recovery 오차는 `1.1324e-8/1.1089e-5`, candidate-policy label은 quantized/integer 모두 `96/96`, 원 32-run ledger-support label은 `32/32`, clipping은 0건이었다. 세 clean oracle은 최대 `510 logical qubits`, `1,286,021 CX`, depth `2,481,760`이며 exact inverse를 사용한다. 이후 LDF, loading sign, solid conversion, cell balance, gas-normalization-to-two-face-to-interior-cell balance, normalized-transport/LDF/component-balance, 제품 gas-inventory normalization·inward-face·LDF·valve·boundary balance까지 직접 연결했다. 별도 440-qubit finite-support controller는 run-specific parameter, valve schedule 및 recorded tank withdrawal을 coherent하게 합성했고, 후속 495-qubit 회로는 capacity·affinity·LDF factor를 5성분 equilibrium/LDF coefficient와 adsorption flag로 변환한다. 최고 성분별 경로는 세 raw 기체재고에서 normalization·pressure·two-face transport를 생성하고 controller-driven dynamic Langmuir·q*/LDF/loading-sign/gas-balance에 직접 소비한다. 추가 647-qubit 회로는 final-cycle product 압력에서 수요를 만들어 포화 인출 또는 비포화 비례배분을 가역 계산한다. 열린 공백은 물리적 비포화 trajectory, 5성분 monolithic composition, adaptive phase integration, routing/noise다.
- **원 tank/spatial physical horizon과 register accounting 완료:** 32개 동결 조건을 100 cycle 재실행해 85개 physical boundary scalar를 저장했다. 32/32가 최종 strict/L1 CSS를 통과했고 latest joint physical horizon은 68 cycle이었다. 최종 CSS/event label과 p95 state-error budget `1e-5`를 처음 만족한 정밀도는 `16 bit`, conservative horizon은 85 cycle이다. 단일 state는 `1,360` data qubits, clean out-of-place current/next는 `2,720`, ten raw feed/product streams까지 보존하면 `2,880`이다. 이는 architecture-specific accounting이며 universal circuit lower bound가 아니다. clean oracle은 향후 cycle unitary를 forward/reverse 각각 85회 호출해야 한다. nonlinear transport arithmetic과 workspace는 미합성이다.
- **competitive-Langmuir 가역 microkernel 완료:** 32-run·101-boundary·2-bed·4-cell의 `25,856` 실제 cell state에서 5성분 경쟁흡착식의 affinity sum, CO2 numerator `P*y_CO2`, pressure×affinity sum과 denominator constant-one preload를 합성했다. 선언한 denominator p95 `<=1e-3`, CO2 q* factor p95 `<=0.05`, nonzero numerator erasure 0 기준을 처음 통과한 정밀도는 `18 bit`다. 회로는 `266 logical qubits`, depth `186,885`, `127,112 forward CX`, `254,224 clean compute-uncompute-equivalent CX`이며 reciprocal/division, 나머지 네 q* output, LDF/ODE와 전체 cycle은 포함하지 않는다.
- **competitive-Langmuir reciprocal/CO2-LDF clean microstep 완료:** prepared 56-bit denominator에서 5-bit 구간주소를 가역 계산하고 32-segment reciprocal QROM, numerator×reciprocal, 24-bit CO2 q*, `dt=1 s` LDF weighted update, copy와 전 workspace uncompute를 연결했다. 첫 통과 tier의 q* p95 상대오차는 `0.040855`, LDF-next는 `7.2596e-4`, erasure는 0이다. 전체 clean 회로는 `515 logical qubits`, depth `1,919,788`, `1,225,138 CX`다. 한 AC cell·CO2 한 성분·한 explicit microstep이며 gas transport나 완전 phase가 아니다.
- **전 성분 reciprocal/LDF clean microsteps 완료:** 동일한 five-component denominator와 clean compute-copy-uncompute 구조를 H2/CO2/CH4/CO/N2에 각각 적용했다. 25,856개 physical cell state에서 성분별 precision·overflow·erasure gate를 모두 통과했고, 개별 회로는 `490–515 logical qubits`, `1,118,920–1,965,308 CX`다. 다섯 loading input/output을 보존하고 arithmetic workspace를 순차 재사용한 modular 계상은 `675 logical qubits`, `6,547,362 additive CX`다. 이는 monolithic phase compilation이 아니며 pressure/transport module과의 state-update 결합은 제외한다.
- **제품단 valve/flux 및 recycle-tank clean modules 완료:** 6,464개 product-end state에서 12-bit pressure address와 20-bit component-flux 정밀도가 active label mismatch 0, nonzero flux erasure 0, active-flow p95 상대오차 `0.00316`, 최대 p95 flow-scale-normalized component error `0.00215`를 만족했다. clean valve/5성분 flux 회로는 `288 logical qubits`, depth `1,379,148`, `800,762 CX`다. 별도 64개 final-cycle ledger에서 24-bit amount/14-bit fraction은 p95 normalized error `5.25e-7`, recycle erasure 0, capacity mismatch 0을 만족한다. 5성분 product/tank/recycle/external/candidate register를 보존한 순차 계상은 `677 logical qubits`, `1,043,990 additive CX`, 최소 capacity headroom `97.40 mol`이다. 두 자료 tier는 한 trajectory로 합성하지 않았고 pressure/face-transport tier와의 next-state/tank-withdrawal 통합은 열려 있다.
- **제품 밸브-to-boundary 5성분 물질수지 직접 합성 완료:** 위 제품 밸브 법칙의 5성분 flux register를 제품 말단 cell의 1초 next-gas balance에 직접 음의 항으로 누적하고, 결과를 복사한 뒤 전체 valve/flux workspace를 exact reverse했다. 32 run × 101 boundary × 2 bed의 `6,464`개 제품단 상태, `32,320`개 성분수지에서 정밀도·erasure·underflow·overflow gate를 모두 통과했다. 선택 정밀도는 비밸브 입력 `16 bit`, valve flux와 next gas `20 bit`; clean 회로는 `842 logical qubits`, depth `3,285,605`, `2,348,388 CX`, retained I/O `528`, cleared workspace `314`, measurement/reset 0이다. 이 tier는 supplied pressure/composition 및 nonvalve term을 사용한다.
- **제품셀 LDF/valve/boundary-balance 성분별 직접 합성 완료:** 같은 20-bit 제품 pressure/composition register가 factor-specialized competitive-Langmuir/LDF를 구동하고, high 18 bits가 valve를 구동한다. 생성된 loading transfer와 valve flux를 한 conservative boundary balance에 누적한 뒤 LDF와 valve workspace를 exact reverse했다. `6,464`개 상태와 `32,320`개 성분수지에서 p95 next-gas 오차는 `3.38e-5–2.13e-4`, 최대오차는 `2.31e-4–4.76e-4`, erasure·underflow·overflow는 0이다. 성분별 clean path는 `1,072–1,195 logical qubits`, depth `15,670,199–45,153,788`, `10,060,060–26,810,396 CX`; 공통경로를 5회 반복한 보수적 상한은 `1,195 peak qubits`, depth `144,913,247`, `88,388,552 additive CX`다. CO2는 10-bit LDF coefficient가 필요했다. 제품 조성 normalization과 inward-face generation은 이후 상위 tier에서 닫았다. finite-support controller의 직접 연결, monolithic five-component transpilation, off-ledger tank demand와 integration은 열려 있다.
- **압력 재구성 및 방향성 내부면 수송 clean modules 완료:** 25,856개 cell state와 19,392개 internal face를 감사했다. 선택 구성은 성분 gas inventory `18 bit`, pressure `20 bit`, effective flow `24 bit`/register `28 bit`, supplied upstream composition `20 bit`다. Pressure p95/max scale-normalized error는 `3.01e-6/5.41e-6`; active-flow p95 상대오차는 `0.00354`, 최대 component-flux p95 flow-scale-normalized error는 `4.86e-5`다. nonzero gas/flux erasure, pressure overflow, pressure-difference underflow, active-label mismatch는 모두 0이다. Pressure circuit은 `152 logical qubits`, depth `158,331`, `93,764 CX`; face circuit은 `404 logical qubits`, depth `2,237,277`, `1,340,390 CX`; two-pressure-plus-one-face modular 계상은 `584 logical qubits`, `1,527,918 additive CX`다. 이 독립 tier는 supplied composition을 사용하며, frozen-support normalization과 cell-balance accumulation은 아래 직접합성 tier에서 별도로 계상한다. Cached support가 local left-to-right orientation이므로 일반 negative-flow switch는 열려 있다.
- **압력-to-two-face-to-interior-cell balance 직접 합성 완료:** 세 인접 셀의 5성분 gas inventory에서 압력 3개를 재구성하고 supplied upwind composition 두 개로 양쪽 내부면의 5성분 flux를 계산했다. 이 열 개의 임시 flux register를 중앙셀의 다섯 보존 물질수지에 직접 누적하고 결과를 복사한 뒤 두 face와 세 pressure circuit을 exact reverse했다. `12,928`개 내부셀 상태와 `64,640`개 성분수지에서 비-face 입력 `16 bit`, face flux `28 bit`, next gas `20 bit`가 전파오차·산술오차·erasure·underflow·overflow gate를 통과했다. clean 회로는 `1,508 logical qubits`, depth `12,250,291`, `8,328,622 CX`, retained I/O `810`, cleared workspace `698`, measurement/reset 0이다. 이 회로는 normalization 추가비용을 비교하기 위한 supplied-composition baseline이며, frozen-support normalization은 바로 아래 상위 tier에서 닫았다. General negative-flow switching은 열려 있고, direct LDF-plus-face coupling은 뒤의 상위 tier에서 닫는다.
- **기체재고 normalization-to-two-face-to-interior-cell balance 직접 합성 완료:** supplied upwind composition 두 개를 제거했다. 각 upwind cell의 18-bit 성분기체 재고를 22-bit 공통량으로 변환하고, 동결 left/centre-cell support에서 만든 8-bit address/256-segment conservative reciprocal QROM과 22-bit multiplier로 다섯 20-bit mole fraction을 생성한다. 25,856개 normalization state에서 최대 성분 p95/max 절대오차는 `2.071e-4/3.105e-4`, mole-fraction-sum p95/max는 `2.098e-4/3.338e-4`, erasure/overflow는 0이다. Propagated face-flux p95는 최대 `1.766e-4`; 다섯 balance p95는 `1.145e-5–1.622e-4`다. Standalone clean normalizer는 `333 logical qubits`, depth `2,153,892`, `1,340,232 CX`; normalizer 2개·pressure 3개·face 2개·balance 5개를 직접 합성한 clean 회로는 `1,651 logical qubits`, depth `22,143,683`, `14,667,150 CX`, retained I/O `610`, cleared workspace `1,041`, measurement/reset 0이다. Reciprocal segmentation은 frozen support에 한정되고, general negative-flow switching은 열려 있다. Direct LDF-plus-normalized-face coupling은 뒤의 상위 tier에서 닫고 coherent parameter register와 phase integration은 열어 둔다.
- **5성분 interior-cell gas-balance clean accumulators 완료:** 12,928개 interior-cell state의 64,640개 성분 물질수지에 `n_next=n+left+desorption-right-adsorption`을 적용했다. 모든 exact next gas는 양수이고 precision·erasure·overflow·underflow gate를 통과했다. H2/CO2/CH4/CO는 16-bit term/20-bit output, N2는 16/22 bit를 사용한다. 개별 clean 회로는 `198–209 logical qubits`, depth `65,228–97,719`, `68,676–80,800 CX`; sign-split term input과 next-gas output을 유지한 순차 workspace-reuse 계상은 `609 logical qubits`, `366,802 additive CX`다. Loading 차이의 sign 추출과 upstream LDF 연결은 아래 두 단계에서 닫았고, normalized face-output도 위 직접합성 tier에서 연결했다. 두 경로를 같은 balance 안에 공동 합성하는 단계는 열려 있다.
- **loading-sign·solid-conversion·cell-balance 직접 인터페이스 완료:** supplied current/next loading register에서 `q_next-q_current`의 부호와 크기를 가역 추출하고, 고정 cell solid mass를 사용해 adsorption/desorption gas term으로 변환한 뒤 위 next-gas balance에 직접 합성하고 workspace를 uncompute했다. standalone LDF accuracy에 충분했던 20/24/20/20/20 bit는 작은 signed difference에 부족해 H2/CO2/CH4/CO/N2에 각각 `26/26/32/32/30 bit`가 필요했다. 성분별 loading-to-term 회로는 `211–265 logical qubits`, `34,534–137,534 CX`; 통합 회로는 `383–431 logical qubits`, `139,600–343,680 CX`; 5성분 순차 계상은 `934 logical qubits`, `1,411,882 additive CX`다. 3-bit 64-pair 구조검사에서 branch mismatch와 dirty workspace는 모두 0이었다.
- **widened LDF-to-sign-to-cell-balance 직접 합성 완료:** 기존 five-component LDF microstep을 26/26/32/32/30-bit interface로 재컴파일하고 current/next loading register를 위 sign/solid-conversion/balance 회로에 직접 매핑한 뒤 두 모듈을 exact reverse했다. 성분별 clean 회로는 `861–929 logical qubits`, depth `4,949,239–7,871,973`, `3,412,254–4,991,534 CX`; 5성분 순차 workspace-reuse 계상은 `1,317 logical qubits`, `19,082,852 additive CX`, additive depth `28,110,021`이다. 모든 widened LDF precision gate를 통과했고 measurement/reset은 0이다. LDF는 아직 reversible run-specific capacity/affinity/kinetic parameter register가 아닌 constant-specialized arithmetic이다.
- **normalized-transport/LDF/interior-balance 성분별 직접 합성 완료:** 같은 세 gas-inventory register에서 두 upwind composition 정규화, 압력 3개, internal face 2개, centre-cell 20-bit pressure/composition, factor-quantized competitive-Langmuir/LDF, loading sign·solid conversion과 conservative next-gas balance를 연결하고 exact reverse했다. `12,928` interior state와 `64,640` balance에서 H2/CO2/CH4/CO/N2 p95 next-gas 오차는 `7.35e-5–1.87e-4`, 최대오차는 `3.46e-4–4.85e-4`, transfer erasure·underflow·overflow는 0이다. 고정 seed·optimization level 1의 성분별 회로는 `1,944–2,039 logical qubits`, depth `32,612,294–59,186,552`, `20,670,468–35,947,274 CX`다. 공통 경로를 5회 반복하는 보수적 상한은 `2,039 peak qubits`, depth `206,113,724`, `128,013,726 additive CX`다. 이는 monolithic five-component transpilation이 아니며 32개 source row는 coherent parameter register가 아니라 parameter-specialized circuit으로 표현된다.
- **gas-inventory-generated product-cell LDF/valve/balance 성분별 직접 합성 완료:** 두 5성분 product/upstream gas-inventory register에서 조성을 각각 정규화하고 두 압력을 재구성해 하나의 inward face를 생성했다. Product composition과 pressure가 factor-specialized competitive-Langmuir/LDF와 valve를 구동하고, 생성된 loading transfer와 valve/inward flux를 loading-sign·solid-mass 변환 후 한 conservative next-gas balance에 누적한 뒤 exact reverse했다. `6,464` state와 `32,320` balance에서 H2/CO2/CH4/CO/N2 p95 next-gas 오차는 `7.58e-5–2.11e-4`, 최대오차는 `2.19e-4–4.98e-4`, erasure·underflow·overflow는 0이다. 성분별 회로는 `1,803–1,952 logical qubits`, depth `31,377,808–60,835,766`, `20,253,112–37,020,740 CX`; 보수적 common-path-repeating 상한은 `1,952 peak qubits`, depth `223,481,789`, `139,413,748 additive CX`다. 제품 조성 정규화와 inward-face 입력 공백은 닫혔고 finite-support run/schedule/tank controller도 별도 합성됐다. 두 tier의 직접 연결, monolithic five-component transpilation, off-ledger withdrawal과 phase/cycle integration은 열려 있다.
- **coherent finite-support run/schedule/tank interface 완료:** 5-qubit run address가 32개 run의 11개 12-bit parameter word를, 3-qubit stage address가 6개 paired-bed stage와 local valve mask를, 7-qubit run/slot address가 final-cycle 5성분 18-bit tank withdrawal을 로드한다. 352 parameter value, 8 schedule address, 640 tank record를 전수 검증했다. parameter p95/max normalized error는 `1.1339e-4/1.2166e-4`, tank p95/max는 `1.3622e-6/1.8654e-6`이고 meaningful erasure, modular underflow, next-state mismatch는 모두 0이다. 통합 회로는 `440 logical qubits`, depth `324,495`, `166,189 CX`, `194,419 u`, measurement/reset 0이다. 이 회로는 32-run/final-cycle ledger support에 한정되며 continuous/off-ledger parameter loading, pressure/flow-derived demand, adaptive integration, direct component-path wiring과 full phase/cycle은 포함하지 않는다.
- **coherent controller-to-five-component coefficient interface 완료:** 위 run QROM의 12-bit capacity·affinity·LDF factor를 직접 소비해 reversible multiplication과 weighted arithmetic으로 다섯 equilibrium prefactor와 다섯 LDF-alpha coefficient를 만들고, schedule word에서 두 bed adsorption-active flag를 복호했다. 32 run의 320 coefficient record와 8 stage의 16 flag를 검증했고 capacity-affinity/LDF-factor/equilibrium/LDF-alpha p95 relative error는 각각 `1.906e-5/9.871e-6/2.301e-5/2.698e-5`, equilibrium/LDF-alpha 최대는 `4.987e-5/4.356e-5`로 모두 `5e-3` gate를 통과했다. 통합 회로는 `495 logical qubits`, depth `526,434`, `353,441 CX`, `436,305 u`, measurement/reset 0이다.
- **coherent coefficient-to-LDF/loading/balance 직접 소비 완료:** controller가 생성한 equilibrium/LDF-alpha coefficient, addressed-bed adsorption mask, supplied 20-bit competitive-Langmuir response를 q* 생성, sign-preserving LDF update, loading-sign/solid conversion, conservative next-gas balance에 직접 합성하고 모든 controller/arithmetic workspace를 exact reverse했다. 32 run의 `64,640`개 성분수지에서 q*/LDF-next/next-gas 최대 scale-normalized error는 `4.324e-5/3.165e-5/3.997e-4`, quantized-transfer erasure·underflow·overflow는 0이다. H2/CO2/CH4/CO/N2 경로는 `1,297–1,486 logical qubits`, depth `1,612,437–3,143,800`, `1,855,912–2,807,252 CX`; repeated-controller 상한은 `1,486 peak qubits`, depth `12,387,085`, `11,911,052 additive CX`다. Dynamic affinity denominator/reciprocal, off-ledger tank demand, adaptive integration과 full phase/cycle은 열려 있다.
- **coherent dynamic-Langmuir-to-LDF/loading/balance 직접 합성 완료:** controller의 retained 12-bit run-affinity word, supplied 20-bit pressure와 5개 composition word에서 affinity sum, denominator, 12-bit address, 4,096-segment reciprocal QROM, numerator와 20-bit response를 가역 생성한 뒤 위 coefficient-consuming 경로에 직접 연결하고 exact reverse했다. 64,640개 성분수지에서 denominator p95/max 절대오차는 `1.955e-4/3.530e-4`, response/q*/LDF-next/next-gas 최대 scale-normalized error는 `2.917e-4/2.852e-4/1.967e-4/3.997e-4`다. H2/CO2/CH4/CO/N2 경로는 `1,771–1,960 logical qubits`, 공통 depth `67,700,348`, `41,440,216–42,391,556 CX`; repeated-controller 상한은 `1,960 peak qubits`, depth `338,501,740`, `209,832,572 additive CX`다. Gas normalization, face generation, off-ledger tank demand, adaptive integration과 full phase/cycle은 열려 있다.
- **coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance 직접 합성 완료:** supplied pressure·composition·face words를 제거했다. 세 raw five-component gas-inventory register에서 두 조성을 가역 정규화하고 압력 3개와 방향성 내부면 2개를 생성한 뒤, centre pressure/composition과 face words를 32-run/6-stage controller, run-affinity Langmuir denominator·4,096-segment reciprocal·response, schedule-gated q*/LDF/loading conversion 및 conservative component balance에 직접 연결했다. transport와 controller workspace는 exact reverse했다. `25,856` normalization state와 `64,640` component-balance record에서 다섯 precision gate를 모두 통과했고 next-gas 최대 scale-normalized error는 `3.997e-4`다. H2/CO2/CH4/CO/N2 경로는 `2,696–2,885 logical qubits`, 공통 depth `89,147,751`, `55,337,688–56,289,028 CX`; repeated-path 상한은 `2,885 peak qubits`, depth `445,738,755`, `279,319,932 additive CX`다. Continuous off-ledger tank demand, out-of-support normalization/negative-flow switching, monolithic five-component transpilation, adaptive phase/cycle integration과 routing은 열려 있다.
- **공개 H2 synchronized-data 가용성 감사 완료:** 실험·pilot·산업·모델·historian 10개 출처를 cycle, valve/step, pressure, feed/product flow, product composition, common clock, raw file, same policy, same event로 분해했다. 동결 product-recycle 정책과 joint event를 공개 raw H2 시계열로 동시에 검증하는 출처는 `0/10`이다. Thelen VA-10은 가장 가까운 공개 H2 실험, Otway는 가장 완전한 공개 synchronized historian이지만 서로 필요한 축을 나눠 가진다. Schell H2/CO2 실험은 cyclic pressure/flow/MS 앵커, Cranfield record는 scoped access에서 `disclaimer.txt`만 확인된 simulation provenance로 제한했다. 결과는 `PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.json/csv/md`에 기록했다.
- **pressure-derived saturated/unsaturated tank-allocation interface 완료:** final-cycle product pressure에서 ideal-gas withdrawal demand를 가역 산출하고 탱크 재고와 비교해 포화 전량 인출 또는 비포화 성분별 비례배분을 선택한다. 18-bit common/5-bit address/16-bit reciprocal 설계는 관측 포화 `128/128`과 제한된 비포화 counterfactual `224/224` label을 보존하며 p95/max component-scale 오차는 `1.687e-4/3.872e-4`다. Clean circuit은 `647 logical qubits`, depth `1,127,046`, `705,194 CX`다. Counterfactual은 관측 tank composition에 대한 산술-domain 시험이며 물리 trajectory 검증은 아니다.
- **CCE 원고·Figures 1–6·Tables 1–4·SI·편집 패키지 완료:** core draft는 `10,493 words`, `219-word` abstract, 참고문헌 18개다. 키워드 6개, 65–76자 highlights 5개, 3,706×1,446 px 및 vector-PDF graphical abstract, 6개 본문 그림의 별도 vector PDF도 현재 저자지침을 충족한다. 4개 검색식의 Crossref/OpenAlex 기록에서 명시적 PSA–QAE/MLAE 직접 일치는 0건이며 보편적 부재나 우선권으로 해석하지 않는다. title page에는 4인 저자 순서·ORCID·이메일·소속·CRediT를 기록했고 OpenAI Codex 사용 공개문도 포함했다. 본문 Table 3과 Table 4는 각각 핵심 8개 행으로 압축했고, 전체 29개 resource tier와 30개 evidence tier는 SI Tables S1과 S2에 수록했다. 전용 원고 감사 `45/45`와 전체 주장 감사 `113/113`가 PASS이며 `318`개 manifest artifact와 공개 staging `326` files/`325` checksums도 검증했다. 동일 recycle H2 검증, 반복 QPU, 물리적 비포화 trajectory와 adaptive reversible five-component phase/cycle unitary가 열려 있어 `submission_ready=false`다.
- **편집자료 claim boundary 고정:** graphical abstract와 cover letter는 RQMC `0.002482`가 noiseless MLAE `0.002892`보다 낮고, response oracle `99 qubits/35,160 CX per call`, parameter-only one-cycle event bridge `32/32 labels`, integrated policy oracle `510 qubits/1,286,021 clean CX`, raw/stabilized aggregate CSS `2/32→32/32`, physical `68→85` cycle horizon/register target, reciprocal/LDF microstep `515 qubits/1,225,138 CX`, normalized transport-balance `1,651 qubits/14,667,150 CX`, coherent finite-support controller `440 qubits/166,189 CX`, controller-to-five-component coefficient interface `495 qubits/353,441 CX`, saturated/unsaturated tank allocation `647 qubits/705,194 CX`, 최고 gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths `2,696–2,885 qubits/55,337,688–56,289,028 CX`, dense loader `2^63 amplitudes`, 실제 IBM `0.625→0.56694`를 구분해 제시한다. 결론은 현재 end-to-end advantage 부재이며 물리적 비포화 trajectory, monolithic/adaptive phase logic, H2 validation이 다음 병목이라는 것이다.
- **남은 필수 게이트:** 양자우위 주장을 하려면 scalable reversible Gaussian-copula/empirical-quantile loader가 필요하다. CCE 자원경계 논문에서 더 시급한 항목은 물리적 비포화 trajectory를 포함한 monolithic five-component physical phase/cycle unitary, 다중-backend QPU 반복과 noise-aware interval, calibrated 동일 H2 정책·사건의 독립 외부검증이다. Frozen-support raw gas inventory에서 normalization·pressure·two-face transport·dynamic response·LDF/loading·component balance와 bounded tank-allocation arithmetic까지 직접 연결됐지만 완전 가역 cyclic oracle은 아직 아니다.

## 참고 링크

- Computers & Chemical Engineering 공식 범위: https://shop.elsevier.com/journals/computers-and-chemical-engineering/0098-1354
- Nenno and Caspari (2024), Dynamic optimization on quantum hardware: https://www.sciencedirect.com/science/article/pii/S0098135424001224
- Leenders et al. (2024), hybrid quantum–classical multi-energy optimization: https://www.sciencedirect.com/science/article/pii/S0098135424001819



