# Hydraulically feasible regeneration-reserve-aware hydrogen pressure swing adsorption under uncertainty with staged membrane polishing and a quantum-ready probability event

Ugwiyeon Lee*, Seong-Yun Bae, Hakrae Kim, Jungsu Lee

Korea Gas Safety Corporation, 1390 Wonjung-ro, Maengdong-myeon, Eumseong-gun, Chungcheongbuk-do 27738, Republic of Korea

## Abstract

Hydrogen pressure swing adsorption must retain product gas for the next purge and repressurization steps before gas can be sold. This work formulates that allocation as a continuous qualified-shipment problem and enforces pressure feasibility between a four-bed PSA, a finite regeneration tank, valves, and a polishing train. A pressure audit showed that the preliminary 7.0 bar tank could not be passively refilled from a 6.2 bar product manifold. The corrected topology therefore uses a 6.0 bar regulated tank, a 0.2 bar fill driving margin, and a discharge booster to the 6.5 bar regeneration header. Within declared feed, adsorption-equilibrium, and kinetic uncertainty, the selected policy of 4 s active purge and 540 s adsorption passed all eight corner cases and all eight predeclared interior hold-outs; a 6 s, 480 s comparison passed none. Specification-qualified hydrogen shipment increased by 6.785-7.341%, the minimum reserve-margin gain was 0.542 bar, and conservative booster duty remained below 0.198 kWh kg-1 H2. A literature-parameterized polymer concentrator followed by dense palladium polishing passed all 16 direct cases. Adaptive DOP853 integration corrected a near-boundary 20%-permeance-loss guard from 0.553 to 0.554 m2; the revised design gave at least 88.322% recovery and maximum CO, CO2, N2, and CH4 contents of 0.121, 4.000, 48.83, and 25.07 ppm. A public actual-syngas 50%-permeance-retention stress increased the conditional installed area to 0.887 m2 and retained all 16 cases. A separately coded fixed-area RK4 solver reproduced all 32 design-case labels, with a maximum recovery difference below 9.4e-8 percentage point relative to DOP853. For a 0.440 m2 chance design, error-buffered trilinear integration gave a minimum scrambled-Sobol probability of 0.956673; a conservative affine event gave 0.951210, and its 10-bit discretization gave 0.950629 with no direct label errors. An exact portable OpenQASM 3 oracle uses 66 logical qubits, 24,042 CX gates, 61,269 primitive gates, and all-to-all depth 36,163 before optimization or routing. Exhaustive 2-, 3-, and 4-bit checks plus direct and random 10-bit checks gave zero phase-label and work-qubit-restoration errors. Device-specific optimization and a corrected-input DWSIM run remain external execution steps. For this smooth three-variable event, randomized quasi-Monte Carlo remains the practical estimator. The contribution is a pressure-consistent separation design rule and an auditable process-to-oracle construction for future higher-dimensional plant uncertainty.

## Keywords

Hydrogen purification; Pressure swing adsorption; Regeneration tank; Membrane polishing; Chance constraint

## Highlights

- A 6.0 bar regeneration tank is passively filled from the 6.2 bar product manifold
- A discharge booster closes the hydraulic path to the 6.5 bar regeneration header
- The selected 4 s purge and 540 s adsorption policy passes 8/8 corners and 8/8 hold-outs
- Qualified hydrogen shipment rises by 6.785-7.341% over the comparison policy
- A 0.554 m2 Pd guard passes all 16 cases at 20% permeance loss
- A 0.887 m2 conditional guard covers a public 50% actual-syngas loss stress
- Independent RK4 reproduces all 32 adaptive-integrator decisions
- A verified 66-qubit OpenQASM oracle connects the process chance constraint to QAE

## 1 Introduction

High-purity hydrogen is required by chemical, metallurgical, energy-storage, and fuel-cell systems. Pressure swing adsorption (PSA) is attractive because selective adsorption and pressure cycling can remove carbon dioxide, methane, carbon monoxide, and nitrogen without a continuously regenerated solvent. The industrial design problem is nevertheless more complicated than maximizing purity or recovery at one outlet. Product hydrogen also performs internal work: it purges low-pressure beds, repressurizes beds before adsorption, and maintains a product or equalization inventory that couples one bed to the others. If this inventory is represented as an unlimited source, a simulated cycle can sell gas that the real plant must retain for its next cycle.

Dynamic PSA optimization has addressed cycle scheduling, adsorbent selection, control, and uncertainty [1-8]. These studies establish that pressure equalization, purge, adsorption duration, valve conductance, and feed composition interact strongly. They also show why cyclic steady state, component conservation, and direct validation matter. However, regeneration demand is often embedded in boundary conditions or reported separately from the product available for shipment. For variable feed and aging adsorbent, the practical question is therefore not simply which cycle gives the highest hydrogen recovery. It is which continuous operating policy preserves regeneration inventory and simultaneously maximizes hydrogen that satisfies a strict product specification.

A second difficulty appears when the PSA outlet is close to, but does not by itself meet, a multi-impurity hydrogen specification. A membrane polishing stage can increase purity, yet a single membrane must trade recovery against contaminant rejection. Published pilot and staged studies support palladium-alloy durability and the value of pre-concentration, but they do not jointly report all impurity limits used here [9-13]. A defensible model must therefore expose permeance loss, finite selectivity, receiver dynamics, and defect leakage as acceptance conditions instead of assigning a perfect final purity.

