# Resource-aware quantum amplitude estimation for chance-constrained pressure swing adsorption: classical baselines, compiled oracle costs, and a hardware boundary

## Abstract

Quantum amplitude estimation (QAE) offers a nominal query advantage for chance-constrained process optimization, but state preparation, reversible evaluation, hardware noise, and strong classical estimators can remove it. We compare Monte Carlo (MC), randomized Sobol quasi-Monte Carlo (RQMC), importance sampling, and maximum-likelihood amplitude estimation (MLAE) on a frozen purity/recovery event from a 32-run cyclic pressure swing adsorption model. At recycle fractions 0.420, 0.427, and 0.430, reference probabilities are 0.92743, 0.47044, and 0.28360. RMSE is 0.00679 for MC, 0.00248 for RQMC, 0.01017 for importance sampling, and 0.00289 for noiseless MLAE. MLAE improves on MC but not RQMC; the nearest failed policy is 11.91 RQMC RMSE from feasibility. Stream-to-event logic requires 510 qubits and 1.286 million CX. Five controller-coupled paths generate composition, pressure, two faces, a run-affinity Langmuir response, LDF uptake, and one component balance directly from raw gas inventories at 2,696–2,885 qubits and 55.34–56.29 million CX. An 845-qubit two-pressure tank circuit preserves 128 physically generated unsaturated, zero-makeup calls in a declared short-schedule control; this is not the frozen policy. On `ibm_marrakesh`, a three-qubit event gives unmitigated MLAE 0.56694 for exact 0.625. Process discrepancy exceeds the QAE precision target, and no screened public source supplies synchronized H2 data for the same policy and event. This PSA regime favors RQMC. QAE requires a validated oracle, repeated reuse, structured loading, and tolerable reversible overhead.

## Keywords

Pressure swing adsorption; quantum amplitude estimation; uncertainty quantification; chance constraints; quasi-Monte Carlo; process systems engineering

## 1. Introduction

PSA design and operation require repeated cyclic simulations under uncertain feed composition, adsorption parameters, valve behavior, and timing. A purity/recovery chance constraint creates an inner uncertainty-propagation problem inside a classical policy search. Crude Monte Carlo is general but slow; scrambled Sobol quasi-Monte Carlo, importance sampling, and surrogates are essential comparators for a quantum proposal.

QAE has nominal inverse-query error, but process applications must load uncertainty, evaluate and uncompute the event, and account for noise. These costs can dominate for enumerable priors or smooth responses that favor QMC.

Classical uncertainty-aware PSA optimization already includes disturbance-aware hydrogen PSA design [@khajuria2013psa], surrogate-assisted multiobjective optimization [@shah2019mlpsa], Bayesian and learned process models [@hybrid2026pvsa; @park2026polybedvpsa; @ceccanti2026deeponet], and open dynamic solvers [@kim2023topsail; @schytt2026nitrogenpsa]. A relevant quantum comparison must therefore survive these accelerations rather than benchmark only against crude MC.

Quantum risk and simulation-based optimization encode feasibility as an amplitude inside a classical decision loop [@woerner2019quantumrisk; @gacon2020qsbo]. Maximum-likelihood QAE avoids the deep Fourier transform of canonical QAE [@callison2022mlqae], and reliability studies provide adjacent failure-probability examples [@he2025qareliability; @sarno2026qaegrad]. Process precedents include amplitude amplification for nonlinear reactor control [@nieman2024cstramplitude] and a QUBO dynamic-optimization study that found no advantage over classical solvers [@nenno2024dynamicquantum]. The scoped search identified no cyclic PSA study combining QAE/MLAE with a matched MC/RQMC/IS benchmark, CSS and balance gates, compiled process-event resources, and a hardware boundary. The novelty claim is limited to this combination.

We retain a classical policy layer and evaluate its chance constraint with classical estimators or MLAE. We report a matched benchmark; verified event oracles and a three-qubit hardware kernel; loading, evaluation, depth, noise, and post-processing costs; and controls showing when classical methods or model error dominate QAE.

## 2. Hybrid PSA chance-constrained workflow

Let `u` denote uncertain feed, material, valve, and timing variables, and let `d` denote a candidate PSA operating policy. A classical PSA evaluator returns purity, recovery, convergence, and balance diagnostics. The joint feasibility event is

`f(u,d) = I[purity(u,d) >= purity_min, recovery(u,d) >= recovery_min, CSS pass, balance pass]`.

The frozen primary rule selects the largest candidate recycle fraction whose point estimate of `p(d)=E[f(u,d)]` exceeds the declared reliability threshold. Confidence-aware lower-bound selection is retained as a finite-sample sensitivity analysis. Candidate generation remains classical. This construction permits the same event labels to be used by MC, RQMC, IS, and MLAE and prevents estimator comparisons from being confounded by different process definitions.

The primary decision case uses product-gas recycle fractions `0.420/0.427/0.430`, the joint event `H2 product >= 0.9998` and `external recovery proxy >= 0.789`, and a target probability of `0.50`. A standardized linear response surface and regularized Gaussian copula are fitted to 32 CSS-converged spatial/tank PSA runs. Eight independently scrambled Sobol calculations with `2^18` points each define the numerical reference. The problem specification, estimator budgets, endpoints, and prohibited claims are frozen in `PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json`.

An externally anchored breakthrough event is retained as a separate circuit-construction and hardware test with exact finite probability `5/8`. The direct finite physical policy table, TU Wien H2/CH4 experiment, Otway valve-pressure log, industrial target, and public dynamic PSA solver serve as calibration, model-form, and reproducibility controls. These controls are not substituted for the primary event and prior.

### 2.1 Evidence hierarchy and process boundary

The workflow uses several process representations for different questions, and their evidential roles are kept separate. The 32-run spatial/tank design defines the primary conditional estimator problem. It includes independent source-gas composition coordinates, adsorption-capacity, affinity and linear-driving-force multipliers, low pressure, equalization conductance, and recycle fraction. Only rows that reached the declared cyclic-steady-state and balance gates enter the primary response fit. This data set is sufficiently structured to define a common estimator benchmark but too small to establish plant validity.

Reduced two-bed simulations support phase ledgers, balances, model-form comparisons, and finite event tables; they do not replace the primary response surface. TU Wien, Otway, and public CO2/N2 evidence remain separate calibration or control tiers. The eight-state breakthrough table is only the hardware kernel.

The declared system boundary ends at conditional policy screening. It does not include compressor sizing, adsorbent replacement, detailed plant scheduling, or an economic objective. The outer policy set is fixed and finite. The inner estimand is the probability of satisfying the process event under the fitted uncertainty model. This boundary is chosen because amplitude estimation applies to the expectation of a bounded indicator, while the outer search and process-model construction remain classical.

Figure 1 summarizes the two coupled paths: the primary process-decision experiment and the resource/validity audit that maps the QAE branch to state preparation, reversible event evaluation, amplification, hardware, and process-model discrepancy.

Table 4 condenses eight claim-critical tiers covering the response model, physical CSS horizon, integrated event oracle, gas-inventory-to-dynamic-Langmuir state update, pressure-derived tank allocation, external controls, and QPU kernel. The complete 31-tier hierarchy is Supplementary Table S2 and remains machine-readable; the tiers are not pooled as replicates of one plant.

### 2.2 Response surface and correlated prior

Let the physical design contain input vectors x_i and two responses y_i: product H2 fraction and the external H2 recovery proxy. Each of the 11 input coordinates is centered and scaled with the design mean and standard deviation. An intercept and the standardized coordinates form the design matrix, and the two responses are fitted jointly by ordinary least squares. The resulting affine map is used only inside the conditional estimator comparison. Leave-one-out diagnostics and residual-stress calculations are reported separately so that response approximation error is not folded into sampling error.

Dependence among the sampled coordinates is represented by a regularized empirical Gaussian copula. For each coordinate, stable ranks are converted to pseudo-observations u_ij=(r_ij+0.5)/32 and then to normal scores z_ij. The sample correlation R of the normal scores is shrunk as

R_reg = 0.90 R + 0.10 I,

which guarantees a stable Cholesky factor for the nearly collinear source-composition fractions. A unit-hypercube draw is transformed to independent normal scores, multiplied by the Cholesky factor, mapped through the normal CDF, and returned to each physical marginal with linear empirical quantiles. This is a reproducible conditional prior inferred from 32 process runs. It is not a posterior distribution for an industrial plant.

