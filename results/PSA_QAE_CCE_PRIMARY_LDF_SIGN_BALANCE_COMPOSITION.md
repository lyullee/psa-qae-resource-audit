# Direct LDF-to-loading-sign-to-cell-balance composition

The widened LDF precision screen covers **25,856** physical cell states. The downstream balance interface covers **64,640** component balances. No QPU job was submitted.

| Component | old bits | compatible bits | address bits | widened LDF qubits | widened LDF CX | composed qubits | composed depth | composed CX |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H2 | 20 | 26 | 8 | 530 | 2,107,572 | 861 | 7,871,973 | 4,991,534 |
| CO2 | 24 | 26 | 5 | 527 | 1,252,758 | 869 | 4,949,239 | 3,412,254 |
| CH4 | 20 | 32 | 4 | 562 | 1,279,980 | 926 | 5,128,934 | 3,579,478 |
| CO | 20 | 32 | 4 | 562 | 1,279,980 | 929 | 5,128,934 | 3,593,420 |
| N2 | 20 | 30 | 4 | 550 | 1,252,708 | 920 | 5,030,941 | 3,506,166 |

With one shared pressure/composition input and sequential component workspace reuse, the five-component accounting is **1,317 logical qubits**, **19,082,852 additive CX**, and additive all-to-all depth **28,110,021**.

The circuit maps each widened LDF current/next-loading register directly into sign extraction, solid-mass conversion, and conservative next-gas accumulation, then reverses the conversion and LDF work. Face-flux generation, composition normalization, reversible run-specific parameters, boundary withdrawal, adaptive integration, routing, and the complete phase/cycle remain open.