Uncertainty adds a third layer. A robust design that passes every bounded case can be larger than necessary, whereas a chance-constrained design accepts a declared small failure region. Estimating that probability links separation engineering to Monte Carlo, randomized quasi-Monte Carlo (RQMC), and quantum amplitude estimation (QAE). QAE can offer a quadratic query advantage for idealized amplitude access [14-17], but state preparation, reversible process arithmetic, and model error can remove that advantage. A process application is useful only when the probability event preserves the engineering decision and its circuit cost is reported.

This study combines a pressure-consistent four-bed PSA, finite regeneration inventory, staged membrane polishing, uncertainty propagation, and a quantum-ready chance event. The model is checked against a public four-bed hydrogen VPSA experiment [8], 468 public Pd-Ag H2/N2 flux records [22], high-pressure and mixed-gas palladium studies [23-29], and an integrated membrane-reactor/PSA study [30]. Adaptive DOP853 and separately coded fixed-area RK4 calculations test numerical sensitivity. The contribution is an engineering operating rule and a reproducible probability event; present quantum advantage and direct certification of the integrated apparatus are outside the claim.

## 2 Problem definition

The process boundary begins at a multicomponent hydrogen-rich PSA feed and ends at a finite product receiver. Four adsorbers follow a staggered adsorption, equalization, blowdown, purge, and repressurization schedule. Product gas first supplies simultaneous internal demand. Remaining gas reaches a 6.2 bar product manifold and passively refills a tank regulated to 6.0 bar. Tank withdrawal is boosted to the 6.5 bar purge and repressurization header. Only surplus product proceeds to polishing and sale.

The primary objective is time-averaged specification-qualified hydrogen delivered from the receiver. The operating-policy screen requires hydrogen fraction at least 0.9997; CO, CO2, N2, and CH4 no greater than 0.5, 5, 300, and 100 ppm; qualified hydrogen at least 0.002 mol s-1; positive regeneration reserve; passive tank-fill margin; bounded booster duty; cyclic convergence; trace integrity; and component conservation. The final physical membrane design additionally freezes recovery and shipment floors of 0.882940 and 0.0022631 mol s-1.

Both policies use a 6.0 bar tank set point. The comparison uses 6 s active purge and a 480 s adsorption stage; the selected policy uses 4 s and 540 s. Physical decisions include polymer and dense-palladium areas, surge capacity, receiver capacity, and regeneration-booster duty. Uncertainty coordinates cover a feed-hydrogen multiplier of 0.95-1.05, paired adsorption capacity-affinity endpoints, and an LDF kinetic multiplier of 0.8-1.2. Their eight endpoint combinations form the engineering cube; eight interior points were declared before the corrected design calculation.

Two design meanings are kept separate. A fully robust design passes every declared direct case. A 95% chance design passes under an independent uniform engineering measure over the declared cube after shifting the event boundary by the largest error on the predeclared interiors. This measure is a transparent design convention; it is not presented as a plant-calibrated probability distribution.

## 3 Methods

### 3.1 Dynamic PSA tank valve and bed model

Each bed is discretized axially and advanced through the staggered cycle with component inventories, competitive equilibrium, LDF uptake, valve-driven flows, and a non-isothermal energy balance. The tank follows component inventory and ideal-gas pressure. A separate hydraulic audit enforces the 6.2-to-6.0 bar passive-fill direction and computes isothermal booster work from the instantaneous tank pressure to the 6.5 bar header at 72% efficiency. Six axial cells and 60 cycles are used for direct decisions, with cyclic-state, trace-integrity, and component-balance gates.

The source model was separately reconstructed for the public Wang et al. four-bed, 12-step H2/CH4/N2/CO2 VPSA apparatus [8]. Published geometry, activated-carbon equilibrium, partial-pressure LDF kinetics, heat effects, step schedule, and experimental breakthrough and pressure data were used. This cross-validation tests reusable conservation, pressure-network, adsorption, and thermal implementations. Because the final process uses a different adsorbent, pressure range, and downstream membrane, it does not directly validate the final apparatus.

### 3.2 Polishing train and finite receivers

Surplus PSA product is compressed from the 6.2 bar manifold to a 20 bar surge buffer and cooled to 298.15 K. A polymer concentrator operates at 20/1 bar. Its permeate is recompressed in three equal-pressure-ratio stages to a dense-palladium stage at 20/1 bar and 693.15 K. Both retentates go to fuel or off-gas, and no internal recycle is credited. The ideal-train screen uses a 4.616 mol surge buffer and a 1.546 mol product receiver; guard-banded finite-selectivity designs co-size the receiver again.

Membrane transfer is evaluated for every saved time packet. The production calculation uses fixed area sections; the independent audit solves the same transfer laws with scipy DOP853 at relative and absolute tolerances of 1e-9 and 1e-13. A second implementation uses classical fourth-order Runge-Kutta over 48, 96, and 192 equal-area sections and does not call the adaptive solver. Exact component ledgers are retained across both membranes and the finite receiver.

The dense-palladium guard imposes finite effective H2/impurity selectivities, hydrogen-permeance loss, and an H2-equivalent Knudsen defect-conductance ratio. This ratio compares local defect H2 transfer with dense-palladium H2 transfer and is not a geometric pinhole fraction. Continuous receiver quality, inventory, recovery, shipment, and mass balance are checked for all eight corners and eight hold-outs.

### 3.3 Robust and chance-constrained calculations

The two operating policies are paired at all eight uncertainty corners. The corrected selected policy is then tested on the eight predeclared interiors. The membrane-area chance calculation fits a trilinear response to the corners, measures its largest absolute error on the predeclared interiors, and shifts the event boundary by that error. Eight independent scrambled Sobol integrations estimate probability under an explicitly uniform engineering measure.