For each candidate policy, the sampled recycle coordinate is overwritten by the fixed decision value before evaluating the response surface. This removes decision uncertainty from the inner prior and leaves nine varying coordinates after the constant source-CO2 coordinate is also removed in the compiled primary oracle. The same transformed samples can be reused across policies, producing a paired policy comparison and reducing variation that would otherwise arise from independent sampling.

The numerical reference for each policy averages eight independently scrambled Sobol calculations, each with 2^18 points. The reference therefore uses 2,097,152 event evaluations per policy on the fitted response surface. The spread across the eight scrambles is retained as a numerical-convergence diagnostic. It is not included in the estimator RMSE denominator as if it were an exact plant truth.

### 2.3 Frozen policy rule and constraint activity

The protocol was frozen before the final matched comparison. The candidate recycle fractions are 0.420, 0.427, and 0.430; the event thresholds are 0.9998 purity and 0.789 recovery; and the target probability is 0.50. The primary rule selects the largest candidate whose estimated probability reaches the target. This rule provides a simple outer decision loss: an estimator is wrong if it changes the selected policy relative to the high-N reference.

Table 1 lists the complete frozen protocol, including the prior, estimator budgets, allowed claim, and prohibited claims.

The point-estimate rule is primary because the main experiment compares estimation methods under equal declared events. A lower-confidence-bound selection is treated as sensitivity analysis rather than silently changing the decision rule after observing results. Probability classification error is recorded for every policy estimate, and policy error is recorded once per three-policy replicate.

The engineering consequence of the outer rule is reported with quantities that require no unmeasured equipment assumptions. A recycle fraction `r` allocates `r` of gross adsorption product to the internal tank, leaves `1-r` as external product, and implies `r/(1-r)` units of internal recycle allocation per unit external product. Each policy's probability margin from the 0.50 target is divided by the observed MC, RQMC, and noiseless-MLAE RMSE and by the residual-stress probability half-width. This audit tests whether improved probability-estimator precision could change the frozen decision. It is not converted to compressor duty, operating cost, or plant profit because no validated pressure-duty or economic model is available.

An affine-support audit is performed before interpreting the joint event. It evaluates the fitted response range over the bounded training-coordinate support. The audit shows that the primary purity threshold is inactive. The original thresholds remain frozen, and a separate rounded threshold grid identifies cases where both purity and recovery are active.

### 2.4 External and physical controls

The controls answer narrower questions than the primary experiment. A finite physical table and synchronized phase ledger check event bookkeeping, pressure, inventory, outlet composition, and balance residuals. A public CO2/N2 solver tests the three numerical policy values in four scenarios; a policy effect must also exceed the change caused by spatial-flux refinement before it counts as independently resolved. These controls define event and numerical consistency without transferring chemistry or claiming that the reduced affine cycle is a transport model.

Three H2 controls are kept distinct. Thelen VA-10 provides a matched equalization-pressure pair with two recovery calculations [@thelen2023h2psa]. A corrected pyAPEP 0.1.8 wrapper applies the three product-split values to a uniform zeolite-5A column, connects purge and pressurisation at the light-product end, counts external source-gas makeup in the recovery denominator, and reports product-tank self-sufficiency [@ga2023pyapep]. Its short policy screen and extended fixed-horizon control are topology-feasibility diagnostics, not CSS validation. The archived toPSAil/Yang case supplies a two-bed, six-step H2/CO model with equalization, product tank, experimental valve/pressure/recovery calibration, and published CSS behavior [@kim2023topsail; @yang1997twobedh2]. Equalization pressure and purge/feed are not product recycle, and the toPSAil repository lacks the published numerical result files, so none of these controls is relabelled as a replication of the frozen selection.

### 2.5 Calibrated one-cycle phase-map bridge

The reduced H2 ledger is extended to retain the full eight-dimensional state of each bed: four gas-phase component inventories and four adsorbed loadings. Component-wise inlet, outlet, and stored inventories are retained for every phase, and both bed states are retained before and after equalization. Eight phase-specific ridge maps predict state increments and integrated outlet H2 from the incoming state, three adsorption-parameter multipliers, and three independent feed-composition coordinates.

Validation uses an outer leave-one-run-out loop over the 20 physical runs. Within each outer training set, ridge strength is selected by an inner leave-one-out loop from eight fixed candidates. The held-out phase maps are then composed in the physical schedule. The original mass-conservative equalization equation is applied between learned phase maps, so equalization is tested for branch consistency but is not represented as learned or reversible arithmetic. This design tests whether a calibrated state-transition bridge can reproduce one cycle without evaluating the held-out differential-equation trajectory.

### 2.6 Primary phase-stream event bridge

The frozen 32-run spatial/tank model is rerun without changing its parameters or outputs. For the final CSS cycle of every run, the ledger records eight bed phases, two endpoint equalizations, four tank withdrawals, and two product/recycle splits. Five-component adsorption inlet streams and external-product streams reconstruct the exact primary purity and recovery event. Aggregate bed states retain component gas and adsorbed inventories while endpoint pressures preserve the spatial direction interface.

Eight phase-specific ridge maps predict aggregate state increments and five-component inlet/outlet streams. Each run is held out in an outer loop and ridge strength is selected inside the other 31 runs. The two held-out adsorption stream predictions are combined with the declared recycle split to reconstruct purity and recovery. This uses the held run's observed phase-start states and therefore tests process-stream observability rather than free-running CSS. Fixed-point precision is accepted only when p95 purity and recovery quantization errors are below 10% of their nested-holdout p95 errors and all 32 event labels are retained. The six event-active stream outputs for each adsorption phase are then transpiled independently.

Two stricter compositions remove intermediate held states. First, the held run supplies only its two aggregate bed states at the final-cycle start; eight phase maps and two separately held-out equalization maps are then composed in schedule order. Second, an outer-held affine initializer predicts the 20 aggregate cycle-start gas/adsorbed coordinates from the 11 frozen uncertainty and decision parameters, after which the same one-cycle composition is evaluated without any held dynamic state. The learned aggregate map is also iterated for 50 cycles from both the observed and predicted start to test local stability rather than assume CSS.

The source of repeated-map instability is diagnosed from the exact Jacobian assembled from the affine phase and equalization blocks. Without using held labels or held dynamic trajectories, a cycle-boundary control anchors the raw map `F(x)` to the outer-held parameter-only initializer `x_css` as `G(x)=(1-w)F(x)+w x_css`. The smallest `w=max(0,1-0.9/rho(F))` sets the fitted local spectral radius to a predeclared 0.9. This screen distinguishes correctable reduced-model instability from a physical tank/spatial CSS result.

A physical-horizon audit reruns all 32 spatial/tank rows for 100 cycles and retains 85 boundary-state scalars: 40 per bed and five tank inventories. Tail stability requires every later cycle to pass strict CSS and retain the final event label. The 8--24-bit screen retains all final strict/L1 CSS decisions and event labels, settles within 100 cycles, and limits p95 final-state relative L1 quantization error to `1e-5`. Register counts use an explicit clean out-of-place current/next layout and are architecture-specific rather than universal lower bounds.

The nonlinear microkernel evaluates `q_i*=qcap_i b_i P y_i/(1+P sum_j b_j y_j)` and `q_next=q+k dt(q*-q)` for `dt=1 s` over all cached cell states. CO2 retains p95 relative-error limits of 5% for `q*` and 0.1% for `q_next`; trace components use p95 absolute errors below 0.25% of their loading-register ranges. Every component must have zero overflow and zero nonzero-`q*` erasure. Each clean circuit copies `q_next` and reverses its arithmetic workspace in an all-to-all `u/CX` basis. Components are first compiled separately, then recompiled at the wider loading-sign interface widths and mapped directly into the balance circuit. Reversible run-specific parameter registers, face generation, and repeated integration remain outside these blocks.

Product-boundary arithmetic uses two source tiers. Across 6,464 cached outlet states, `k_out max(P-P_back,0)` and five fluxes `F y_i` must retain all active and nonzero labels within the declared flow errors. Temporary flux registers feed five product-cell balances before valve reversal. The supplied-nonvalve inventory screen requires zero erasure, underflow, and overflow, p95 error below `1e-4`, and maximum error below `2e-4` of each next-inventory scale. The direct product-cell follow-on shares 20-bit pressure/composition registers between a factor-specialized competitive-Langmuir/LDF path and the valve, whose inputs are the high 18 bits. Generated loading transfer and valve flux enter the same balance; its p95/maximum next-gas limits are `2.5e-4/5e-4`. Separately, 64 final-cycle records screen fixed `r=0.420` product splitting, tank candidates, and a 100 mol capacity flag at `1e-6` p95 normalized error. The one-second circuits and integrated records remain separate tiers.

