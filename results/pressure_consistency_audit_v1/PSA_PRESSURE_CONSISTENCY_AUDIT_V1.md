# PSA regeneration-tank pressure consistency audit

The frozen six-cell inventory ledger was checked against the pressures used by
the adsorption and regeneration boundaries.

- adsorption/source header: **6.500 bar**
- adsorption product-manifold backpressure: **6.200 bar**
- selected tank set point: **7.000 bar**
- selected passive-fill margin: **-0.800 bar**
- selected minimum tank pressure: **4.531 bar**
- worst unboosted delivery margin: **-1.969 bar**
- unboosted hydraulic passes: **0/16**

The component ledger closes, but an uncompressed 6.2-bar product manifold
cannot refill a 7.0-bar tank.  The tank also falls below the 6.5-bar pressure
assumed by the purge and pressurization source boundary.  The next operating
screen therefore uses passive refill at a tank set point no greater than 6.0
bar and explicitly treats tank discharge as a boosted service.