### 3.4 Process probability oracle

Installed dense-palladium area is the physical design coordinate. At 0.440 m2, 13 of 16 direct stress cases pass while the continuous chance probability exceeds 0.95. A conservative affine event is checked against every direct label and digitized with 10 qubits for each of three uncertainty coordinates. Reversible signed accumulation and comparison require 66 logical qubits. The circuit follows source-equivalent weighted-adder and two's-complement comparator constructions and is expanded exactly to OpenQASM 3 using X, H, T, Tdg, Z, and CX. Its portable unoptimized resources are 24,042 CX gates, 61,269 total primitive gates, and all-to-all depth 36,163. These counts exclude device routing, error correction, and hardware calibration.

### 3.5 Independent thermodynamic and numerical checks

Compression is recalculated from the corrected 6.2 bar product manifold to the 20 bar polishing buffer and from the 1 bar polymer permeate to the 20 bar palladium feed. A corrected 16-case DWSIM input deck was generated, but local execution stopped when Windows Application Control blocked DWSIM.FileStorage.dll. Earlier Peng-Robinson runs are therefore shown only as evidence that the flowsheet and staged-compression method execute; their numerical duties are not used as current corrected-input results.

The independent RK4 implementation evaluates the frozen polymer solution-diffusion and finite-selectivity palladium equations at 48, 96, and 192 area sections. It covers the 0.554 m2, 80%-retention guard and the 0.887 m2, 50%-retention actual-syngas stress over all 16 direct cases. This isolates numerical implementation and mesh sensitivity while retaining the same constitutive laws.

A separate external-data calculation reconstructs the Ververs et al. tubular Pd-Ag experiment [22]. The implementation uses their axial H2 and N2 balances, Richardson parameters for 0.150, 0.300, and 0.467 m membranes, stagnant-film equation, 64 mm annular hydraulic diameter, and local correlation Sh=1.846Gz^0.60. H2-N2 diffusivity is calculated independently with the Fuller correlation, and 96, 192, and 384-section RK4 meshes are compared. No mixture-flux parameter is fitted. The downloaded workbook contains 468 numeric records, 45 more than the 423 stated in the article; all public records are retained without undocumented filtering.

### 3.6 High-pressure inhibition transfer and hot-stage audit

Boon et al. reported 105 randomized inhibition tests at 22 bar retentate pressure, 2 bar permeate pressure, 350-450 C, 50-70% H2, and up to 2% CO [23]. Their published linear regression, eta=1-KCO<pCO>-KH2O<pH2O>, is applied without refitting. Because the present design feed is dry, the steam term is set to zero. The arithmetic uses the average CO partial pressure between each palladium feed and retentate and evaluates both the central 420 C coefficient and its upper 95% uncertainty limit. This transfer tests whether the installed-area guards cover measured high-pressure inhibition; it does not validate impurity leakage.

Earlier DWSIM hot-stage calculations established a workable Peng-Robinson flowsheet with three-stage recompression, a 420 C palladium heater, coolers, and component closure. Because the pressure-consistent input rerun is blocked on the current host, those values are retained as a structural and method cross-check only. Published 22-26 bar palladium inhibition and endurance studies [23,24] independently define the pressure and temperature evidence boundary.

### 3.7 Public selectivity transfer and module acceptance threshold

The 0.887 m2 design is replayed while one effective impurity selectivity is reduced and the others remain fixed. Logarithmic bisection finds the lowest value preserving all 16 events; a 25% simultaneous margin and upward rounding form an incoming-module screen. Li et al. [25] and DOE/MPT [26] provide public high-pressure and defect-leakage stresses, respectively, and are used as transfer and rejection controls rather than matched certification.

### 3.8 Independent full-syngas bench evidence and analytical-resolution audit

Sanchez et al. tested a 0.01216 m2 precommercial Pd membrane in a bench facility with feed, retentate, and permeate slipstreams analysed by gas chromatography [27]. Their synthetic unconverted-shift gas contained 17% H2, 19% CO, 7% CO2, and 57% steam and was tested at 593-723 K and 0.15-1.0 MPa. Reported TCD accuracy was 0.01 vol% (about 100 ppm). The present audit therefore uses the experiment as a multicomponent feasibility, inhibition-direction, permeance, and recovery anchor, but does not translate the paper's 'pure hydrogen' wording into certification of the present 0.5 ppm CO or 5 ppm CO2 limits.

### 3.9 Synchronized mixed-gas rejection control

The DOE/Pall FY 2008 report provides feed, retentate, and permeate flow and composition for a Pd90Au10 membrane at 400 C, 62 psia feed, 12 psia permeate, and 50 psi pressure difference [28]. The feed contained 51% H2, 26% CO2, 21% steam, and 2% CO. The observed permeate contained 99.95% H2, 450 ppm CO2, and 75 ppm CO. H2 recovery is calculated directly as 775/1020=75.98%. System-level H2/CO and H2/CO2 separation factors are calculated from the reported feed and permeate mole fractions and transferred to the 0.887 m2 design while N2 and CH4 remain at their selected values. Because the factors include wet-mixture, support, film, and defect effects, this is an empirical rejection stress rather than an intrinsic-permeability fit.

### 3.10 Positive high-recovery and actual coal-gas validation anchors