Internal transport is screened over 25,856 cached cell states and 19,392 faces. Fixed-point inventories generate pressure; two pressures and an upstream composition generate five one-second transfers. Selection requires zero erasure, overflow, underflow, and label mismatch plus declared pressure, flow, and flux limits. All cached nonzero faces are left-to-right, so general negative-flow upwind switching remains excluded. A supplied-composition circuit is retained as an interface baseline. The direct normalization tier converts the five component-specific 18-bit inventory codes to a common 22-bit amount scale, forms total gas, extracts an 8-bit support-adaptive reciprocal address, loads a conservative 22-bit reciprocal from a 256-segment QROM, and multiplies each component amount into a 20-bit mole fraction. The thresholds are frozen from the audited left/centre-cell support; zero output overflow and erasure are required, but out-of-support guarantees are not claimed. For each interior cell, two normalizers, three pressure circuits, and two face circuits feed `n_next=n+F_left+desorption-F_right-adsorption`; five outputs are copied before exact face/pressure/normalization reversal. A separate interface derives loading-change sign and magnitude, applies fixed solid mass, and uncomputes; each widened LDF output is also mapped into that interface and reversed. The joint screen feeds the full 20-bit centre pressure and composition outputs into parameter-specialized competitive-Langmuir/LDF circuits, then consumes the generated loading change in the same balance as the generated two-face transfers. The propagated face-to-inventory screen uses p95/maximum limits `2e-4/5e-4`, while its arithmetic-only limits remain `2.5e-5/5e-5`; all erasure, overflow, and underflow rates must be zero.

The finite-support control interface uses a five-qubit run address to XOR eleven 12-bit parameter words, a three-qubit stage address to decode six paired-bed steps and their local valve masks, and a seven-qubit run/slot address to load five 18-bit recorded tank withdrawals. Each withdrawal is subtracted from a retained tank input and reversed. A separate support-specific circuit reconstructs source-end pressure from five gas inventories, computes `k_in Δt max(P_high-P_end,0)`, compares this demand proxy with tank inventory, copies the tank on the saturated branch, and uncomputes all work. The general unsaturated allocation remains outside scope.

The final joint event is first compiled as a modular interface from three unsigned aggregate registers: adsorption-feed H2, external-product H2, and external-product impurity. Separate physical scales avoid losing the small impurity inventory. Register precision must retain all 32 labels and keep p95 purity and recovery quantization error below 10% of the nested-held-out stream-map p95 errors. Division is removed by integer cross-multiplication. Two `WeightedAdder`/`IntegerComparator` blocks retain the purity and recovery flags, a controlled-Z marks their conjunction, and the flag computation is inverted exactly.

The upstream connection is then synthesized without materializing 12 separate scalar stream registers. Because both adsorption maps are affine, fixing one candidate recycle fraction lets their feed and product terms be collapsed algebraically into the same three aggregate observables. The external fraction is folded into the product-H2 and impurity coefficients; shared process parameters use one register rather than one copy per bed. The resulting policy oracle starts from 29 unique encoded phase-state/parameter variables at 12 bits each, constructs three aggregate registers, performs the two event comparisons, marks the joint phase, and applies the exact circuit inverse. Aggregate precision is accepted against the same 10%-of-nested-holdout budgets over 32 phase-state points and all three candidate policies. Each candidate is a separate classically selected probability oracle; coherent superposition over policies is not used.

## 3. Estimators and resource accounting

All estimators use the same declared event and uncertainty distribution. MC and scrambled Sobol-QMC report replicated error or confidence intervals. Importance sampling reports normalized weights and effective sample size. MLAE uses circuits with Grover powers `m` and fits the event probability from the binomial likelihood

`Pr(y_m | p) = Binomial[n_m, sin²((2m+1)asin(sqrt(p)))]`.

The cost comparison separates the following terms:

- classical process evaluations;
- state-preparation or loader operations;
- controlled forward and inverse process-oracle operations;
- event comparison and amplitude marking;
- circuit repetitions and measured QPU usage; and
- classical likelihood fitting.

The eight-state hardware tier has event labels `[0,0,1,0,1,1,1,1]` and exact probability `5/8`. A four-qubit reversible flag oracle verifies the mapping on all address and target basis states. Boolean minimization gives

`f(q2,q1,q0) = q2 OR (q1 AND NOT q0)`.

The hardware circuit implements the equivalent phase predicate on three logical qubits, eliminating the flag and repeated flag compute/uncompute. Grover powers `m=[0,1,2]` form the primary QPU experiment; `m=4` is a simulation stress control.

### 3.1 Matched classical estimators

Crude Monte Carlo uses 3,500 pseudorandom unit-hypercube draws per replicate. Randomized QMC uses 4,096 points from an independently scrambled Sobol net. A new scramble seed is assigned to every one of the 200 replications. The sample counts differ because Sobol generation uses a power of two; both observed accuracy and actual calls are reported rather than forcing equal nominal N.

The importance sampler operates in the independent standard-normal latent space of the copula. A local event-boundary direction is estimated at recycle 0.427 by finite differences of the standardized minimum purity/recovery margin. The direction is normalized to length 1.5. Samples are drawn from an equal mixture of N(0,I), N(+s,I), and N(-s,I), where s is the boundary shift. Likelihood ratios use the exact three-component mixture density. Effective sample size,

ESS = (sum_i w_i)^2 / sum_i w_i^2,

and the maximum normalized weight are retained for every replicate. The unnormalized estimator averages w_i f_i because the proposal and target densities are both known. The base component makes the proposal defensive, but it does not guarantee improvement for the broad, non-rare primary event.

The same state sample is evaluated for all three policies within each MC, RQMC, or IS replicate. This pairing makes the selected-policy error sensitive to estimator noise rather than to unrelated prior samples. Local wall time covers sampling, prior transformation, response evaluation, and, for MLAE, likelihood fitting. It is labeled by computation type and never equated with hardware execution time.

### 3.2 MLAE experiment

The MLAE schedule uses Grover powers m={0,1,2,4,8} and 100 shots at each power. The amplitude-oracle query convention counts 2m+1 calls per shot, giving

100 [1+3+5+9+17] = 3,500

queries. For a true event probability p, theta=asin(sqrt(p)), and the ideal success probability at power m is sin^2[(2m+1)theta]. Binomial counts are generated for every policy and replicate and the likelihood is evaluated on a grid of 20,001 candidate probabilities.

The noiseless MLAE comparison isolates estimator behavior conditional on an exact amplitude oracle. Two sensitivity cases replace each ideal amplified probability q by (1-2 eta)q+eta for eta=0.01 and 0.05. This symmetric contraction is a diagnostic noise proxy rather than a device model. It shows how amplification can turn a small per-circuit distortion into estimator bias. The actual IBM experiment is analyzed separately from these simulated noise levels.

### 3.3 Error and decision metrics

For every method, error is pooled across the three policy probabilities and 200 replications. Reported metrics are RMSE, mean absolute error, and signed bias. A probability classification is correct when the estimate and reference lie on the same side of the 0.50 target. The policy selection is correct when the largest estimated feasible candidate equals the reference selection. Correct-selection fractions use two-sided Wilson 95% intervals, which remain defined at 0 or 1 observed error rates.

The error metrics are conditional on the response surface and copula prior. Residual-stress and cross-oracle differences are reported outside the sampling RMSE so that model discrepancy is not mistaken for estimator variance. This separation also prevents an artificially precise quantum estimate from implying a correspondingly precise process conclusion.

### 3.4 Resource crossover

The first crossover uses forward-evaluation-equivalent units. The measured 3,500-sample MC RMSE is extrapolated with N^(-1/2) to the count matching noiseless MLAE; 10,000 bootstraps of complete three-policy replications propagate uncertainty. The equal-RMSE MC count divided by 3,500 is the maximum loader-plus-controlled-oracle multiplier consistent with an ideal advantage over crude MC. This normalized proxy is kept separate from compiled gates and quantum wall time.

The finite-table phase oracle marks either successful rows or their globally phase-equivalent complement. Exhaustive basis evaluation verifies both forms before all-to-all CX and linear-connectivity ECR transpilation. The structured response oracle fixed-point encodes each active coordinate, accumulates signed weights, compares recovery with its threshold, phases the event, and uncomputes. Resolution increases until classifier disagreement is below the observed MLAE RMSE. Its frozen-schedule count excludes loading, routing, reset, and fault tolerance.

