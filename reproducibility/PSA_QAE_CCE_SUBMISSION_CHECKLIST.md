# CCE submission checklist

## Scientifically complete in the local package

- [x] Frozen policy candidates, joint event, chance target, estimator budgets, and failure rules.
- [x] Matched 200-replication MC/RQMC/IS/MLAE comparison.
- [x] Decision-margin analysis showing limited value from estimator precision below RQMC.
- [x] Primitive-gate resource ladder for finite, response, calibrated-map, and hardware tiers.
- [x] Exact 32-run primary final-cycle phase ledger and nested held-out phase-stream reconstruction of 32/32 event labels, conditional on observed phase-start states.
- [x] Twelve primary event-active stream blocks compiled at 12-bit inputs/16-bit outputs: 272 logical qubits, 1,101,233 forward CX, and 2,202,466 clean CX.
- [x] Final aggregate-stream purity/recovery arithmetic compiled at 16 bits: 32/32 labels, 125 logical qubits, and 182,981 clean CX with exact circuit uncomputation.
- [x] Integrated policy-specific stream-to-event oracle compiled at 19 aggregate bits: 96/96 candidate-policy labels, 32/32 ledger-support labels, 510 logical qubits, and at most 1,286,021 clean CX.
- [x] Parameter-only nested-held-out CSS initializer: 32/32 one-cycle event labels with no held dynamic state; 20 blocks compiled to 118 logical qubits and 578,702 forward CX.
- [x] Fifty-cycle stability boundary reported: raw map 28/32 terminal labels and 2/32 CSS passes; label-free spectral anchoring 32/32 labels and CSS passes, explicitly limited to a reduced-surrogate correction.
- [x] Direct 32-run tank/spatial CSS horizon: latest joint physical horizon 68 cycles; 16-bit screen gives 85 cycles and 1,360/2,720/2,880-qubit architecture-specific register accounting.
- [x] Competitive-Langmuir numerator/denominator microkernel compiled over 25,856 physical cell states: 18 bits, 266 logical qubits, 127,112 forward CX, and 254,224 clean compute-uncompute-equivalent CX.
- [x] Clean competitive-Langmuir reciprocal/CO2-LDF follow-on compiled: five-bit denominator address, 24-bit arithmetic, 515 logical qubits, 1,225,138 CX, and p95 LDF-next error 7.26e-4.
- [x] Clean H2/CO2/CH4/CO/N2 one-cell LDF microsteps compiled separately: 490–515 logical qubits and 1,118,920–1,965,308 CX each; sequential workspace-reuse accounting is 675 logical qubits and 6,547,362 additive CX.
- [x] Product-end valve/component-flux module compiled at 288 logical qubits and 800,762 CX; separate five-component fixed-policy product-split/tank-capacity accounting is 677 logical qubits and 1,043,990 additive CX.
- [x] Gas-inventory pressure reconstruction compiled at 152 logical qubits and 93,764 CX; oriented internal-face five-component transport compiled at 404 logical qubits and 1,340,390 CX, with 584-qubit/1,527,918-additive-CX modular accounting.
- [x] Three pressure reconstructions and two internal faces directly composed with five centre-cell balances: 1,508 logical qubits, depth 12,250,291, and 8,328,622 CX over 12,928 states/64,640 component balances.
- [x] Both upwind compositions generated reversibly from gas inventories and directly composed with the same transport/balance path: 1,651 logical qubits, depth 22,143,683, and 14,667,150 CX; standalone normalizer 333 qubits/1,340,232 CX; 25,856 normalization states with zero erasure/overflow.
- [x] Five sign-split interior-cell component balances compiled at 198–209 logical qubits and 68,676–80,800 CX each; workspace-reuse accounting is 609 logical qubits and 366,802 additive CX over 64,640 cached balances with zero underflow.
- [x] Current/next loading sign extraction and solid-mass conversion directly composed with cell balance: 26/26/32/32/30-bit interfaces, 383–431 qubits and 139,600–343,680 CX per component, and 934 qubits/1,411,882 additive CX with workspace reuse.
- [x] Widened LDF current/next registers directly composed with sign extraction, solid conversion, and next-gas balance: 861–929 qubits and 3,412,254–4,991,534 CX per component; five-component accounting is 1,317 qubits/19,082,852 additive CX.
- [x] Full 20-bit normalized pressure/composition and both generated internal faces directly connected to parameter-specialized LDF uptake and the same component balance: 1,944–2,039 qubits and 20,670,468–35,947,274 CX per path; 2,039-peak-qubit/128,013,726-additive-CX conservative upper bound; monolithic five-component transpilation explicitly open.
- [x] Shared product pressure/composition directly connected to factor-specialized LDF uptake, product-valve flux, and one boundary balance: 1,072–1,195 qubits and 10,060,060–26,810,396 CX per component; 1,195-peak-qubit/88,388,552-additive-CX conservative upper bound; product normalization, inward-face generation, controller wiring, and monolithic compilation explicitly open.
- [x] Two product-end gas inventories directly connected through two composition normalizers, two pressure reconstructions, one inward face, factor-specialized LDF uptake, product-valve flux, loading conversion, and one boundary balance: 1,803–1,952 qubits and 20,253,112–37,020,740 CX per component; 1,952-peak-qubit/139,413,748-additive-CX conservative upper bound; consumption of controller-generated coefficients and monolithic compilation explicitly open.
- [x] Coherent finite-support run/schedule/tank controller: 352 run-parameter values, 8 schedule addresses, and 640 tank records checked; 440 qubits, depth 324,495, and 166,189 CX with zero meaningful tank erasure, underflow, or mismatch.
- [x] Coherent run factors directly converted to five component equilibrium and LDF-alpha coefficients plus paired-bed adsorption flags: 320 coefficient records and 16 flags checked; 495 qubits, depth 526,434, and 353,441 CX; all declared relative-error gates pass.
- [x] Intermediate coefficient-consumer audit with a supplied 20-bit Langmuir response: 64,640 component balances; 1,297–1,486 qubits and 1,855,912–2,807,252 CX per path; zero quantized-transfer erasure.
- [x] Run-affinity-dependent Langmuir denominator/reciprocal generated from supplied 20-bit pressure and five compositions and consumed in the same five schedule-gated paths: 64,640 component balances; 1,771–1,960 qubits and 41,440,216–42,391,556 CX per path; denominator p95/max 1.955e-04/3.530e-04.
- [x] Three raw five-component gas inventories directly connected through two normalizers, three pressure reconstructions, two oriented faces, coherent control, dynamic Langmuir response, q*/LDF/loading conversion, and one conservative component balance: 2,696–2,885 qubits and 55,337,688–56,289,028 CX per path; 2,885-peak-qubit/279,319,932-additive-CX conservative upper bound.
- [x] Correlated dense-loader infeasibility control and explicit structured-loader caveat.
- [x] Nine-job IBM hardware campaign across three backends and three fixed transpiler seeds, with job IDs, counts, layouts, calibration times, charges, crossed variability analysis, and claim boundary.
- [x] Independent H2/public-simulator controls reported without cross-system pooling.
- [x] Prospective H2 campaign precision target.
- [x] Main manuscript, six main figures, four main tables, SI draft, environment freezes, hashes, highlights, cover-letter draft, and graphical abstract.
- [x] Condense Tables 3 and 4 to eight claim-critical rows each in the main text and reproduce the complete 31/32-tier audit tables as Supplementary Tables S1/S2.
- [x] Compile the pressure-derived saturated/unsaturated tank-allocation tier: 647 qubits, depth 1,127,046, and 705,194 CX; preserve 128 observed saturated and 224 bounded-counterfactual unsaturated labels with p95/max component-scale errors 1.687e-4/3.872e-4.

