# Cover letter draft — Computers & Chemical Engineering

[Date]

Dear Editor,

Please consider our manuscript, “Resource-aware quantum amplitude estimation for chance-constrained pressure swing adsorption: classical baselines, compiled oracle costs, and a hardware boundary,” for publication as a research article in *Computers & Chemical Engineering*.

The manuscript asks a process-systems question that asymptotic quantum-computing analyses usually leave unresolved: does amplitude estimation improve an actual PSA chance-constrained policy decision after strong classical estimators, state preparation, reversible process evaluation, and hardware error are counted on the same basis? We freeze three product-recycle policies and one joint hydrogen purity/recovery event, then compare Monte Carlo, scrambled Sobol randomized quasi-Monte Carlo, defensive-mixture importance sampling, and noiseless maximum-likelihood amplitude estimation over 200 matched replications.

The result is deliberately resource-aware. Scrambled Sobol RQMC attains RMSE 0.002482, below noiseless MLAE at 0.002892. A compiled response-event oracle requires 99 logical qubits and 35,160 CX per call. A parameter-only initializer and one-cycle composition recover 32/32 event labels without held dynamic states; its 20 affine blocks reach 118 logical qubits and 578,702 forward CX. A policy-specific stream-to-event oracle retains 96/96 candidate-policy and 32/32 ledger-support labels at up to 510 logical qubits and 1,286,021 CX. Raw aggregate 50-cycle repetition passes CSS in only 2/32 runs, whereas all 32 source tank/spatial models settle with a latest joint horizon of 68 cycles. A 16-bit audit gives an 85-cycle target and 2,880-qubit clean out-of-place state/stream accounting point before nonlinear transport workspace. Five controller-coupled paths now generate normalized compositions, three pressures, two faces, the run-affinity Langmuir denominator/reciprocal, and q*/LDF/loading/balance updates directly from raw three-cell inventories. They compile to 2,696–2,885 qubits and 55,337,688–56,289,028 CX each. A 557-qubit pressure-derived circuit removes the withdrawal lookup on all 128 frozen saturated tank calls. A 647-qubit extension selects that branch or proportional allocation and preserves 128 observed saturated plus 224 bounded-counterfactual unsaturated labels; the added cases test arithmetic rather than physical trajectories. A completed three-qubit IBM experiment measures 0.56694 for exact 0.625 and serves as a hardware-noise boundary.

The paper's contribution is the separation of estimator error, decision value, process-model validity, state-loading cost, reversible-oracle cost, and QPU behavior within one chemical-engineering workflow. Independent H2 literature data and two public simulator paths do not validate the selected policy; we report these results as negative or directional controls and quantify the accuracy required of a future same-control H2 campaign. This boundary is central to the manuscript: we do not claim quantum advantage, industrial H2 validation, or deployment readiness.

We believe the paper fits the journal because it connects uncertainty-aware process optimization, cyclic adsorption modeling, numerical benchmarking, and emerging computational hardware through a reproducible decision framework. The submission includes the main manuscript, supporting information, code and data manifests, highlights, and a graphical abstract.

[Confirm before submission: This manuscript is original, is not under consideration elsewhere, and all authors approve its submission.]

[Confirm before submission: conflict-of-interest statement.]

[Confirm before submission: funding statement. The manuscript already contains the Elsevier-format generative-AI declaration; all authors must approve it with the final text.]

Sincerely,

Ugwiyeon Lee
Korea Gas Safety Corporation
1390 Wonjung-ro, Maengdong-myeon, Eumseong-gun, Chungcheongbuk-do 27738, Republic of Korea
lyullee@kgs.or.kr
[Telephone, if required]