The DOE/UTRC final report describes a pilot-scale approximately 0.139 m2 Pd-Cu separator [29]. Its durability feed contained 75% H2, 1% CO, 5% CO2, 19% H2O, and 1.65 ppmv H2S. At 500.8 +/- 10.6 C and 184.7 +/- 7.8 psig, the separator produced 2.36 +/- 0.20 lb day-1 H2 at 93.4 +/- 8.0% recovery for about 1,300 h. Before a small leak began at 2,624 h, the report assigned 99.9999% H2 purity from the ideal H2/N2 separation factor; this corresponds to about 1 ppm total non-H2 but is not component-resolved analysis. A separate 77 h actual coal-gas test measured 2.43 lb day-1 and 74.3% recovery, compared with frozen-model predictions of 2.32 lb day-1 and 70.1%. These records are used as positive recovery, bulk-purity, durability, and model-transfer anchors. They are not treated as direct certification of the final 20-bar five-component product.

### 3.11 Integrated CMR-PSA joint-gate bracket

Bang et al. integrated a Pd-Cu water-gas-shift catalytic membrane reactor with activated-carbon/zeolite four-bed PSA [30]. The CMR was experimentally operated with a CO/H2/CO2 feed of 65:30:5 vol%, steam/carbon ratios of 1-5, 360-380 C, 6-10 bar, and H2 sweep. The public record used here does not establish the complete four-bed PSA output as an independently measured dataset, so the two overall results are treated as published integrated-process operating points. The high-recovery point gave 91.37% H2 recovery, more than 99.9991% H2, and 8.67 ppm CO. The low-CO point gave 85.99% recovery and 0.15 ppm CO. Each point is compared separately with the frozen 88.294% recovery floor and 0.5 ppm CO limit. This creates a literature bracket of the conjunction used by the process oracle; it is not a fit to the present model or direct validation of the final apparatus.

### 3.12 Blind third-language membrane-transport replay

A compiled C# packetwise implementation was previously used to verify the independent transport method on the preceding input set. The regenerated 6.0 bar train was not replayed because native execution is restricted on the current host. Its figure is retained to document the third-language method, but the current pressure-consistent claims rely on direct six-cell integration, DOP853, and the newly rerun Python RK4 calculation.

## 4 Results

### 4.1 Regeneration reserve changes the operating decision

The pressure audit rejected the preliminary 7.0 bar tank because the 6.2 bar product manifold could not fill it passively. With the corrected 6.0 bar tank and discharge booster, the 6 s/480 s comparison failed all eight corners whereas the 4 s/540 s policy passed all eight. Qualified shipment increased by 6.785-7.341%, minimum reserve margin improved by at least 0.542 bar, and the selected conservative booster duty was no greater than 0.197 kWh kg-1 qualified H2. The maximum cyclic-state residual and relative cycle balance error were 1.225e-5 and 1.661e-5.

### 4.2 Direct hold-out and continuous chance design

All eight predeclared interior conditions passed the corrected six-cell, 60-cycle calculation. Their minimum tank pressure was 3.546 bar, minimum reserve margin was 2.746 bar, maximum N2 was 227.24 ppm, and maximum booster duty was 0.194 kWh kg-1. All passive-fill, trace-integrity, cyclic-state, and mass-balance gates passed. The separate physical-area chance event at 0.440 m2 gave a minimum scrambled-Sobol probability of 0.956673 after hold-out buffering.

### 4.3 Public dynamic experiment checks transferable model physics

The source-specific Wang reconstruction reproduced multicomponent half-feed breakthrough times with a maximum absolute relative error of 11.37%, composition curves with a maximum species RMSE of 0.0229 mole fraction, and temperature traces with a maximum sensor RMSE of 2.37 C. Four cyclic pressure levels had an RMSE of 0.0666 bar. At engineering cyclic steady state, Run XII recovery differed from experiment by -0.666 percentage point, whereas eight-cell purity was underpredicted by 2.037 percentage points. The comparison supports the model family and its ledgers while preserving a clear apparatus-transfer boundary.

### 4.4 Staging is required to meet the joint separation target

Direct membrane evidence shows why a single ideal polisher is not an adequate engineering representation. A 1,050 cm2 multicomponent Pd/Au/Pd pilot achieved 98-99.87% purity and 64% recovery over 840 h [9]. A two-stage Pd-alloy experiment used a 99.99% purity and 80% recovery benchmark [10]. A binary repaired-Pd membrane reached 99.986% purity and 91% recovery [11], but the simple binary feed does not test the present contaminants. Published PSA-plus-membrane and staged concentration-plus-palladium simulations enter the present purity-recovery region [12,13]. More directly, the present polymer area normalizes to 0.513-0.530 m2 per Nm3 h-1 across all 16 cases, only 1.025-1.059 times the Zito 20-bar value of 0.5 m2 per Nm3 h-1 for 90% recovery [13]. The same public table supplies the exact polymer and Pd transport coefficients used here. This quantitative agreement supports parameter traceability and scale plausibility, while the differing feeds and pressures prevent it from serving as final validation.

The ideal literature-bounded train uses a 0.1892 m2 polymer stage and 0.4799 m2 dense-palladium stage. It passes all eight corners and eight hold-outs, with minimum recovery 93.450%, minimum qualified hydrogen 0.0024562 mol s-1, 4.616 mol surge capacity, and 1.546 mol receiver capacity. The conservative design-screen compression requirement is 2.573 kWh kg-1 H2 for the corrected 6.2-to-20 bar boundary and interstage recompression.

### 4.5 Adaptive integration corrects the final guard band

The fixed-section calculation suggested that 0.553 m2 would cover 20% permeance loss. Adaptive DOP853 integration found one failure, so bisection and upward rounding increased the guard to 0.554 m2. This revised area is a numerical and performance guard, not a membrane-manufacturing tolerance.

