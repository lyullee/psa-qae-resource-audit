# Public toPSAil/Yang H2 model and experiment audit

This audit connects the public toPSAil Yang case inputs, the published model-validation statements, and the original H2/CO experiment to the frozen CCE case. It is an independent same-chemistry model/experiment anchor. It is not counted as validation of the frozen product-gas recycle selection.

## Public model facts

| item | audited value |
|---|---|
| chemistry | H2/CO = 0.70/0.30 |
| adsorbent and process | zeolite 5A; two beds; six steps |
| pressure range | 1.01325-11.14575 bar in the archived inputs |
| cycle | equalization, repressurization, high-pressure feed/product, equalization, depressurization, low-pressure product-gas purge |
| dynamic models | isothermal/nonisothermal and no-pressure-drop/Ergun variants; 25 CSTRs |
| experiment | 99.99% H2 purity and 75.87% H2 recovery for H2/CO |
| reported CSS controls | 13 cycles isothermal; 42 nonisothermal; 36 event-driven; 31 Ergun |
| result files in repository | no distributed MAT cycle outputs found |

## Frozen-event comparison

The Yang experiment exceeds the frozen purity threshold by `+0.010` percentage point but misses the recovery threshold by `-3.03` percentage points. Its frozen joint-event label would therefore be **False**. This is a useful high-purity experimental anchor and a negative event-boundary check.

## Claim boundary

The workbooks independently establish the same H2/CO chemistry, two-bed six-step schedule, equalization, product tank, purge path, valve constants, and spatial discretization used in the published validation. Kim and Scott report tuning constant-pressure valves to experimental feed/purge flows, pressure-changing valves to stepwise pressure changes, and heat-transfer coefficients to experimental recovery.

The external P/F coordinate is not the local product-gas recycle fraction. The former is purge flow divided by feed flow; the latter is the fraction of gross light product split from external product and returned internally. The numeric candidates `0.420/0.427/0.430` cannot be assigned to P/F without synchronized stream totals. Consequently, this closes a same-chemistry model/experiment gap but leaves the same-policy selection gate open.

Status: `independent_same_chemistry_model_and_experimental_anchor_policy_mapping_open`.
