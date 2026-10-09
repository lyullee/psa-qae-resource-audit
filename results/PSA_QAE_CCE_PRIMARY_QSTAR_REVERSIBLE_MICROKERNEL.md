# Reversible competitive-Langmuir numerator/denominator microkernel

The screen uses **25,856** cell states from all 32 physical 100-cycle trajectories. The compiled block prepares the shared five-component affinity sum, `P*y_CO2`, and the scaled denominator `1 + P sum(b_i y_i)` in separate output registers.

The first tier passing p95 denominator error <= `1e-03`, p95 CO2 qstar-factor error <= `0.05`, and zero nonzero-numerator erasures is **18 bits**. It uses **266 logical qubits**, depth **186,885**, **127,112 forward CX**, and **254,224 clean-equivalent CX** in an all-to-all `u/CX` basis.

The equilibrium reciprocal/division, final loading scaling, all five outputs, LDF update, and ODE time integration are not compiled. The result is a measured nonlinear subkernel boundary rather than a completed physical phase or cycle oracle.