## Scientific gates that most affect CCE acceptance

- [ ] **Highest priority:** same physical product-recycle control in H2, with synchronized pressure, valve state, feed/product/recycle flow, continuous product composition, cycle index, and product/recycle split.
- [ ] Use held-out groups or runs; target recovery RMSE <=1.517 percentage points across the observed recycle support, or about <=0.156 percentage points if retaining only the 0.420–0.430 span.
- [x] Repeat the frozen QPU kernel on three backends and three fixed transpiler seeds; report the complete crossed nine-job hardware boundary and descriptive variation without claiming a universal device effect.
- [ ] Generate a physically integrated unsaturated tank trajectory, connect the completed normalized dynamic component paths into at least one complete adsorption phase, and compare it with the 85-cycle physical target.
- [ ] If an end-to-end advantage claim is pursued, implement and compile a scalable structured correlated loader. This is unnecessary for the present boundary-paper claim.

## Author and journal administration

- [x] Record final author order, Korea Gas Safety Corporation affiliation, Ugwiyeon Lee as corresponding author, emails, and validated ORCID check digits.
- [x] Draft the CRediT statement: Ugwiyeon Lee holds the research and manuscript roles; Seong-Yun Bae, Hakrae Kim, and Jungsu Lee hold Writing – review & editing.
- [ ] Obtain explicit approval of the final manuscript, order, and CRediT statement from every author.
- [x] Insert a Methods description and pre-reference declaration of OpenAI Codex use that follows Elsevier's June 2026 generative-AI policy; retain author confirmation as a final approval gate.
- [ ] Confirm funding, acknowledgements, and conflict of interest statements.
- [x] Convert the manuscript, author title page, and SI into separate DOCX files and verify their Word-rendered pages (30-page review manuscript, 1-page title page, and 7-page SI at the current revision).
- [x] Apply the current CCE reference, table, and artwork requirements: author-year citations, alphabetized references, editable tables without shading or vertical rules, and separate vector-PDF versions of all six main figures.
- [x] Verify the graphical abstract against the current guide: 3,706 x 1,446 px PNG plus vector PDF, exceeding the 1,328 x 531 px minimum.
- [ ] Create a permanent public code/data archive and insert its DOI.
- [ ] Confirm the originality/not-under-review statements in the cover letter.
- [ ] Perform final English, symbol, unit, figure-number, and cross-reference checks.

## Submission decision

The package is structurally complete but `submission_ready=false`. A resource-boundary methods paper can be submitted after author/journal administration if the remaining scientific gates are disclosed. The multi-backend repeated-QPU gate is now complete; the strongest CCE version still closes the same-control H2 validation gate. End-to-end quantum advantage remains outside the supported claim.
