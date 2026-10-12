# Ververs 2024 public raw-data reproduction

- Records evaluated: **468**.
- Published local Sherwood form, independent RK4 MARE: **4.41%**.
- Published local Sherwood form, within 10%: **92.52%**.
- No-CP MARE: **29.02%**.
- No-CP within 10%: **9.62%**.
- Median predicted flux reduction from concentration polarization: **19.94%**.
- Maximum 192-vs-384-section flux difference: **0.00577%**.

The implementation uses the paper's equations and tabulated membrane parameters without fitting to the mixture-flux data. Fuller binary diffusivity and a 22.414 L/mol normal-flow basis are independent implementation choices.
The public workbook contains 468 numeric mixture records, whereas the article states 423. All 468 records are retained without undocumented filtering.

This validates binary-gas model form and trend only. It does not validate the final five-component 20-bar polishing result or poisoning guard.