The calibrated phase-map precision screen limits fixed-point p95 state and outlet-H2 errors to 10% of nested-holdout p95. The minimum proxy uses 11 bits per active input and a 16-bit accumulator. Qiskit `WeightedAdder` blocks implement nine scalar outputs for each of eight phases; counts are reported forward and for serial compute-uncompute with scalar-workspace reuse. Constant/state updates, equalization, repeated CSS, event comparison, loading, routing, and fault tolerance remain open.

The primary event-active tier similarly compiles 12 adsorption-stream blocks at 12 input bits and 16 output bits. It remains conditional on observed phase-start states. A modular final event block starts from three 16-bit aggregate stream registers, performs the two ratio tests by integer cross-multiplication, marks their conjunction, and uncomputes its work registers. The policy-specific integrated tier collapses the same affine stream maps directly into 19-bit aggregate registers, includes fixed-policy recycle scaling, and connects them to the joint event in one clean oracle. A separate parameter-only CSS initializer uses 9 bits per active parameter and a 14-bit accumulator after satisfying state-L1, purity, and recovery budgets with 32/32 labels. Physical repeated-cycle state generation, loading, routing, and fault tolerance remain outside these compiled arithmetic tiers.

A three-bit structural control connects reversible updates, conservative transfer, two comparators, a joint phase mark, and exact uncomputation. Exhaustive coherent evaluation over 64 states tests module wiring; its integer dynamics are not fitted PSA kinetics.

### 3.5 State-preparation boundary

The low-resolution copula loader is an exact arbitrary-state control. A 2^18 scrambled-Sobol sample is quantized on one- and two-bit grids for each of the nine active coordinates. Cell frequencies define amplitudes sqrt(n_j/N). Qiskit StatePreparation synthesizes the resulting state in an all-to-all u/CX basis. A full statevector fidelity check is performed for the nine-qubit case; the 18-qubit case is compiler-checked without allocating a second full statevector.

This construction is deliberately unfavorable but concrete. It measures what dense exact loading costs at resolutions that can still be compiled locally. The seven-bit requirement comes from the independently compiled response oracle and is used to expose the dense address-space boundary. No seven-bit loader circuit is claimed. A structured loader could exploit the Gaussian transform and piecewise empirical quantiles, so the dense count is a negative control rather than a lower bound for every possible algorithm.

### 3.6 Hardware protocol

The hardware tier uses a separate eight-state process-linked event with exact p=5/8. The minimized three-qubit phase predicate is inserted into the same Grover construction used by the likelihood model. Circuits are transpiled to a named backend with a recorded seed, physical layout, depth, and two-qubit-gate count. Each circuit receives 4,096 shots in the completed reference job. Raw bitstrings, runtime metrics, calibration timestamp, and the submitted circuit metadata are archived before fitting the likelihood.

Only the IBM instance verified as plan open is permitted by the submission script. Local simulation and dry-run transpilation are separate commands. Retrieving an existing job does not submit a workload. A prepared replication matrix covers three backends and three transpiler seeds, but it remains outside the primary evidence until job identifiers and results exist.

### 3.7 Reproducibility and claim control

The primary protocol, estimator records, resource tables, circuit reports, and figures are machine readable. Local package runners regenerate the matched estimator and gate-compilation artifacts without submitting QPU work. SHA-256 manifests record code, input, result, report, and figure files. A separate claim audit checks frozen probabilities, estimator errors, gate counts, hardware metadata, external-control outcomes, and required reviewer-facing files.

Random seeds are explicit for the high-N references, RQMC replications, estimator simulation, transpilation, and bootstrap. The manuscript distinguishes measured quantities, compiled resource counts, arithmetic proxies, extrapolations, and future requirements. Prohibited claims in the frozen protocol include industrial H2 validation, a global PSA optimum, end-to-end quantum speedup, and equivalence between local likelihood-fit time and QPU execution time.

The novelty screen was refreshed on 9 October 2026 using the exact and related queries `"pressure swing adsorption" "quantum amplitude estimation"`, `"pressure swing adsorption" quantum computing optimization`, `"quantum amplitude estimation" adsorption process`, and `"quantum amplitude estimation" chemical process optimization`. Candidate records were followed to publisher, DOI, or preprint pages and separated into QAE/risk methods, process-quantum precedents, and classical PSA optimization. No direct cyclic multicomponent PSA study embedding QAE or MLAE in a chance-constraint calculation was identified. This is a bounded search observation rather than proof of universal absence; the complete query scope and exclusion rule are reported in the Supporting Information.

OpenAI Codex was used as an AI-assisted development environment for code drafting and refactoring, local workflow orchestration, consistency audits, figure and table assembly, manuscript organization, and language editing. The authors retained control of the scientific protocol and evidence selection, executed or retrieved the reported computations in the documented environments, inspected the source data and generated artifacts, and verified numerical claims through deterministic checks, inverse tests, SHA-256 manifests, and manual review. No AI-generated value was accepted as process or QPU evidence without an underlying executable or archived source artifact.

## 4. Results

### 4.1 Classical estimator and policy result

Reference probabilities for recycle `0.420/0.427/0.430` are `0.927431/0.470440/0.283597`, so the frozen point-estimate rule selects `0.420`. Across 200 replications, RMSE is `0.006794` for 3,500-sample MC, `0.002482` for 4,096-point RQMC, `0.010170` for 3,500-sample defensive-mixture IS, and `0.002892` for noiseless 3,500-query MLAE. MC, RQMC, and MLAE select `0.420` in all replicates; IS does so in 199. Corresponding Wilson 95% correct-selection intervals are `[0.981,1.000]` and `[0.972,0.999]`.

The selected split leaves `0.580` as external product and allocates `0.7241` recycle units per external-product unit. The nearest failed policy, `0.427`, has probability shortfall `0.029560`, which is `11.91` RQMC RMSE, `10.22` MLAE RMSE, and `7.57` residual-stress half-width. Finer probability estimation therefore cannot change the frozen decision within this surrogate; independent model discrepancy remains larger.

Table 2 reports evaluation/query counts, error, classification, policy selection, intervals, and local surrogate or likelihood-fit time. Figure 2 shows the common probability curves and RMSE ranking. An affine-support audit finds minimum purity `0.9998353`, above the frozen `0.9998` threshold, so the primary event is recovery-controlled. Thresholds remain unchanged. In a disclosed `5 × 5` sensitivity grid, eight cells activate both constraints, retain the `0.420` selection, and agree across four scrambled-Sobol references.

IS has median ESS `2603.6/3500` without dominant weights. Its symmetric shifted proposal wastes evaluations for this non-rare event, documenting that a favorable rare-event comparator cannot be assumed.

### 4.2 Resource crossover

MC would require approximately `19,323` evaluations to match the measured 3,500-query MLAE RMSE, allowing at most `5.521` forward-equivalent units per amplitude-oracle query. The optimistic spatial/tank proxy assigns `2.00045` forward equivalents to controlled evaluation plus loading, so MLAE is `0.362` of equal-RMSE MC work. Observed RQMC is both more accurate and only `0.212` of equal-RMSE MC work; MLAE is `1.709` times its work. Figure 3 therefore treats the crude-MC crossover as a conditional future regime, not a wall-time advantage.

A dense 11-dimensional, eight-bit table would require 88 address qubits and `2.306e18` GiB. In a five-qubit finite-table control, marking seven failures instead of 25 successes reduces one oracle from 900 to 252 CX, or from 1,839 to 507 ECR. The fixed MLAE schedule expands to about 432,000 CX or 883,600 ECR; a submission-free `ibm_marrakesh` preflight gives about 778,800 CZ, with median `m=8` depth 11,437 and 4,157 CZ.

The structured recovery-plane oracle uses nine seven-bit coordinates, signed weighted addition, comparison, phase marking, and uncomputation. Its event disagreement is `0.002045`, below MLAE RMSE `0.002892`. One call requires 99 logical qubits, depth 59,012, and 35,160 CX under all-to-all connectivity. The frozen 1,500-call schedule therefore costs at least 52.74 million CX before correlated loading, routing, and error correction, invalidating the favorable arithmetic proxy as an end-to-end speedup estimate.

Exact dense loading confirms the bottleneck. At one bit per active coordinate, the nine-qubit loader uses 502 CX with disagreement `0.154617`. At two bits, the 18-qubit loader uses 262,125 CX with disagreement `0.098045`. Matching the seven-bit oracle tier requires 63 loader qubits and `2^63` amplitudes; a float64 table alone is 64 EiB. Structured reversible Gaussian-copula and empirical-quantile generation is therefore an unresolved prerequisite rather than a claimed lower bound.

### 4.3 Hardware boundary

