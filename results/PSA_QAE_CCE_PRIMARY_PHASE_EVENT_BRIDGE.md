# Primary phase-stream to chance-event bridge

Eight phase-specific ridge maps predict aggregate bed-state increments and five-component inlet/outlet streams. Each outer held run is predicted by maps fitted to the other 31 runs, with ridge strength selected by an inner leave-one-out loop. The two held-out adsorption stream predictions are combined with the declared product-recycle split to reconstruct purity, external recovery, and the frozen event.

Event labels match in 32/32 held runs (1.000); false positives=0 and false negatives=0. Purity MAE is 3.790e-08 and recovery MAE is 7.272e-05.

| bed | phase | p95 state-increment L1 | p95 inlet-stream L1 | p95 outlet-stream L1 |
|---|---|---:|---:|---:|
| A | adsorption | 0.00033 | 0.00008 | 0.00006 |
| A | blowdown | 0.00006 | 0.00000 | 0.00006 |
| A | pressurization | 0.00020 | 0.00017 | 0.00000 |
| A | purge | 0.00011 | 0.00001 | 0.00001 |
| B | adsorption | 0.00063 | 0.00015 | 0.00015 |
| B | blowdown | 0.00009 | 0.00000 | 0.00007 |
| B | pressurization | 0.00007 | 0.00007 | 0.00000 |
| B | purge | 0.00019 | 0.00002 | 0.00003 |

This closes event observability only conditional on the actual held phase-start states. The phase maps are not composed through equalization and repeated CSS, and no plant or end-to-end quantum claim follows.
