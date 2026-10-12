"""Run the membrane and aging validation chain on corrected 6-bar PSA traces."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
STEPS = [
    ("stage_train", "psa_stage_resolved_membrane_train.py"),
    ("physical_qae", "psa_physical_pd_area_qae_bridge.py"),
    ("finite_leakage", "psa_pd_leakage_aging_sensitivity.py"),
    ("independent_ode", "psa_independent_ode_membrane_audit.py"),
    ("actual_syngas_guard", "psa_pd_syngas_poisoning_guard_v1.py"),
]


def environment() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PSA_STAGE_INPUT_VARIANT": "pressure_consistent_6bar_v1",
            "PSA_STAGE_OUTPUT_DIR": "pressure_consistent_stage_resolved_membrane_train_v1",
            "PSA_QAE_TRAIN_DIR": "pressure_consistent_stage_resolved_membrane_train_v1",
            "PSA_QAE_OUTPUT_DIR": "pressure_consistent_physical_pd_area_qae_bridge_v1",
            "PSA_PD_TRAIN_DIR": "pressure_consistent_stage_resolved_membrane_train_v1",
            "PSA_PD_SENSITIVITY_OUTPUT_DIR": "pressure_consistent_pd_leakage_aging_sensitivity_v1",
            "PSA_ODE_TRAIN_DIR": "pressure_consistent_stage_resolved_membrane_train_v1",
            "PSA_ODE_PD_DIR": "pressure_consistent_pd_leakage_aging_sensitivity_v1",
            "PSA_ODE_OUTPUT_DIR": "pressure_consistent_independent_ode_membrane_audit_v1",
            "PSA_SYNGAS_ODE_DIR": "pressure_consistent_independent_ode_membrane_audit_v1",
            "PSA_SYNGAS_OUTPUT_DIR": "pressure_consistent_pd_actual_syngas_poisoning_guard_v1",
        }
    )
    return env


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-step", choices=[name for name, _ in STEPS], default=STEPS[0][0])
    parser.add_argument("--through-step", choices=[name for name, _ in STEPS], default=STEPS[-1][0])
    args = parser.parse_args()
    start_index = [name for name, _ in STEPS].index(args.from_step)
    end_index = [name for name, _ in STEPS].index(args.through_step)
    if end_index < start_index:
        raise ValueError("through-step precedes from-step")
    records = []
    for name, filename in STEPS[start_index : end_index + 1]:
        started = time.time()
        completed = subprocess.run(
            [sys.executable, str(HERE / filename)],
            cwd=str(HERE),
            env=environment(),
            check=True,
        )
        records.append(
            {
                "step": name,
                "script": filename,
                "returncode": completed.returncode,
                "wall_time_s": time.time() - started,
            }
        )
        print(json.dumps(records[-1]), flush=True)
    print(json.dumps({"status": "pressure_consistent_membrane_chain_complete", "steps": records}, indent=2))


if __name__ == "__main__":
    main()
