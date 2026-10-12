"""Run the selectivity acceptance audit on the pressure-consistent 6-bar train."""

from __future__ import annotations

import os

os.environ["PSA_STAGE_INPUT_VARIANT"] = "pressure_consistent_6bar_v1"
os.environ["PSA_STAGE_OUTPUT_DIR"] = "pressure_consistent_stage_resolved_membrane_train_v1"
os.environ["PSA_STAGE_UPSTREAM_PRESSURE_PA"] = "620000"
os.environ["PSA_PD_TRAIN_DIR"] = "pressure_consistent_stage_resolved_membrane_train_v1"
os.environ["PSA_PD_SENSITIVITY_OUTPUT_DIR"] = "pressure_consistent_pd_leakage_aging_sensitivity_v1"
os.environ["PSA_ODE_TRAIN_DIR"] = "pressure_consistent_stage_resolved_membrane_train_v1"
os.environ["PSA_ODE_PD_DIR"] = "pressure_consistent_pd_leakage_aging_sensitivity_v1"
os.environ["PSA_ODE_OUTPUT_DIR"] = "pressure_consistent_independent_ode_membrane_audit_v1"
os.environ["PSA_SELECTIVITY_ODE_DIR"] = "pressure_consistent_independent_ode_membrane_audit_v1"
os.environ["PSA_SELECTIVITY_OUTPUT_DIR"] = "pressure_consistent_public_selectivity_acceptance_audit_v1"

from psa_qae.psa_public_selectivity_acceptance_audit_v1 import main  # noqa: E402


if __name__ == "__main__":
    main()
