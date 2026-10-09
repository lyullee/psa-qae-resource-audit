# Coherent run-factor to five-component LDF coefficient interface

The frozen 32-run controller now feeds reversible arithmetic rather than ending at a parameter register. Its 12-bit capacity, affinity, and LDF-factor words generate a capacity-affinity product, five component equilibrium prefactors, five LDF alpha coefficients, and two adsorption-active flags decoded from the synchronized paired-bed schedule.

The table audit checks **320 component coefficients** and **16 bed/stage flags**. The equilibrium-prefactor p95/maximum relative errors are **2.301e-05/4.987e-05**; the LDF-alpha p95/maximum errors are **2.698e-05/4.356e-05**.

The directly transpiled circuit uses **495 logical qubits**, depth **526,434**, **353,441 CX**, and **436,305 u** gates, with no measurement or reset. It clears the multiplier, weighted-adder, QROM, constant, and flag workspaces while retaining the parameter, schedule, coefficient, and adsorption-flag registers.

This is a finite-support controller-to-kinetics coefficient interface. Direct use of the coefficient registers inside the pressure/composition reciprocal, loading update, component balance, off-ledger tank demand, and adaptive phase/cycle remains open.

Artifacts: `PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.json`, `PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.csv`. No QPU job was submitted.