The 0.554 m2 design passed all 16 direct cases. Minimum recovery was 0.883221 and minimum qualified hydrogen was 0.00236055 mol s-1. Maximum CO, CO2, N2, and CH4 were 0.1204, 3.9998, 48.83, and 25.07 ppm. The receiver capacity was 1.2320 mol (30.541 L at 1 bar and 298.15 K), and module and receiver balance errors remained below 4.2e-17 and 1.3e-11 mol.

### 4.6 Corrected compression duty and external-simulator boundary

Changing the polishing inlet from the obsolete 8 bar assumption to the physically available 6.2 bar manifold increased the conservative design-screen compression requirement to 2.573 kWh kg-1 H2, without changing area, recovery, purity, or pass labels. A corrected 16-case DWSIM deck was generated. Its execution was blocked before solving by Windows Application Control, so earlier DWSIM results in Figure 8 are not used as corrected quantitative evidence.

### 4.7 The compact QAE event preserves the process decision

At 0.440 m2 installed dense-palladium area, 13 of 16 direct points passed. The error-buffered trilinear probability had a minimum-scramble value of 0.956673; the conservative affine probability was 0.951210. Ten-bit digitization gave 0.950629, an absolute probability error of 0.000581, with zero false-positive and zero false-negative direct labels. The included OpenQASM 3 oracle uses 66 logical qubits, 24,042 CX gates, 61,269 primitive gates, and all-to-all depth 36,163 before optimization or routing. It produced zero phase-label and restoration errors in exhaustive 2-, 3-, and 4-bit tests, all 16 direct 10-bit engineering states, and 4,096 seeded random 10-bit states.

RQMC is still the practical estimator for this smooth three-variable event. The quantum construction supplies a reproducible Boolean event, integer coefficients, register layout, and discretization error. It becomes computationally interesting only when future plant-calibrated uncertainty is higher-dimensional, process evaluation is expensive, and repeated risk queries can reuse the same oracle.

### 4.8 Public actual-syngas aging defines a larger conditional guard

A public coal-syngas membrane study reported a 40-50% loss of hydrogen permeance while Pd-Au selectivity remained stable for more than 473 h [21]. Under the conservative 50% retention stress, bisection required 0.8860 m2 and the installed guard was rounded to 0.887 m2. All 16 cases passed with minimum recovery 0.883679 and minimum qualified hydrogen 0.00236153 mol s-1.

### 4.9 A separately coded RK4 solver preserves both design decisions

At 192 sections per membrane, fixed-grid RK4 passed all 16 cases for both the 0.554 m2, 80%-retention guard and the 0.887 m2, 50%-retention guard. All 32 labels matched DOP853. The maximum recovery difference was 9.33e-8 percentage point, the maximum relative qualified-flow difference was 1.01e-9, and maximum component-balance error was 4.25e-17 mol.

### 4.10 Public flux data validate the concentration-polarization model form

The independently implemented Ververs model reproduced all 468 numeric H2/N2 records in the public workbook without fitting mixture-flux data. Including the published local Sherwood correlation gave 4.405% mean absolute relative error, 3.144% median absolute relative error, R2=0.9966, and 92.52% of predictions within 10% of experiment. The 192-section result differed from the 384-section result by at most 0.00577%. When concentration polarization was omitted while axial depletion and the same Richardson parameters were retained, mean absolute relative error increased to 29.016%, R2 decreased to 0.8481, and only 9.62% of predictions remained within 10%. The local film model predicted a median 19.94% flux penalty. This public raw-data reproduction independently verifies the need for concentration-polarization physics; its binary 2-5 bar, 350-450 C apparatus does not certify the present five-component 20-bar polisher.

### 4.11 High-pressure palladium evidence and legacy hot-stage cross-check

The earlier hot-stage DWSIM run resolved three-stage compression, a 420 C palladium heater, coolers, and Peng-Robinson closure for the preceding input set. The present corrected deck could not be executed under the host DLL policy, so Figure 13 documents the method and equipment structure rather than current energy numbers. Published 22 bar inhibition and 26 bar, 400 C endurance studies [23,24] independently support the pressure-temperature feasibility envelope but do not certify the final impurity vector.

The literature inhibition and endurance records support retaining an explicit permeance-loss guard. The 0.554 and 0.887 m2 designs are therefore interpreted as conditional engineering sizes tied to 80% and 50% permeance retention, respectively. A matched wet multicomponent module test remains necessary before converting either size into a procurement specification.

### 4.12 Public selectivity data define an incoming-module acceptance rule

Pressure-consistent bisection converts each impurity leakage channel into an incoming-module selectivity threshold. The rounded, simultaneous guard and all 16 direct confirmations are reported in Table 5 and Figure 14. Public defect-leaking selectivity vectors are retained as rejection stresses, which separates required area from required membrane integrity.

### 4.13 Full-syngas bench evidence has an analytical boundary

The Sanchez membrane produced a hydrogen-only permeate by the reported GC analysis under the full unconverted-shift-gas mixture, and maximum hydrogen recovery was about 47% at 723 K and 1 MPa [27]. The same study reported a pure-H2 permeance of 2.8 m3 m-2 h-1 kPa-0.5, pure-N2 or pure-CO2 permeate below 8 mL min-1 at 1 MPa, and no measured CO or steam in the permeate during binary and ternary tests. This is independent evidence that hot multicomponent Pd separation, reversible co-component inhibition, and nonzero recovery are physically credible. Its 100 ppm TCD accuracy is 200 times the project CO limit and 20 times the CO2 limit; the source therefore cannot validate the final component-selectivity vector or product gate. It closes a model-trend gap while leaving the matched analytical-validation gate explicit.

