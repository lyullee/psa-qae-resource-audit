# Wang 2023 공개 COG-VPSA 실험 벤치마크

## 무엇을 새로 확보했는가

Wang et al.의 4-bed 12-step 실험실 VPSA 보조자료에서 공개된 **실험 breakthrough marker**와 **실험 bed-pressure curve**를 재현 가능한 좌표 규칙으로 추출했다. Figure S15에서 170개 marker core, Figure S20(c,d)에서 145개의 정규화 압력점을 얻었다. 주 논문 Table 4에서는 실험 순도·회수율이 있는 6개 run과 저자 simulation만 있는 6개 run을 구분해 옮겼다. 보조자료 Table S1의 60개 운전점은 저자 모델의 계산표이므로 실험자료와 별도 분류했다.

## 독립적인 공학 근거

Figure S15의 feed 조성은 H₂/CH₄/N₂/CO₂ = 0.58/0.29/0.07/0.06이다. 각 불순물이 feed 농도의 50%에 처음 도달한 digitized time은 다음과 같다.

- N2: 213.88 s
- CH4: 385.44 s
- CO2: 943.38 s

따라서 관측 순서는 **N2 → CH4 → CO2**이다. 이는 흡착 강도와 mass-transfer front가 서로 다른 다성분 breakthrough를 만든다는 외부 실험 근거다. Figure S20(c,d)는 한 주기 안에서 가압·고압 유지·감압·저압 구간이 반복되는 압력 파형을 제공하므로, 우리 동적 모델이 단순 정상상태 분리기가 아니라 cyclic pressure process를 재현하는지 확인하는 외부 shape benchmark로 쓸 수 있다.

주 논문 Table 4의 실험 run은 `I, II, III, VI, IX, XII`이다. 저자 simulation과의 최대 순도 오차는 `0.60` percentage point다. 회수율 최대 오차는 Run II의 `6.03` percentage point이며, Run II를 제외하면 최대 `0.39` percentage point다. 따라서 “거의 모든 simulation이 0.6% 이내”라는 원문의 표현과 Run II 예외를 함께 보존했다. 이 6개 점은 우리 모델이 앞으로 source apparatus를 재현할 때 사용할 정량 hold-out target이다.

## 사용할 수 있는 주장

- 공개 실험곡선으로 breakthrough 순서와 cyclic pressure shape를 독립 확인했다.
- Table 4의 6개 실험 운전점은 purity/recovery 정량 hold-out 목표이며, 현재 모델의 예측값으로 오인하지 않는다.
- Table S1은 feed pressure와 vacuum pressure 변화에 따른 purity–recovery–power 방향성을 비교하는 **저자 모델 기반** trend benchmark다.
- 이 자료는 향후 source apparatus를 별도로 재현할 때 독립 hold-out 입력으로 사용할 수 있다.

## 사용할 수 없는 주장

- 공개된 것은 원시 시간동기 valve–tank–flow–composition log가 아니다.
- RB3 activated carbon을 쓴 저압 COG-VPSA와 현재 모델의 흡착제·장치·주기가 다르다.
- 따라서 이 결과만으로 현재 PSA 모델을 보정했다거나 plant validation을 마쳤다고 쓸 수 없다.
- Table S1의 60개 점은 실험점이 아니라 논문 저자의 parametric simulation이다.

## 숫자화 오차와 재현성

축 좌표 한 픽셀은 약 3.15 s와 mole fraction 0.00238이다. marker 중심 판독 오차를 ±2 px로 두어 약 ±6.3 s, ±0.0048 mole fraction으로 기록했다. 압력축의 ±2 px는 약 ±0.0353 bar다. 원본 PDF SHA-256은 `b32b669a63bdbb8f99926a1cc119820c34c802e25f042a4f66d25cd50de90bf0`이다.

## 출처

- DOI: https://doi.org/10.1016/j.cej.2023.144920
- Article: https://www.sciencedirect.com/science/article/pii/S1385894723036513
- Public supplement: https://ars.els-cdn.com/content/image/1-s2.0-S1385894723036513-mmc1.pdf
- License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
