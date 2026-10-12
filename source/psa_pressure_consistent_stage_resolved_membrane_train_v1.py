"""Run the frozen stage-resolved membrane train on the corrected 6-bar PSA data."""

from __future__ import annotations

import os

os.environ["PSA_STAGE_INPUT_VARIANT"] = "pressure_consistent_6bar_v1"
os.environ["PSA_STAGE_OUTPUT_DIR"] = "pressure_consistent_stage_resolved_membrane_train_v1"
os.environ["PSA_STAGE_UPSTREAM_PRESSURE_PA"] = "620000"

from psa_qae.psa_stage_resolved_membrane_train import main  # noqa: E402


if __name__ == "__main__":
    main()
