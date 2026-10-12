"""Build the pressure-consistent SPT manuscript from the corrected evidence chain."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
PROJECT = ROOT.parents[1]

spec = importlib.util.spec_from_file_location("legacy_spt_builder", ROOT / "build_spt_full_manuscript.py")
legacy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(legacy)

EVIDENCE = RESULTS / "final_objective_evidence_v45" / "PSA_FINAL_OBJECTIVE_EVIDENCE_V45.json"
OUT = RESULTS / "spt_pressure_consistent_manuscript_v3"
MD_OUT = OUT / "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.md"
DOCX_OUT = OUT / "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.docx"
MANIFEST_OUT = OUT / "MANIFEST_SHA256.json"
REFERENCE_AUDIT_OUT = OUT / "REFERENCE_METADATA_AUDIT.json"

CUBE_JSON = RESULTS / "hydraulically_feasible_full_6cell_cube_v1" / "PSA_HYDRAULICALLY_FEASIBLE_FULL_6CELL_CUBE_V1.json"
HOLDOUT_JSON = RESULTS / "hydraulically_feasible_selected_6cell_holdout_v1" / "PSA_HYDRAULICALLY_FEASIBLE_SELECTED_6CELL_HOLDOUT_V1.json"
TRAIN_JSON = RESULTS / "pressure_consistent_stage_resolved_membrane_train_v1" / "PSA_STAGE_RESOLVED_MEMBRANE_TRAIN.json"
ODE_JSON = RESULTS / "pressure_consistent_independent_ode_membrane_audit_v1" / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.json"
SYNGAS_JSON = RESULTS / "pressure_consistent_pd_actual_syngas_poisoning_guard_v1" / "PSA_PD_ACTUAL_SYNGAS_POISONING_GUARD_V1.json"
QAE_JSON = RESULTS / "pressure_consistent_physical_pd_area_qae_bridge_v1" / "PSA_PHYSICAL_PD_AREA_QAE_BRIDGE.json"
RK4_JSON = RESULTS / "pressure_consistent_independent_rk4_membrane_crosscheck_v1" / "PSA_INDEPENDENT_RK4_MEMBRANE_CROSSCHECK_V1.json"
SELECTIVITY_JSON = RESULTS / "pressure_consistent_public_selectivity_acceptance_audit_v1" / "PSA_PUBLIC_SELECTIVITY_ACCEPTANCE_AUDIT_V1.json"
PORTABLE_QASM_JSON = RESULTS / "pressure_consistent_portable_qasm_oracle_v1" / "PSA_PRESSURE_CONSISTENT_PORTABLE_QASM_ORACLE_V1.json"
DWSIM_JSON = PROJECT / "07_DWSIM_Aspen_재현" / "results" / "pressure_consistent_stage_train_v1" / "psa_stage_train_dwsim_audit" / "PSA_STAGE_TRAIN_DWSIM_CROSSCHECK.json"

OLD_PACKAGE = RESULTS / "spt_engineering_results_v1"

FIGURES = {
    1: RESULTS / "hydraulically_feasible_full_6cell_cube_v1" / "PSA_HYDRAULICALLY_FEASIBLE_FULL_6CELL_CUBE_V1.png",
    2: RESULTS / "hydraulically_feasible_selected_6cell_holdout_v1" / "PSA_HYDRAULICALLY_FEASIBLE_SELECTED_6CELL_HOLDOUT_V1.png",
    3: OLD_PACKAGE / "Fig3_public_dynamic_external_validation.png",
    4: RESULTS / "membrane_public_evidence_audit_v2" / "Fig_membrane_public_evidence_audit_v2.png",
    5: RESULTS / "pressure_consistent_stage_resolved_membrane_train_v1" / "Fig_stage_resolved_membrane_train.png",
    6: RESULTS / "pressure_consistent_independent_ode_membrane_audit_v1" / "Fig_independent_ode_membrane_audit.png",
    7: RESULTS / "pressure_consistent_pd_leakage_aging_sensitivity_v1" / "Fig_pd_leakage_aging_sensitivity.png",
    8: PROJECT / "07_DWSIM_Aspen_재현" / "results" / "pressure_consistent_stage_train_v1" / "psa_stage_train_dwsim_audit" / "Fig_psa_stage_train_dwsim_crosscheck.png",
    9: RESULTS / "pressure_consistent_portable_qasm_oracle_v1" / "Fig_pressure_consistent_portable_qasm_oracle_v1.png",
    10: RESULTS / "pressure_consistent_pd_actual_syngas_poisoning_guard_v1" / "Fig_pd_actual_syngas_poisoning_guard_v1.png",
    11: RESULTS / "pressure_consistent_independent_rk4_membrane_crosscheck_v1" / "Fig_independent_rk4_membrane_crosscheck_v1.png",
    12: RESULTS / "ververs_2024_mass_transfer_validation_v1" / "Fig_ververs_2024_mass_transfer_validation_v1.png",
    13: PROJECT / "07_DWSIM_Aspen_재현" / "results" / "psa_stage_train_high_temperature_audit" / "Fig_stage_train_high_temperature_audit.png",
    14: RESULTS / "pressure_consistent_public_selectivity_acceptance_audit_v1" / "Fig_public_selectivity_acceptance_audit_v1.png",
    15: RESULTS / "sanchez_2014_validation_audit_v1" / "Fig_sanchez_detection_resolution_v1.png",
    16: RESULTS / "doe_pall_2008_mixed_gas_validation_v1" / "Fig_doe_pall_2008_mixed_gas_validation_v1.png",
    17: RESULTS / "utrc_2012_high_recovery_validation_v1" / "Fig_utrc_2012_high_recovery_validation_v1.png",
    18: RESULTS / "bang_2021_joint_gate_validation_v1" / "Fig_bang_2021_joint_gate_validation_v1.png",
    19: RESULTS / "csharp_direct_transport_crosscheck_v1" / "Fig_csharp_direct_transport_crosscheck_v1.png",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


legacy.TITLE = (
    "Hydraulically feasible regeneration-reserve-aware hydrogen pressure swing adsorption "
    "under uncertainty with staged membrane polishing and a quantum-ready probability event"
)
legacy.OUT = OUT
legacy.MD_OUT = MD_OUT
legacy.DOCX_OUT = DOCX_OUT
legacy.MANIFEST_OUT = MANIFEST_OUT
legacy.REFERENCE_AUDIT_OUT = REFERENCE_AUDIT_OUT
legacy.EVIDENCE = EVIDENCE
legacy.DATA_AVAILABILITY = (
    "The complete calculation records, direct states, portable OpenQASM circuit, corrected DWSIM input and results, figures, "
    "tables, and SHA-256 manifests are archived under the version-independent repository DOI "
    "https://doi.org/10.5281/zenodo.23271866 and mirrored at "
    "https://github.com/lyullee/psa-qae-resource-audit."
)

legacy.ABSTRACT = (
    "Hydrogen pressure swing adsorption must retain product gas for the next purge and repressurization steps before gas can be sold. "
    "This work formulates that allocation as a continuous qualified-shipment problem and enforces pressure feasibility between a four-bed PSA, a finite regeneration tank, valves, and a polishing train. "
    "A pressure audit showed that the preliminary 7.0 bar tank could not be passively refilled from a 6.2 bar product manifold. The corrected topology therefore uses a 6.0 bar regulated tank, a 0.2 bar fill driving margin, and a discharge booster to the 6.5 bar regeneration header. "
    "Within declared feed, adsorption-equilibrium, and kinetic uncertainty, the selected policy of 4 s active purge and 540 s adsorption passed all eight corner cases and all eight predeclared interior hold-outs; a 6 s, 480 s comparison passed none. Specification-qualified hydrogen shipment increased by 6.785-7.341%, the minimum reserve-margin gain was 0.542 bar, and conservative booster duty remained below 0.198 kWh kg-1 H2. "
    "A literature-parameterized polymer concentrator followed by dense palladium polishing passed all 16 direct cases. Adaptive DOP853 integration corrected a near-boundary 20%-permeance-loss guard from 0.553 to 0.554 m2; the revised design gave at least 88.322% recovery and maximum CO, CO2, N2, and CH4 contents of 0.121, 4.000, 48.83, and 25.07 ppm. A public actual-syngas 50%-permeance-retention stress increased the conditional installed area to 0.887 m2 and retained all 16 cases. A separately coded fixed-area RK4 solver reproduced all 32 design-case labels, with a maximum recovery difference below 9.4e-8 percentage point relative to DOP853. "
    "A corrected DWSIM 8.7.1 Peng-Robinson calculation solved all 16 horizon-averaged cases at the 6.2 bar inlet, with maximum component-balance error 8.95e-19 mol s-1 and compression demand of 3.091-3.183 kWh kg-1 H2. "
    "For a 0.440 m2 chance design, error-buffered trilinear integration gave a minimum scrambled-Sobol probability of 0.956673; a conservative affine event gave 0.951210, and its 10-bit discretization gave 0.950629 with no direct label errors. An exact portable OpenQASM 3 oracle uses 66 logical qubits, 24,042 CX gates, 61,269 primitive gates, and all-to-all depth 36,163 before optimization or routing. Exhaustive 2-, 3-, and 4-bit checks plus direct and random 10-bit checks gave zero phase-label and work-qubit-restoration errors. "
    "For this smooth three-variable event, randomized quasi-Monte Carlo remains the practical estimator. The contribution is a pressure-consistent separation design rule and an auditable process-to-oracle construction for future higher-dimensional plant uncertainty."
)

legacy.HIGHLIGHTS = [
    "A 6.0 bar regeneration tank is passively filled from the 6.2 bar product manifold",
    "A discharge booster closes the hydraulic path to the 6.5 bar regeneration header",
    "The selected 4 s purge and 540 s adsorption policy passes 8/8 corners and 8/8 hold-outs",
    "Qualified hydrogen shipment rises by 6.785-7.341% over the comparison policy",
    "A 0.554 m2 Pd guard passes all 16 cases at 20% permeance loss",
    "A 0.887 m2 conditional guard covers a public 50% actual-syngas loss stress",
    "Independent RK4 reproduces all 32 adaptive-integrator decisions",
    "Corrected DWSIM Peng-Robinson calculations solve all 16 process cases",
    "A verified 66-qubit OpenQASM oracle connects the process chance constraint to QAE",
]

sections = copy.deepcopy(legacy.SECTIONS)

sections[0][1][4] = (
    "This study combines a pressure-consistent four-bed PSA, finite regeneration inventory, staged membrane polishing, uncertainty propagation, and a quantum-ready chance event. The model is checked against a public four-bed hydrogen VPSA experiment [8], 468 public Pd-Ag H2/N2 flux records [22], high-pressure and mixed-gas palladium studies [23-29], and an integrated membrane-reactor/PSA study [30]. Adaptive DOP853 and separately coded fixed-area RK4 calculations test numerical sensitivity. The contribution is an engineering operating rule and a reproducible probability event; present quantum advantage and direct certification of the integrated apparatus are outside the claim."
)

sections[1][1][0] = (
    "The process boundary begins at a multicomponent hydrogen-rich PSA feed and ends at a finite product receiver. Four adsorbers follow a staggered adsorption, equalization, blowdown, purge, and repressurization schedule. Product gas first supplies simultaneous internal demand. Remaining gas reaches a 6.2 bar product manifold and passively refills a tank regulated to 6.0 bar. Tank withdrawal is boosted to the 6.5 bar purge and repressurization header. Only surplus product proceeds to polishing and sale."
)
sections[1][1][1] = (
    "The primary objective is time-averaged specification-qualified hydrogen delivered from the receiver. The operating-policy screen requires hydrogen fraction at least 0.9997; CO, CO2, N2, and CH4 no greater than 0.5, 5, 300, and 100 ppm; qualified hydrogen at least 0.002 mol s-1; positive regeneration reserve; passive tank-fill margin; bounded booster duty; cyclic convergence; trace integrity; and component conservation. The final physical membrane design additionally freezes recovery and shipment floors of 0.882940 and 0.0022631 mol s-1."
)
sections[1][1][2] = (
    "Both policies use a 6.0 bar tank set point. The comparison uses 6 s active purge and a 480 s adsorption stage; the selected policy uses 4 s and 540 s. Physical decisions include polymer and dense-palladium areas, surge capacity, receiver capacity, and regeneration-booster duty. Uncertainty coordinates cover a feed-hydrogen multiplier of 0.95-1.05, paired adsorption capacity-affinity endpoints, and an LDF kinetic multiplier of 0.8-1.2. Their eight endpoint combinations form the engineering cube; eight interior points were declared before the corrected design calculation."
)

sections[2][1][1] = (
    "Each bed is discretized axially and advanced through the staggered cycle with component inventories, competitive equilibrium, LDF uptake, valve-driven flows, and a non-isothermal energy balance. The tank follows component inventory and ideal-gas pressure. A separate hydraulic audit enforces the 6.2-to-6.0 bar passive-fill direction and computes isothermal booster work from the instantaneous tank pressure to the 6.5 bar header at 72% efficiency. Six axial cells and 60 cycles are used for direct decisions, with cyclic-state, trace-integrity, and component-balance gates."
)
sections[2][1][4] = (
    "Surplus PSA product is compressed from the 6.2 bar manifold to a 20 bar surge buffer and cooled to 298.15 K. A polymer concentrator operates at 20/1 bar. Its permeate is recompressed in three equal-pressure-ratio stages to a dense-palladium stage at 20/1 bar and 693.15 K. Both retentates go to fuel or off-gas, and no internal recycle is credited. The ideal-train screen uses a 4.616 mol surge buffer and a 1.546 mol product receiver; guard-banded finite-selectivity designs co-size the receiver again."
)
sections[2][1][5] = (
    "Membrane transfer is evaluated for every saved time packet. The production calculation uses fixed area sections; the independent audit solves the same transfer laws with scipy DOP853 at relative and absolute tolerances of 1e-9 and 1e-13. A second implementation uses classical fourth-order Runge-Kutta over 48, 96, and 192 equal-area sections and does not call the adaptive solver. Exact component ledgers are retained across both membranes and the finite receiver."
)
sections[2][1][6] = (
    "The dense-palladium guard imposes finite effective H2/impurity selectivities, hydrogen-permeance loss, and an H2-equivalent Knudsen defect-conductance ratio. This ratio compares local defect H2 transfer with dense-palladium H2 transfer and is not a geometric pinhole fraction. Continuous receiver quality, inventory, recovery, shipment, and mass balance are checked for all eight corners and eight hold-outs."
)
sections[2][1][8] = (
    "The two operating policies are paired at all eight uncertainty corners. The corrected selected policy is then tested on the eight predeclared interiors. The membrane-area chance calculation fits a trilinear response to the corners, measures its largest absolute error on the predeclared interiors, and shifts the event boundary by that error. Eight independent scrambled Sobol integrations estimate probability under an explicitly uniform engineering measure."
)
sections[2][1][10] = (
    "Installed dense-palladium area is the physical design coordinate. At 0.440 m2, 13 of 16 direct stress cases pass while the continuous chance probability exceeds 0.95. A conservative affine event is checked against every direct label and digitized with 10 qubits for each of three uncertainty coordinates. Reversible signed accumulation and comparison require 66 logical qubits. The circuit follows source-equivalent weighted-adder and two's-complement comparator constructions and is expanded exactly to OpenQASM 3 using X, H, T, Tdg, Z, and CX. Its portable unoptimized resources are 24,042 CX gates, 61,269 total primitive gates, and all-to-all depth 36,163. These counts exclude device routing, error correction, and hardware calibration."
)
sections[2][1][12] = (
    "Compression is recalculated from the corrected 6.2 bar product manifold to the 20 bar polishing buffer and from the 1 bar polymer permeate to the 20 bar palladium feed. The corrected 16-case deck was executed in DWSIM 8.7.1 with the Peng-Robinson property package, a 72% efficient first compressor, and three equal-pressure-ratio intercooled recompression stages. Windows Application Control blocked the distributed file-storage assembly only; a syntax-equivalent local rebuild from the official v8.7.1 source was preloaded, while the thermodynamic and unit-operation assemblies remained unchanged. DWSIM receives horizon-averaged component split fractions from the packet-resolved Python membrane model, so this is an independent pressure, duty, thermodynamic-state, and material-closure check rather than an independent membrane-transport calculation."
)
sections[2][1][13] = (
    "The independent RK4 implementation evaluates the frozen polymer solution-diffusion and finite-selectivity palladium equations at 48, 96, and 192 area sections. It covers the 0.554 m2, 80%-retention guard and the 0.887 m2, 50%-retention actual-syngas stress over all 16 direct cases. This isolates numerical implementation and mesh sensitivity while retaining the same constitutive laws."
)
sections[2][1][17] = (
    "The corrected DWSIM calculation establishes the 6.2-to-20 bar compression, three-stage recompression, intercooling, and component closure at 298.15 K. An earlier hot-stage calculation additionally documents a 420 C palladium heater and coolers for the preceding input set; its heat-integration numbers are retained only as structural evidence. Published 22-26 bar palladium inhibition and endurance studies [23,24] independently define the high-temperature evidence boundary."
)
sections[2][1][19] = (
    "The 0.887 m2 design is replayed while one effective impurity selectivity is reduced and the others remain fixed. Logarithmic bisection finds the lowest value preserving all 16 events; a 25% simultaneous margin and upward rounding form an incoming-module screen. Li et al. [25] and DOE/MPT [26] provide public high-pressure and defect-leakage stresses, respectively, and are used as transfer and rejection controls rather than matched certification."
)
sections[2][1][29] = (
    "A compiled C# packetwise implementation was previously used to verify the independent transport method on the preceding input set. The regenerated 6.0 bar train was not replayed because native execution is restricted on the current host. Its figure is retained to document the third-language method, but the current pressure-consistent claims rely on direct six-cell integration, DOP853, and the newly rerun Python RK4 calculation."
)

sections[3][1][1] = (
    "The pressure audit rejected the preliminary 7.0 bar tank because the 6.2 bar product manifold could not fill it passively. With the corrected 6.0 bar tank and discharge booster, the 6 s/480 s comparison failed all eight corners whereas the 4 s/540 s policy passed all eight. Qualified shipment increased by 6.785-7.341%, minimum reserve margin improved by at least 0.542 bar, and the selected conservative booster duty was no greater than 0.197 kWh kg-1 qualified H2. The maximum cyclic-state residual and relative cycle balance error were 1.225e-5 and 1.661e-5."
)
sections[3][1][3] = (
    "All eight predeclared interior conditions passed the corrected six-cell, 60-cycle calculation. Their minimum tank pressure was 3.546 bar, minimum reserve margin was 2.746 bar, maximum N2 was 227.24 ppm, and maximum booster duty was 0.194 kWh kg-1. All passive-fill, trace-integrity, cyclic-state, and mass-balance gates passed. The separate physical-area chance event at 0.440 m2 gave a minimum scrambled-Sobol probability of 0.956673 after hold-out buffering."
)
sections[3][1][8] = (
    "The ideal literature-bounded train uses a 0.1892 m2 polymer stage and 0.4799 m2 dense-palladium stage. It passes all eight corners and eight hold-outs, with minimum recovery 93.450%, minimum qualified hydrogen 0.0024562 mol s-1, 4.616 mol surge capacity, and 1.546 mol receiver capacity. The conservative design-screen compression requirement is 2.573 kWh kg-1 H2 for the corrected 6.2-to-20 bar boundary and interstage recompression."
)
sections[3][1][10] = (
    "The fixed-section calculation suggested that 0.553 m2 would cover 20% permeance loss. Adaptive DOP853 integration found one failure, so bisection and upward rounding increased the guard to 0.554 m2. This revised area is a numerical and performance guard, not a membrane-manufacturing tolerance."
)
sections[3][1][11] = (
    "The 0.554 m2 design passed all 16 direct cases. Minimum recovery was 0.883221 and minimum qualified hydrogen was 0.00236055 mol s-1. Maximum CO, CO2, N2, and CH4 were 0.1204, 3.9998, 48.83, and 25.07 ppm. The receiver capacity was 1.2320 mol (30.541 L at 1 bar and 298.15 K), and module and receiver balance errors remained below 4.2e-17 and 1.3e-11 mol."
)
sections[3][1][12] = "4.6 Corrected DWSIM compression and process-simulator cross-check"
sections[3][1][13] = (
    "Changing the polishing inlet from the obsolete 8 bar assumption to the physically available 6.2 bar manifold increased the ideal-gas isothermal design-screen requirement to 2.573 kWh kg-1 H2, without changing area, recovery, purity, or pass labels. The corrected DWSIM deck solved all 16 cases with zero calculation errors. Maximum component-balance error was 8.95e-19 mol s-1 and maximum product-stream difference from the supplied split fractions was 1.30e-18 mol s-1. DWSIM adiabatic compression required 3.091-3.183 kWh kg-1 H2, 16.94-16.98% above the matched isothermal lower bound. Maximum first-compressor and recompression-stage discharge temperatures were 460.03 and 433.64 K, respectively."
)
sections[3][1][15] = (
    "At 0.440 m2 installed dense-palladium area, 13 of 16 direct points passed. The error-buffered trilinear probability had a minimum-scramble value of 0.956673; the conservative affine probability was 0.951210. Ten-bit digitization gave 0.950629, an absolute probability error of 0.000581, with zero false-positive and zero false-negative direct labels. The included OpenQASM 3 oracle uses 66 logical qubits, 24,042 CX gates, 61,269 primitive gates, and all-to-all depth 36,163 before optimization or routing. It produced zero phase-label and restoration errors in exhaustive 2-, 3-, and 4-bit tests, all 16 direct 10-bit engineering states, and 4,096 seeded random 10-bit states."
)
sections[3][1][16] = (
    "RQMC is still the practical estimator for this smooth three-variable event. The quantum construction supplies a reproducible Boolean event, integer coefficients, register layout, and discretization error. It becomes computationally interesting only when future plant-calibrated uncertainty is higher-dimensional, process evaluation is expensive, and repeated risk queries can reuse the same oracle."
)
sections[3][1][18] = (
    "A public coal-syngas membrane study reported a 40-50% loss of hydrogen permeance while Pd-Au selectivity remained stable for more than 473 h [21]. Under the conservative 50% retention stress, bisection required 0.8860 m2 and the installed guard was rounded to 0.887 m2. All 16 cases passed with minimum recovery 0.883679 and minimum qualified hydrogen 0.00236153 mol s-1."
)
sections[3][1][20] = (
    "At 192 sections per membrane, fixed-grid RK4 passed all 16 cases for both the 0.554 m2, 80%-retention guard and the 0.887 m2, 50%-retention guard. All 32 labels matched DOP853. The maximum recovery difference was 9.33e-8 percentage point, the maximum relative qualified-flow difference was 1.01e-9, and maximum component-balance error was 4.25e-17 mol."
)
sections[3][1][23] = "4.11 High-pressure palladium evidence and legacy hot-stage cross-check"
sections[3][1][24] = (
    "The corrected DWSIM run resolves the current 6.2 bar pressure basis, compressor duties, temperatures, and Peng-Robinson closure, as shown in Figure 8. Figure 13 retains the earlier 420 C heater and heat-integration structure for the preceding input set and is not used for current energy numbers. Published 22 bar inhibition and 26 bar, 400 C endurance studies [23,24] independently support the high-temperature feasibility envelope but do not certify the final impurity vector."
)
sections[3][1][25] = (
    "The literature inhibition and endurance records support retaining an explicit permeance-loss guard. The 0.554 and 0.887 m2 designs are therefore interpreted as conditional engineering sizes tied to 80% and 50% permeance retention, respectively. A matched wet multicomponent module test remains necessary before converting either size into a procurement specification."
)
sections[3][1][27] = (
    "Pressure-consistent bisection converts each impurity leakage channel into an incoming-module selectivity threshold. The rounded, simultaneous guard and all 16 direct confirmations are reported in Table 5 and Figure 14. Public defect-leaking selectivity vectors are retained as rejection stresses, which separates required area from required membrane integrity."
)
sections[3][1][31] = (
    "The DOE/Pall flow ledger gives 75.98% H2 recovery, 75 ppm CO, and 450 ppm CO2 [28]. These values are 13.15 percentage points below the project recovery floor and 150 and 90 times the respective impurity limits. The corresponding system-level H2/CO and H2/CO2 separation factors are also far below the corrected incoming-module guards of 5,660 and 168,660. The experiment therefore supplies a synchronized empirical rejection control: measured impurity leakage, rather than membrane area alone, prevents entry into the joint pass region."
)
sections[3][1][37] = (
    "The compiled C# replay previously demonstrated that the transport implementation could be reproduced without membrane split inputs. It belongs to the superseded input set and is not counted as current pressure-consistent confirmation. The corrected claim is instead supported by direct packetwise DOP853 and the independently coded RK4 result in Section 4.9."
)

sections[4][1][1] = (
    "The principal result is a physically closed material-allocation rule. Product hydrogen first secures the next cycle, the 6.2 bar manifold passively restores the 6.0 bar tank, and a booster supplies the 6.5 bar regeneration header when tank pressure falls below it. Shortening active purge and extending adsorption increased qualified saleable hydrogen without relaxing product quality or reserve gates."
)
sections[4][1][2] = (
    "The robust and chance designs answer different questions. The 0.4799 m2 ideal palladium stage passes all direct cases under the ideal dense-Pd assumption. The 0.440 m2 chance design accepts a small low-performance region under the declared uniform measure. The 0.554 and 0.887 m2 guards then address finite selectivity and permeance loss. These areas must be reported with their assumptions because they are not interchangeable."
)
sections[4][1][4] = (
    "The 0.553-to-0.554 m2 correction is small in area but important in logic because the event lies near its recovery boundary. Adaptive integration exposed the missed failure, and the independent RK4 mesh reproduced the corrected 32 labels to much tighter tolerance than the engineering margin. This adverse result supports the final guard rather than being hidden as solver noise."
)
sections[4][1][6] = (
    "The work contributes a separation-process operating rule: pressure-consistent regeneration inventory, strict product quality, and uncertain feed and adsorption performance are optimized together. Public experiments validate transferable dynamic, mass-transfer, inhibition, recovery, and rejection behavior, while their measurement limits are carried into the claim boundary. The missing experiment is a synchronized test of the final integrated apparatus at the declared ppm limits."
)
sections[4][1][8] = (
    "QAE is subordinate to the separation result. Current RQMC is cheaper for this three-dimensional response. The quantum contribution is the auditable reduction from a physical membrane-area chance constraint to a verified discrete reversible event with known probability error, a portable OpenQASM implementation, and explicit pre-routing resources. The 24,042-CX count is a reproducible upper-level resource baseline rather than an optimized device cost, and no hardware-advantage claim is made."
)
sections[4][1][10] = (
    "The main limitations are the uniform engineering uncertainty measure, transfer of adsorption and membrane parameters across apparatuses, common constitutive laws in DOP853 and RK4, use of supplied horizon-averaged membrane split fractions in DWSIM, lack of device-specific quantum routing and execution, and the lack of a matched component-resolved integrated experiment. Public membrane studies establish feasibility, recovery scale, degradation stresses, and rejection cases, but their feeds, pressures, modules, and analytical resolutions differ. These boundaries define the next validation work and do not change the pressure-consistent numerical design decision reported here."
)

sections[5][1][0] = (
    "A finite regeneration inventory makes hydrogen PSA an allocation problem between the next cycle and sale. The physically feasible design uses a 6.0 bar tank passively filled from the 6.2 bar product manifold and a booster to the 6.5 bar regeneration header. The selected 4 s purge and 540 s adsorption policy passed 8/8 uncertainty corners and 8/8 predeclared hold-outs, increased qualified shipment by 6.785-7.341%, and kept conservative booster duty below 0.198 kWh kg-1 H2."
)
sections[5][1][1] = (
    "The staged polishing train combines a 0.1892 m2 polymer concentrator with dense-palladium polishing. Adaptive integration set the 20%-loss guard at 0.554 m2; it passed 16/16 cases with minimum recovery 88.322% and every impurity below its limit. A public 50%-retention actual-syngas stress increased the conditional guard to 0.887 m2 and again passed 16/16. Independent RK4 preserved all 32 final labels, confirming that the design decision is insensitive to the numerical integrator and refined area mesh."
)
sections[5][1][2] = (
    "The corrected DWSIM calculation solved all 16 horizon-averaged cases and quantified the adiabatic compression penalty above the isothermal screen. The physical chance event at 0.440 m2 has conservative continuous probability 0.951210 and 10-bit discrete probability 0.950629 with no direct label errors. The verified portable oracle requires 66 logical qubits and has an exact pre-routing count of 24,042 CX gates. RQMC remains preferred for the present model; QAE becomes relevant when validated plant uncertainty and repeated probability queries make classical event evaluation expensive. Device-specific quantum execution and a synchronized integrated experiment remain external validation steps."
)

legacy.SECTIONS = sections

legacy.FIGURE_CAPTIONS.update(
    {
        1: "Pressure-consistent operating-policy comparison across the complete eight-corner uncertainty cube. Both policies use a 6.0 bar tank; the selected 4 s/540 s schedule preserves reserve and increases qualified shipment.",
        2: "Eight predeclared interior hold-outs for the corrected 6.0 bar tank and discharge-booster topology.",
        5: "Corrected pressure-consistent polymer plus dense-palladium train over eight corners and eight hold-outs.",
        6: "Independent continuous-area DOP853 audit that changes the 20%-permeance-loss palladium guard from 0.553 to 0.554 m2.",
        7: "Finite selectivity, defect leakage, and permeance-retention sensitivity for the corrected train.",
        8: "Corrected DWSIM 8.7.1 Peng-Robinson cross-check for all 16 horizon-averaged cases at the 6.2 bar polishing inlet. The calculation independently checks pressure states, compression and cooling duties, temperatures, and material closure while using membrane split fractions supplied by the packet model.",
        9: "Verified physical dense-palladium-area chance event and portable OpenQASM resource baseline. CX and depth are exact all-to-all counts before device optimization and routing.",
        10: "Corrected installed-area requirement under the 40-50% actual-syngas permeance-loss stress.",
        11: "Corrected fixed-area RK4 mesh refinement and agreement with adaptive DOP853 for both guard designs.",
        13: "Earlier hot-stage DWSIM equipment and heat-integration audit retained as structural evidence for the 420 C palladium stage; current corrected compression results are reported in Figure 8.",
        14: "Pressure-consistent component selectivity thresholds and simultaneous incoming-module acceptance guard.",
        19: "Third-language packetwise method evidence from the superseded input set. It is not counted as current pressure-consistent confirmation.",
    }
)


def add_figure(doc, display_number, source_number=None):
    path = FIGURES[display_number]
    assert path.exists(), path
    p = doc.add_paragraph()
    p.alignment = legacy.WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = legacy.Pt(8)
    p.paragraph_format.space_after = legacy.Pt(3)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=legacy.Inches(6.65))
    c = doc.add_paragraph()
    c.paragraph_format.space_after = legacy.Pt(8)
    c.alignment = legacy.WD_ALIGN_PARAGRAPH.JUSTIFY
    r = c.add_run(f"Figure {display_number}. ")
    legacy.set_font(r, size=9, bold=True)
    r = c.add_run(legacy.FIGURE_CAPTIONS[display_number])
    legacy.set_font(r, size=9)


def data_tables(_evidence):
    cube = load(CUBE_JSON)["summary"]
    hold = load(HOLDOUT_JSON)["summary"]
    train = load(TRAIN_JSON)
    ode_doc = load(ODE_JSON)
    ode = ode_doc["revised_guard_design"]
    confirm = ode["direct_confirmation"]
    syngas = load(SYNGAS_JSON)["conservative_50_percent_retention_design"]
    qae = load(QAE_JSON)
    qv = qae["validation"]
    qr = qae["conservative_affine_oracle"]["ten_bit_resources"]
    portable = load(PORTABLE_QASM_JSON)
    pr = portable["resources"]
    dwsim = load(DWSIM_JSON)
    de = dwsim["energy_and_temperature"]
    selectivity = load(SELECTIVITY_JSON)
    thresholds = {row["impurity"]: row for row in selectivity["component_acceptance_thresholds"]}
    procurement = selectivity["design"]["rounded_procurement_acceptance_vector"]
    public = {row["scenario_id"]: row for row in selectivity["public_stress_scenarios"]}
    return [
        (1, "Pressure-consistent operating decision", ["Decision", "Comparison", "Selected", "Evidence"], [
            ["Tank set point", "6.0 bar", "6.0 bar", "6.2 bar manifold"],
            ["Active purge", "6 s", "4 s", "8 corners"],
            ["Adsorption stage", "480 s", "540 s", "60 cycles"],
            ["Joint pass", "0/8", "8/8", "Direct model"],
            ["Predeclared hold-out", "-", f"{hold['direct_pass_count']}/8", "Independent interiors"],
            ["Qualified H2 gain", "Reference", f"{cube['minimum_shipment_improvement_percent']:.3f}-{cube['maximum_shipment_improvement_percent']:.3f}%", "Paired cases"],
            ["Maximum booster duty", "-", f"{cube['selected_maximum_booster_kwh_per_kg_qualified_h2']:.3f} kWh kg-1", "6.5 bar discharge"],
        ]),
        (2, "Evidence hierarchy", ["Evidence", "Result", "Supported claim", "Boundary"], [
            ["Uncertainty corners", "8/8 selected pass", "Robust policy", "Declared cube"],
            ["Predeclared interiors", "8/8 pass", "Hold-out transfer", "Finite sample"],
            ["Wang experiment", "11.37% max breakthrough error", "Dynamic model family", "Different apparatus"],
            ["Adaptive ODE", "0.554 m2 passes 16/16", "Numerical guard", "Same transport laws"],
            ["Independent RK4", "32/32 labels agree", "Implementation robustness", "Same constitutive laws"],
            ["Ververs data", "468 flux records", "Concentration polarization", "Binary 2-5 bar"],
            ["Public Pd studies", "pressure, aging, rejection anchors", "Feasibility envelope", "Unmatched modules"],
            ["Corrected DWSIM", "16/16 solved", "Pressure/duty/closure", "Supplied membrane splits"],
            ["Portable QASM", "0 phase/restoration errors", "Executable event", "Pre-routing resources"],
        ]),
        (3, "Membrane and receiver design tiers", ["Quantity", "Value", "Gate"], [
            ["Polymer area", f"{train['selected_design']['concentrator_area_m2']:.4f} m2", "Literature bounded"],
            ["Ideal dense-Pd area", f"{train['selected_design']['pd_area_m2']:.4f} m2", "16/16 direct"],
            ["20% loss guard", f"{ode['selected_rounded_pd_area_m2']:.3f} m2", f"{confirm['pass_count']}/16"],
            ["50% loss guard", f"{syngas['selected_rounded_installed_area_m2']:.3f} m2", f"{syngas['pass_count']}/16"],
            ["Guard receiver", f"{ode['receiver_capacity_mol']:.6f} mol", f"{ode['receiver_volume_L_at_1bar_298K']:.3f} L"],
            ["Minimum recovery", f"{confirm['minimum_recovery']*100:.4f}%", "88.2940% floor"],
            ["Minimum qualified H2", f"{confirm['minimum_qualified_h2_rate_mol_s']:.7f} mol s-1", "0.0022631 floor"],
            ["Maximum CO2", f"{confirm['maximum_co2_ppm']:.4f} ppm", "5 ppm"],
        ]),
        (4, "Corrected energy and quantum-event summary", ["Calculation", "Metric", "Value"], [
            ["Regeneration booster", "Maximum duty", f"{cube['selected_maximum_booster_kwh_per_kg_qualified_h2']:.3f} kWh kg-1 H2"],
            ["Polishing compression", "Conservative screen", f"{train['selected_design']['maximum_compression_energy_kwh_kg_h2']:.3f} kWh kg-1 H2"],
            ["Polishing compression", "Pressure basis", "6.2->20 bar; 1->20 bar"],
            ["DWSIM compression", "Adiabatic range", f"{de['dwsim_specific_compression_kWh_kg_H2_range'][0]:.3f}-{de['dwsim_specific_compression_kWh_kg_H2_range'][1]:.3f} kWh kg-1 H2"],
            ["DWSIM compression", "Premium over isothermal", f"{100*(de['adiabatic_to_isothermal_power_ratio_range'][0]-1):.2f}-{100*(de['adiabatic_to_isothermal_power_ratio_range'][1]-1):.2f}%"],
            ["DWSIM temperatures", "Maximum discharges", f"{de['maximum_first_compressor_discharge_K']:.2f} / {de['maximum_interstage_compressor_discharge_K']:.2f} K"],
            ["QAE event", "Chance Pd area", f"{qae['event']['selected_chance_pd_area_m2']:.3f} m2"],
            ["QAE event", "Continuous affine probability", f"{qv['conservative_affine_probability']:.6f}"],
            ["QAE event", "10-bit probability", f"{qr['exact_discrete_oracle_probability']:.6f}"],
            ["QAE event", "Discretization error", f"{qr['absolute_probability_discretization_error']:.6f}"],
            ["QAE event", "Logical qubits", str(qr['total_logical_qubits'])],
            ["OpenQASM 3", "Portable CX", f"{pr['portable_primitive_cx']:,}"],
            ["OpenQASM 3", "Primitive size / depth", f"{pr['portable_primitive_size']:,} / {pr['portable_primitive_depth_all_to_all']:,}"],
        ]),
        (5, "Dense-Pd incoming-module selectivity acceptance", ["Component/test", "Minimum or measured", "Acceptance guard", "Direct result"], [
            ["H2/CO", f"{thresholds['CO']['minimum_effective_selectivity']:,.1f}", f">= {procurement['CO']:,.0f}", "16/16 at guard"],
            ["H2/CO2", f"{thresholds['CO2']['minimum_effective_selectivity']:,.1f}", f">= {procurement['CO2']:,.0f}", "16/16 at guard"],
            ["H2/N2", f"{thresholds['N2']['minimum_effective_selectivity']:,.1f}", f">= {procurement['N2']:,.0f}", "16/16 at guard"],
            ["H2/CH4", f"{thresholds['CH4']['minimum_effective_selectivity']:,.2f}", f">= {procurement['CH4']:,.0f}", "16/16 at guard"],
            ["Li 2011 end test", f"H2/N2={public['li_2011_n2_end_of_test']['alpha_n2']:.1f}", "N2 transfer only", f"{public['li_2011_n2_end_of_test']['pass_count']}/16"],
            ["DOE/MPT 60 psig", "H2/i=92-116", "defect stress", f"{public['doe_mpt_2005_shell_60psig']['pass_count']}/16"],
        ]),
    ]


legacy.add_figure = add_figure
legacy.data_tables = data_tables


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    evidence = load(EVIDENCE)
    assert evidence["schema"] == "psa-final-objective-evidence/v45"
    OUT.mkdir(parents=True, exist_ok=True)
    for path in FIGURES.values():
        assert path.exists(), path
    legacy.write_markdown(evidence)
    legacy.build_docx(evidence)
    old_audit = RESULTS / "spt_full_manuscript_v1" / "REFERENCE_METADATA_AUDIT.json"
    shutil.copy2(old_audit, REFERENCE_AUDIT_OUT)
    sources = [EVIDENCE, CUBE_JSON, HOLDOUT_JSON, TRAIN_JSON, ODE_JSON, SYNGAS_JSON, QAE_JSON, RK4_JSON, SELECTIVITY_JSON, PORTABLE_QASM_JSON, DWSIM_JSON, *FIGURES.values()]
    outputs = [MD_OUT, DOCX_OUT, REFERENCE_AUDIT_OUT]
    manifest = {
        "schema": "psa-spt-pressure-consistent-manuscript/v3",
        "status": "pressure_consistent_manuscript_with_verified_portable_qasm_and_corrected_dwsim_crosscheck",
        "sources": [{"path": str(p.relative_to(PROJECT)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in sources],
        "outputs": [{"path": str(p.relative_to(PROJECT)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in outputs],
        "claim_boundary": {
            "current": "6.0 bar tank, discharge booster, corrected 6.2 bar polishing inlet, 8 corners, 8 hold-outs, DOP853, RK4, and 16-case DWSIM Peng-Robinson cross-check",
            "pending": "device-specific quantum optimization/routing and synchronized integrated experimental certification",
            "legacy_only": "earlier hot-stage DWSIM heat-integration values and C# packet replay",
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"docx": str(DOCX_OUT), "markdown": str(MD_OUT), "figures": len(FIGURES), "references": len(legacy.REFERENCES)}, indent=2))


if __name__ == "__main__":
    main()