### 4.14 A synchronized public experiment fails the strict gate

The DOE/Pall flow ledger gives 75.98% H2 recovery, 75 ppm CO, and 450 ppm CO2 [28]. These values are 13.15 percentage points below the project recovery floor and 150 and 90 times the respective impurity limits. The corresponding system-level H2/CO and H2/CO2 separation factors are also far below the corrected incoming-module guards of 5,660 and 168,660. The experiment therefore supplies a synchronized empirical rejection control: measured impurity leakage, rather than membrane area alone, prevents entry into the joint pass region.

### 4.15 DOE/UTRC supplies a positive high-recovery validation anchor

The DOE/UTRC simulated-syngas durability mean of 93.4% recovery is 5.11 percentage points above the present 88.294% recovery floor [29]. The one-standard-deviation lower value is 85.4%, so the record supports target feasibility without proving a deterministic pass at every reported fluctuation. The pre-leak calculated purity of 99.9999% corresponds to approximately 1 ppm total non-H2, compared with the present 300 ppm bulk ceiling implied by 99.97% H2. After a small leak developed, the reported purity fell to about 99.98%, or 200 ppm total impurity, demonstrating how bulk purity can remain apparently acceptable while component-specific limits remain unknown. In the independent actual coal-gas run, the frozen model underpredicted product rate by 4.53% and recovery by 4.2 percentage points. Together these results add the positive side of the validation hierarchy: high recovery and bulk purity are physically achievable in a durable multicomponent Pd-Cu separator, and a physics model predicts actual-gas performance to engineering accuracy. Because the report does not resolve CO, CO2, N2, and CH4 in the permeate at the present limits, the component-specific acceptance gate remains open.

### 4.16 Published integrated operating points bracket the joint CO-recovery gate

Neither of the two reported Bang operating points satisfies the present joint event [30]. The 91.37% recovery point exceeds the project recovery floor by 3.076 percentage points but its 8.67 ppm CO is 17.34 times the 0.5 ppm limit. The 0.15 ppm CO point uses only 30% of the CO allowance but its 85.99% recovery is 2.304 percentage points below the floor. By comparison, the present conservative 0.887 m2 model has a worst-case pair of 88.3676% recovery and 0.1207 ppm CO, giving margins of only 0.0736 percentage point and 0.3793 ppm. The published pair therefore demonstrates the engineering conflict that motivates a joint event rather than separate purity and recovery summaries. It also makes the present claim falsifiable: a matched experiment must enter the upper-left pass region instead of reproducing either side of the observed tradeoff. Because the source used a reacting CMR, H2 sweep, and no N2 or CH4 in the reported feed, it does not certify the final five-component product.

### 4.17 Third-language packetwise transport preserves every decision

The compiled C# replay previously demonstrated that the transport implementation could be reproduced without membrane split inputs. It belongs to the superseded input set and is not counted as current pressure-consistent confirmation. The corrected claim is instead supported by direct packetwise DOP853 and the independently coded RK4 result in Section 4.9.

## 5 Discussion

### 5.1 Engineering meaning of the selected policy

The principal result is a physically closed material-allocation rule. Product hydrogen first secures the next cycle, the 6.2 bar manifold passively restores the 6.0 bar tank, and a booster supplies the 6.5 bar regeneration header when tank pressure falls below it. Shortening active purge and extending adsorption increased qualified saleable hydrogen without relaxing product quality or reserve gates.

The robust and chance designs answer different questions. The 0.4799 m2 ideal palladium stage passes all direct cases under the ideal dense-Pd assumption. The 0.440 m2 chance design accepts a small low-performance region under the declared uniform measure. The 0.554 and 0.887 m2 guards then address finite selectivity and permeance loss. These areas must be reported with their assumptions because they are not interchangeable.

### 5.2 Why the independent numerical failure strengthens the design

The 0.553-to-0.554 m2 correction is small in area but important in logic because the event lies near its recovery boundary. Adaptive integration exposed the missed failure, and the independent RK4 mesh reproduced the corrected 32 labels to much tighter tolerance than the engineering margin. This adverse result supports the final guard rather than being hidden as solver noise.

### 5.3 Separation journal relevance and experimental boundary

The work contributes a separation-process operating rule: pressure-consistent regeneration inventory, strict product quality, and uncertain feed and adsorption performance are optimized together. Public experiments validate transferable dynamic, mass-transfer, inhibition, recovery, and rejection behavior, while their measurement limits are carried into the claim boundary. The missing experiment is a synchronized test of the final integrated apparatus at the declared ppm limits.

### 5.4 Quantum role and computational boundary

QAE is subordinate to the separation result. Current RQMC is cheaper for this three-dimensional response. The quantum contribution is the auditable reduction from a physical membrane-area chance constraint to a verified discrete reversible event with known probability error, a portable OpenQASM implementation, and explicit pre-routing resources. The 24,042-CX count is a reproducible upper-level resource baseline rather than an optimized device cost, and no hardware-advantage claim is made.

### 5.5 Limitations

The main limitations are the uniform engineering uncertainty measure, transfer of adsorption and membrane parameters across apparatuses, common constitutive laws in DOP853 and RK4, absence of a corrected-input DWSIM execution on the restricted host, lack of device-specific quantum routing and execution, and the lack of a matched component-resolved integrated experiment. Public membrane studies establish feasibility, recovery scale, degradation stresses, and rejection cases, but their feeds, pressures, modules, and analytical resolutions differ. These boundaries define the next validation work and do not change the pressure-consistent numerical design decision reported here.