The Open-plan hardware experiment ran on the 156-qubit `ibm_marrakesh` processor on 9 October 2026 (job `db42v34lf4us73c24q50`). The three circuits used Grover powers `m=[0,1,2]` with 4,096 shots each. Their transpiled depths were 4, 73, and 141, with 0, 19, and 39 two-qubit gates, respectively. The measured good-state frequencies were 0.624756, 0.406006, and 0.854004, compared with ideal amplified probabilities 0.625000, 0.156250, and 0.976563. The resulting unmitigated MLAE estimate was 0.566940, giving an absolute error of 0.058060 relative to `p=0.625`. The ideal-model likelihood interval `[0.564320,0.569545]` excludes the exact value and is therefore evidence of hardware-model misspecification rather than a valid uncertainty interval for the noisy estimate. The job consumed 5 s of charged QPU time (0.0829 resource units). The shallow `m=0` circuit retained the original event probability, whereas the amplified circuits accumulated sufficient coherent and stochastic error to bias the joint likelihood fit. Raw bitstring counts, physical layouts, calibration time, and runtime metrics are archived with the result package.

Figure 5 compares the ideal and observed amplified probabilities and the corresponding ideal-likelihood profiles. The separation between the exact probability and the hardware likelihood maximum is presented as bias evidence, not as a calibrated confidence interval.

### 4.4 Process-model discrepancy

For the recycle-`0.427` surrogate, leave-one-out residual vectors from the 32 physical PSA rows are jointly resampled onto a fixed 4,096-state copula sample. Across 512 replications, the base event probability is `0.471680`, the stressed mean is `0.472226`, and the central 95% range is `[0.468262,0.476074]`. Its `0.003906` half-width is 3.91 times the ideal-QAE target `epsilon=0.001` and exceeds noiseless MLAE RMSE. This is a scale diagnostic, not a calibrated discrepancy posterior.

A paired reduced-versus-spatial/tank diagnostic gives maximum probability differences of `0.7500`, `0.5625`, and `0.5000` at 8, 16, and 32 states. The last is 500 times the `0.001` target. Because the spatial/tank arm fails its strict maximum-CSS diagnostic, this is evidence of model-form scale rather than validation and prioritizes calibration over finer amplitude estimation.

### 4.5 Independent public-model policy control

The released dynamic two-bed CO2/N2 PSA model (Mendeley DOI `10.17632/564nt6pcgb.1`, code release `v1.4.0`) provides an independent chemistry-analog control. Its light-product purge-to-feed conductance ratio is the closest available analog of the local product-gas recycle fraction. The exact candidate values `0.420/0.427/0.430` are evaluated directly to cyclic steady state in four public-model parameter scenarios. All four scenarios show lower N2 purity at `0.430` than at `0.420`; three of four show lower CO2 recovery. Only two scenarios are strictly monotone in recovery across all three closely spaced policies. The source-defined event probability over the four deterministic scenarios is `0.50` for every policy, so the external largest-feasible rule returns `0.430` and does not reproduce the local `0.420` selection.

The policy signals are below the external solver's metric-resolution scale. At 4,800 output points per phase, the baseline recovery change from `0.420` to `0.430` is `−0.000828` percentage point, only `1.72%` of the recovery shift induced by refining the flux quadrature from 1,200 to 4,800 points. In the low-kinetics scenario the refined recovery change is `+0.000170` percentage point, only `0.33%` of the quadrature shift. The endpoint signs are reproducible under refinement, but their magnitude is insufficient for independent chance-selection validation. This control supports the purity direction and exposes recovery-direction/model-resolution uncertainty; it is not H2 calibration or industrial validation.

Figure 6 places these two validity limits on one page. Panels (a) and (b) compare estimator precision with residual-stress model-form scale; panels (c) and (d) show that the external purity direction is repeatable while the recovery-policy signal is only 1.72% or 0.33% of the corresponding quadrature-refinement shift.

### 4.6 Independent same-chemistry H2 mechanism control

Thelen VA-10 supplies an independent one-factor H2 control [@thelen2023h2psa]. Raising equalization pressure from 4.50 to 4.75 bara changes purity from 99.95% to 99.93% and recovery from 81.45% to 79.15% by direct meter or 80.78% to 79.47% by pulse transmitter. The common negative direction supports the mechanism, but both points fail the frozen 99.98% purity threshold and the source reports recovery sensitivity of roughly one percentage point to a 1% feed-flow deviation. It therefore does not validate the recycle policy or joint event.

The 13-run Voigt H2/CH4 table provides a second resolution test. Its group-held-out recovery RMSE is 5.854 percentage points and its purge/feed coefficient is -77.97 percentage points per unit. Applying only the frozen candidate spacings gives implied recovery effects of 0.546, 0.780, and 0.234 percentage point. The widest effect is only `0.1332` of held-out RMSE and would require a `37.5×` RMSE reduction to satisfy the five-times resolution gate. Continuous purity is not identifiable, and purge/feed ratio is not product recycle. The public H2 table therefore cannot resolve or validate the frozen selection.

A strict availability audit covers ten public experimental, industrial, simulation, and historian sources. None supplies H2 chemistry, a downloadable synchronized valve/pressure/feed-flow/product-flow/product-composition record, the frozen product-recycle coordinate, and the frozen joint event together. The closest H2 experiment is Thelen VA-10, whereas the only fully downloadable synchronized historian is the cross-chemistry Otway data. The Schell H2/CO2 laboratory study provides cyclic pressure, flow, and mass-spectrometer evidence but not a joined raw archive or the same control [@schell2013precombustion]. This `0/10` result fixes the external claim boundary rather than treating heterogeneous sources as plant replicates.

### 4.7 Corrected independent pyAPEP topology-feasibility control

The initial wrapper placed product-gas pressurisation at the feed end and omitted high-purity makeup from the recovery denominator. Its 12-run CSS/mesh values are superseded. The corrected wrapper places both product-gas steps at the light-product end, counts all external H2 inputs, and requires product-tank self-sufficiency.

The corrected 15-cycle screen is pre-CSS: purity is `0.793870`, recovery falls from `0.047980` to `0.047192`, and tank supply is `0.03463–0.03545`. The 450-cycle `0.420` control reaches purity `0.991666`, recovery `0.044166`, tank fraction `0.03164`, and CSS residual `1.2538e-3`, failing all four gates. It is a topology stress test rather than a CSS-converged same-policy control.

#### Public toPSAil/Yang same-chemistry model and experiment anchor

The original Yang H2/CO experiment used a two-bed six-step zeolite-5A cycle at approximately 0.101--1.115 MPa (1--11 atm as reported) with a 70/30 feed and produced 99.99% H2 at 75.87% recovery [@yang1997twobedh2]. Relative to the frozen event, the purity is 0.01 percentage point above the 99.98% threshold and the recovery is 3.03 percentage points below the 78.9% threshold, so its joint-event label is false. This gives a high-purity H2 experimental boundary without retuning the event.

The archived toPSAil workbooks cover isothermal/nonisothermal and no-pressure-drop/Ergun variants. Reported CSS requires 13, 42, 36, and 31 cycles, respectively [@kim2023topsail]. These cases support public model tractability, CSS behavior, and valve/pressure/recovery calibration but do not reproduce the frozen `0.420/0.427/0.430` product split: Yang varies purge/feed and step times, and numerical results are absent from the archive. The same-policy gate remains open.

### 4.8 Calibrated one-cycle bridge

Nested leave-one-run-out predictions are accurate for the reduced-model phase ledger. Across the eight named bed phases, median one-step state relative L1 error ranges from 0.00001 to 0.00051; phasewise p95 values range from 0.00001 to 0.00222. Median phase-end pressure error ranges from 0.00006 to 0.00217 bar, and the largest phasewise p95 pressure error is 0.00762 bar. For phases with nonzero product or exhaust, median outlet-H2 absolute error is at most 0.00017.

When the held-out maps are composed through one synchronized cycle, median joint-state relative L1 error is 0.00149, p95 is 0.00317, and the maximum over 20 held-out runs is 0.00319. The median error is 0.0038 times the initial-state persistence baseline. Median final pressure errors are 0.00734 bar for bed A and 0.00741 bar for bed B; p95 errors are 0.01668 and 0.01687 bar. Equalization direction is correct for all 40 calls and no negative predicted state value requires clipping.

This establishes a held-out one-cycle affine bridge, not a reversible cyclic PSA oracle: equalization remains classical, repeated CSS is absent, and the event is not evaluated from the bridge. The fixed-point study covers only the variable affine-map layer.

### 4.9 Fixed-point and primitive-gate boundary for the phase maps

