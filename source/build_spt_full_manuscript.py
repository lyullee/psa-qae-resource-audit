"""Build the SPT-oriented full manuscript with current external validation."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
RESULTS = HERE / "results"
PACKAGE = RESULTS / "spt_engineering_results_v1"
EVIDENCE = RESULTS / "final_objective_evidence_v42" / "PSA_FINAL_OBJECTIVE_EVIDENCE_V42.json"
OUT = RESULTS / "spt_full_manuscript_v1"
MD_OUT = OUT / "SPT_FULL_MANUSCRIPT_DRAFT.md"
DOCX_OUT = OUT / "SPT_FULL_MANUSCRIPT_DRAFT.docx"
MANIFEST_OUT = OUT / "MANIFEST_SHA256.json"
REFERENCE_AUDIT_OUT = OUT / "REFERENCE_METADATA_AUDIT.json"
PUBLIC_EVIDENCE_FIGURE = RESULTS / "membrane_public_evidence_audit_v2" / "Fig_membrane_public_evidence_audit_v2.png"
SYNGAS_GUARD_DIR = RESULTS / "pd_actual_syngas_poisoning_guard_v1"
SYNGAS_GUARD_JSON = SYNGAS_GUARD_DIR / "PSA_PD_ACTUAL_SYNGAS_POISONING_GUARD_V1.json"
SYNGAS_GUARD_FIGURE = SYNGAS_GUARD_DIR / "Fig_pd_actual_syngas_poisoning_guard_v1.png"
RK4_DIR = RESULTS / "independent_rk4_membrane_crosscheck_v1"
RK4_JSON = RK4_DIR / "PSA_INDEPENDENT_RK4_MEMBRANE_CROSSCHECK_V1.json"
RK4_FIGURE = RK4_DIR / "Fig_independent_rk4_membrane_crosscheck_v1.png"
VERVERS_DIR = RESULTS / "ververs_2024_mass_transfer_validation_v1"
VERVERS_JSON = VERVERS_DIR / "PSA_VERVERS_2024_MASS_TRANSFER_VALIDATION_V1.json"
VERVERS_FIGURE = VERVERS_DIR / "Fig_ververs_2024_mass_transfer_validation_v1.png"
HIGH_TEMP_DIR = PROJECT / "07_DWSIM_Aspen_재현" / "results" / "psa_stage_train_high_temperature_audit"
HIGH_TEMP_JSON = HIGH_TEMP_DIR / "PSA_STAGE_TRAIN_HIGH_TEMPERATURE_AUDIT.json"
HIGH_TEMP_FIGURE = HIGH_TEMP_DIR / "Fig_stage_train_high_temperature_audit.png"
SELECTIVITY_DIR = RESULTS / "public_selectivity_acceptance_audit_v1"
SELECTIVITY_JSON = SELECTIVITY_DIR / "PSA_PUBLIC_SELECTIVITY_ACCEPTANCE_AUDIT_V1.json"
SELECTIVITY_FIGURE = SELECTIVITY_DIR / "Fig_public_selectivity_acceptance_audit_v1.png"
SANCHEZ_DIR = RESULTS / "sanchez_2014_validation_audit_v1"
SANCHEZ_JSON = SANCHEZ_DIR / "PSA_SANCHEZ_2014_VALIDATION_AUDIT_V1.json"
SANCHEZ_FIGURE = SANCHEZ_DIR / "Fig_sanchez_detection_resolution_v1.png"
DOE_PALL_DIR = RESULTS / "doe_pall_2008_mixed_gas_validation_v1"
DOE_PALL_JSON = DOE_PALL_DIR / "PSA_DOE_PALL_2008_MIXED_GAS_VALIDATION_V1.json"
DOE_PALL_FIGURE = DOE_PALL_DIR / "Fig_doe_pall_2008_mixed_gas_validation_v1.png"
UTRC_DIR = RESULTS / "utrc_2012_high_recovery_validation_v1"
UTRC_JSON = UTRC_DIR / "PSA_UTRC_2012_HIGH_RECOVERY_VALIDATION_V1.json"
UTRC_FIGURE = UTRC_DIR / "Fig_utrc_2012_high_recovery_validation_v1.png"
BANG_DIR = RESULTS / "bang_2021_joint_gate_validation_v1"
BANG_JSON = BANG_DIR / "PSA_BANG_2021_JOINT_GATE_VALIDATION_V1.json"
BANG_FIGURE = BANG_DIR / "Fig_bang_2021_joint_gate_validation_v1.png"
CSHARP_DIR = RESULTS / "csharp_direct_transport_crosscheck_v1"
CSHARP_JSON = CSHARP_DIR / "PSA_CSHARP_DIRECT_TRANSPORT_CROSSCHECK_V1.json"
CSHARP_FIGURE = CSHARP_DIR / "Fig_csharp_direct_transport_crosscheck_v1.png"
DATA_AVAILABILITY = (
    "The complete calculation records, direct states, circuit files, DWSIM flowsheets, figures, tables, "
    "and SHA-256 manifests are organized in the project reproducibility package. A permanent repository "
    "DOI will be added before submission."
)


TITLE = (
    "Regeneration reserve aware hydrogen pressure swing adsorption under uncertainty "
    "with staged membrane polishing and a quantum ready probability oracle"
)

AUTHORS = [
    "Ugwiyeon Lee*", "Seong-Yun Bae", "Hakrae Kim", "Jungsu Lee"
]
AFFILIATION = (
    "Korea Gas Safety Corporation, 1390 Wonjung-ro, Maengdong-myeon, "
    "Eumseong-gun, Chungcheongbuk-do 27738, Republic of Korea"
)


ABSTRACT = (
    "Hydrogen pressure swing adsorption is commonly optimized by purity and recovery, but a cyclic plant must also retain "
    "enough product gas to purge and repressurize its adsorbers. Treating this regeneration inventory as an infinite boundary "
    "can overstate the gas available for sale. This work formulates a four-bed hydrogen PSA as a continuous qualified-shipment "
    "problem in which product gas first satisfies simultaneous purge and repressurization demand, then refills a finite "
    "pressure-regulated tank, and only the remaining overflow reaches a polymer concentration stage and dense-palladium "
    "polisher. Feed hydrogen, joint adsorption equilibrium, and linear-driving-force kinetics were varied over a declared "
    "engineering cube. A policy with a 7.0 bar tank set point, 4 s active purge, and 540 s adsorption stage passed all eight "
    "uncertainty corners, whereas the comparison policy passed none, while increasing specification-qualified shipment by "
    "6.80-7.36%. Eight predeclared interior cases also passed. A hold-out-error-buffered continuous uncertainty integration "
    "identified a 95% chance design and was converted into a reversible probability event for quantum amplitude estimation. "
    "For the final physical train, adaptive continuous-area integration corrected a near-boundary numerical bias: a preliminary "
    "0.553 m2 palladium guard passed 15 of 16 direct cases, whereas 0.554 m2 passed all 16 at 20% permeance loss. A separate "
    "public actual-syngas stress range of 40-50% permeance loss increased the conditional installed area to 0.739-0.887 m2, "
    "with all 16 cases retained. A separately coded fixed-area RK4 solver reproduced all 32 design-case decisions from the "
    "adaptive calculation. A third implementation in compiled C# then read all 61,440 blind time packets, received no membrane "
    "split fractions, and again preserved all 32 decisions; its maximum horizon hydrogen-flow difference was 2.95e-7 relative. "
    "Without refitting mixture-flux data, an independent reconstruction of a published local-Sherwood "
    "film model reproduced 468 public H2/N2 flux records with 4.41% mean absolute relative error and R2=0.9966; omitting "
    "concentration polarization increased the error to 29.02%. The limiting "
    "hydrogen recovery was 88.3217%, and maximum CO, CO2, N2, and CH4 concentrations were 0.121, 3.998, 51.643, and 25.153 ppm. "
    "A Peng-Robinson DWSIM reconstruction then solved both installed-area tiers in all 32 horizon-averaged cases with an explicit "
    "420 C palladium stage. Three-stage intercooled compression required 2.784-2.877 kWh per kg hydrogen; after an 80% sensible-heat "
    "recovery credit, palladium heating added 0.367-0.385 kWh per kg. Applying a published 22-bar inhibition regression without "
    "refitting gave a conservative 97.10% minimum permeance retention and a required area of 0.456 m2, below both installed guards. "
    "Component-wise adaptive bisection then converted public selectivity data into a rounded incoming-module acceptance rule: "
    "effective H2/CO, H2/CO2, H2/N2, and H2/CH4 selectivities must be at least 5,310, 158,110, 540, and 40. "
    "An independent DOE/UTRC Pd-Cu test sustained 93.4% mean recovery for about 1,300 h on simulated syngas and reported "
    "99.9999% pre-leak bulk purity; an actual coal-gas test gave 74.3% recovery versus a 70.1% frozen-model prediction. "
    "A published integrated Pd-Cu reactor and four-bed PSA study then bracketed the present joint event: its 91.37% "
    "recovery point contained 8.67 ppm CO, whereas its 0.15 ppm CO point recovered 85.99% H2. "
    "The compact 10-bit event oracle used 66 logical qubits and 17,690 CX gates. The present probability "
    "model remains cheaper with randomized quasi-Monte Carlo; the quantum result is a verified process-to-oracle construction "
    "for future higher-dimensional uncertainty rather than a claim of current computational advantage."
)

KEYWORDS = [
    "Hydrogen purification",
    "Pressure swing adsorption",
    "Regeneration tank",
    "Membrane polishing",
    "Chance constraint",
]

HIGHLIGHTS = [
    "Finite regeneration inventory changes saleable hydrogen and feasible operation",
    "The selected PSA policy passes all eight uncertainty corners",
    "Actual-syngas permeance loss expands the conditional Pd guard to 0.887 m2",
    "A 1,300 h DOE/UTRC test supplies a positive high-recovery validation anchor",
    "Published CMR-PSA operating points bracket the joint CO-recovery target",
    "A blind 61,440-packet C# transport replay preserves all 32 decisions",
    "Component-resolved selectivity thresholds define an incoming Pd-module test",
    "A 66-qubit reversible event connects the process probability to QAE",
]


SECTIONS: list[tuple[str, list[str]]] = [
    (
        "1 Introduction",
        [
            "High-purity hydrogen is required by chemical, metallurgical, energy-storage, and fuel-cell systems. Pressure swing adsorption (PSA) is attractive because selective adsorption and pressure cycling can remove carbon dioxide, methane, carbon monoxide, and nitrogen without a continuously regenerated solvent. The industrial design problem is nevertheless more complicated than maximizing purity or recovery at one outlet. Product hydrogen also performs internal work: it purges low-pressure beds, repressurizes beds before adsorption, and maintains a product or equalization inventory that couples one bed to the others. If this inventory is represented as an unlimited source, a simulated cycle can sell gas that the real plant must retain for its next cycle.",
            "Dynamic PSA optimization has addressed cycle scheduling, adsorbent selection, control, and uncertainty [1-8]. These studies establish that pressure equalization, purge, adsorption duration, valve conductance, and feed composition interact strongly. They also show why cyclic steady state, component conservation, and direct validation matter. However, regeneration demand is often embedded in boundary conditions or reported separately from the product available for shipment. For variable feed and aging adsorbent, the practical question is therefore not simply which cycle gives the highest hydrogen recovery. It is which continuous operating policy preserves regeneration inventory and simultaneously maximizes hydrogen that satisfies a strict product specification.",
            "A second difficulty appears when the PSA outlet is close to, but does not by itself meet, a multi-impurity hydrogen specification. A membrane polishing stage can increase purity, yet a single membrane must trade recovery against contaminant rejection. Published pilot and staged studies support palladium-alloy durability and the value of pre-concentration, but they do not jointly report all impurity limits used here [9-13]. A defensible model must therefore expose permeance loss, finite selectivity, receiver dynamics, and defect leakage as acceptance conditions instead of assigning a perfect final purity.",
            "Uncertainty adds a third layer. A robust design that passes every bounded case can be larger than necessary, whereas a chance-constrained design accepts a declared small failure region. Estimating that probability links separation engineering to Monte Carlo, randomized quasi-Monte Carlo (RQMC), and quantum amplitude estimation (QAE). QAE can offer a quadratic query advantage for idealized amplitude access [14-17], but state preparation, reversible process arithmetic, and model error can remove that advantage. A process application is useful only when the probability event preserves the engineering decision and its circuit cost is reported.",
            "This study combines these three layers in one evidence chain. First, a staggered four-bed PSA is connected to finite purge, repressurization, and regeneration-tank inventories. Second, a polymer concentrator, dense-palladium polisher, and finite product receiver are resolved along every saved dynamic trajectory. Third, a buffered chance event is compared with classical estimators and compiled as a reversible QAE oracle. The workflow is checked against a public four-bed hydrogen VPSA experiment [8], 468 public Pd-Ag H2/N2 flux records [22], a 22-bar palladium inhibition study [23], a 26-bar multicomponent palladium-alloy endurance study [24], a 20-35 bar five-component WGS membrane campaign [25], supported-Pd defect-leakage measurements [26], a bench-scale unconverted-shift-gas Pd separation test [27], a synchronized DOE/Pall wet mixed-gas test [28], a DOE/UTRC pilot-scale Pd-Cu durability and actual coal-gas campaign [29], and an integrated Pd-Cu catalytic-membrane-reactor/four-bed-PSA experiment that reports both high-recovery and low-CO operating points [30], together with adaptive DOP853, separately coded Python RK4, a blind packetwise C# RK4 replay, and DWSIM checks. The contribution is an engineering operating rule and its verified probability event; no present quantum advantage or direct experimental certification of the final integrated apparatus is claimed.",
        ],
    ),
    (
        "2 Problem definition",
        [
            "The process boundary begins at a multicomponent hydrogen-rich PSA feed and ends at a finite product receiver. Four adsorbers operate on a staggered schedule so that adsorption, pressure equalization, blowdown, purge, and repressurization overlap. High-pressure product is allocated in a fixed physical order. Simultaneous purge and repressurization demand is supplied first. The remaining gas refills a pressure-regulated regeneration tank. Only manifold overflow beyond this internal demand can enter the polishing train and become saleable product.",
            "The engineering objective is the time-averaged molar flow of qualified hydrogen delivered from the receiver. A packet contributes to this objective only while every condition is satisfied: hydrogen mole fraction is at least 0.9997; CO, CO2, N2, and CH4 are no greater than 0.5, 5, 300, and 100 ppm; overall hydrogen recovery is at least 0.882940; qualified hydrogen flow is at least 0.0022631 mol s-1; the regeneration tank remains above its reserve threshold; the surge buffer and product receiver remain within capacity; the cyclic state is converged; and mass-balance and numerical gates pass. This event definition prevents high flow outside specification from being counted as production.",
            "The main operating variables are regeneration-tank set point, active purge duration, and adsorption-stage duration. The comparison policy uses 6.6 bar, 6 s, and 480 s. The selected policy uses 7.0 bar, 4 s, and 540 s. Physical polishing decisions include polymer membrane area, installed dense-palladium area, surge capacity, and receiver capacity. The uncertainty coordinates are a feed-hydrogen multiplier from 0.95 to 1.05, a joint adsorption-equilibrium coordinate drawn from literature-bounded capacity-affinity pairs, and an LDF kinetic multiplier from 0.8 to 1.2. The eight combinations of the coordinate endpoints form the complete engineering cube. Eight additional interior coordinates were fixed before validation.",
            "Two design meanings are kept separate. A fully robust design passes every declared direct case. A 95% chance design passes under an independent uniform engineering measure over the declared cube after shifting the event boundary by the largest error on the predeclared interiors. This measure is a transparent design convention; it is not presented as a plant-calibrated probability distribution.",
        ],
    ),
    (
        "3 Methods",
        [
            "3.1 Dynamic PSA tank valve and bed model",
            "Each bed is discretized axially and advanced through the staggered cycle with component gas inventories, competitive adsorption equilibrium, LDF uptake, valve-driven inter-bed and boundary flows, and a non-isothermal energy balance. Product, exhaust, purge, repressurization, and equalization streams are integrated explicitly. The tank state follows its component inventory and ideal-gas pressure; withdrawal is limited by available inventory and the pressure-regulated demand. The selected direct calculations use six axial cells and 60 cycles. A run is accepted only after cyclic-state, trace-integrity, and component-balance checks pass. Mesh and longer-horizon calculations are used as numerical controls rather than as calibration data.",
            "The source model was separately reconstructed for the public Wang et al. four-bed, 12-step H2/CH4/N2/CO2 VPSA apparatus [8]. Published geometry, activated-carbon equilibrium, partial-pressure LDF kinetics, heat effects, step schedule, and experimental breakthrough and pressure data were used. This cross-validation tests reusable conservation, pressure-network, adsorption, and thermal implementations. Because the final process uses a different adsorbent, pressure range, and downstream membrane, it does not directly validate the final apparatus.",
            "3.2 Polishing train and finite receivers",
            "The PSA overflow is first compressed from 8 to 20 bar and cooled to 298.15 K. A polymer membrane operates with 20 bar feed and 1 bar permeate to raise the hydrogen fraction before the dense-palladium stage. The polymer permeate is recompressed in three equal-pressure-ratio stages with intercooling to 298.15 K. A recuperative heater then raises the palladium feed to 693.15 K (420 C), and the dense-palladium stage operates at 20/1 bar. Both hot outlet streams are cooled to 298.15 K. The energy audit credits 80% of their combined recoverable sensible duty against the palladium-feed heater. Retentates are assigned to fuel or off-gas, so no internal recycle is credited. A 5.721 L surge buffer at 20 bar decouples the cyclic PSA packets from the polishing stages.",
            "Membrane transfer is evaluated packet by packet over membrane area. The production model originally used fixed equal-area Euler sections. The independent numerical audit integrates the same transfer laws as a continuous-area ordinary differential equation using scipy solve_ivp with DOP853, relative tolerance 1e-9, and absolute tolerance 1e-13 [18]. The limiting case is replayed at 1e-10 and 1e-14. The audit covers all 1,920 packets in every direct case and retains exact component ledgers across both membranes and the product receiver.",
            "The dense-palladium acceptance calculation imposes 20% hydrogen-permeance loss, finite effective H2/impurity selectivities, and an H2-equivalent Knudsen defect-conductance ratio. This ratio is a local conductance ratio relative to dense-palladium hydrogen transfer, not a geometric pinhole-area fraction. The receiver is sized from the packet-level inventory swing with a fixed heel; continuous product quality is checked at every integration step.",
            "3.3 Robust and chance-constrained calculations",
            "The comparison and selected policies are paired at all eight uncertainty corners. Direct results provide regeneration reserve, qualified shipment, recovery, receiver behavior, and numerical diagnostics. A trilinear response is exact at the corners and is tested at the eight predeclared interiors. For the chance calculation, the joint event margin is shifted conservatively by the maximum absolute interior error. Eight independent scrambled Sobol integrations are then used to estimate probability [19]. The selected design must exceed 0.95 in the least favorable scramble. Crude Monte Carlo and RQMC use identical event calls and sample budgets.",
            "3.4 Process probability oracle",
            "For the quantum bridge, installed dense-palladium area is the physical design coordinate. At 0.440 m2, the chance event is nontrivial: 13 of 16 direct stress points pass, while continuous probability exceeds the 0.95 target. A conservative affine event is fitted to the buffered trilinear boundary and checked for false-positive and false-negative labels on all direct cases. Each of three uncertainty coordinates is digitized with 10 qubits. Reversible signed accumulation and comparison mark the pass amplitude. Reported resources cover this event oracle only; QAE reflections, routing, error correction, noise mitigation, and readout are excluded.",
            "3.5 Independent thermodynamic and numerical checks",
            "The horizon-averaged stage train is reconstructed in DWSIM 8.7.1 using the Peng-Robinson property package [20]. Component separators receive the packet-model split fractions, while DWSIM independently determines pressure states, adiabatic compressor work, cooler duties, temperatures, and material closure. A single 1-to-20 bar recompression step was rejected after producing discharge temperatures above 830 K; the accepted design uses three intercooled stages. This check is independent for thermodynamics and equipment staging but not for membrane transport.",
            "A second membrane implementation was written without calling the adaptive solver. It integrates the same frozen polymer solution-diffusion and finite-selectivity palladium equations with classical fourth-order Runge-Kutta steps over 48, 96, and 192 equal-area sections per membrane. The independent bisection closure for polymer permeate composition and all component ledgers are evaluated for both final palladium designs and all 16 direct cases. This test isolates numerical-method and implementation sensitivity; because the constitutive laws are unchanged, it is not an independent physical validation.",
            "A separate external-data calculation reconstructs the Ververs et al. tubular Pd-Ag experiment [22]. The implementation uses their axial H2 and N2 balances, Richardson parameters for 0.150, 0.300, and 0.467 m membranes, stagnant-film equation, 64 mm annular hydraulic diameter, and local correlation Sh=1.846Gz^0.60. H2-N2 diffusivity is calculated independently with the Fuller correlation, and 96, 192, and 384-section RK4 meshes are compared. No mixture-flux parameter is fitted. The downloaded workbook contains 468 numeric records, 45 more than the 423 stated in the article; all public records are retained without undocumented filtering.",
            "3.6 High-pressure inhibition transfer and hot-stage audit",
            "Boon et al. reported 105 randomized inhibition tests at 22 bar retentate pressure, 2 bar permeate pressure, 350-450 C, 50-70% H2, and up to 2% CO [23]. Their published linear regression, eta=1-KCO<pCO>-KH2O<pH2O>, is applied without refitting. Because the present design feed is dry, the steam term is set to zero. The arithmetic uses the average CO partial pressure between each palladium feed and retentate and evaluates both the central 420 C coefficient and its upper 95% uncertainty limit. This transfer tests whether the installed-area guards cover measured high-pressure inhibition; it does not validate impurity leakage.",
            "The complete hot-stage DWSIM audit covers both the 0.554 m2, 80%-retention tier and the 0.887 m2, 50%-retention tier at all eight uncertainty corners and eight hold-outs, for 32 cases. Peng-Robinson calculations independently determine the three-stage recompression work, 420 C heater duty, outlet cooler duties, pressure states, and component closure. Membrane splits remain inputs from the packet model. The 26-bar, 400 C, five-component Pd-Ag test of Peters et al. is used as a separate high-pressure feasibility anchor because it reported 500 h without membrane failure [24]; its different membrane and wet feed preclude direct validation.",
            "3.7 Public selectivity transfer and module acceptance threshold",
            "The conservative 0.887 m2 design is replayed while the effective H2 selectivity against one impurity is reduced and the other three are held at their selected values. Logarithmic bisection finds the lowest selectivity that preserves all 16 direct uncertainty and hold-out events. A 25% margin is then imposed on each component simultaneously and rounded upward to form an incoming-module acceptance rule. Li et al. provide a 673 K, 20-35 bara, five-component WGS-mixture campaign on a 580.6 cm2 multitubular Pd module [25]. Its reported H2 and N2 permeances are transferred only as H2/N2 selectivity stresses because the permeate used an intentional N2 sweep. The DOE/MPT supported-Pd measurements at 400 C provide measured H2/CO, H2/CO2, and H2/N2 defect-leakage selectivities of approximately 68-116 [26]. These are used as rejection stresses, not as matched product validation.",
            "3.8 Independent full-syngas bench evidence and analytical-resolution audit",
            "Sanchez et al. tested a 0.01216 m2 precommercial Pd membrane in a bench facility with feed, retentate, and permeate slipstreams analysed by gas chromatography [27]. Their synthetic unconverted-shift gas contained 17% H2, 19% CO, 7% CO2, and 57% steam and was tested at 593-723 K and 0.15-1.0 MPa. Reported TCD accuracy was 0.01 vol% (about 100 ppm). The present audit therefore uses the experiment as a multicomponent feasibility, inhibition-direction, permeance, and recovery anchor, but does not translate the paper's 'pure hydrogen' wording into certification of the present 0.5 ppm CO or 5 ppm CO2 limits.",
            "3.9 Synchronized mixed-gas rejection control",
            "The DOE/Pall FY 2008 report provides feed, retentate, and permeate flow and composition for a Pd90Au10 membrane at 400 C, 62 psia feed, 12 psia permeate, and 50 psi pressure difference [28]. The feed contained 51% H2, 26% CO2, 21% steam, and 2% CO. The observed permeate contained 99.95% H2, 450 ppm CO2, and 75 ppm CO. H2 recovery is calculated directly as 775/1020=75.98%. System-level H2/CO and H2/CO2 separation factors are calculated from the reported feed and permeate mole fractions and transferred to the 0.887 m2 design while N2 and CH4 remain at their selected values. Because the factors include wet-mixture, support, film, and defect effects, this is an empirical rejection stress rather than an intrinsic-permeability fit.",
            "3.10 Positive high-recovery and actual coal-gas validation anchors",
            "The DOE/UTRC final report describes a pilot-scale approximately 0.139 m2 Pd-Cu separator [29]. Its durability feed contained 75% H2, 1% CO, 5% CO2, 19% H2O, and 1.65 ppmv H2S. At 500.8 +/- 10.6 C and 184.7 +/- 7.8 psig, the separator produced 2.36 +/- 0.20 lb day-1 H2 at 93.4 +/- 8.0% recovery for about 1,300 h. Before a small leak began at 2,624 h, the report assigned 99.9999% H2 purity from the ideal H2/N2 separation factor; this corresponds to about 1 ppm total non-H2 but is not component-resolved analysis. A separate 77 h actual coal-gas test measured 2.43 lb day-1 and 74.3% recovery, compared with frozen-model predictions of 2.32 lb day-1 and 70.1%. These records are used as positive recovery, bulk-purity, durability, and model-transfer anchors. They are not treated as direct certification of the final 20-bar five-component product.",
            "3.11 Integrated CMR-PSA joint-gate bracket",
            "Bang et al. integrated a Pd-Cu water-gas-shift catalytic membrane reactor with activated-carbon/zeolite four-bed PSA [30]. The CMR was experimentally operated with a CO/H2/CO2 feed of 65:30:5 vol%, steam/carbon ratios of 1-5, 360-380 C, 6-10 bar, and H2 sweep. The public record used here does not establish the complete four-bed PSA output as an independently measured dataset, so the two overall results are treated as published integrated-process operating points. The high-recovery point gave 91.37% H2 recovery, more than 99.9991% H2, and 8.67 ppm CO. The low-CO point gave 85.99% recovery and 0.15 ppm CO. Each point is compared separately with the frozen 88.294% recovery floor and 0.5 ppm CO limit. This creates a literature bracket of the conjunction used by the process oracle; it is not a fit to the present model or direct validation of the final apparatus.",
            "3.12 Blind third-language membrane-transport replay",
            "A standalone C# implementation received all 61,440 time-packet feed rows but no polymer or palladium split fractions and no expected product columns. It independently integrated the same frozen solution-diffusion and finite-selectivity Sieverts-law equations with 48 fixed-area RK4 sections per stage and a 32-iteration polymer permeate-composition closure. The resulting packetwise products were passed through the frozen receiver and event calculation and compared with the adaptive DOP853 results. This test separates language, code structure, mesh, and integrator implementation; it does not provide an independent constitutive model or experimental measurement.",
        ],
    ),
    (
        "4 Results",
        [
            "4.1 Regeneration reserve changes the operating decision",
            "At the 2,000 cm2 single-stage-equivalent robust reference, the comparison policy failed the joint event at all eight uncertainty corners. The selected 7.0 bar, 4 s, 540 s policy passed all eight. Qualified hydrogen shipment increased by 6.802-7.356%, and the minimum regeneration-tank pressure increased by at least 0.9944 bar. The largest final cyclic-state residual was 1.225e-5 and the largest relative cycle mass-balance error was 1.661e-5. The improvement arises from protecting tank inventory and reducing the duration of active purge while allowing more net production time, rather than from relaxing product quality.",
            "4.2 Direct hold-out and continuous chance design",
            "All eight predeclared interior conditions passed in the direct six-cell, 60-cycle model. The trilinear event reproduced all corner and interior labels. At the 2,214 cm2 single-stage-equivalent coordinate, nominal probability was 0.989932. After the maximum hold-out-error shift, the mean probability over eight 2^20-point scrambled-Sobol integrations was 0.950349 and the minimum was 0.950334. This coordinate remains a probability-model development variable and is not interpreted as an installed physical module area.",
            "4.3 Public dynamic experiment checks transferable model physics",
            "The source-specific Wang reconstruction reproduced multicomponent half-feed breakthrough times with a maximum absolute relative error of 11.37%, composition curves with a maximum species RMSE of 0.0229 mole fraction, and temperature traces with a maximum sensor RMSE of 2.37 C. Four cyclic pressure levels had an RMSE of 0.0666 bar. At engineering cyclic steady state, Run XII recovery differed from experiment by -0.666 percentage point, whereas eight-cell purity was underpredicted by 2.037 percentage points. The comparison supports the model family and its ledgers while preserving a clear apparatus-transfer boundary.",
            "4.4 Staging is required to meet the joint separation target",
            "Direct membrane evidence shows why a single ideal polisher is not an adequate engineering representation. A 1,050 cm2 multicomponent Pd/Au/Pd pilot achieved 98-99.87% purity and 64% recovery over 840 h [9]. A two-stage Pd-alloy experiment used a 99.99% purity and 80% recovery benchmark [10]. A binary repaired-Pd membrane reached 99.986% purity and 91% recovery [11], but the simple binary feed does not test the present contaminants. Published PSA-plus-membrane and staged concentration-plus-palladium simulations enter the present purity-recovery region [12,13]. More directly, the present polymer area normalizes to 0.513-0.530 m2 per Nm3 h-1 across all 16 cases, only 1.025-1.059 times the Zito 20-bar value of 0.5 m2 per Nm3 h-1 for 90% recovery [13]. The same public table supplies the exact polymer and Pd transport coefficients used here. This quantitative agreement supports parameter traceability and scale plausibility, while the differing feeds and pressures prevent it from serving as final validation.",
            "The ideal literature-bounded stage-resolved train uses a 0.1892 m2 polymer stage and 0.4799 m2 dense-palladium stage. It passes the eight corners and eight predeclared interiors, with minimum recovery 93.460% and minimum qualified flow 0.0024573 mol s-1. The fine-mesh recovery change is 0.094 percentage point, more than 50 times smaller than the remaining recovery margin.",
            "4.5 Adaptive integration corrects the final guard band",
            "The fixed-section calculation suggested that a 0.553 m2 palladium area would cover 20% permeance loss. Adaptive DOP853 integration found polymer-stage hydrogen recovery 0.155-0.175 percentage point lower than the 72-section Euler calculation. Under the independent integrator, the 0.553 m2 guard passed only 15 of 16 direct cases; corner 06 reached recovery 0.881992, below the frozen 0.882940 floor. The minimum unrounded area was 0.553773 m2, so the selected installed guard is 0.554 m2.",
            "The revised design passes all 16 direct cases. Minimum recovery is 0.883217 and minimum qualified hydrogen flow is 0.00236132 mol s-1. The product receiver is 1.222725 mol, equivalent to 30.311 L at 1 bar and 298.15 K. Maximum CO, CO2, N2, and CH4 concentrations are 0.1205, 3.9983, 51.6435, and 25.1526 ppm. Maximum membrane and receiver balance residuals are 4.16e-17 and 1.07e-11 mol. Tight replay changes limiting recovery by only 8.92e-11. The maximum passing H2-equivalent defect-conductance ratio is 3.698e-5; a 20% guard gives 2.958e-5 and also passes all 16 cases.",
            "4.6 DWSIM closes process states and corrects compression duty",
            "All 16 regenerated DWSIM cases solved with no calculation errors. Maximum component closure was 7.32e-19 mol s-1 and maximum difference from the Python product reference was 1.30e-18 mol s-1. Adiabatic compression required 47.894-50.730 W, corresponding to 2.785-2.877 kWh kg-1 qualified H2. This is 15.28-15.36% above the isothermal lower bound. Total cooling duty was 48.052-50.885 W; maximum first-stage and recompression discharge temperatures were 420.49 and 433.64 K.",
            "4.7 The compact QAE event preserves the process decision",
            "At an installed dense-palladium area of 0.440 m2, the validation-error-buffered trilinear probability had a minimum-scramble value of 0.960617. The deliberately conservative affine event had exact probability 0.955711 and no direct-label disagreement at the 16 corners and interiors. Ten-bit digitization gave probability 0.955254, an absolute error of 4.57e-4. The compiled event used 66 logical qubits, depth 29,585, and 17,690 CX gates.",
            "RQMC remains the appropriate estimator for the present three-variable event because the response is smooth and inexpensive. The value of the quantum construction is different: it shows exactly which regeneration, recovery, shipment, and receiver conditions must be mapped into a reversible probability flag. A future application would require more uncertain variables, repeated risk queries, an expensive validated oracle, and a structured state loader before the ideal QAE query scaling could become practically relevant.",
            "4.8 Public actual-syngas aging defines a larger conditional guard",
            "A large-module experiment in actual desulfurized coal-derived syngas reported 99.8-99.9% hydrogen purity but a 40-50% decrease in hydrogen permeance; Pd-Au selectivity remained stable for more than 473 h [21]. Applying that public degradation range as a stress condition, rather than as matched validation, increased the required installed Pd area to 0.739 m2 at 60% retention and 0.887 m2 at 50% retention. Both designs passed all 16 direct uncertainty and hold-out cases under the adaptive finite-selectivity model. The conservative 0.887 m2 design is 60.1% larger than the 0.554 m2 20%-loss guard and gives minimum overall hydrogen recovery of 88.3676%, a 30.371 L receiver, and maximum CO, CO2, N2, and CH4 concentrations of 0.1207, 4.0027, 51.7667, and 25.1816 ppm. This calculation converts published aging evidence into a testable installed-area rule while retaining the apparatus-transfer boundary.",
            "4.9 A separately coded RK4 solver preserves both design decisions",
            "At 192 equal-area sections per membrane, the fixed-grid RK4 calculation passed all 16 cases for the 0.554 m2, 80%-retention design and all 16 cases for the 0.887 m2, 50%-retention design. All 32 event labels matched the adaptive DOP853 calculation. The maximum recovery difference was 8.83e-8 percentage point, maximum hydrogen-flow relative difference was 9.54e-10, maximum horizon impurity difference was 3.85e-7 ppm, and maximum component-balance residual was 4.25e-17 mol. Refinement from 48 to 96 sections reduced the maximum component difference against the 192-section result from about 2.03e-6 to 1.16e-7. The pass therefore survives a distinct integration method and an explicit area-mesh sequence.",
            "4.10 Public flux data validate the concentration-polarization model form",
            "The independently implemented Ververs model reproduced all 468 numeric H2/N2 records in the public workbook without fitting mixture-flux data. Including the published local Sherwood correlation gave 4.405% mean absolute relative error, 3.144% median absolute relative error, R2=0.9966, and 92.52% of predictions within 10% of experiment. The 192-section result differed from the 384-section result by at most 0.00577%. When concentration polarization was omitted while axial depletion and the same Richardson parameters were retained, mean absolute relative error increased to 29.016%, R2 decreased to 0.8481, and only 9.62% of predictions remained within 10%. The local film model predicted a median 19.94% flux penalty. This public raw-data reproduction independently verifies the need for concentration-polarization physics; its binary 2-5 bar, 350-450 C apparatus does not certify the present five-component 20-bar polisher.",
            "4.11 Explicit high-temperature palladium operation remains feasible",
            "All 32 hot-stage DWSIM cases solved for the two installed-area tiers. Maximum component-balance error was 8.67e-19 mol s-1 and maximum product-reference difference was 1.73e-18 mol s-1. Gross heating from 298.15 to 693.15 K required 31.54-33.93 W. The two hot outlet streams contained 31.56-33.95 W of recoverable sensible duty; with the declared 80% recovery credit, external palladium heating fell to 6.31-6.79 W, or 0.367-0.385 kWh kg-1 H2. Three-stage compression plus this external heat equivalent was 3.151-3.261 kWh kg-1 H2.",
            "The project cases had average palladium-stage CO partial pressures of 2.760-4.033 kPa and feed H2 partial pressures of 18.59-18.77 bar. Applying the published 22-bar inhibition equation at 420 C with the upper 95% CO coefficient gave a minimum permeance retention of 0.97097 and required 0.4563 m2. The installed 0.554 and 0.887 m2 guards therefore retain 21.4% and 94.4% area margin, respectively. Even the upper 95% coefficient reported at 357 C gave 0.93064 minimum retention. The result shows that the declared 20% and 50% permeance-loss stresses are more severe than this near-pressure CO-inhibition transfer predicts. Because the source membrane was pure Pd, included steam, and operated at lower H2 partial pressure, this is a conservative sizing support rather than matched five-component validation.",
            "4.12 Public selectivity data define an incoming-module acceptance rule",
            "For the 0.887 m2, 50%-retention design, the component-specific minimum effective H2/CO, H2/CO2, H2/N2, and H2/CH4 selectivities were 4,245.1, 126,482.2, 424.9, and 24.86. Imposing a 25% margin on all four simultaneously and rounding upward gives an incoming-module requirement of 5,310, 158,110, 540, and 40. This rounded vector passed all 16 direct cases; maximum CO, CO2, N2, and CH4 concentrations were 0.3997, 3.9991, 223.64, and 63.34 ppm. The Li end-of-test H2/N2 transfer of 307.7 passed only 1/16 cases and reached 391.7 ppm N2, whereas its recovered-permeance value of 461.5 passed 16/16 with 261.5 ppm N2 when the other three selectivities were retained. The DOE/MPT vectors near 70-116 passed 0/16 and produced 5,440-6,530 ppm CO2. The adverse public cases demonstrate that increasing Pd area cannot substitute for a leak-tight component-selectivity specification.",
            "4.13 Full-syngas bench evidence has an analytical boundary",
            "The Sanchez membrane produced a hydrogen-only permeate by the reported GC analysis under the full unconverted-shift-gas mixture, and maximum hydrogen recovery was about 47% at 723 K and 1 MPa [27]. The same study reported a pure-H2 permeance of 2.8 m3 m-2 h-1 kPa-0.5, pure-N2 or pure-CO2 permeate below 8 mL min-1 at 1 MPa, and no measured CO or steam in the permeate during binary and ternary tests. This is independent evidence that hot multicomponent Pd separation, reversible co-component inhibition, and nonzero recovery are physically credible. Its 100 ppm TCD accuracy is 200 times the project CO limit and 20 times the CO2 limit; the source therefore cannot validate the final component-selectivity vector or product gate. It closes a model-trend gap while leaving the matched analytical-validation gate explicit.",
            "4.14 A synchronized public experiment fails the strict gate",
            "The DOE/Pall flow ledger gives 75.98% H2 recovery, 75 ppm CO, and 450 ppm CO2 [28]. These values are 13.15 percentage points below the project recovery floor and 150 and 90 times the respective impurity limits. The corresponding system-level H2/CO and H2/CO2 separation factors are 522.6 and 1,132.3, compared with incoming-module guards of 5,310 and 158,110. When those two observed factors are transferred into the 0.887 m2, 50%-retention train, all 16 direct cases fail: maximum CO and CO2 become 4.054 and 558.21 ppm. Recovery remains above the project floor in the transfer calculation, showing that the rejection is caused by measured impurity leakage rather than by membrane area or hydrogen throughput. The experiment therefore supplies a synchronized empirical negative control for the acceptance rule.",
            "4.15 DOE/UTRC supplies a positive high-recovery validation anchor",
            "The DOE/UTRC simulated-syngas durability mean of 93.4% recovery is 5.11 percentage points above the present 88.294% recovery floor [29]. The one-standard-deviation lower value is 85.4%, so the record supports target feasibility without proving a deterministic pass at every reported fluctuation. The pre-leak calculated purity of 99.9999% corresponds to approximately 1 ppm total non-H2, compared with the present 300 ppm bulk ceiling implied by 99.97% H2. After a small leak developed, the reported purity fell to about 99.98%, or 200 ppm total impurity, demonstrating how bulk purity can remain apparently acceptable while component-specific limits remain unknown. In the independent actual coal-gas run, the frozen model underpredicted product rate by 4.53% and recovery by 4.2 percentage points. Together these results add the positive side of the validation hierarchy: high recovery and bulk purity are physically achievable in a durable multicomponent Pd-Cu separator, and a physics model predicts actual-gas performance to engineering accuracy. Because the report does not resolve CO, CO2, N2, and CH4 in the permeate at the present limits, the component-specific acceptance gate remains open.",
            "4.16 Published integrated operating points bracket the joint CO-recovery gate",
            "Neither of the two reported Bang operating points satisfies the present joint event [30]. The 91.37% recovery point exceeds the project recovery floor by 3.076 percentage points but its 8.67 ppm CO is 17.34 times the 0.5 ppm limit. The 0.15 ppm CO point uses only 30% of the CO allowance but its 85.99% recovery is 2.304 percentage points below the floor. By comparison, the present conservative 0.887 m2 model has a worst-case pair of 88.3676% recovery and 0.1207 ppm CO, giving margins of only 0.0736 percentage point and 0.3793 ppm. The published pair therefore demonstrates the engineering conflict that motivates a joint event rather than separate purity and recovery summaries. It also makes the present claim falsifiable: a matched experiment must enter the upper-left pass region instead of reproducing either side of the observed tradeoff. Because the source used a reacting CMR, H2 sweep, and no N2 or CH4 in the reported feed, it does not certify the final five-component product.",
            "4.17 Third-language packetwise transport preserves every decision",
            "The compiled C# replay processed all 61,440 blind packets and passed all 32 design-case pairs. Every event label agreed with adaptive DOP853. The maximum horizon hydrogen-flow difference was 2.95e-7 relative, the maximum recovery difference was 2.73e-5 percentage point, and the largest horizon and receiver impurity differences were 1.14e-4 and 1.52e-4 ppm, respectively. Maximum component-balance residual was 5.55e-17 mol. These errors are far below the preregistered numerical thresholds and do not alter the thin recovery boundary of the 0.887 m2 design. The result strengthens numerical reproducibility because the C# calculation receives raw time packets rather than Python-generated membrane splits, while leaving the experimental and licensed-Aspen validation boundaries unchanged.",
        ],
    ),
    (
        "5 Discussion",
        [
            "5.1 Engineering meaning of the selected policy",
            "The principal result is a material-allocation rule. Product hydrogen is not immediately revenue gas. It first guarantees the next cycle by supplying purge and repressurization and by restoring a finite tank. This ordering explains why the selected policy can increase both reserve pressure and saleable qualified flow. The higher tank set point creates inventory margin, the shorter active purge limits internal consumption, and the longer adsorption stage increases productive time. Because all flows are counted in one component ledger, the gain cannot be produced by borrowing unrecorded makeup hydrogen.",
            "The robust and chance designs answer different questions. The 0.4799 m2 ideal palladium stage passes every direct case inside the literature-bounded transport model. The 0.440 m2 chance design accepts a thin low-performance region but exceeds 95% under the declared continuous measure. The 0.554 m2 guard asks whether the robust train survives 20% palladium permeance loss, finite impurity leakage, numerical integration correction, and receiver dynamics. The 0.887 m2 conditional guard asks the more severe question implied by the 50% actual-syngas permeance loss reported in public long-duration testing. These areas are design tiers tied to different evidence and should not be ranked as competing estimates of one unknown optimum.",
            "5.2 Why the independent numerical failure strengthens the design",
            "The difference between 0.553 and 0.554 m2 is small, but the event is close to its recovery boundary. The adaptive integrator exposed a failure that a coarser fixed-section calculation hid. Retaining this adverse result is more informative than reporting only the corrected design: it quantifies the numerical safety margin and shows that mesh error can change a binary engineering decision even when concentration curves appear similar. The tight replay, component ledgers, 32/32 agreement of the separately coded Python RK4 solver, and 32/32 blind packetwise C# agreement establish that the revised pass is not a solver-tolerance, language, or single-implementation artifact.",
            "5.3 Separation journal relevance and experimental boundary",
            "The work contributes a separation-process design rule rather than a new adsorbent or membrane material. Its global relevance is the recurring need to operate cyclic hydrogen purifiers under variable feed and adsorbent degradation while preserving regeneration gas. The public Wang experiment provides source-specific validation of the dynamic adsorption and pressure-network equations. The 468-point Ververs reproduction provides direct external validation of axial depletion and concentration-polarization model form. The 22-bar Boon data support the high-pressure CO-inhibition allowance, while the 26-bar Peters test anchors the feasibility of prolonged hot multicomponent operation. The Li and DOE/MPT transfers add an adverse validation layer: they separate acceptable and rejected membrane selectivity regimes and convert the leakage model into a vendor-testable incoming specification. The Sanchez full-syngas bench test independently supports hot multicomponent separation and recovery behavior, while its 100 ppm analytical accuracy defines why it cannot certify the present CO and CO2 gates. The DOE/Pall synchronized flow ledger provides an empirical rejection control: a 99.95% H2 product that would appear highly pure by bulk composition still fails the present CO, CO2, and recovery requirements. The DOE/UTRC campaign supplies the complementary positive anchors: sustained 93.4% mean recovery and calculated 99.9999% pre-leak bulk purity on simulated syngas, plus a frozen model within 4.53% of actual coal-gas hydrogen production. The Bang integrated CMR-PSA study adds the missing decision-level link: one reported operating point passes recovery but fails CO, while another passes CO but fails recovery. The joint event therefore represents a published process-design conflict rather than a quantum-motivated abstraction. Published staged membrane experiments further support the physical architecture. Nevertheless, no public experiment identified here reports the final Zeolite-5A/polymer/palladium apparatus with simultaneous CO, CO2, N2, and CH4 measurements at the declared limits. The final module selectivities and defect ratio are therefore acceptance targets for a matched experiment or vendor model, not measured properties of a commercial module.",
            "5.4 Quantum role and computational boundary",
            "The QAE portion is subordinate to the separation result. For this three-dimensional smooth probability surface, scrambled Sobol integration is faster and more accurate than a practical quantum implementation. The compiled oracle is still useful because it prevents an abstract quantum speedup argument from being detached from tank reserve, receiver capacity, recovery, and product quality. It also shows that a nominally simple probability comparison requires 66 logical qubits and 17,690 CX gates before reflections or fault-tolerant overhead are included.",
            "5.5 Limitations",
            "Fourteen limitations define the current claim boundary. First, the independent uniform uncertainty measure is an engineering convention and should be replaced by synchronized plant-calibrated weights when available. Second, the maximum interior error is a deterministic stress buffer, not a statistical confidence interval. Third, DWSIM independently checks thermodynamics, equipment staging, duties, and horizon-averaged material balance but receives membrane split fractions from the packet model. The blind C# replay removes those split inputs from a third numerical implementation, yet DOP853, Python RK4, and C# RK4 still use the same constitutive transport laws; local DWSIM direct-transport automation was blocked by Windows Application Control and is not claimed as completed. Fourth, model-family validation on the public activated-carbon VPSA apparatus does not certify the final Zeolite-5A and membrane train. Fifth, the Ververs reproduction validates binary depletion and concentration-polarization physics at 2-5 bar and 350-450 C, not five-component leakage. Sixth, the Boon transfer supports near-pressure CO-inhibition sizing but uses pure Pd, steam, and lower H2 partial pressure. Seventh, the Peters endurance result uses a different Pd-Ag module and wet WGS feed. Eighth, the 40-50% actual-syngas permeance-loss range comes from a different coal-syngas module and is used as a conservative sizing stress, not as a degradation prediction for the present feed. Ninth, the Li campaign uses an intentional N2 permeate sweep, so only its independently measured H2/N2 permeances are transferred. Tenth, the DOE/MPT data are low-pressure pure-gas defect measurements and define a rejection stress rather than the performance of a modern dense module. Eleventh, the Sanchez full-syngas test has 100 ppm TCD accuracy and a different wet feed, so it validates operating trends and recovery scale rather than the declared ppm-level product specification. Twelfth, the DOE/Pall synchronized test omitted N2 and CH4 and reports one preliminary wet-mixture condition, so its separation factors are used only as a system-level rejection control. Thirteenth, the DOE/UTRC high-recovery feed omitted N2 and CH4, operated at different pressure and temperature, and inferred purity from H2/N2 separation rather than component-resolved analysis; it supports recovery, durability, bulk purity, and model transfer but does not certify the final impurity vector. Fourteenth, the Bang CMR was experimental but the public record used here does not establish the complete integrated four-bed PSA result as independently measured; the study used H2 sweep, omitted N2 and CH4, and its two reported points bracket rather than enter the present joint pass region. These boundaries do not alter the computed design rules, but they determine what must be tested before industrial deployment.",
        ],
    ),
    (
        "6 Conclusions",
        [
            "A finite regeneration inventory changes the hydrogen PSA operating problem from outlet maximization to allocation of product between the next cycle and sale. Under the declared feed, equilibrium, and kinetic uncertainty cube, the selected 7.0 bar tank set point, 4 s active purge, and 540 s adsorption stage passed all eight corners and increased qualified shipment by 6.80-7.36% relative to the comparison policy. Eight predeclared interiors and a buffered continuous probability calculation supported the decision.",
            "The physical polishing design requires staging. A 0.1892 m2 polymer concentrator reduces the burden on the dense-palladium polisher. Independent adaptive integration corrected the 20%-permeance-loss guard from 0.553 to 0.554 m2; the corrected design passed all 16 direct cases with minimum recovery 88.3217% and all four impurity maxima below their limits. A public actual-syngas aging stress expanded the conditional guard to 0.739 m2 for 40% loss and 0.887 m2 for 50% loss, again with 16/16 passes. Component-wise bisection converted the leakage uncertainty into a rounded incoming-module acceptance vector of H2/CO >=5,310, H2/CO2 >=158,110, H2/N2 >=540, and H2/CH4 >=40; the simultaneous vector passed 16/16. Public defect-leaking Pd vectors near 70-116 failed 0/16, showing why membrane area and membrane integrity must be specified separately. A separately coded Python RK4 mesh and a blind 61,440-packet C# RK4 replay both reproduced all 32 final design-case decisions. An unfitted reconstruction of 468 public H2/N2 flux records reached 4.41% mean absolute relative error and showed that removing concentration polarization increases error to 29.02%. The explicit 420 C DWSIM audit solved all 32 cases and established 2.784-2.877 kWh kg-1 H2 for compression plus 0.367-0.385 kWh kg-1 for external palladium heating after 80% heat recovery. A published 22-bar inhibition regression required only 0.456 m2 at its upper 95% CO coefficient, leaving both installed guards conservative. A separate full-syngas bench experiment supports hot multicomponent Pd operation and reports about 47% maximum recovery, but its 100 ppm TCD accuracy cannot certify the present 0.5 ppm CO and 5 ppm CO2 gates. A synchronized DOE/Pall test provides an empirical rejection control: its 75 ppm CO, 450 ppm CO2, and 75.98% recovery fail the project gate, and transferring its observed CO and CO2 separation factors fails 16/16 direct cases. Complementing that rejection case, the DOE/UTRC campaign sustained 93.4% mean recovery for about 1,300 h with calculated 99.9999% pre-leak bulk purity, and its frozen model predicted actual coal-gas hydrogen production within 4.53%. The Bang integrated CMR-PSA study then showed the decision conflict directly: 91.37% recovery came with 8.67 ppm CO, while 0.15 ppm CO reduced recovery to 85.99%. The present model predicts entry into the joint pass region, but matched component-resolved validation remains open.",
            "The same engineering event was reduced to a 66-qubit reversible probability oracle without changing any of the 16 direct labels. RQMC remains the preferred estimator for the present smooth three-variable problem. QAE becomes relevant only if future plant-calibrated uncertainty is higher dimensional, the validated process evaluation is expensive, and many probability or tail-risk queries reuse the same oracle. The immediate experimental priority is a matched multicomponent membrane test at the declared impurity detection limits.",
        ],
    ),
]


REFERENCES = [
    "J. Yang, C.-H. Lee, J.-W. Chang, Separation of hydrogen mixtures by a two-bed pressure swing adsorption process using zeolite 5A, Ind. Eng. Chem. Res. 36 (1997) 2789-2798. https://doi.org/10.1021/ie960728h.",
    "A.M. Ribeiro, C.A. Grande, F.V.S. Lopes, J.M. Loureiro, A.E. Rodrigues, Four beds pressure swing adsorption for hydrogen purification: case of humid feed and activated carbon beds, AIChE J. 55 (2009) 2292-2302. https://doi.org/10.1002/aic.11886.",
    "H. Khajuria, E.N. Pistikopoulos, Optimization and control of pressure swing adsorption processes under uncertainty, AIChE J. 59 (2013) 120-131. https://doi.org/10.1002/aic.13783.",
    "Y. Park, J.-H. Kang, D.-K. Moon, Y.S. Jo, C.-H. Lee, Parallel and series multi-bed pressure swing adsorption processes for H2 recovery from a lean hydrogen mixture, Chem. Eng. J. 408 (2021) 127299. https://doi.org/10.1016/j.cej.2020.127299.",
    "T. Kim, J.K. Scott, Dynamic modeling and simulation of pressure swing adsorption processes using toPSAil, Comput. Chem. Eng. 176 (2023) 108309. https://doi.org/10.1016/j.compchemeng.2023.108309.",
    "S. Ga, N. An, C. Joo, J. Kim, pyAPEP: an all-in-one software package for the automated preparation of adsorption process simulations, Comput. Phys. Commun. 291 (2023) 108830. https://doi.org/10.1016/j.cpc.2023.108830.",
    "A. Golmakani, S.A. Nabavi, V. Manovic, Data for the paper Effect of impurities on ultra-pure hydrogen production by pressure vacuum swing adsorption, Cranfield Online Research Data (2019). https://doi.org/10.17862/cranfield.rd.10123346.",
    "J. Wang, X. Chen, T. Du, L. Liu, P.A. Webley, G.K. Li, Hydrogen production from low pressure coke oven gas by vacuum pressure swing adsorption, Chem. Eng. J. 472 (2023) 144920. https://doi.org/10.1016/j.cej.2023.144920.",
    "B. Castro-Dominguez, I.P. Mardilovich, R. Ma, N.K. Kazantzis, A.G. Dixon, Y.H. Ma, Performance of a pilot-scale multitube membrane module under coal-derived syngas for hydrogen production and separation, J. Membr. Sci. 523 (2017) 515-523. https://doi.org/10.1016/j.memsci.2016.10.024.",
    "A. Iulianelli, A. Brunetti, L. Pino, C. Italiano, G.D. Ferrante, M. Gensini, A. Vita, An integrated two stages inorganic membrane-based system to generate and recover decarbonized H2: An experimental study and performance indexes analysis, Renew. Energy 210 (2023) 472-485. https://doi.org/10.1016/j.renene.2023.04.095.",
    "J. Yu, J. Zhang, C. Bao, H. Li, H. Xu, J. Sun, Confined and in-situ zeolite synthesis: A novel strategy for defect reparation over dense Pd membranes for hydrogen separation, Sep. Purif. Technol. 184 (2017) 43-53. https://doi.org/10.1016/j.seppur.2017.04.035.",
    "B. Li, G. He, X. Jiang, Y. Dai, X. Ruan, Pressure swing adsorption/membrane hybrid processes for hydrogen purification with a high recovery, Front. Chem. Sci. Eng. 10 (2016) 255-264. https://doi.org/10.1007/s11705-016-1567-1.",
    "P.F. Zito, A. Brunetti, G. Barbieri, Hydrogen concentration and purification by membrane process: A multistage analysis, Renew. Energy 218 (2023) 119243. https://doi.org/10.1016/j.renene.2023.119243.",
    "S. Woerner, D.J. Egger, Quantum risk analysis, npj Quantum Inf. 5 (2019) 15. https://doi.org/10.1038/s41534-019-0130-6.",
    "G. Brassard, P. Hoyer, M. Mosca, A. Tapp, Quantum amplitude amplification and estimation, Contemp. Math. 305 (2002) 53-74.",
    "A. Callison, D.E. Browne, Improved maximum-likelihood quantum amplitude estimation, arXiv:2209.03321 (2022). https://arxiv.org/abs/2209.03321.",
    "J. He et al., An efficient quantum computing based structural reliability analysis method using quantum amplitude estimation, Struct. Saf. 114 (2025) 102555. https://doi.org/10.1016/j.strusafe.2024.102555.",
    "P. Virtanen et al., SciPy 1.0: fundamental algorithms for scientific computing in Python, Nat. Methods 17 (2020) 261-272. https://doi.org/10.1038/s41592-019-0686-2.",
    "A.B. Owen, Scrambled net variance for integrals of smooth functions, Ann. Stat. 25 (1997) 1541-1562. https://doi.org/10.1214/aos/1031594731.",
    "D. Medeiros, DWSIM open-source chemical process simulator, https://dwsim.org (accessed 12 October 2026).",
    "F. Guazzone, J. Catalano, I.P. Mardilovich, T. Wu, R.C. Lambrecht, S. Datta, J. Kniep, S. Pande, N.K. Kazantzis, Y.H. Ma, Enhancement of the long-term permeance, selectivity stability, and recoverability of Pd-Au membranes in coal derived syngas atmospheres, Energy Fuels 27 (2013) 4150-4160. https://doi.org/10.1021/ef302130s.",
    "W.J.R. Ververs, M. Ongis, A. Arratibel, L. Di Felice, F. Gallucci, On the modeling of external mass transfer phenomena in Pd-based membrane separations, Int. J. Hydrogen Energy 71 (2024) 1121-1133. https://doi.org/10.1016/j.ijhydene.2024.04.337. Dataset: https://doi.org/10.5281/zenodo.7961792.",
    "J. Boon, J.A.Z. Pieterse, F.P.F. van Berkel, Y.C. van Delft, M. van Sint Annaland, Hydrogen permeation through palladium membranes and inhibition by carbon monoxide, carbon dioxide, and steam, J. Membr. Sci. 496 (2015) 344-358. https://doi.org/10.1016/j.memsci.2015.08.061.",
    "T.A. Peters, M. Stange, H. Klette, R. Bredesen, High pressure performance of thin Pd-23%Ag/stainless steel composite membranes in water gas shift gas mixtures; influence of dilution, mass transfer and surface effects on the hydrogen flux, J. Membr. Sci. 316 (2008) 119-127. https://doi.org/10.1016/j.memsci.2007.08.056.",
    "H. Li, A. Goldbach, W. Li, H. Xu, WGS-mixture separation and WGS reaction test in a bench-scale multi-tubular membrane reactor, Energy Procedia 4 (2011) 666-673. https://doi.org/10.1016/j.egypro.2011.01.103.",
    "Media and Process Technology Inc., Development of a Novel Membrane Reactor for Direct Hydrogen Production from Coal, final technical report DE-FG36-04GO14330, U.S. Department of Energy (2005). https://www.osti.gov/servlets/purl/883041.",
    "J.M. Sanchez, M.M. Barreiro, M. Marono, Bench-scale study of separation of hydrogen from gasification gases using a palladium-based membrane reactor, Fuel 116 (2014) 894-903. https://doi.org/10.1016/j.fuel.2013.02.051.",
    "J. Acquaviva, High Performance Palladium-Based Membrane for Hydrogen Separation and Purification, DOE Hydrogen Program FY 2008 Annual Progress Report, contract DE-FG36-05GO15093, pp. 57-62 (2008). https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/progress08/ii_a_9_acquaviva.pdf.",
    "S. Emerson, N. Magdefrau, Y. She, C. Thibaud-Erkey, Advanced Palladium Membrane Scale-up for Hydrogen Separation, final technical report DE-FE0004967, U.S. Department of Energy (2012). https://doi.org/10.2172/1063878.",
    "G. Bang, D.K. Moon, J.H. Kang, Y.J. Han, K.M. Kim, C.H. Lee, High-purity hydrogen production via a water-gas-shift reaction in a palladium-copper catalytic membrane reactor integrated with pressure swing adsorption, Chem. Eng. J. 411 (2021) 128473. https://doi.org/10.1016/j.cej.2021.128473.",
]


FIGURE_CAPTIONS = {
    1: "Engineering design and probability-event chain, from PSA regeneration allocation to robust and chance-constrained polishing decisions.",
    2: "Classical sampling and oracle-resolution diagnostics for the buffered event.",
    3: "Public dynamic H2-VPSA validation using the Wang et al. apparatus.",
    4: "Public membrane purity-recovery evidence and flow-normalized area traceability. Different feeds and pressures make this a scaling audit rather than a matched validation.",
    5: "Stage-resolved polymer and dense-palladium polishing train over 16 direct dynamic cases.",
    6: "Physical dense-palladium-area chance event and reversible-oracle bridge.",
    7: "Finite palladium leakage and permeance-aging sensitivity.",
    8: "DWSIM Peng-Robinson process cross-check for compression, cooling, temperatures, and closure.",
    9: "Independent continuous-area ODE audit and correction of the dense-palladium guard band.",
    10: "Installed dense-palladium area required to preserve the frozen process event under the 40-50% permeance-loss range reported for actual coal-derived syngas. The literature apparatus is used as a degradation stress, not as matched validation.",
    11: "Fixed-area RK4 mesh refinement and agreement with the adaptive DOP853 membrane calculation for both final design tiers. The comparison tests numerical implementation sensitivity while retaining the same constitutive transport laws.",
    12: "Independent reproduction of 468 public H2/N2 Pd-Ag membrane flux records using the published local Sherwood correlation. Including concentration polarization sharply reduces error relative to an otherwise identical depletion-only calculation.",
    13: "Explicit 420 C dense-palladium stage audit across both installed-area tiers. DWSIM resolves compression and heat-recovered duties for 32 cases, while the published 22-bar inhibition regression tests the installed-area margins without refitting.",
    14: "Component-specific effective-selectivity thresholds for the conservative 0.887 m2, 50%-retention design. Minimum values preserve all 16 direct cases; the 1.25x vector defines an incoming-module acceptance guard. Selected values are the original literature-parameterized design inputs.",
    15: "Analytical-resolution boundary of the public Sanchez bench test. The reported 0.01 vol% TCD accuracy is equivalent to about 100 ppm and therefore cannot directly certify the 0.5 ppm CO or 5 ppm CO2 gates used here.",
    16: "Synchronized DOE/Pall mixed-gas experiment used as an empirical rejection control. The observed impurity concentrations, effective separation factors, and hydrogen recovery all remain below the corresponding project acceptance requirements.",
    17: "DOE/UTRC pilot-scale Pd-Cu validation anchors. The simulated-syngas durability test provides a positive high-recovery and calculated bulk-purity case; the actual coal-gas run tests the frozen physics model. Purity was inferred from H2/N2 separation and is not component-resolved certification.",
    18: "Published Pd-Cu catalytic-membrane-reactor/four-bed-PSA operating points relative to the frozen joint gate. The two points pass opposite single criteria and bracket the upper-left joint pass region; the present worst-case point is a model prediction, not a matched experiment.",
    19: "Blind third-language packetwise membrane-transport replay. Compiled C# fixed-mesh RK4 receives no membrane split fractions and preserves all 32 adaptive-integrator decisions, with discrepancies far below the frozen numerical thresholds.",
}


FIGURE_AFTER = {
    "4.1": 1,
    "4.2": 2,
    "4.3": 3,
    "4.4a": 4,
    "4.4b": 5,
    "4.5": 9,
    "4.6": 8,
    "4.7a": 6,
    "4.7b": 7,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def set_font(run, size=10.5, bold=None, italic=None, color="000000"):
    run.font.name = "Times New Roman"
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, end])
    set_font(run, size=9)


def set_cell(cell, text, header=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = str(text)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for side in ("top", "start", "bottom", "end"):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), "80")
        node.set(qn("w:type"), "dxa")
        margins.append(node)
    if header:
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "1F4E78")
        tc_pr.append(shd)
    for paragraph in cell.paragraphs:
        paragraph.alignment = align
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        for run in paragraph.runs:
            set_font(run, size=8.3, bold=header, color="FFFFFF" if header else "000000")


def add_table(doc, number, title, headers, rows, widths=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(9)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(f"Table {number}. {title}")
    set_font(r, size=9.5, bold=True)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = True
    header_props = table.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    header_props.append(repeat)
    for j, h in enumerate(headers):
        set_cell(table.rows[0].cells[j], h, header=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        for j, value in enumerate(row):
            if i % 2:
                shd = OxmlElement("w:shd")
                shd.set(qn("w:fill"), "EAF2F8")
                cells[j]._tc.get_or_add_tcPr().append(shd)
            set_cell(cells[j], value, align=WD_ALIGN_PARAGRAPH.CENTER if j and len(str(value)) < 22 else WD_ALIGN_PARAGRAPH.LEFT)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_figure(doc, display_number, source_number=None):
    source_number = display_number if source_number is None else source_number
    if source_number == 4:
        matches = [PUBLIC_EVIDENCE_FIGURE]
    elif source_number == 10:
        matches = [SYNGAS_GUARD_FIGURE]
    elif source_number == 11:
        matches = [RK4_FIGURE]
    elif source_number == 12:
        matches = [VERVERS_FIGURE]
    elif source_number == 13:
        matches = [HIGH_TEMP_FIGURE]
    elif source_number == 14:
        matches = [SELECTIVITY_FIGURE]
    elif source_number == 15:
        matches = [SANCHEZ_FIGURE]
    elif source_number == 16:
        matches = [DOE_PALL_FIGURE]
    elif source_number == 17:
        matches = [UTRC_FIGURE]
    elif source_number == 18:
        matches = [BANG_FIGURE]
    elif source_number == 19:
        matches = [CSHARP_FIGURE]
    else:
        matches = sorted(PACKAGE.glob(f"Fig{source_number}_*.png"))
    assert len(matches) == 1, (source_number, matches)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(matches[0]), width=Inches(6.65))
    c = doc.add_paragraph()
    c.paragraph_format.space_after = Pt(8)
    c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = c.add_run(f"Figure {display_number}. ")
    set_font(r, size=9, bold=True)
    r = c.add_run(FIGURE_CAPTIONS[source_number])
    set_font(r, size=9)


def add_body_paragraph(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Inches(0.22)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run(text)
    set_font(r)


def data_tables(evidence):
    primary = evidence["primary_engineering_decision"]
    ode = evidence["independent_ode_membrane_audit"]["revised_guard_design"]
    confirm = ode["direct_confirmation"]
    dwsim = evidence["dwsim_stage_train_crosscheck"]
    oracle = json.loads((RESULTS / "physical_pd_area_qae_bridge" / "PSA_PHYSICAL_PD_AREA_QAE_BRIDGE.json").read_text(encoding="utf-8"))
    syngas_guard = json.loads(SYNGAS_GUARD_JSON.read_text(encoding="utf-8"))["conservative_50_percent_retention_design"]
    high_temp = json.loads(HIGH_TEMP_JSON.read_text(encoding="utf-8"))
    hot = high_temp["dwsim"]
    inhibition = high_temp["boon_2015_high_pressure_inhibition_anchor"]
    selectivity_audit = json.loads(SELECTIVITY_JSON.read_text(encoding="utf-8"))
    threshold = {
        row["impurity"]: row
        for row in selectivity_audit["component_acceptance_thresholds"]
    }
    procurement = selectivity_audit["design"]["rounded_procurement_acceptance_vector"]
    public_scenarios = {
        row["scenario_id"]: row
        for row in selectivity_audit["public_stress_scenarios"]
    }
    return [
        (
            1,
            "Operating and design decisions",
            ["Decision", "Comparison", "Selected", "Evidence"],
            [
                ["Tank set point", "6.6 bar", "7.0 bar", "8 corners"],
                ["Active purge", "6 s", "4 s", "8 corners"],
                ["Adsorption stage", "480 s", "540 s", "60 cycles"],
                ["Joint pass", "0/8", "8/8", "Direct model"],
                ["Qualified H2 gain", "Reference", "6.80-7.36%", "Paired cases"],
                ["Final Pd guard", "0.553 m2", "0.554 m2", "15/16 to 16/16"],
            ],
        ),
        (
            2,
            "Numerical and validation evidence hierarchy",
            ["Evidence", "Result", "Supported claim", "Boundary"],
            [
                ["Uncertainty corners", "8/8 pass", "Robust policy", "Declared cube"],
                ["Predeclared interiors", "8/8 pass", "Hold-out transfer", "Finite sample"],
                ["Wang experiment", "11.37% max breakthrough error", "Model family", "Different apparatus"],
                ["Adaptive ODE", "0.554 m2 passes 16/16", "Numerical guard", "Same transport laws"],
                ["Independent RK4", "32/32 labels agree", "Implementation robustness", "Same transport laws"],
                ["Ververs raw data", "468 flux records", "CP model form", "Binary 2-5 bar"],
                ["Boon 22 bar", "105 inhibition tests", "High-pressure inhibition", "Different pure-Pd module"],
                ["Peters 26 bar", "500 h WGS exposure", "Hot-stage feasibility", "Different Pd-Ag module"],
                ["Sanchez full syngas", "47% max recovery", "Hot multicomponent feasibility", "100 ppm TCD accuracy"],
                ["DOE/Pall wet mixture", "75 ppm CO; 450 ppm CO2", "Empirical rejection control", "No N2 or CH4"],
                ["DOE/UTRC Pd-Cu", "93.4% recovery; 99.9999% bulk H2", "Positive recovery/durability anchor", "Purity not component resolved"],
                ["DWSIM", "32/32 solved", "Thermodynamics and duties", "Splits supplied"],
                ["Oracle", "0/16 label errors", "Event preservation", "No speedup claim"],
            ],
        ),
        (
            3,
            "Membrane and receiver design tiers",
            ["Quantity", "Value", "Gate"],
            [
                ["Polymer area", "0.1892 m2", "Literature bounded"],
                ["Dense-Pd area", f"{ode['selected_rounded_pd_area_m2']:.3f} m2", "20% permeance loss"],
                ["Conditional Pd area", f"{syngas_guard['selected_rounded_installed_area_m2']:.3f} m2", "50% actual-syngas stress"],
                ["Receiver", f"{ode['receiver_capacity_mol']:.6f} mol", f"{ode['receiver_volume_L_at_1bar_298K']:.3f} L"],
                ["Minimum recovery", f"{confirm['minimum_recovery']*100:.4f}%", "88.2940% floor"],
                ["Minimum qualified H2", f"{confirm['minimum_qualified_h2_rate_mol_s']:.7f} mol s-1", "0.0022631 floor"],
                ["Maximum CO2", f"{confirm['maximum_co2_ppm']:.4f} ppm", "5 ppm"],
                ["Defect conductance guard", f"{evidence['independent_ode_membrane_audit']['revised_defect_boundary']['guard_banded_ratio']:.3e}", "H2 equivalent"],
            ],
        ),
        (
            4,
            "DWSIM and quantum resource summary",
            ["Calculation", "Metric", "Value"],
            [
                ["DWSIM", "Solved cases", f"{hot['case_count']}/{hot['case_count']}"],
                ["DWSIM", "Pd temperature", f"{hot['pd_operating_temperature_C']:.0f} C"],
                ["DWSIM", "Compression", f"{hot['compression_kWh_kg_H2_range'][0]:.3f}-{hot['compression_kWh_kg_H2_range'][1]:.3f} kWh kg-1"],
                ["DWSIM", "External Pd heat", f"{hot['external_pd_thermal_kWh_kg_H2_range'][0]:.3f}-{hot['external_pd_thermal_kWh_kg_H2_range'][1]:.3f} kWh kg-1"],
                ["DWSIM", "Compression + heat", f"{hot['compression_plus_external_heat_equivalent_kWh_kg_H2_range'][0]:.3f}-{hot['compression_plus_external_heat_equivalent_kWh_kg_H2_range'][1]:.3f} kWh kg-1"],
                ["DWSIM", "Maximum discharge", f"{dwsim['energy_and_temperature']['maximum_interstage_compressor_discharge_K']:.2f} K"],
                ["Boon transfer", "Required Pd area", f"{inhibition['minimum_installed_area_m2_at_420C_95pct_upper_inhibition']:.3f} m2"],
                ["QAE event", "Chance Pd area", f"{oracle['event']['selected_chance_pd_area_m2']:.3f} m2"],
                ["QAE event", "Discrete probability", f"{oracle['conservative_affine_oracle']['ten_bit_resources']['exact_discrete_oracle_probability']:.6f}"],
                ["QAE event", "Logical qubits", str(oracle['conservative_affine_oracle']['ten_bit_resources']['total_logical_qubits'])],
                ["QAE event", "CX gates", f"{oracle['conservative_affine_oracle']['ten_bit_resources']['transpiled_cx']:,}"],
            ],
        ),
        (
            5,
            "Dense-Pd incoming-module selectivity acceptance",
            ["Component/test", "Minimum or measured", "Acceptance guard", "Direct result"],
            [
                ["H2/CO", f"{threshold['CO']['minimum_effective_selectivity']:,.1f}", f">= {procurement['CO']:,.0f}", "16/16 at guard"],
                ["H2/CO2", f"{threshold['CO2']['minimum_effective_selectivity']:,.1f}", f">= {procurement['CO2']:,.0f}", "16/16 at guard"],
                ["H2/N2", f"{threshold['N2']['minimum_effective_selectivity']:,.1f}", f">= {procurement['N2']:,.0f}", "16/16 at guard"],
                ["H2/CH4", f"{threshold['CH4']['minimum_effective_selectivity']:,.2f}", f">= {procurement['CH4']:,.0f}", "16/16 at guard"],
                ["Li 2011 end test", f"H2/N2={public_scenarios['li_2011_n2_end_of_test']['alpha_n2']:.1f}", "N2 transfer only", f"{public_scenarios['li_2011_n2_end_of_test']['pass_count']}/16"],
                ["DOE/MPT 60 psig", "H2/i=92-116", "defect stress", f"{public_scenarios['doe_mpt_2005_shell_60psig']['pass_count']}/16"],
            ],
        ),
    ]


def write_markdown(evidence):
    lines = [f"# {TITLE}", "", ", ".join(AUTHORS), "", AFFILIATION, "", "## Abstract", "", ABSTRACT, "", "## Keywords", "", "; ".join(KEYWORDS), "", "## Highlights", ""]
    lines.extend([f"- {x}" for x in HIGHLIGHTS])
    lines.append("")
    for heading, paras in SECTIONS:
        lines.extend([f"## {heading}", ""])
        for para in paras:
            if para and para[0].isdigit() and "." in para[:5] and len(para.split()) < 12:
                lines.extend([f"### {para}", ""])
            else:
                lines.extend([para, ""])
    lines.extend([
        "## CRediT authorship contribution statement", "",
        "Ugwiyeon Lee: Conceptualization, Methodology, Software, Formal analysis, Investigation, Data curation, Visualization, Writing - original draft, Writing - review and editing, Project administration. Seong-Yun Bae: Writing - review and editing. Hakrae Kim: Writing - review and editing. Jungsu Lee: Writing - review and editing.", "",
        "## Declaration of competing interest", "", "The authors declare no competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.", "",
        "## Data and code availability", "", DATA_AVAILABILITY, "",
        "## Declaration of generative AI and AI-assisted technologies", "", "During manuscript preparation, the authors used OpenAI Codex for code drafting and refactoring, local workflow orchestration, figure and table generation, manuscript organization, and language editing. The authors reviewed and edited the outputs, reran the documented analyses, verified numerical claims and sources, and take full responsibility for the publication.", "",
        "## References", "",
    ])
    lines.extend([f"[{i}] {ref}" for i, ref in enumerate(REFERENCES, 1)])
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")


def build_docx(evidence):
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.70)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)
    section.header_distance = Inches(0.28)
    section.footer_distance = Inches(0.30)

    for style_name, size, bold in [("Normal", 10.5, False), ("Title", 17, True), ("Heading 1", 13, True), ("Heading 2", 11.5, True)]:
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = bold
        style.font.color.rgb = RGBColor(0, 0, 0)
    title_ppr = doc.styles["Title"]._element.get_or_add_pPr()
    title_border = title_ppr.find(qn("w:pBdr"))
    if title_border is not None:
        title_ppr.remove(title_border)

    header = section.header.paragraphs[0]
    header.text = "Regeneration reserve aware hydrogen PSA"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in header.runs:
        set_font(run, size=8.5, italic=True, color="555555")
    footer = section.footer.paragraphs[0]
    add_page_number(footer)

    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    direct_border = p._p.get_or_add_pPr().find(qn("w:pBdr"))
    if direct_border is not None:
        p._p.get_or_add_pPr().remove(direct_border)
    r = p.add_run(TITLE)
    set_font(r, size=17, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(", ".join(AUTHORS))
    set_font(r, size=11.5, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(AFFILIATION)
    set_font(r, size=10, italic=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("* Corresponding author: lyullee@kgs.or.kr; ORCID 0009-0008-8976-5363")
    set_font(r, size=9.5)

    h = doc.add_heading("Abstract", level=1)
    h.paragraph_format.space_before = Pt(10)
    add_body_paragraph(doc, ABSTRACT)
    p = doc.add_paragraph()
    r = p.add_run("Keywords: ")
    set_font(r, bold=True)
    r = p.add_run("; ".join(KEYWORDS))
    set_font(r)

    h = doc.add_heading("Highlights", level=1)
    for item in HIGHLIGHTS:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        set_font(p.add_run(item))

    inserted_figures = set()
    table_map = {1: "4.1", 2: "4.3", 3: "4.5", 4: "4.7"}
    tables = {t[0]: t for t in data_tables(evidence)}

    for heading, paras in SECTIONS:
        h = doc.add_heading(heading, level=1)
        current_sub = ""
        para_index = 0
        for para in paras:
            if para and para[0].isdigit() and "." in para[:5] and len(para.split()) < 12:
                current_sub = para.split()[0]
                para_index = 0
                h2 = doc.add_heading(para, level=2)
                h2.paragraph_format.keep_with_next = True
                continue
            add_body_paragraph(doc, para)
            para_index += 1

            if current_sub == "4.1" and para_index == 1:
                add_table(doc, *tables[1])
                add_figure(doc, 1); inserted_figures.add(1)
            elif current_sub == "4.2" and para_index == 1:
                add_figure(doc, 2); inserted_figures.add(2)
            elif current_sub == "4.3" and para_index == 1:
                add_table(doc, *tables[2])
                add_figure(doc, 3); inserted_figures.add(3)
            elif current_sub == "4.4" and para_index == 1:
                add_figure(doc, 4); inserted_figures.add(4)
            elif current_sub == "4.4" and para_index == 2:
                add_figure(doc, 5); inserted_figures.add(5)
            elif current_sub == "4.5" and para_index == 2:
                add_table(doc, *tables[3])
                add_figure(doc, 6, 9); inserted_figures.add(6)
                add_figure(doc, 7); inserted_figures.add(7)
            elif current_sub == "4.6" and para_index == 1:
                add_figure(doc, 8); inserted_figures.add(8)
            elif current_sub == "4.7" and para_index == 1:
                add_table(doc, *tables[4])
                add_figure(doc, 9, 6); inserted_figures.add(9)
            elif current_sub == "4.8" and para_index == 1:
                add_figure(doc, 10); inserted_figures.add(10)
            elif current_sub == "4.9" and para_index == 1:
                add_figure(doc, 11); inserted_figures.add(11)
            elif current_sub == "4.10" and para_index == 1:
                add_figure(doc, 12); inserted_figures.add(12)
            elif current_sub == "4.11" and para_index == 1:
                add_figure(doc, 13); inserted_figures.add(13)
            elif current_sub == "4.12" and para_index == 1:
                add_table(doc, *tables[5])
                add_figure(doc, 14); inserted_figures.add(14)
            elif current_sub == "4.13" and para_index == 1:
                add_figure(doc, 15); inserted_figures.add(15)
            elif current_sub == "4.14" and para_index == 1:
                add_figure(doc, 16); inserted_figures.add(16)
            elif current_sub == "4.15" and para_index == 1:
                add_figure(doc, 17); inserted_figures.add(17)
            elif current_sub == "4.16" and para_index == 1:
                add_figure(doc, 18); inserted_figures.add(18)
            elif current_sub == "4.17" and para_index == 1:
                add_figure(doc, 19); inserted_figures.add(19)

    assert inserted_figures == set(range(1, 20)), inserted_figures

    for heading, text in [
        ("CRediT authorship contribution statement", "Ugwiyeon Lee: Conceptualization, Methodology, Software, Formal analysis, Investigation, Data curation, Visualization, Writing - original draft, Writing - review and editing, Project administration. Seong-Yun Bae: Writing - review and editing. Hakrae Kim: Writing - review and editing. Jungsu Lee: Writing - review and editing."),
        ("Declaration of competing interest", "The authors declare no competing financial interests or personal relationships that could have appeared to influence the work reported in this paper."),
        ("Data and code availability", DATA_AVAILABILITY),
        ("Declaration of generative AI and AI-assisted technologies", "During manuscript preparation, the authors used OpenAI Codex for code drafting and refactoring, local workflow orchestration, figure and table generation, manuscript organization, and language editing. The authors reviewed and edited the outputs, reran the documented analyses, verified numerical claims and sources, and take full responsibility for the publication."),
    ]:
        doc.add_heading(heading, level=1)
        add_body_paragraph(doc, text)

    h = doc.add_heading("References", level=1)
    h.paragraph_format.keep_with_next = True
    for i, ref in enumerate(REFERENCES, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_after = Pt(2)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        set_font(p.add_run(f"[{i}] {ref}"), size=8.5)

    doc.core_properties.title = TITLE
    doc.core_properties.author = "Ugwiyeon Lee; Seong-Yun Bae; Hakrae Kim; Jungsu Lee"
    doc.core_properties.subject = "SPT-oriented manuscript on regeneration-reserve-aware hydrogen PSA"
    doc.core_properties.keywords = ", ".join(KEYWORDS)
    doc.save(DOCX_OUT)


def main():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["schema"] == "psa-final-objective-evidence/v42"
    OUT.mkdir(parents=True, exist_ok=True)
    write_markdown(evidence)
    build_docx(evidence)
    reference_audit = {
        "schema": "psa-spt-reference-metadata-audit/v1",
        "checked_on": "2026-10-12",
        "method": "DOI metadata was checked against Crossref; the Cranfield dataset was checked against its institutional repository record.",
        "corrected_references": [
            {"reference": 9, "doi": "10.1016/j.memsci.2016.10.024", "metadata_source": "https://api.crossref.org/works/10.1016%2Fj.memsci.2016.10.024", "status": "title, authors, journal, volume, year, and pages matched"},
            {"reference": 10, "doi": "10.1016/j.renene.2023.04.095", "metadata_source": "https://api.crossref.org/works/10.1016%2Fj.renene.2023.04.095", "status": "title, authors, journal, volume, year, and pages matched"},
            {"reference": 11, "doi": "10.1016/j.seppur.2017.04.035", "metadata_source": "https://api.crossref.org/works/10.1016%2Fj.seppur.2017.04.035", "status": "title, authors, journal, volume, year, and pages matched"},
            {"reference": 12, "doi": "10.1007/s11705-016-1567-1", "metadata_source": "https://api.crossref.org/works/10.1007%2Fs11705-016-1567-1", "status": "title, authors, journal, volume, year, and pages matched"},
            {"reference": 13, "doi": "10.1016/j.renene.2023.119243", "metadata_source": "https://api.crossref.org/works/10.1016%2Fj.renene.2023.119243", "status": "title, authors, journal, volume, year, and article number matched"},
            {"reference": 21, "doi": "10.1021/ef302130s", "metadata_source": "https://api.crossref.org/works/10.1021%2Fef302130s", "status": "title, authors, journal, volume, issue, year, and pages matched"},
            {"reference": 22, "doi": "10.1016/j.ijhydene.2024.04.337", "metadata_source": "https://api.crossref.org/works/10.1016%2Fj.ijhydene.2024.04.337", "status": "title, authors, journal, volume, year, pages, and public dataset matched"},
            {"reference": 23, "doi": "10.1016/j.memsci.2015.08.061", "metadata_source": "https://api.crossref.org/works/10.1016%2Fj.memsci.2015.08.061", "status": "title, authors, journal, volume, year, and pages matched"},
            {"reference": 24, "doi": "10.1016/j.memsci.2007.08.056", "metadata_source": "https://api.crossref.org/works/10.1016%2Fj.memsci.2007.08.056", "status": "title, authors, journal, volume, year, and pages matched"},
            {"reference": 25, "doi": "10.1016/j.egypro.2011.01.103", "metadata_source": "https://api.crossref.org/works/10.1016%2Fj.egypro.2011.01.103", "status": "title, authors, journal, volume, year, and pages matched"},
            {"reference": 27, "doi": "10.1016/j.fuel.2013.02.051", "metadata_source": "https://api.crossref.org/works/10.1016%2Fj.fuel.2013.02.051", "status": "title, authors, journal, volume, year, and pages matched"},
        ],
        "dataset_reference": {
            "reference": 7,
            "doi": "10.17862/cranfield.rd.10123346",
            "metadata_source": "https://dspace.lib.cranfield.ac.uk/items/01190c6a-eb8e-4476-9358-afc4fc591b41",
            "status": "title, creators, year, publisher, DOI, and related article verified",
        },
        "technical_report_reference": {
            "reference": 26,
            "report_number": "DE-FG36-04GO14330",
            "metadata_source": "https://www.osti.gov/servlets/purl/883041",
            "status": "title, contractor, report number, sponsor, year, and public full text verified",
        },
        "doe_progress_report_reference": {
            "reference": 28,
            "contract_number": "DE-FG36-05GO15093",
            "metadata_source": "https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/progress08/ii_a_9_acquaviva.pdf",
            "status": "title, author, contractor, contract, year, pages, Figure 3 flows, and public full text verified",
        },
        "doe_utrc_final_report_reference": {
            "reference": 29,
            "doi": "10.2172/1063878",
            "contract_number": "DE-FE0004967",
            "metadata_source": "https://doi.org/10.2172/1063878",
            "status": "title, authors, contract, date, 60-page public full text, durability values, and actual-gas comparison verified",
        },
        "bang_integrated_cmr_psa_reference": {
            "reference": 30,
            "doi": "10.1016/j.cej.2021.128473",
            "metadata_source": "https://yonsei.elsevierpure.com/en/publications/high-purity-hydrogen-production-via-a-water-gas-shift-reaction-in/",
            "status": "title, authors, journal, volume, article number, feed, conditions, and both reported CO-recovery operating points verified",
        },
    }
    REFERENCE_AUDIT_OUT.write_text(json.dumps(reference_audit, indent=2), encoding="utf-8")
    sources = [EVIDENCE, PACKAGE / "SPT_ENGINEERING_RESULTS_MANIFEST.json"]
    sources += sorted(PACKAGE.glob("Fig*.png"))
    sources.append(PUBLIC_EVIDENCE_FIGURE)
    sources += [SYNGAS_GUARD_JSON, SYNGAS_GUARD_FIGURE, RK4_JSON, RK4_FIGURE, VERVERS_JSON, VERVERS_FIGURE, HIGH_TEMP_JSON, HIGH_TEMP_FIGURE, HIGH_TEMP_DIR / "MANIFEST_SHA256.json", SELECTIVITY_JSON, SELECTIVITY_FIGURE, SELECTIVITY_DIR / "MANIFEST_SHA256.json", SANCHEZ_JSON, SANCHEZ_FIGURE, SANCHEZ_DIR / "MANIFEST_SHA256.json", DOE_PALL_JSON, DOE_PALL_FIGURE, DOE_PALL_DIR / "MANIFEST_SHA256.json", UTRC_JSON, UTRC_FIGURE, UTRC_DIR / "MANIFEST_SHA256.json", BANG_JSON, BANG_FIGURE, BANG_DIR / "MANIFEST_SHA256.json", CSHARP_JSON, CSHARP_FIGURE, CSHARP_DIR / "MANIFEST_SHA256.json"]
    outputs = [MD_OUT, DOCX_OUT, REFERENCE_AUDIT_OUT]
    manifest = {
        "schema": "psa-spt-full-manuscript/v1",
        "status": "full_draft_with_public_validation_joint_gate_and_blind_csharp_transport_replay",
        "sources": [{"path": str(p.relative_to(PROJECT)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in sources],
        "outputs": [{"path": str(p.relative_to(PROJECT)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in outputs],
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"docx": str(DOCX_OUT), "markdown": str(MD_OUT), "figures": 19, "references": len(REFERENCES)}, indent=2))


if __name__ == "__main__":
    main()