## 6 Conclusions

A finite regeneration inventory makes hydrogen PSA an allocation problem between the next cycle and sale. The physically feasible design uses a 6.0 bar tank passively filled from the 6.2 bar product manifold and a booster to the 6.5 bar regeneration header. The selected 4 s purge and 540 s adsorption policy passed 8/8 uncertainty corners and 8/8 predeclared hold-outs, increased qualified shipment by 6.785-7.341%, and kept conservative booster duty below 0.198 kWh kg-1 H2.

The staged polishing train combines a 0.1892 m2 polymer concentrator with dense-palladium polishing. Adaptive integration set the 20%-loss guard at 0.554 m2; it passed 16/16 cases with minimum recovery 88.322% and every impurity below its limit. A public 50%-retention actual-syngas stress increased the conditional guard to 0.887 m2 and again passed 16/16. Independent RK4 preserved all 32 final labels, confirming that the design decision is insensitive to the numerical integrator and refined area mesh.

The physical chance event at 0.440 m2 has conservative continuous probability 0.951210 and 10-bit discrete probability 0.950629 with no direct label errors. The verified portable oracle requires 66 logical qubits and has an exact pre-routing count of 24,042 CX gates. RQMC remains preferred for the present model; QAE becomes relevant when validated plant uncertainty and repeated probability queries make classical event evaluation expensive. Device-specific quantum execution, a corrected-input DWSIM solve, and a synchronized integrated experiment remain external validation steps.

## CRediT authorship contribution statement

Ugwiyeon Lee: Conceptualization, Methodology, Software, Formal analysis, Investigation, Data curation, Visualization, Writing - original draft, Writing - review and editing, Project administration. Seong-Yun Bae: Writing - review and editing. Hakrae Kim: Writing - review and editing. Jungsu Lee: Writing - review and editing.

## Declaration of competing interest

The authors declare no competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

## Data and code availability

The complete calculation records, direct states, portable OpenQASM circuit, DWSIM input deck, figures, tables, and SHA-256 manifests are archived under the version-independent repository DOI https://doi.org/10.5281/zenodo.23271866 and mirrored at https://github.com/lyullee/psa-qae-resource-audit.

## Declaration of generative AI and AI-assisted technologies

During manuscript preparation, the authors used OpenAI Codex for code drafting and refactoring, local workflow orchestration, figure and table generation, manuscript organization, and language editing. The authors reviewed and edited the outputs, reran the documented analyses, verified numerical claims and sources, and take full responsibility for the publication.

## References

