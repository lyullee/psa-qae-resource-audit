# Coherent gas-inventory-to-dynamic-Langmuir/LDF/balance paths

Status: **gas_inventory_to_dynamic_langmuir_ldf_balance_five_component_paths_compiled**

Three raw five-component gas inventories now generate both normalized upwind compositions, the pressure triplet, and two oriented face-flux vectors. The centre pressure/composition and component face words feed the coherent run/stage controller, dynamic run-affinity Langmuir response, q*/LDF/loading conversion, and conservative balance directly; all temporary transport and controller registers are reversed.

The frozen support contains **25,856 normalization states** and **64,640 component-balance records**. The dynamic response uses **8 affinity bits** and **4,096 reciprocal segments**.

| component | response p95/max | q* p95/max | LDF-next p95/max | next-gas p95/max | pass |
|---|---:|---:|---:|---:|---|
| H2 | 1.710e-04/2.917e-04 | 1.588e-04/2.852e-04 | 1.119e-04/1.967e-04 | 8.753e-05/2.040e-04 | True |
| CO2 | 1.316e-06/1.744e-05 | 1.194e-06/1.676e-05 | 4.349e-08/6.163e-07 | 1.007e-05/1.116e-04 | True |
| CH4 | 1.063e-06/2.296e-06 | 9.540e-07/1.927e-06 | 1.888e-07/3.782e-07 | 8.467e-05/1.944e-04 | True |
| CO | 1.071e-06/1.408e-06 | 9.488e-07/1.341e-06 | 1.432e-07/1.939e-07 | 1.783e-04/3.997e-04 | True |
| N2 | 9.026e-07/1.515e-06 | 8.119e-07/1.287e-06 | 2.184e-07/3.328e-07 | 7.673e-05/1.329e-04 | True |

| compiled component path | logical qubits | depth | CX |
|---|---:|---:|---:|
| H2 | 2,696 | 89,147,751 | 55,337,688 |
| CO2 | 2,697 | 89,147,751 | 55,364,870 |
| CH4 | 2,885 | 89,147,751 | 56,289,028 |
| CO | 2,876 | 89,147,751 | 56,172,020 |
| N2 | 2,871 | 89,147,751 | 56,156,326 |

Continuous off-ledger tank demand, out-of-support flow reversal/normalization, monolithic five-component phase/cycle integration, routing, external H2 validation, and quantum advantage remain open.

No QPU job was submitted.