The joint precision screen assigns 10% of the nested-holdout p95 error to fixed-point arithmetic. The resulting budgets are 1.2478e-4 for state relative L1 and 3.0438e-5 for outlet-H2 absolute error. A 14-bit output accumulator never satisfies both budgets over the tested input range because output-weight rounding creates an error floor. The minimum sequential-register proxy among the screened feasible pairs is 11 bits per active input and a 16-bit scalar accumulator. At this point the measured p95 quantization errors are 9.9978e-5 for state and 2.2017e-5 for outlet H2. With as many as 14 active inputs, the input and scalar-sum registers alone imply a 170-qubit proxy before adder workspace.

All 72 scalar variable weighted sums in the eight-phase schedule were then transpiled. Reusing the scalar workspace, the largest block requires 186 logical qubits. Serial execution of the 72 forward blocks has depth 8,257,830 and 4,183,986 CX gates. A clean compute-uncompute bound doubles the two-qubit count to 8,367,972 CX gates. These are direct primitive-gate counts for the fitted affine variable terms, not an estimate of a complete PSA oracle. Constant injection, state update, equalization, repeated CSS, chance-event comparison, correlated loading, and device routing can only increase the total.

A 15-qubit structural control has depth 405 and 304 CX. All 64 labels match the integer map, coherent amplitude error is at most `2.78e-16`, and nine work/event qubits clear. This three-bit control does not calibrate equalization, CSS, or the H2 event.

Figure 4 assembles the measured resource ladder: the resolution that fixes the response-event oracle, the low-bit dense-loader boundary, the joint input/output precision screen for the calibrated phase maps, and the compiled CX cost of their affine variable terms. Table 3 condenses eight decision-relevant resource tiers while preserving separate per-call, schedule-level, simulated, preflight, and real-QPU columns. The complete 30-tier ladder is Supplementary Table S1, preventing resources from different tiers from being added as if they described one completed circuit.

### 4.10 Primary phase-stream event connection

The replayed primary ledger reconstructs every source-CSV output from final-cycle process streams. All 32 runs pass the original CSS gate; maximum replay errors are `2.89e-15` for purity and `1.33e-10` for recovery, and the 25/32 joint-event count is preserved. Each run contributes eight phase records, two equalizations, four tank withdrawals, and two product/recycle splits. This closes the previously missing observability link between the primary process model and its chance event.

Nested held-out phase-stream maps reproduce all 32 event labels with no false positives or negatives. Purity MAE is `3.79e-8` and recovery MAE is `7.27e-5`; the largest absolute errors are `1.46e-7` and `1.82e-4`, respectively. The minimum fixed-point pair within both 10%-of-holdout budgets uses 12 input bits and a 16-bit scalar accumulator and retains 32/32 labels. Compiling the 12 event-active adsorption-stream blocks gives a maximum of 272 logical qubits with scalar-workspace reuse, `1,101,233` forward CX, and `2,202,466` clean compute-uncompute CX. These counts remain conditional on the observed held phase-start states. Their separate-scalar form does not include stream accumulation, recycle scaling, free-running equalization/CSS, state loading, or routing.

The modular final event-arithmetic screen uses separate fixed-point scales for aggregate feed H2, external-product H2, and external impurity. Sixteen bits per register are the first tested precision satisfying both 10%-of-holdout error budgets and all 32 labels; p95 purity and recovery quantization errors are `1.64e-9` and `9.88e-6`. Eight coefficient bits preserve both comparator flags on every row. The clean compute–phase–uncompute circuit requires 125 logical qubits, depth `355,454`, and `182,981` CX in an all-to-all u/CX basis.

The integrated policy-specific construction closes the preceding arithmetic connection. With 12 bits on each of 29 unique phase-state/parameter inputs, 19 aggregate bits are the first precision satisfying both budgets over the 96 candidate-policy state points. The p95 purity and recovery quantization errors are `1.13e-8` and `1.11e-5`; quantized and integer comparisons retain 96/96 float-map labels with zero clipping. Rebuilding the coefficients at each of the original 32 recycle values also retains 32/32 ledger labels. Thirteen coefficient bits satisfy the normalized-margin gate for each frozen candidate. The three clean policy oracles require 510 logical qubits and `1,282,525–1,286,021` CX; the maximum depth is `2,481,760`. Thus aggregation, fixed-policy recycle scaling, joint phase marking, and exact uncomputation are compiled in one circuit. The supplied phase-start states are still observed/calibrated inputs rather than outputs of stable physical/reversible CSS, and loading and routing remain excluded.

Composing the eight phase and two equalization maps from only the held final-cycle start retains 32/32 labels, with purity/recovery MAE `8.61e-8/6.43e-5` and p95 cycle-closure L1 `1.09e-4`. Removing held dynamic states entirely, the parameter-only CSS initializer plus one-cycle composition also retains 32/32 labels; purity/recovery MAE is `3.64e-7/3.22e-4`, initializer p95 state L1 is `7.01e-4`, and predicted-cycle closure p95 is `1.39e-5`, with no clipping. The accuracy-feasible 9-bit-input/14-bit-output initializer compiles as 20 scalar blocks requiring at most 118 logical qubits, `578,702` forward CX, and `1,157,404` clean CX before reversible state update.

Repeated composition supplies a necessary negative control. Starting from the observed final-cycle state, 50-cycle terminal labels fall to 21/32 and only 1/32 runs passes the tail aggregate CSS gate. Starting from the parameter-only initializer improves terminal labels to 28/32, but only 2/32 runs passes the gate; p95 terminal residual is `4.14e-2`, and clipping/extrapolation appears. Thus the initializer is a validated local surrogate route to the one-cycle event, not an iterative physical or reversible CSS solver.

The exact outer-held cycle Jacobians explain this failure: raw spectral radii span `1.040–1.254`, all above unity. The label-free spectral rule requires anchor weights `0.135–0.282` to reach radius 0.9. Fifty stabilized cycles then retain 32/32 terminal labels and pass the aggregate CSS gate in 32/32 runs; p95 terminal residual is `6.24e-8`, p95 drift from the predicted initializer is `1.10e-4`, and no clipping occurs. This is a mathematical stability control for the aggregate surrogate. Because the anchor explicitly pulls every cycle toward a learned initializer rather than deriving the correction from conservation-law tank and spatial dynamics, it does not establish physical or reversible CSS.

#### Physical tank/spatial CSS horizon and register accounting

All 32 physical rows pass strict and L1 CSS at cycle 100. The latest tail-stable strict-CSS cycle is 68 and the latest event-label cycle is 33. Sixteen bits per scalar are the first precision satisfying the `1e-5` p95 state-error budget while retaining all 32 final CSS decisions and event labels; quantization raises the conservative horizon to 85 cycles.

At 16 bits, one physical state occupies 1,360 data qubits. Separate current/next states use 2,720; retaining ten raw feed/product scalars gives 2,880. These architecture-specific counts exclude nonlinear transport, workspace, loading, routing, and fault tolerance. A clean fixed-horizon oracle would call a future reversible cycle map 85 times forward and 85 times in reverse. The physical horizon is therefore quantified, while nonlinear reversible transport remains open.

#### Competitive-Langmuir reciprocal/LDF microstep boundary

Across 25,856 cell states spanning `0.0513–15.65 bar`, separately compiled H2, CO2, CH4, CO, and N2 circuits pass their precision, overflow, and erasure gates. The CO2 selection uses a five-bit denominator address and 24-bit arithmetic, giving p95 `q*` and LDF-next relative errors of `0.0409` and `7.26e-4`; its circuit uses 515 qubits and 1,225,138 CX. Component circuits use 490–515 logical qubits and 1,118,920–1,965,308 CX. Retaining all current/next loadings with sequential workspace reuse gives 675 qubits and 6,547,362 additive CX. This closes modular one-cell, one-second equilibrium/loading updates, while transport, pressure, composition, routing, and repeated integration remain open.

#### Product-boundary valve/flux and recycle-tank accounting

The 6,464-state valve screen is half active over `0.0513–15.65 bar` at `14.85 bar` back pressure. A 12-bit address and 20-bit flux registers give zero mismatch/erasure, active-flow p95 error `0.00316`, and maximum normalized component error `0.00215`; the circuit uses 288 qubits and 800,762 CX. Separate 24-bit tank accounting gives error `5.25e-7`, exact labels, 97.40 mol minimum headroom, 677 qubits, and 1,043,990 additive CX.

Direct composition propagates those flux registers through 32,320 product-cell balances. Sixteen-bit nonvalve inputs and 20-bit outputs pass all gates; p95 scaled error is `8.37e-6–6.53e-5`. The clean circuit retains 528 input/output qubits, clears 314 work qubits, and uses 842 logical qubits, depth 3,285,605, and 2,348,388 CX.

