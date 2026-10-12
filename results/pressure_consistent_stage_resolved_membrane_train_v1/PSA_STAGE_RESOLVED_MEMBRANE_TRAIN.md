# Stage-resolved concentration + dense-Pd membrane train

## Engineering result

The saved dynamic PSA outlet from all eight uncertainty corners and all eight predeclared interior hold-outs was passed through a finite surge buffer, two explicit membrane stages, and a co-sized finite receiver. The selected single-pass train is:

- stage 1: **polymer H2 concentrator, 0.1892 m²**;
- stage 2: **ideal dense-Pd H2 polisher, 0.4799 m²**;
- cyclic-flow surge buffer: **4.6159 mol (5.721 L at 20 bar and 298 K)**;
- feed/permeate pressures: **20/1 bar** for both membrane stages;
- interstage permeate recompression: **1 to 20 bar**;
- internal recycle: **0**; both retentates are routed to fuel/offgas;
- receiver: **1.5460 mol (38.324 L at 1 bar and 298 K)** with the frozen heel fraction and constant-outlet controller.

The area search was bounded by the Zito et al. flow-scaled polymer/carbon + Pd configurations. It first required all 16 direct cases to meet the frozen recovery and qualified-shipment floors. Among configurations within 0.1% of the maximum worst-case shipment, it minimized Pd area, total area, and compression energy.

## Direct dynamic confirmation

| result | value |
|---|---:|
| corner passes | 8/8 |
| predeclared hold-out passes | 8/8 |
| minimum overall H2 recovery | 93.450% |
| minimum qualified H2 rate | 0.0024562 mol/s |
| minimum H2 entering Pd stage | 92.976% |
| maximum compression-only energy | 2.360 kWh/kg H2 |
| installed surge-buffer capacity | 4.6159 mol |
| installed product-receiver capacity | 1.5460 mol |
| minimum inherited regeneration-tank pressure | 3.5311 bar |
| maximum module balance residual | 3.886e-16 mol |
| maximum receiver balance residual | 8.233e-10 mol |

All 16 packet-wise receiver calculations pass the continuous product gate and inventory gate. The selected train therefore replaces the former 2,214 cm² single-stage interpretation with an explicit physical architecture while preserving the engineering event.

## Strict impurity implication

Pre-concentration reduces the worst ideal selectivity required at the Pd feed by the following factors:

| impurity | direct raw-feed requirement | worst after stage 1 | reduction |
|---|---:|---:|---:|
| CO | 53,869.1 | 885.3 | 60.85× |
| CO2 | 152,647.9 | 7,946.9 | 19.21× |
| N2 | 3,276.4 | 117.6 | 27.86× |
| CH4 | 573.1 | 5.2 | 111.04× |


The dense-Pd stage is ideal and defect-free in this calculation, so its modeled product is pure H2. The table quantifies the finite-selectivity performance that a real module must demonstrate. It does not replace component-resolved measurements.

## Numerical and energy boundaries

The recovery change between the 72/144 and 144/288 area meshes is **9.432e-04** (0.094 percentage point). The fine-mesh recovery margin above the frozen gate is **5.062 percentage points**, or **53.7 times** the mesh change, and the pass decision is unchanged at all three resolutions. The 60-cycle PSA horizon, tank reserve, CSS, and conservation evidence are inherited from each saved source trajectory. Energy includes isothermal compression at 72% efficiency; heating, cooling, pressure drop, vacuum, membrane cost, lifetime, and retentate fuel credit remain open.