[1] J. Yang, C.-H. Lee, J.-W. Chang, Separation of hydrogen mixtures by a two-bed pressure swing adsorption process using zeolite 5A, Ind. Eng. Chem. Res. 36 (1997) 2789-2798. https://doi.org/10.1021/ie960728h.
[2] A.M. Ribeiro, C.A. Grande, F.V.S. Lopes, J.M. Loureiro, A.E. Rodrigues, Four beds pressure swing adsorption for hydrogen purification: case of humid feed and activated carbon beds, AIChE J. 55 (2009) 2292-2302. https://doi.org/10.1002/aic.11886.
[3] H. Khajuria, E.N. Pistikopoulos, Optimization and control of pressure swing adsorption processes under uncertainty, AIChE J. 59 (2013) 120-131. https://doi.org/10.1002/aic.13783.
[4] Y. Park, J.-H. Kang, D.-K. Moon, Y.S. Jo, C.-H. Lee, Parallel and series multi-bed pressure swing adsorption processes for H2 recovery from a lean hydrogen mixture, Chem. Eng. J. 408 (2021) 127299. https://doi.org/10.1016/j.cej.2020.127299.
[5] T. Kim, J.K. Scott, Dynamic modeling and simulation of pressure swing adsorption processes using toPSAil, Comput. Chem. Eng. 176 (2023) 108309. https://doi.org/10.1016/j.compchemeng.2023.108309.
[6] S. Ga, N. An, C. Joo, J. Kim, pyAPEP: an all-in-one software package for the automated preparation of adsorption process simulations, Comput. Phys. Commun. 291 (2023) 108830. https://doi.org/10.1016/j.cpc.2023.108830.
[7] A. Golmakani, S.A. Nabavi, V. Manovic, Data for the paper Effect of impurities on ultra-pure hydrogen production by pressure vacuum swing adsorption, Cranfield Online Research Data (2019). https://doi.org/10.17862/cranfield.rd.10123346.
[8] J. Wang, X. Chen, T. Du, L. Liu, P.A. Webley, G.K. Li, Hydrogen production from low pressure coke oven gas by vacuum pressure swing adsorption, Chem. Eng. J. 472 (2023) 144920. https://doi.org/10.1016/j.cej.2023.144920.
[9] B. Castro-Dominguez, I.P. Mardilovich, R. Ma, N.K. Kazantzis, A.G. Dixon, Y.H. Ma, Performance of a pilot-scale multitube membrane module under coal-derived syngas for hydrogen production and separation, J. Membr. Sci. 523 (2017) 515-523. https://doi.org/10.1016/j.memsci.2016.10.024.
[10] A. Iulianelli, A. Brunetti, L. Pino, C. Italiano, G.D. Ferrante, M. Gensini, A. Vita, An integrated two stages inorganic membrane-based system to generate and recover decarbonized H2: An experimental study and performance indexes analysis, Renew. Energy 210 (2023) 472-485. https://doi.org/10.1016/j.renene.2023.04.095.
[11] J. Yu, J. Zhang, C. Bao, H. Li, H. Xu, J. Sun, Confined and in-situ zeolite synthesis: A novel strategy for defect reparation over dense Pd membranes for hydrogen separation, Sep. Purif. Technol. 184 (2017) 43-53. https://doi.org/10.1016/j.seppur.2017.04.035.
[12] B. Li, G. He, X. Jiang, Y. Dai, X. Ruan, Pressure swing adsorption/membrane hybrid processes for hydrogen purification with a high recovery, Front. Chem. Sci. Eng. 10 (2016) 255-264. https://doi.org/10.1007/s11705-016-1567-1.
[13] P.F. Zito, A. Brunetti, G. Barbieri, Hydrogen concentration and purification by membrane process: A multistage analysis, Renew. Energy 218 (2023) 119243. https://doi.org/10.1016/j.renene.2023.119243.
[14] S. Woerner, D.J. Egger, Quantum risk analysis, npj Quantum Inf. 5 (2019) 15. https://doi.org/10.1038/s41534-019-0130-6.
[15] G. Brassard, P. Hoyer, M. Mosca, A. Tapp, Quantum amplitude amplification and estimation, Contemp. Math. 305 (2002) 53-74.
[16] A. Callison, D.E. Browne, Improved maximum-likelihood quantum amplitude estimation, arXiv:2209.03321 (2022). https://arxiv.org/abs/2209.03321.
[17] J. He et al., An efficient quantum computing based structural reliability analysis method using quantum amplitude estimation, Struct. Saf. 114 (2025) 102555. https://doi.org/10.1016/j.strusafe.2024.102555.
[18] P. Virtanen et al., SciPy 1.0: fundamental algorithms for scientific computing in Python, Nat. Methods 17 (2020) 261-272. https://doi.org/10.1038/s41592-019-0686-2.
[19] A.B. Owen, Scrambled net variance for integrals of smooth functions, Ann. Stat. 25 (1997) 1541-1562. https://doi.org/10.1214/aos/1031594731.
[20] D. Medeiros, DWSIM open-source chemical process simulator, https://dwsim.org (accessed 12 October 2026).
[21] F. Guazzone, J. Catalano, I.P. Mardilovich, T. Wu, R.C. Lambrecht, S. Datta, J. Kniep, S. Pande, N.K. Kazantzis, Y.H. Ma, Enhancement of the long-term permeance, selectivity stability, and recoverability of Pd-Au membranes in coal derived syngas atmospheres, Energy Fuels 27 (2013) 4150-4160. https://doi.org/10.1021/ef302130s.
[22] W.J.R. Ververs, M. Ongis, A. Arratibel, L. Di Felice, F. Gallucci, On the modeling of external mass transfer phenomena in Pd-based membrane separations, Int. J. Hydrogen Energy 71 (2024) 1121-1133. https://doi.org/10.1016/j.ijhydene.2024.04.337. Dataset: https://doi.org/10.5281/zenodo.7961792.
[23] J. Boon, J.A.Z. Pieterse, F.P.F. van Berkel, Y.C. van Delft, M. van Sint Annaland, Hydrogen permeation through palladium membranes and inhibition by carbon monoxide, carbon dioxide, and steam, J. Membr. Sci. 496 (2015) 344-358. https://doi.org/10.1016/j.memsci.2015.08.061.
[24] T.A. Peters, M. Stange, H. Klette, R. Bredesen, High pressure performance of thin Pd-23%Ag/stainless steel composite membranes in water gas shift gas mixtures; influence of dilution, mass transfer and surface effects on the hydrogen flux, J. Membr. Sci. 316 (2008) 119-127. https://doi.org/10.1016/j.memsci.2007.08.056.
[25] H. Li, A. Goldbach, W. Li, H. Xu, WGS-mixture separation and WGS reaction test in a bench-scale multi-tubular membrane reactor, Energy Procedia 4 (2011) 666-673. https://doi.org/10.1016/j.egypro.2011.01.103.
[26] Media and Process Technology Inc., Development of a Novel Membrane Reactor for Direct Hydrogen Production from Coal, final technical report DE-FG36-04GO14330, U.S. Department of Energy (2005). https://www.osti.gov/servlets/purl/883041.
[27] J.M. Sanchez, M.M. Barreiro, M. Marono, Bench-scale study of separation of hydrogen from gasification gases using a palladium-based membrane reactor, Fuel 116 (2014) 894-903. https://doi.org/10.1016/j.fuel.2013.02.051.
[28] J. Acquaviva, High Performance Palladium-Based Membrane for Hydrogen Separation and Purification, DOE Hydrogen Program FY 2008 Annual Progress Report, contract DE-FG36-05GO15093, pp. 57-62 (2008). https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/progress08/ii_a_9_acquaviva.pdf.
[29] S. Emerson, N. Magdefrau, Y. She, C. Thibaud-Erkey, Advanced Palladium Membrane Scale-up for Hydrogen Separation, final technical report DE-FE0004967, U.S. Department of Energy (2012). https://doi.org/10.2172/1063878.
[30] G. Bang, D.K. Moon, J.H. Kang, Y.J. Han, K.M. Kim, C.H. Lee, High-purity hydrogen production via a water-gas-shift reaction in a palladium-copper catalytic membrane reactor integrated with pressure swing adsorption, Chem. Eng. J. 411 (2021) 128473. https://doi.org/10.1016/j.cej.2021.128473.