The product-cell follow-on removes the supplied adsorption/desorption inputs. For each component, the same 20-bit pressure and composition registers drive a run-specialized LDF path and, through their high 18 bits, the valve. The generated loading transfer and valve flux enter one boundary balance before exact reversal. Across 6,464 states and 32,320 balances, component p95 next-gas errors are `3.38e-5–2.13e-4` and maxima are `2.31e-4–4.76e-4`, with no transfer erasure, underflow, or overflow. The H2/CO2/CH4/CO/N2 paths use 1,072–1,195 qubits, depths 15,670,199–45,153,788, and 10,060,060–26,810,396 CX. Their conservative repeated-common-path upper bound is 1,195 peak qubits, depth 144,913,247, and 88,388,552 CX. CO2 requires a 10-bit LDF coefficient.

The product-cell construction removes supplied composition and inward-face inputs. Two five-component gas inventories generate normalized compositions, pressures, one inward face, factor-specialized LDF and valve transfers, and one conservative balance with exact reversal. The five paths use 1,803–1,952 qubits and 20,253,112–37,020,740 CX; all precision and cleanliness gates pass. Monolithic five-component transpilation, adaptive integration, and a complete phase remain open.

#### Coherent run, valve-schedule, and tank-withdrawal interface

The five-qubit run QROM reproduces 352 parameter values with 12-bit p95/maximum normalized errors `1.13e-4/1.22e-4` at 140 qubits and 49,176 CX. The decoder verifies all eight stage addresses, including six valid paired-bed valve states, at 27 qubits and 492 CX. The 18-bit tank block verifies 640 records with p95/maximum normalized errors `1.36e-6/1.87e-6` and no erasure, underflow, or next-state mismatch at 282 qubits and 116,521 CX.

The combined run/schedule/tank interface retains its outputs, clears the withdrawal workspace, and uses 440 logical qubits, depth 324,495, and 166,189 CX. A second circuit consumes the loaded capacity, affinity, and LDF-factor words in reversible multiplication, generating five equilibrium prefactors, five LDF-alpha coefficients, and two schedule-derived adsorption flags. Across 320 coefficient and 16 flag checks, equilibrium and LDF maximum relative errors are `4.99e-5` and `4.36e-5`. It uses 495 logical qubits, depth 526,434, and 353,441 CX, with no measurement or reset.

An intermediate audit supplies the 20-bit Langmuir response to isolate coefficient consumption. Across 64,640 balances, maximum q*, LDF-next, and next-gas errors are `4.32e-5`, `3.17e-5`, and `4.00e-4`, with no erased transfer. Its five paths use 1,297–1,486 qubits and 1,855,912–2,807,252 CX.

A clean follow-on consumes the retained 12-bit run-affinity word, 20-bit pressure, and five 20-bit compositions. It constructs the Langmuir denominator, a 4,096-segment reciprocal, numerator, and response before direct coefficient/q*/LDF/loading/balance consumption and exact uncomputation. Denominator p95/max errors are `1.96e-4/3.53e-4`; maximum response, q*, LDF-next, and next-gas errors are `2.92e-4`, `2.85e-4`, `1.97e-4`, and `4.00e-4`. The five paths use 1,771–1,960 qubits and 41,440,216–42,391,556 CX at depth 67,700,348. Their repeated-controller upper bound is 1,960 peak qubits, depth 338,501,740, and 209,832,572 additive CX. Pressure, composition, and face words remain supplied at this intermediate tier.

The highest component tier removes those supplied words. Three five-component gas inventories generate two normalized compositions, three pressures, and two oriented faces; the centre state then feeds coherent control, dynamic Langmuir response, q*/LDF update, loading conversion, and conservative balance before exact reversal. All five paths pass 25,856 normalization states and 64,640 component records with maximum next-gas error `4.00e-4`. They use 2,696–2,885 qubits, depth 89,147,751, and 55,337,688–56,289,028 CX; the repeated-path upper bound is 2,885 peak qubits, additive depth 445,738,755, and 279,319,932 additive CX.

The tank follow-on removes the recorded-withdrawal QROM. A 557-qubit circuit retains all 128 frozen saturation labels, and a 647-qubit extension preserves 128 observed saturated plus 224 arithmetic-counterfactual unsaturated labels (`1.687e-4/3.872e-4` p95/maximum component-scale error). A separate 500-cycle source-model control keeps the sample-0 recycle fraction but shortens non-adsorption from 10 to 0.02 s. It reaches CSS `9.949e-7`; exact replay gives 128/128 unsaturated, zero-makeup calls. Start/end-pressure trapezoidal demand reduces p95 relative error from 9.72% to 0.853%. The clean circuit uses 845 qubits, depth 1,634,701, and 1,078,054 CX, with withdrawal/next-tank error `8.320e-6/9.241e-6`. This short-schedule control does not validate the frozen schedule or a plant. Frozen-schedule unsaturated coverage and monolithic phase integration remain open.

#### Pressure reconstruction and oriented internal-face transport

The 18-bit-inventory/20-bit-pressure circuit gives p95/maximum normalized errors `3.01e-6/5.41e-6`, no erasure or overflow, and uses 152 qubits, depth 158,331, and 93,764 CX.

The face circuit uses 20-bit pressures, 24 effective flow bits in a 28-bit register, and 20-bit supplied compositions. The 19,200 positive and 192 zero faces have no underflow, mismatch, or erasure; flow p95 relative error is `0.00354` and maximum normalized flux error is `4.86e-5`. One face uses 404 qubits and 1,340,390 CX; modular two-pressure/one-face accounting is 584 qubits and 1,527,918 additive CX.

The supplied-composition baseline computes three pressures and both faces, consumes their ten temporary component-flux registers in five centre-cell balances, copies the outputs, and reverses all transport work. Across 12,928 states/64,640 balances, 16-bit nonface inputs, 28-bit fluxes, and 20-bit outputs pass every gate; propagated p95 errors are `8.48e-6–1.20e-4`. The clean circuit uses 1,508 qubits, depth 12,250,291, and 8,328,622 CX.

The normalized direct tier removes both independent five-component composition inputs. Its 22-bit common amounts, 22-bit reciprocal, and 8-bit address are the first screened combination that passes the composition, propagated face, and five balance gates together. Across 25,856 normalization states, maximum component p95/maximum absolute composition errors are `2.071e-4/3.105e-4`; mole-fraction-sum p95/maximum errors are `2.098e-4/3.338e-4`, with zero erasure and overflow. The propagated face-flux p95 error is at most `1.766e-4` of the flow scale. All five 16-bit-nonface/28-bit-flux/20-bit-output balances pass; component p95 next-inventory errors range from `1.145e-5` to `1.622e-4`. The standalone clean normalizer uses 333 qubits, depth 2,153,892, and 1,340,232 CX. Two normalizers composed with the three pressures, two faces, and five balances use 1,651 qubits, depth 22,143,683, and 14,667,150 CX; 610 input/output qubits are retained and 1,041 work qubits are cleared. The additional 6.339 million CX relative to the supplied-composition baseline quantifies the normalization interface cost. The reciprocal table is calibrated to the frozen support. The joint LDF coupling is assessed below; withdrawal, integration, routing, and a full cycle remain open.

#### Conservative interior-cell gas balance

All 64,640 exact next-gas balances are positive. Supplied-sign accumulators require 198–209 qubits and 68,676–80,800 CX; five-component accounting is 609 qubits and 366,802 additive CX. Direct loading-sign extraction requires H2/CO2/CH4/CO/N2 widths 26/26/32/32/30 rather than 20/24/20/20/20. Sign/solid-conversion/balance needs 383–431 qubits and 139,600–343,680 CX per component, or 934 qubits/1,411,882 additive CX. A 64-pair control has zero branch, magnitude, or workspace mismatch. Recompiled widened LDF-to-sign-to-balance circuits use 861–929 qubits, depth 4,949,239–7,871,973, and 3,412,254–4,991,534 CX; sequential accounting is 1,317 qubits/19,082,852 additive CX.

#### Joint normalized transport, LDF uptake, and cell balance

The joint audit uses the same three encoded gas inventories for normalization, pressure reconstruction, both internal faces, and the centre-cell current-gas term. The full 20-bit centre pressure and composition outputs drive factor-quantized, run-specialized competitive-Langmuir/LDF paths; the generated loading change is sign split, converted by the solid mass, and consumed with the two generated face transfers in one conservative balance before exact reversal. Across 12,928 interior states and 64,640 component balances, the selected H2/CO2/CH4/CO/N2 loading widths are 26/26/38/36/36 bits, reciprocal address widths are 11/9/10/8/8 bits, and factor widths are 9/8/9/7/6 bits. Component p95 next-gas errors are `7.35e-5–1.87e-4`; maxima are `3.46e-4–4.85e-4`, with zero transfer erasure, underflow, and overflow.

Five directly connected one-component paths were transpiled separately at optimization level 1 and fixed seed. They use 1,944–2,039 logical qubits, depths 32,612,294–59,186,552, and 20,670,468–35,947,274 CX. Their common-path-repeating upper bound is 2,039 peak qubits, depth 206,113,724, and 128,013,726 CX. The coherent controller now generates the run-dependent equilibrium/LDF coefficients, but those registers are not yet consumed by these paths. Monolithic five-component compilation, adaptive integration, routing, and a full cycle remain open.

## 5. Discussion

The workflow identifies the applicable computational regime. Finite tables favor enumeration; the smooth surrogate favors Sobol-QMC; estimator precision below model-form error has no decision value. Constraint activity should therefore be screened before compilation. The response, loader, phase-map, kinetic, pressure/transport, and product-boundary results show that logical query counts conceal large fixed-point and two-qubit-gate costs. Public-model controls also show that a policy signal can fall below numerical refinement or fail topology and material-boundary gates. QAE remains prospective when an expensive validated oracle is reused across many risk queries and structured loading plus synthesis preserve its query margin.

The real-QPU tier tests executable compilation and noise sensitivity. Its eight-state discretization is intentionally too small to establish computational advantage. Its value is to connect the process event, reversible logic, transpiled circuit, and observed hardware statistics without replacing the larger end-to-end resource analysis. The observed divergence between the nearly unbiased `m=0` frequency and the biased amplified likelihood also shows why deeper amplitude-amplification circuits require an explicit noise model or mitigation strategy; increasing the query power alone does not improve the engineering probability estimate on the tested hardware.

### 5.1 Limitations

The primary probability model is conditional on 32 CSS-converged spatial/tank runs. The affine response surface cannot represent arbitrary nonlinear adsorption or valve interactions, and the empirical copula is weakly identified in 11 dimensions. Its diagonal shrinkage is chosen for numerical stability rather than inferred from a hierarchical uncertainty model. The high-N Sobol reference reduces integration error for this fitted model; it does not reduce uncertainty in the fitted model itself.

The frozen primary event also has an inactive purity constraint over the bounded surrogate support. Retaining the event preserves the preregistered comparison, and the threshold grid demonstrates that a joint-active region exists, but the main estimator result is driven by recovery. A future process data set should place both product constraints near the operating frontier before the quantum algorithm is designed. Otherwise extra reversible comparators add circuit cost without changing the decision.

The process representations answer different validation questions; the structured public-data audit finds `0/10` sources satisfying the synchronized same-policy H2 gate. The Thelen pair supports the equalization/recovery direction but not the recycle event. The CO2/N2 policy signal is below its quadrature shift. In the corrected pyAPEP wrapper, the short screen is pre-CSS and the 450-cycle control still fails CSS, purity, recovery, and product-tank self-sufficiency; the superseded feed-end/adsorption-feed-only calculation is excluded from evidence. The toPSAil/Yang anchor reaches high H2 purity, while its purge/feed control differs from product recycle and 75.87% recovery fails the event. The manuscript therefore supports a transferable workflow and conditional PSA case, not industrial validation.

Resource tiers remain separate. The 85-cycle/2,880-qubit point is register accounting, and repeated common work remains explicit in additive bounds. The 440/495-qubit tiers cover finite control and coefficient generation. The 647-qubit tank circuit tests bounded counterfactuals; the 845-qubit tier tests one short-schedule physical trajectory. Frozen-schedule unsaturated coverage, adaptive integration, routing, and full phases remain open.

The completed QPU evidence is one job on one backend. The ideal-model likelihood interval excludes the exact probability because hardware bias is not represented in the likelihood. This interval cannot be interpreted as a calibrated confidence interval for the noisy device. Multi-backend repeated execution, execution-time calibration records, readout mitigation, and a run-level overdispersion or bootstrap analysis remain necessary for a hardware-general statement.

### 5.2 Implications for process-systems computation

The results suggest a screening order for quantum probability estimation in process engineering. First, verify that the engineering event is decision active and that process-model discrepancy is smaller than the desired estimator error. Second, compare MC with randomized QMC and a problem-appropriate importance sampler on exactly the same prior. Third, identify whether the process model is sufficiently expensive and reused often enough to amortize reversible implementation. Fourth, compile the event arithmetic and state loader at the resolution required by the decision. Hardware execution should follow these checks, because a small executable kernel alone does not establish relevance to the full process problem.

This order changes where effort should be spent. The nearest failed policy is 11.91 RQMC RMSE from feasibility, so lower MLAE error does not change the frozen decision. The conditional p=0.50 crossing is recycle `0.42659`, but even the full observed support `0.3508–0.4481` produces only `1.296` times the independent H2 recovery RMSE. A five-times confirmatory gate would require recovery group-CV RMSE at most `1.517` percentage points across that full span, or `0.156` percentage point for the current 0.010 span. Better same-control H2 calibration therefore precedes finer probability estimation; a structured loader and calibrated reversible equalization/CSS/event logic remain the subsequent quantum requirements.

The negative estimator ranking is useful. RQMC wins because the fitted event is a smooth, moderate-dimensional transformation with a cheap surrogate. This identifies the type of problem that should not be moved to QAE. A more plausible quantum regime would combine an expensive process oracle, continuous correlated uncertainty, many repeated probability or tail-risk queries, and limited QMC smoothness. Rare events may increase the relative value of amplitude methods, but only if importance sampling or subset simulation does not exploit the same structure more cheaply.

### 5.3 Claim boundary for CCE

The CCE contribution is a process-linked resource audit and decision framework. The paper can support three claims: MLAE improves over matched crude MC in the frozen conditional experiment; RQMC remains more accurate and cheaper for the current surrogate; and state preparation, reversible response evaluation, and hardware noise remove any present end-to-end advantage. It can also support a bounded novelty statement that no direct cyclic PSA plus QAE case was identified in the scoped literature search.

The paper cannot support industrial performance, a global recycle optimum, or realized speedup. The process ledgers, raw-gas-inventory state updates, pressure-derived tank-allocation arithmetic, and one model-derived short-schedule unsaturated trajectory narrow the process-to-oracle gap. Frozen-schedule unsaturated coverage, adaptive integration, routing, and a monolithic phase/cycle remain open. Stronger claims require a calibrated same-policy H2 event result, complete cycle logic, a scalable correlated loader, and repeated noise-aware hardware results.

## 6. Conclusions

QAE improves on crude MC but not Sobol-QMC. Physical runs settle by cycle 68, and 16-bit quantization gives an 85-cycle, 2,880-qubit register point. Raw-inventory component paths require 2,696–2,885 qubits and 55.34–56.29 million CX. An 845-qubit tank circuit preserves 128 physically generated unsaturated calls in a short-schedule control, while the 510-qubit policy oracle retains every frozen label. Monolithic phase integration, frozen-schedule unsaturated coverage, structured loading, H2 validation, and repeated hardware evidence remain open.

## Data and code availability

The frozen primary protocol, complete estimator records, process tables, compiled-circuit resource reports, raw QPU counts, retrieval metadata, figures, and SHA-256 manifests are stored in the project reproducibility package. The IBM API credential is excluded. Local runners regenerate the matched primary experiment and gate-compilation package without QPU submission. The submission archive should preserve the recorded software environments, random seeds, source-data provenance, and machine-readable claim audit under a permanent repository DOI.

## Supporting information

Supporting information contains estimator records; threshold activity; oracle truth tables; response and phase-map screens; the primary ledger; the physical CSS/register audit; five component-specific LDF records; pressure/internal-face transport, direct pressure/two-face/balance, loading-sign, direct LDF/sign/balance, normalized-transport/LDF/component-balance, and interior-cell balance records; product-boundary and direct valve/boundary-balance records; event bridges; repeated-cycle screens; compiled initializer, stream, event, and policy records; loader controls; IBM metadata; external controls; and integrity manifests. Evidence tiers remain separate.

## Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

During the preparation of this work, the authors used OpenAI Codex to assist with code drafting and refactoring, local workflow orchestration, figure and table generation, manuscript organization, and language editing. After using this service, the authors reviewed and edited the code and text, reran the documented analyses, verified the cited sources and numerical claims, and take full responsibility for the content of the publication.


