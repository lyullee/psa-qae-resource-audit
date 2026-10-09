"""Audit the CCE manuscript draft without claiming that open evidence gates are closed."""

from __future__ import annotations

import json
import re
from zipfile import ZipFile
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from lxml import etree


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
MANUSCRIPT = RESULTS / "PSA_QAE_CCE_CORE_MANUSCRIPT_DRAFT.md"
BIB = RESULTS / "PSA_QAE_SCI_REFERENCES.bib"
WORKFLOW_PNG = RESULTS / "PSA_QAE_CCE_WORKFLOW_FIGURE.png"
WORKFLOW_PDF = RESULTS / "PSA_QAE_CCE_WORKFLOW_FIGURE.pdf"
FIGURE_PLAN = RESULTS / "PSA_QAE_CCE_FIGURE_TABLE_PLAN_2026-10-09.md"
GATE_MANIFEST = RESULTS / "PSA_QAE_CCE_GATE_COMPILATION_MANIFEST.json"
CLAIMS_AUDIT = RESULTS / "PSA_QAE_SCI_CLAIMS_AUDIT.json"
PHASE_FIXED_JSON = RESULTS / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN.json"
PHASE_FIXED_PNG = RESULTS / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN_FIGURE.png"
PHASE_COMPILE_JSON = RESULTS / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE.json"
PHASE_COMPILE_PNG = RESULTS / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE_FIGURE.png"
SMALL_E2E_JSON = RESULTS / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.json"
SMALL_E2E_PNG = RESULTS / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE_FIGURE.png"
H2_RESOLUTION_JSON = RESULTS / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.json"
H2_RESOLUTION_PNG = RESULTS / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT_FIGURE.png"
TOPSAIL_YANG_JSON = RESULTS / "PSA_QAE_CCE_TOPSAIL_YANG_H2_PUBLIC_MODEL_AUDIT.json"
TOPSAIL_YANG_PNG = RESULTS / "PSA_QAE_CCE_TOPSAIL_YANG_H2_PUBLIC_MODEL_AUDIT_FIGURE.png"
PUBLIC_H2_AUDIT_JSON = RESULTS / "PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.json"
PUBLIC_H2_AUDIT_MD = RESULTS / "PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.md"
PROSPECTIVE_DESIGN_JSON = RESULTS / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.json"
PROSPECTIVE_DESIGN_PNG = RESULTS / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT_FIGURE.png"
PRIMARY_PHASE_LEDGER_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
PRIMARY_PHASE_LEDGER_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER_FIGURE.png"
PRIMARY_PHYSICAL_CSS_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.json"
PRIMARY_PHYSICAL_CSS_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT_FIGURE.png"
PRIMARY_QSTAR_MICROKERNEL_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.json"
PRIMARY_QSTAR_MICROKERNEL_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL_FIGURE.png"
PRIMARY_QSTAR_LDF_MICROSTEP_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.json"
PRIMARY_QSTAR_LDF_MICROSTEP_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP_FIGURE.png"
PRIMARY_EVENT_BRIDGE_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.json"
PRIMARY_EVENT_BRIDGE_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE_FIGURE.png"
PRIMARY_EVENT_FIXED_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.json"
PRIMARY_EVENT_FIXED_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN_FIGURE.png"
PRIMARY_EVENT_COMPILE_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.json"
PRIMARY_EVENT_COMPILE_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE_FIGURE.png"
PRIMARY_FINAL_EVENT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.json"
PRIMARY_FINAL_EVENT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.png"
PRIMARY_POLICY_STREAM_EVENT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.json"
PRIMARY_POLICY_STREAM_EVENT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.png"
PRIMARY_FREE_RUNNING_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING.json"
PRIMARY_FREE_RUNNING_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING_FIGURE.png"
PRIMARY_REPEATED_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN.json"
PRIMARY_REPEATED_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN_FIGURE.png"
CSS_INITIALIZER_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.json"
CSS_INITIALIZER_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE_FIGURE.png"
CSS_REPEATED_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.json"
CSS_REPEATED_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN_FIGURE.png"
CSS_STABILITY_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.json"
CSS_STABILITY_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN_FIGURE.png"
CSS_FIXED_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.json"
CSS_FIXED_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN_FIGURE.png"
CSS_COMPILE_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.json"
CSS_COMPILE_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE_FIGURE.png"
RESOURCE_LADDER_PNG = RESULTS / "PSA_QAE_CCE_RESOURCE_LADDER_FIGURE.png"
RESOURCE_LADDER_PDF = RESULTS / "PSA_QAE_CCE_RESOURCE_LADDER_FIGURE.pdf"
RESOURCE_TABLE_JSON = RESULTS / "PSA_QAE_CCE_RESOURCE_TABLE3.json"
RESOURCE_TABLE_MD = RESULTS / "PSA_QAE_CCE_RESOURCE_TABLE3.md"
TABLE1_JSON = RESULTS / "PSA_QAE_CCE_TABLE1_FROZEN_PROTOCOL.json"
TABLE1_MD = RESULTS / "PSA_QAE_CCE_TABLE1_FROZEN_PROTOCOL.md"
TABLE2_JSON = RESULTS / "PSA_QAE_CCE_TABLE2_MATCHED_ESTIMATORS.json"
TABLE2_MD = RESULTS / "PSA_QAE_CCE_TABLE2_MATCHED_ESTIMATORS.md"
TABLE4_JSON = RESULTS / "PSA_QAE_CCE_TABLE4_EVIDENCE_HIERARCHY.json"
TABLE4_MD = RESULTS / "PSA_QAE_CCE_TABLE4_EVIDENCE_HIERARCHY.md"
COHERENT_RUN_SCHEDULE_TANK_JSON = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.json"
COHERENT_RUN_SCHEDULE_TANK_MD = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.md"
COHERENT_RUN_FACTOR_LDF_JSON = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.json"
COHERENT_RUN_FACTOR_LDF_MD = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.md"
COHERENT_COEFFICIENT_LDF_BALANCE_JSON = RESULTS / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.json"
COHERENT_COEFFICIENT_LDF_BALANCE_MD = RESULTS / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.md"
COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_JSON = RESULTS / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.json"
COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_MD = RESULTS / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.md"
COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE_JSON = RESULTS / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.json"
COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE_MD = RESULTS / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.md"
OFFLEDGER_TANK_SATURATION_JSON = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.json"
OFFLEDGER_TANK_SATURATION_MD = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.md"
OFFLEDGER_TANK_PROPORTIONAL_JSON = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.json"
OFFLEDGER_TANK_PROPORTIONAL_MD = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.md"
FIGURE2_PNG = RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION_FIGURE.png"
FIGURE2_PDF = RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION_FIGURE.pdf"
FIGURE3_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY_FIGURE.png"
FIGURE3_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY_FIGURE.pdf"
FIGURE5_PNG = RESULTS / "FIG_QPU_MLAE_HARDWARE_BOUNDARY.png"
FIGURE5_PDF = RESULTS / "FIG_QPU_MLAE_HARDWARE_BOUNDARY.pdf"
FIGURE6_PNG = RESULTS / "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.png"
FIGURE6_PDF = RESULTS / "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.pdf"
FIGURE_CAPTIONS = RESULTS / "PSA_QAE_CCE_MAIN_FIGURE_CAPTIONS.md"
EDITORIAL_JSON = RESULTS / "PSA_QAE_CCE_EDITORIAL_PACKAGE.json"
EDITORIAL_MD = RESULTS / "PSA_QAE_CCE_EDITORIAL_PACKAGE.md"
COVER_LETTER = RESULTS / "PSA_QAE_CCE_COVER_LETTER_DRAFT.md"
HIGHLIGHTS = RESULTS / "PSA_QAE_CCE_HIGHLIGHTS.txt"
SUBMISSION_CHECKLIST = RESULTS / "PSA_QAE_CCE_SUBMISSION_CHECKLIST.md"
GRAPHICAL_ABSTRACT_PNG = RESULTS / "PSA_QAE_CCE_GRAPHICAL_ABSTRACT.png"
GRAPHICAL_ABSTRACT_PDF = RESULTS / "PSA_QAE_CCE_GRAPHICAL_ABSTRACT.pdf"
SUBMISSION_MANUSCRIPT_DOCX = RESULTS / "PSA_QAE_CCE_SUBMISSION_MANUSCRIPT.docx"
NOVELTY_SEARCH_JSON = RESULTS / "PSA_QAE_CCE_NOVELTY_SEARCH_AUDIT.json"
NOVELTY_SEARCH_MD = RESULTS / "PSA_QAE_CCE_NOVELTY_SEARCH_AUDIT.md"
SUPPLEMENTARY_DRAFT = RESULTS / "PSA_QAE_CCE_SUPPLEMENTARY_INFORMATION_DRAFT.md"
OUT_JSON = RESULTS / "PSA_QAE_CCE_MANUSCRIPT_DRAFT_AUDIT.json"
OUT_MD = RESULTS / "PSA_QAE_CCE_MANUSCRIPT_DRAFT_AUDIT.md"


def check(rows: list[dict[str, object]], name: str, passed: bool, detail: str) -> None:
    rows.append({"name": name, "pass": bool(passed), "detail": detail})


def main() -> None:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    bib = BIB.read_text(encoding="utf-8")
    gate = json.loads(GATE_MANIFEST.read_text(encoding="utf-8"))
    claims = json.loads(CLAIMS_AUDIT.read_text(encoding="utf-8"))
    editorial = json.loads(EDITORIAL_JSON.read_text(encoding="utf-8"))
    novelty = json.loads(NOVELTY_SEARCH_JSON.read_text(encoding="utf-8"))

    words = len(text.split())
    abstract_match = re.search(r"## Abstract\s+(.*?)\s+## Keywords", text, flags=re.S)
    abstract_words = len(abstract_match.group(1).split()) if abstract_match else 0
    citations = sorted(set(re.findall(r"@([A-Za-z0-9_]+)", text)))
    missing_citations = [key for key in citations if f"{{{key}," not in bib]

    required_sections = [
        "## Abstract",
        "## 1. Introduction",
        "## 2. Hybrid PSA chance-constrained workflow",
        "## 3. Estimators and resource accounting",
        "### 2.6 Primary phase-stream event bridge",
        "## 4. Results",
        "## 5. Discussion",
        "### 5.1 Limitations",
        "### 5.3 Claim boundary for CCE",
        "### 4.10 Primary phase-stream event connection",
        "## 6. Conclusions",
        "## Data and code availability",
        "## Supporting information",
    ]
    required_anchors = [
        "0.92743",
        "0.47044",
        "0.28360",
        "0.00679",
        "0.00248",
        "0.01017",
        "0.00289",
        "35,160 CX",
        "52.74 million CX",
        "262,125 CX",
        "64 EiB",
        "11 bits per active input",
        "186 logical qubits",
        "4,183,986 CX",
        "8,367,972 CX",
        "0.56694",
        "0.058060",
        "0.003906",
        "500 times",
        "10.17632/564nt6pcgb.1",
        "0.991666",
        "0.044166",
        "0.03164",
        "1.2538e-3",
        "0.029560",
        "11.91",
        "304 CX",
        "0.1332",
        "37.5×",
        "0.42659",
        "1.296",
        "1.517",
        "272 logical qubits",
        "1,101,233",
        "2,202,466",
        "125 logical qubits",
        "182,981",
        "510 logical qubits",
        "1,286,021",
        "96/96",
        "9 bits per active parameter",
        "118 logical qubits",
        "578,702",
        "1,157,404",
        "28/32",
        "2/32",
        "1.040–1.254",
        "0.135–0.282",
        "6.24e-8",
        "tail-stable strict-CSS cycle is 68",
        "2,880",
        "25,856 cell states",
        "515 logical qubits",
        "1,225,138 CX",
        "0/10",
        "934",
        "1,411,882",
        "26/26/32/32/30",
        "383–431",
        "64-pair",
        "1,317",
        "19,082,852",
        "861–929",
        "4,991,534",
        "842 logical qubits",
        "2,348,388 CX",
        "3,285,605",
        "32,320",
        "1,508 qubits",
        "8,328,622 CX",
        "12,250,291",
        "64,640",
        "1,651 qubits",
        "14,667,150 CX",
        "22,143,683",
        "333 qubits",
        "1,340,232 CX",
        "25,856 normalization states",
        "2.071e-4",
        "1,944–2,039",
        "128,013,726",
        "206,113,724",
        "1,072–1,195",
        "10,060,060–26,810,396",
        "88,388,552",
        "144,913,247",
        "440 logical qubits",
        "166,189 CX",
        "324,495",
        "1.13e-4",
        "1.36e-6",
        "495 logical qubits",
        "353,441 CX",
        "526,434",
        "4.99e-5",
        "4.36e-5",
        "1,297–1,486",
        "1,855,912–2,807,252",
        "1,771–1,960",
        "41,440,216–42,391,556",
        "338,501,740",
        "209,832,572",
        "2,696–2,885",
        "55,337,688–56,289,028",
        "445,738,755",
        "279,319,932",
        "557-qubit",
        "647-qubit",
        "845-qubit",
        "1,078,054 CX",
        "128/128 unsaturated",
        "0.853%",
        "9.949e-7",
        "short-schedule",
    ]
    prohibited_positive_claims = [
        "demonstrates quantum advantage",
        "achieves quantum speedup",
        "industrially validated hydrogen psa",
        "first-ever quantum psa",
        "global optimum is",
    ]
    open_gate_phrases = [
        "calibrated same-policy H2 event result",
        "reversible equalization/CSS/event logic",
        "scalable correlated loader",
        "repeated noise-aware hardware results",
    ]

    checks: list[dict[str, object]] = []
    check(checks, "main-text word count", 6000 <= words <= 10500, f"words={words}")
    check(
        checks,
        "abstract length",
        180 <= abstract_words <= 250,
        f"abstract_words={abstract_words}",
    )
    missing_sections = [value for value in required_sections if value not in text]
    check(
        checks,
        "required manuscript sections",
        not missing_sections,
        f"missing={missing_sections}",
    )
    missing_anchors = [value for value in required_anchors if value not in text]
    check(
        checks,
        "quantitative claim anchors",
        not missing_anchors,
        f"missing={missing_anchors}",
    )
    check(
        checks,
        "citation keys resolve",
        len(citations) >= 12 and not missing_citations,
        f"citations={len(citations)}, missing={missing_citations}",
    )
    present_bad = [
        value for value in prohibited_positive_claims if value in text.lower()
    ]
    check(
        checks,
        "prohibited positive claims absent",
        not present_bad,
        f"present={present_bad}",
    )
    missing_open_gates = [value for value in open_gate_phrases if value not in text]
    check(
        checks,
        "open evidence gates disclosed",
        not missing_open_gates,
        f"missing={missing_open_gates}",
    )
    check(
        checks,
        "workflow figure and figure plan",
        WORKFLOW_PNG.exists() and WORKFLOW_PDF.exists() and FIGURE_PLAN.exists(),
        f"png={WORKFLOW_PNG.exists()}, pdf={WORKFLOW_PDF.exists()}, plan={FIGURE_PLAN.exists()}",
    )
    check(
        checks,
        "calibrated phase-map resource artifacts",
        PHASE_FIXED_JSON.exists()
        and PHASE_FIXED_PNG.exists()
        and PHASE_COMPILE_JSON.exists()
        and PHASE_COMPILE_PNG.exists(),
        f"fixed_json={PHASE_FIXED_JSON.exists()}, fixed_png={PHASE_FIXED_PNG.exists()}, compile_json={PHASE_COMPILE_JSON.exists()}, compile_png={PHASE_COMPILE_PNG.exists()}",
    )
    public_h2 = json.loads(PUBLIC_H2_AUDIT_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "public H2 synchronized-data claim boundary",
        PUBLIC_H2_AUDIT_JSON.exists()
        and PUBLIC_H2_AUDIT_MD.exists()
        and public_h2["status"]
        == "no_public_source_closes_same_product_recycle_same_event_synchronized_raw_gate"
        and int(public_h2["summary"]["sources"]) == 10
        and int(public_h2["summary"]["strict_gate_pass_sources"]) == 0,
        f"sources={public_h2['summary']['sources']}, strict_pass={public_h2['summary']['strict_gate_pass_sources']}",
    )
    small_e2e = json.loads(SMALL_E2E_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "small coherent module-connection control",
        SMALL_E2E_JSON.exists()
        and SMALL_E2E_PNG.exists()
        and small_e2e.get("verification", {}).get("all_work_and_event_qubits_clean_after_uncompute") is True
        and small_e2e.get("verification", {}).get("all_event_phase_labels_match") is True,
        f"json={SMALL_E2E_JSON.exists()}, png={SMALL_E2E_PNG.exists()}, clean={small_e2e.get('verification', {}).get('all_work_and_event_qubits_clean_after_uncompute')}",
    )
    h2_resolution = json.loads(H2_RESOLUTION_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "independent H2 policy-spacing resolution audit",
        H2_RESOLUTION_JSON.exists()
        and H2_RESOLUTION_PNG.exists()
        and h2_resolution.get("gate", {}).get("all_pairs_fail_5x_resolution") is True
        and h2_resolution.get("gate", {}).get("counts_as_external_selection_validation") is False,
        f"json={H2_RESOLUTION_JSON.exists()}, png={H2_RESOLUTION_PNG.exists()}, all_pairs_fail={h2_resolution.get('gate', {}).get('all_pairs_fail_5x_resolution')}",
    )
    topsail_yang = json.loads(TOPSAIL_YANG_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "public toPSAil/Yang same-chemistry H2 model audit",
        TOPSAIL_YANG_JSON.exists()
        and TOPSAIL_YANG_PNG.exists()
        and topsail_yang.get("status") == "independent_same_chemistry_model_and_experimental_anchor_policy_mapping_open"
        and topsail_yang.get("topology_checks", {}).get("all_cases_h2_co") is True
        and topsail_yang.get("topology_checks", {}).get("all_cases_two_bed_six_step") is True
        and topsail_yang.get("event_comparison", {}).get("yang_purity_passes_frozen_threshold") is True
        and topsail_yang.get("event_comparison", {}).get("yang_recovery_passes_frozen_threshold") is False
        and topsail_yang.get("gate", {}).get("same_policy_event_validation") is False
        and topsail_yang.get("qpu_submission") is False,
        f"cases={len(topsail_yang.get('public_workbook_cases', []))}, joint_event={topsail_yang.get('event_comparison', {}).get('yang_joint_event_under_frozen_thresholds')}, same_policy={topsail_yang.get('gate', {}).get('same_policy_event_validation')}",
    )
    prospective = json.loads(PROSPECTIVE_DESIGN_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "prospective decision-active policy design audit",
        PROSPECTIVE_DESIGN_JSON.exists()
        and PROSPECTIVE_DESIGN_PNG.exists()
        and prospective.get("primary_protocol_unchanged") is True
        and prospective.get("independent_h2_resolution_design", {}).get("five_rmse_spacing_fits_inside_training_support") is False,
        f"json={PROSPECTIVE_DESIGN_JSON.exists()}, png={PROSPECTIVE_DESIGN_PNG.exists()}, primary_unchanged={prospective.get('primary_protocol_unchanged')}",
    )
    primary_ledger = json.loads(PRIMARY_PHASE_LEDGER_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "frozen primary final-cycle phase ledger",
        PRIMARY_PHASE_LEDGER_JSON.exists()
        and PRIMARY_PHASE_LEDGER_PNG.exists()
        and primary_ledger.get("sample_count") == 32
        and primary_ledger.get("event", {}).get("joint_event_count") == 25
        and primary_ledger.get("verification", {}).get("css_pass_count") == 32
        and primary_ledger.get("verification", {}).get("all_event_outputs_replay_source_csv") is True
        and primary_ledger.get("qpu_submission") is False,
        f"runs={primary_ledger.get('sample_count')}, events={primary_ledger.get('event', {}).get('joint_event_count')}, css={primary_ledger.get('verification', {}).get('css_pass_count')}",
    )
    physical_css = json.loads(PRIMARY_PHYSICAL_CSS_JSON.read_text(encoding="utf-8"))
    physical_horizon = physical_css.get("physical_horizon", {})
    physical_precision = physical_css.get("fixed_point_screen", {}).get("selected", {})
    physical_registers = physical_css.get("reversible_register_accounting", {})
    check(
        checks,
        "physical tank/spatial CSS horizon and register accounting",
        PRIMARY_PHYSICAL_CSS_JSON.exists()
        and PRIMARY_PHYSICAL_CSS_PNG.exists()
        and physical_css.get("status")
        == "physical_tank_spatial_css_horizon_and_register_accounting_quantified_transport_unitary_open"
        and physical_horizon.get("max_joint_strict_css_event_horizon") == 68
        and physical_precision.get("bits_per_scalar") == 16
        and physical_precision.get("safe_fixed_horizon") == 85
        and physical_registers.get("single_physical_state_data_qubits") == 1360
        and physical_registers.get("out_of_place_current_next_state_plus_raw_event_stream_data_qubits") == 2880
        and physical_css.get("qpu_submission") is False,
        f"physical_horizon={physical_horizon.get('max_joint_strict_css_event_horizon')}, bits={physical_precision.get('bits_per_scalar')}, safe_horizon={physical_precision.get('safe_fixed_horizon')}, out_of_place_qubits={physical_registers.get('out_of_place_current_next_state_plus_raw_event_stream_data_qubits')}",
    )
    qstar_microkernel = json.loads(PRIMARY_QSTAR_MICROKERNEL_JSON.read_text(encoding="utf-8"))
    qstar_selected = qstar_microkernel.get("selected", {})
    check(
        checks,
        "competitive-Langmuir reversible microkernel",
        PRIMARY_QSTAR_MICROKERNEL_JSON.exists()
        and PRIMARY_QSTAR_MICROKERNEL_PNG.exists()
        and qstar_microkernel.get("status")
        == "competitive_langmuir_numerator_denominator_preparation_compiled_reciprocal_ode_open"
        and qstar_microkernel.get("physical_state_source", {}).get("cell_states_evaluated") == 25856
        and qstar_selected.get("bits_per_pressure_and_composition") == 18
        and qstar_selected.get("logical_qubits") == 266
        and qstar_selected.get("forward_cx") == 127112
        and qstar_selected.get("clean_compute_uncompute_cx") == 254224
        and qstar_selected.get("passes_declared_microkernel_precision_gate") is True
        and qstar_microkernel.get("qpu_submission") is False,
        f"states={qstar_microkernel.get('physical_state_source', {}).get('cell_states_evaluated')}, bits={qstar_selected.get('bits_per_pressure_and_composition')}, qubits={qstar_selected.get('logical_qubits')}, forward_CX={qstar_selected.get('forward_cx')}",
    )
    qstar_ldf_microstep = json.loads(PRIMARY_QSTAR_LDF_MICROSTEP_JSON.read_text(encoding="utf-8"))
    qstar_ldf_selected = qstar_ldf_microstep.get("selected", {})
    qstar_ldf_resources = qstar_ldf_microstep.get("compiled_clean_microstep", {})
    check(
        checks,
        "competitive-Langmuir reciprocal and CO2 LDF clean microstep",
        PRIMARY_QSTAR_LDF_MICROSTEP_JSON.exists()
        and PRIMARY_QSTAR_LDF_MICROSTEP_PNG.exists()
        and qstar_ldf_microstep.get("status")
        == "competitive_langmuir_reciprocal_and_co2_ldf_microstep_compiled_full_phase_cycle_open"
        and qstar_ldf_microstep.get("physical_state_source", {}).get("cell_states_evaluated") == 25856
        and qstar_ldf_selected.get("denominator_address_bits") == 5
        and qstar_ldf_selected.get("arithmetic_bits") == 24
        and float(qstar_ldf_selected.get("qstar_p95_relative_error", 1.0)) < 5.0e-2
        and float(qstar_ldf_selected.get("ldf_next_p95_relative_error", 1.0)) < 1.0e-3
        and qstar_ldf_selected.get("nonzero_qstar_erased_fraction") == 0.0
        and qstar_ldf_resources.get("logical_qubits") == 515
        and qstar_ldf_resources.get("depth_all_to_all") == 1919788
        and qstar_ldf_resources.get("cx") == 1225138
        and qstar_ldf_microstep.get("qpu_submission") is False,
        f"states={qstar_ldf_microstep.get('physical_state_source', {}).get('cell_states_evaluated')}, address_bits={qstar_ldf_selected.get('denominator_address_bits')}, arithmetic_bits={qstar_ldf_selected.get('arithmetic_bits')}, qubits={qstar_ldf_resources.get('logical_qubits')}, CX={qstar_ldf_resources.get('cx')}",
    )
    primary_event = json.loads(PRIMARY_EVENT_BRIDGE_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "nested-holdout primary phase-stream event bridge",
        PRIMARY_EVENT_BRIDGE_JSON.exists()
        and PRIMARY_EVENT_BRIDGE_PNG.exists()
        and primary_event.get("event_summary", {}).get("event_matches") == 32
        and primary_event.get("event_summary", {}).get("false_positive_count") == 0
        and primary_event.get("event_summary", {}).get("false_negative_count") == 0
        and primary_event.get("event_summary", {}).get("purity_mae", 1.0) < 4.0e-8
        and primary_event.get("event_summary", {}).get("recovery_mae", 1.0) < 8.0e-5
        and primary_event.get("qpu_submission") is False,
        f"labels={primary_event.get('event_summary', {}).get('event_matches')}/32, purity_mae={primary_event.get('event_summary', {}).get('purity_mae')}, recovery_mae={primary_event.get('event_summary', {}).get('recovery_mae')}",
    )
    primary_fixed = json.loads(PRIMARY_EVENT_FIXED_JSON.read_text(encoding="utf-8"))
    primary_compile = json.loads(PRIMARY_EVENT_COMPILE_JSON.read_text(encoding="utf-8"))
    selected_event = primary_fixed.get("minimum_configuration_within_budgets_and_all_labels", {})
    compiled_event = primary_compile.get("aggregate", {})
    check(
        checks,
        "primary event-active fixed-point and primitive-gate layer",
        PRIMARY_EVENT_FIXED_JSON.exists()
        and PRIMARY_EVENT_FIXED_PNG.exists()
        and PRIMARY_EVENT_COMPILE_JSON.exists()
        and PRIMARY_EVENT_COMPILE_PNG.exists()
        and selected_event.get("bits_per_input") == 12
        and selected_event.get("sum_bits_per_scalar_output") == 16
        and selected_event.get("event_matches_vs_actual") == 32
        and compiled_event.get("max_logical_qubits_reusing_scalar_workspace") == 272
        and compiled_event.get("serial_forward_cx") == 1101233
        and compiled_event.get("serial_clean_compute_uncompute_cx") == 2202466
        and primary_compile.get("qpu_submission") is False,
        f"selected={selected_event.get('bits_per_input')}/{selected_event.get('sum_bits_per_scalar_output')}, qubits={compiled_event.get('max_logical_qubits_reusing_scalar_workspace')}, forward_CX={compiled_event.get('serial_forward_cx')}",
    )
    primary_final_event = json.loads(PRIMARY_FINAL_EVENT_JSON.read_text(encoding="utf-8"))
    final_precision = primary_final_event.get("precision_screen", {}).get("selected", {})
    final_coefficient = primary_final_event.get("coefficient_screen", {}).get("selected", {})
    final_compile = primary_final_event.get("primitive_gate_compile", {}).get("clean_phase_oracle", {})
    final_verification = primary_final_event.get("verification", {})
    check(
        checks,
        "primary final joint-event arithmetic",
        PRIMARY_FINAL_EVENT_JSON.exists()
        and PRIMARY_FINAL_EVENT_PNG.exists()
        and final_precision.get("bits") == 16
        and final_precision.get("within_both_budgets_and_labels") is True
        and final_coefficient.get("coefficient_bits") == 8
        and final_verification.get("integer_event_matches") == 32
        and final_verification.get("false_positives") == 0
        and final_verification.get("false_negatives") == 0
        and final_compile.get("logical_qubits") == 125
        and final_compile.get("cx") == 182981
        and primary_final_event.get("qpu_submission") is False,
        f"bits={final_precision.get('bits')}, coefficient_bits={final_coefficient.get('coefficient_bits')}, labels={final_verification.get('integer_event_matches')}/32, qubits={final_compile.get('logical_qubits')}, clean_CX={final_compile.get('cx')}",
    )
    policy_stream_event = json.loads(PRIMARY_POLICY_STREAM_EVENT_JSON.read_text(encoding="utf-8"))
    policy_precision = policy_stream_event.get("precision_screen", {}).get("selected", {})
    policy_verification = policy_stream_event.get("verification", {})
    policy_resources = policy_stream_event.get("primitive_gate_compile", {}).get("policy_resources", [])
    check(
        checks,
        "primary policy stream-to-event clean oracle",
        PRIMARY_POLICY_STREAM_EVENT_JSON.exists()
        and PRIMARY_POLICY_STREAM_EVENT_PNG.exists()
        and policy_precision.get("aggregate_bits") == 19
        and policy_precision.get("within_both_budgets_and_labels") is True
        and policy_verification.get("candidate_integer_event_matches_vs_float") == 96
        and policy_verification.get("ledger_support_event_matches_vs_actual") == 32
        and policy_verification.get("candidate_input_clip_count") == 0
        and max(row["clean_phase_oracle"]["logical_qubits"] for row in policy_resources) == 510
        and max(row["clean_phase_oracle"]["cx"] for row in policy_resources) == 1286021
        and policy_stream_event.get("qpu_submission") is False,
        f"aggregate_bits={policy_precision.get('aggregate_bits')}, candidate_labels={policy_verification.get('candidate_integer_event_matches_vs_float')}/96, ledger_labels={policy_verification.get('ledger_support_event_matches_vs_actual')}/32, max_qubits={max((row['clean_phase_oracle']['logical_qubits'] for row in policy_resources), default=None)}, max_clean_CX={max((row['clean_phase_oracle']['cx'] for row in policy_resources), default=None)}",
    )
    primary_free = json.loads(PRIMARY_FREE_RUNNING_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "primary one-cycle free-running aggregate event bridge",
        PRIMARY_FREE_RUNNING_JSON.exists()
        and PRIMARY_FREE_RUNNING_PNG.exists()
        and primary_free.get("event_summary", {}).get("event_matches") == 32
        and primary_free.get("event_summary", {}).get("false_positive_count") == 0
        and primary_free.get("event_summary", {}).get("false_negative_count") == 0
        and primary_free.get("event_summary", {}).get("total_clipped_state_entries") == 0
        and primary_free.get("event_summary", {}).get("total_clipped_stream_entries") == 0
        and primary_free.get("qpu_submission") is False,
        f"labels={primary_free.get('event_summary', {}).get('event_matches')}/32, recovery_mae={primary_free.get('event_summary', {}).get('recovery_mae')}, p95_closure={primary_free.get('event_summary', {}).get('p95_final_cycle_closure_relative_l1')}",
    )
    primary_repeated = json.loads(PRIMARY_REPEATED_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "observed-start repeated-cycle instability control",
        PRIMARY_REPEATED_JSON.exists()
        and PRIMARY_REPEATED_PNG.exists()
        and primary_repeated.get("summary", {}).get("cycles_per_run") == 50
        and primary_repeated.get("summary", {}).get("terminal_event_matches") == 21
        and primary_repeated.get("summary", {}).get("tail_css_gate_1e_4_count") == 1
        and primary_repeated.get("summary", {}).get("total_clipped_state_entries", 0) > 0
        and primary_repeated.get("qpu_submission") is False,
        f"terminal_labels={primary_repeated.get('summary', {}).get('terminal_event_matches')}/32, css={primary_repeated.get('summary', {}).get('tail_css_gate_1e_4_count')}/32",
    )
    css_initializer = json.loads(CSS_INITIALIZER_JSON.read_text(encoding="utf-8"))
    css_repeated = json.loads(CSS_REPEATED_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "parameter-only CSS initializer and repeated-cycle boundary",
        CSS_INITIALIZER_JSON.exists()
        and CSS_INITIALIZER_PNG.exists()
        and CSS_REPEATED_JSON.exists()
        and CSS_REPEATED_PNG.exists()
        and css_initializer.get("held_run_dynamic_states_supplied") == 0
        and css_initializer.get("summary", {}).get("event_matches") == 32
        and css_initializer.get("summary", {}).get("total_initial_clipped_state_entries") == 0
        and css_repeated.get("summary", {}).get("terminal_event_matches") == 28
        and css_repeated.get("summary", {}).get("tail_css_gate_1e_4_count") == 2
        and css_initializer.get("qpu_submission") is False
        and css_repeated.get("qpu_submission") is False,
        f"one_cycle={css_initializer.get('summary', {}).get('event_matches')}/32, terminal={css_repeated.get('summary', {}).get('terminal_event_matches')}/32, css={css_repeated.get('summary', {}).get('tail_css_gate_1e_4_count')}/32",
    )
    css_stability = json.loads(CSS_STABILITY_JSON.read_text(encoding="utf-8"))
    stability_summary = css_stability.get("summary", {})
    check(
        checks,
        "parameter-only aggregate spectral-stability boundary",
        CSS_STABILITY_JSON.exists()
        and CSS_STABILITY_PNG.exists()
        and css_stability.get("held_run_dynamic_states_supplied") == 0
        and css_stability.get("held_run_event_labels_used_for_stabilization") is False
        and stability_summary.get("target_spectral_radius") == 0.9
        and stability_summary.get("raw_spectral_radius_min", 0.0) > 1.0
        and stability_summary.get("terminal_event_matches") == 32
        and stability_summary.get("tail_css_gate_1e_4_count") == 32
        and stability_summary.get("total_clipped_state_entries") == 0
        and stability_summary.get("total_clipped_stream_entries") == 0
        and css_stability.get("qpu_submission") is False,
        f"raw_rho=[{stability_summary.get('raw_spectral_radius_min')},{stability_summary.get('raw_spectral_radius_max')}], weight=[{stability_summary.get('anchor_weight_min')},{stability_summary.get('anchor_weight_max')}], labels={stability_summary.get('terminal_event_matches')}/32, css={stability_summary.get('tail_css_gate_1e_4_count')}/32",
    )
    css_fixed = json.loads(CSS_FIXED_JSON.read_text(encoding="utf-8"))
    css_compile = json.loads(CSS_COMPILE_JSON.read_text(encoding="utf-8"))
    selected_css = css_fixed.get("minimum_configuration_within_all_budgets_and_labels", {})
    compiled_css = css_compile.get("aggregate", {})
    check(
        checks,
        "parameter-only CSS initializer fixed-point and primitive-gate layer",
        CSS_FIXED_JSON.exists()
        and CSS_FIXED_PNG.exists()
        and CSS_COMPILE_JSON.exists()
        and CSS_COMPILE_PNG.exists()
        and selected_css.get("bits_per_input") == 9
        and selected_css.get("sum_bits_per_scalar_output") == 14
        and selected_css.get("event_matches_vs_actual") == 32
        and compiled_css.get("scalar_blocks") == 20
        and compiled_css.get("max_logical_qubits_reusing_scalar_workspace") == 118
        and compiled_css.get("serial_forward_cx") == 578702
        and compiled_css.get("serial_clean_compute_uncompute_cx") == 1157404
        and css_compile.get("qpu_submission") is False,
        f"selected={selected_css.get('bits_per_input')}/{selected_css.get('sum_bits_per_scalar_output')}, qubits={compiled_css.get('max_logical_qubits_reusing_scalar_workspace')}, forward_CX={compiled_css.get('serial_forward_cx')}",
    )
    check(
        checks,
        "main-text resource ladder figure and table",
        RESOURCE_LADDER_PNG.exists()
        and RESOURCE_LADDER_PDF.exists()
        and RESOURCE_TABLE_JSON.exists()
        and RESOURCE_TABLE_MD.exists(),
        f"figure_png={RESOURCE_LADDER_PNG.exists()}, figure_pdf={RESOURCE_LADDER_PDF.exists()}, table_json={RESOURCE_TABLE_JSON.exists()}, table_md={RESOURCE_TABLE_MD.exists()}",
    )
    check(
        checks,
        "main-text protocol estimator and evidence tables",
        TABLE1_JSON.exists()
        and TABLE1_MD.exists()
        and TABLE2_JSON.exists()
        and TABLE2_MD.exists()
        and TABLE4_JSON.exists()
        and TABLE4_MD.exists(),
        f"table1={TABLE1_JSON.exists() and TABLE1_MD.exists()}, table2={TABLE2_JSON.exists() and TABLE2_MD.exists()}, table4={TABLE4_JSON.exists() and TABLE4_MD.exists()}",
    )
    coherent_interface = json.loads(COHERENT_RUN_SCHEDULE_TANK_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "coherent finite-support run schedule tank interface",
        COHERENT_RUN_SCHEDULE_TANK_JSON.exists()
        and COHERENT_RUN_SCHEDULE_TANK_MD.exists()
        and coherent_interface.get("status")
        == "finite_support_coherent_run_parameter_valve_schedule_and_tank_withdrawal_interface_compiled_adaptive_cycle_open"
        and coherent_interface.get("parameter_encoding", {}).get("basis_table_values_checked") == 352
        and coherent_interface.get("schedule_encoding", {}).get("basis_addresses_checked") == 8
        and coherent_interface.get("tank_encoding", {}).get("basis_component_records_checked") == 640
        and coherent_interface.get("tank_encoding", {}).get("selected", {}).get("passes_declared_precision_gate") is True
        and coherent_interface.get("integrated_interface", {}).get("logical_qubits") == 440
        and coherent_interface.get("integrated_interface", {}).get("depth_all_to_all") == 324495
        and coherent_interface.get("integrated_interface", {}).get("cx") == 166189
        and coherent_interface.get("qpu_submission") is False,
        f"parameters={coherent_interface.get('parameter_encoding', {}).get('basis_table_values_checked')}, schedule={coherent_interface.get('schedule_encoding', {}).get('basis_addresses_checked')}, tank={coherent_interface.get('tank_encoding', {}).get('basis_component_records_checked')}, resources={coherent_interface.get('integrated_interface', {}).get('logical_qubits')}q/{coherent_interface.get('integrated_interface', {}).get('cx')}CX",
    )
    coherent_factor_ldf = json.loads(COHERENT_RUN_FACTOR_LDF_JSON.read_text(encoding="utf-8"))
    check(
        checks,
        "coherent controller to five-component LDF coefficient interface",
        COHERENT_RUN_FACTOR_LDF_JSON.exists()
        and COHERENT_RUN_FACTOR_LDF_MD.exists()
        and coherent_factor_ldf.get("status")
        == "finite_support_coherent_run_factors_directly_wired_to_five_component_ldf_coefficients_full_state_update_open"
        and coherent_factor_ldf.get("support", {}).get("coefficient_records_checked") == 320
        and coherent_factor_ldf.get("support", {}).get("schedule_flags_checked") == 16
        and coherent_factor_ldf.get("precision", {}).get("passes_declared_precision_gate") is True
        and coherent_factor_ldf.get("precision", {}).get("five_component_equilibrium_prefactor_max_relative_error", 1.0) <= 5.0e-5
        and coherent_factor_ldf.get("precision", {}).get("five_component_ldf_alpha_max_relative_error", 1.0) <= 4.4e-5
        and coherent_factor_ldf.get("compiled_interface", {}).get("logical_qubits") == 495
        and coherent_factor_ldf.get("compiled_interface", {}).get("depth_all_to_all") == 526434
        and coherent_factor_ldf.get("compiled_interface", {}).get("cx") == 353441
        and coherent_factor_ldf.get("qpu_submission") is False,
        f"coefficients={coherent_factor_ldf.get('support', {}).get('coefficient_records_checked')}, flags={coherent_factor_ldf.get('support', {}).get('schedule_flags_checked')}, resources={coherent_factor_ldf.get('compiled_interface', {}).get('logical_qubits')}q/{coherent_factor_ldf.get('compiled_interface', {}).get('cx')}CX",
    )
    coherent_coefficient_ldf_balance = json.loads(
        COHERENT_COEFFICIENT_LDF_BALANCE_JSON.read_text(encoding="utf-8")
    )
    coherent_consumer_resources = {
        row["component"]: row
        for row in coherent_coefficient_ldf_balance.get(
            "componentwise_compiled_direct_paths", []
        )
    }
    coherent_consumer_upper = coherent_coefficient_ldf_balance.get(
        "conservative_five_component_upper_bound", {}
    )
    check(
        checks,
        "coherent coefficient-consuming component LDF loading balance paths",
        COHERENT_COEFFICIENT_LDF_BALANCE_JSON.exists()
        and COHERENT_COEFFICIENT_LDF_BALANCE_MD.exists()
        and coherent_coefficient_ldf_balance.get("status")
        == "coherent_run_coefficients_consumed_in_five_schedule_gated_component_ldf_loading_balance_paths_dynamic_denominator_open"
        and coherent_coefficient_ldf_balance.get("support", {}).get(
            "component_balance_records_checked"
        )
        == 64640
        and len(coherent_coefficient_ldf_balance.get("components", [])) == 5
        and all(
            row.get("passes_declared_precision_gate") is True
            and row.get("nonzero_quantized_transfer_erased_fraction") == 0.0
            for row in coherent_coefficient_ldf_balance.get("components", [])
        )
        and set(coherent_consumer_resources) == {"H2", "CO2", "CH4", "CO", "N2"}
        and coherent_consumer_upper.get("logical_qubits_peak") == 1486
        and coherent_consumer_upper.get("depth_all_to_all_additive_upper_bound")
        == 12387085
        and coherent_consumer_upper.get("cx_additive_upper_bound") == 11911052
        and coherent_consumer_upper.get("monolithic_five_component_transpile")
        is False
        and coherent_coefficient_ldf_balance.get("qpu_submission") is False,
        f"balances={coherent_coefficient_ldf_balance.get('support', {}).get('component_balance_records_checked')}, peak={coherent_consumer_upper.get('logical_qubits_peak')}q, additive_CX={coherent_consumer_upper.get('cx_additive_upper_bound')}",
    )
    coherent_dynamic = json.loads(
        COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_JSON.read_text(encoding="utf-8")
    )
    coherent_dynamic_resources = {
        row["component"]: row
        for row in coherent_dynamic.get("componentwise_compiled_direct_paths", [])
    }
    coherent_dynamic_upper = coherent_dynamic.get(
        "conservative_five_component_upper_bound", {}
    )
    coherent_dynamic_design = coherent_dynamic.get(
        "selected_dynamic_response_design", {}
    )
    check(
        checks,
        "coherent dynamic Langmuir response to LDF loading balance paths",
        COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_JSON.exists()
        and COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_MD.exists()
        and coherent_dynamic.get("status")
        == "dynamic_run_affinity_langmuir_response_consumed_in_five_compiled_component_paths"
        and coherent_dynamic.get("support", {}).get(
            "component_balance_records_checked"
        )
        == 64640
        and coherent_dynamic_design.get("affinity_bits") == 8
        and coherent_dynamic_design.get("denominator_address_bits") == 12
        and coherent_dynamic_design.get("reciprocal_segments") == 4096
        and coherent_dynamic_design.get("denominator_max_absolute_error", 1.0)
        <= 3.6e-4
        and all(
            row.get("passes_declared_precision_gate") is True
            for row in coherent_dynamic.get("components", [])
        )
        and set(coherent_dynamic_resources) == {"H2", "CO2", "CH4", "CO", "N2"}
        and coherent_dynamic_upper.get("logical_qubits_peak") == 1960
        and coherent_dynamic_upper.get("depth_all_to_all_additive_upper_bound")
        == 338501740
        and coherent_dynamic_upper.get("cx_additive_upper_bound") == 209832572
        and coherent_dynamic_upper.get("monolithic_five_component_transpile")
        is False
        and coherent_dynamic.get("qpu_submission") is False,
        f"balances={coherent_dynamic.get('support', {}).get('component_balance_records_checked')}, peak={coherent_dynamic_upper.get('logical_qubits_peak')}q, additive_CX={coherent_dynamic_upper.get('cx_additive_upper_bound')}",
    )
    coherent_normalized_dynamic = json.loads(
        COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE_JSON.read_text(
            encoding="utf-8"
        )
    )
    coherent_normalized_dynamic_resources = {
        row["component"]: row
        for row in coherent_normalized_dynamic.get(
            "componentwise_compiled_direct_paths", []
        )
    }
    coherent_normalized_dynamic_upper = coherent_normalized_dynamic.get(
        "conservative_five_component_upper_bound", {}
    )
    check(
        checks,
        "coherent gas inventory to dynamic Langmuir transport LDF balance paths",
        COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE_JSON.exists()
        and COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE_MD.exists()
        and coherent_normalized_dynamic.get("status")
        == "gas_inventory_to_dynamic_langmuir_ldf_balance_five_component_paths_compiled"
        and coherent_normalized_dynamic.get("support", {}).get(
            "normalization_states"
        )
        == 25856
        and coherent_normalized_dynamic.get("support", {}).get(
            "component_balance_records_checked"
        )
        == 64640
        and all(
            row.get("passes_declared_precision_gate") is True
            for row in coherent_normalized_dynamic.get("components", [])
        )
        and set(coherent_normalized_dynamic_resources)
        == {"H2", "CO2", "CH4", "CO", "N2"}
        and coherent_normalized_dynamic_upper.get("logical_qubits_peak") == 2885
        and coherent_normalized_dynamic_upper.get(
            "depth_all_to_all_additive_upper_bound"
        )
        == 445738755
        and coherent_normalized_dynamic_upper.get("cx_additive_upper_bound")
        == 279319932
        and coherent_normalized_dynamic_upper.get(
            "monolithic_five_component_transpile"
        )
        is False
        and coherent_normalized_dynamic.get("qpu_submission") is False,
        f"normalization={coherent_normalized_dynamic.get('support', {}).get('normalization_states')}, balances={coherent_normalized_dynamic.get('support', {}).get('component_balance_records_checked')}, peak={coherent_normalized_dynamic_upper.get('logical_qubits_peak')}q, additive_CX={coherent_normalized_dynamic_upper.get('cx_additive_upper_bound')}",
    )
    offledger_tank = json.loads(
        OFFLEDGER_TANK_SATURATION_JSON.read_text(encoding="utf-8")
    )
    offledger_selected = offledger_tank.get("selected_design", {})
    offledger_resources = offledger_tank.get("compiled_clean_circuit", {})
    check(
        checks,
        "pressure-derived saturated tank withdrawal interface",
        OFFLEDGER_TANK_SATURATION_JSON.exists()
        and OFFLEDGER_TANK_SATURATION_MD.exists()
        and offledger_tank.get("status")
        == "frozen_support_pressure_derived_saturated_tank_withdrawal_compiled"
        and offledger_tank.get("support", {}).get("records") == 128
        and offledger_selected.get("common_bits") == 20
        and offledger_selected.get("exact_demand_saturated_records") == 128
        and offledger_selected.get("end_pressure_lower_bound_saturated_records")
        == 128
        and offledger_selected.get("encoded_saturated_records") == 128
        and offledger_selected.get("saturation_flag_mismatch_count") == 0
        and offledger_selected.get("lower_bound_violation_count") == 0
        and offledger_selected.get("modular_next_tank_underflow_count") == 0
        and offledger_selected.get("meaningful_withdrawal_erased_count") == 0
        and offledger_selected.get(
            "all_output_p95_scale_normalized_absolute_error", 1.0
        )
        <= 2.1e-6
        and offledger_resources.get("logical_qubits") == 557
        and offledger_resources.get("depth_all_to_all") == 327212
        and offledger_resources.get("cx") == 195276
        and offledger_resources.get("measurement") == 0
        and offledger_resources.get("reset") == 0
        and offledger_tank.get("qpu_submission") is False,
        f"records={offledger_tank.get('support', {}).get('records')}, labels={offledger_selected.get('encoded_saturated_records')}/128, margin={offledger_selected.get('minimum_lower_bound_minus_tank_mol')}, resources={offledger_resources.get('logical_qubits')}q/{offledger_resources.get('cx')}CX",
    )
    offledger_proportional = json.loads(
        OFFLEDGER_TANK_PROPORTIONAL_JSON.read_text(encoding="utf-8")
    )
    proportional_selected = offledger_proportional.get("selected_design", {})
    proportional_resources = offledger_proportional.get(
        "compiled_clean_circuit", {}
    )
    check(
        checks,
        "pressure-derived saturated and bounded-unsaturated proportional tank allocation",
        OFFLEDGER_TANK_PROPORTIONAL_JSON.exists()
        and OFFLEDGER_TANK_PROPORTIONAL_MD.exists()
        and offledger_proportional.get("status")
        == "pressure_derived_saturated_and_bounded_unsaturated_proportional_tank_allocation_compiled"
        and offledger_proportional.get("support", {}).get(
            "observed_frozen_final_cycle_records"
        )
        == 128
        and offledger_proportional.get("support", {}).get(
            "observed_saturated_records"
        )
        == 128
        and offledger_proportional.get("support", {}).get(
            "counterfactual_arithmetic_records"
        )
        == 224
        and offledger_proportional.get("support", {}).get(
            "counterfactual_unsaturated_records"
        )
        == 224
        and proportional_selected.get("common_bits") == 18
        and proportional_selected.get("address_bits") == 5
        and proportional_selected.get("reciprocal_bits") == 16
        and proportional_selected.get("encoded_saturated_records") == 128
        and proportional_selected.get("encoded_unsaturated_records") == 224
        and proportional_selected.get("saturation_flag_mismatch_count") == 0
        and proportional_selected.get("unsaturated_fraction_overflow_count") == 0
        and proportional_selected.get("modular_next_tank_underflow_count") == 0
        and proportional_selected.get("meaningful_withdrawal_erased_count") == 0
        and proportional_selected.get(
            "withdrawal_and_next_p95_component_scale_normalized_absolute_error",
            1.0,
        )
        <= 1.7e-4
        and proportional_selected.get(
            "withdrawal_and_next_max_component_scale_normalized_absolute_error",
            1.0,
        )
        <= 3.9e-4
        and proportional_selected.get("passes_declared_domain_gate") is True
        and proportional_resources.get("logical_qubits") == 647
        and proportional_resources.get("depth_all_to_all") == 1127046
        and proportional_resources.get("cx") == 705194
        and proportional_resources.get("measurement") == 0
        and proportional_resources.get("reset") == 0
        and offledger_proportional.get("qpu_submission") is False,
        f"observed={offledger_proportional.get('support', {}).get('observed_saturated_records')}, counterfactual={offledger_proportional.get('support', {}).get('counterfactual_unsaturated_records')}, resources={proportional_resources.get('logical_qubits')}q/{proportional_resources.get('cx')}CX",
    )
    check(
        checks,
        "complete main-text figure set and captions",
        all(
            path.exists()
            for path in [
                FIGURE2_PNG,
                FIGURE2_PDF,
                FIGURE3_PNG,
                FIGURE3_PDF,
                FIGURE5_PNG,
                FIGURE5_PDF,
                FIGURE6_PNG,
                FIGURE6_PDF,
                FIGURE_CAPTIONS,
            ]
        ),
        f"figure2={FIGURE2_PNG.exists() and FIGURE2_PDF.exists()}, figure3={FIGURE3_PNG.exists() and FIGURE3_PDF.exists()}, figure5={FIGURE5_PNG.exists() and FIGURE5_PDF.exists()}, figure6={FIGURE6_PNG.exists() and FIGURE6_PDF.exists()}, captions={FIGURE_CAPTIONS.exists()}",
    )
    check(
        checks,
        "machine-readable CCE editorial package",
        EDITORIAL_JSON.exists()
        and editorial.get("status") == "editorial_materials_complete_scientific_submission_gates_open"
        and editorial.get("title") == text.splitlines()[0].removeprefix("# ").strip()
        and len(editorial.get("highlights", [])) == 5
        and max(editorial.get("highlight_character_counts", [999])) <= 85
        and editorial.get("submission_ready") is False
        and editorial.get("qpu_submission") is False,
        f"status={editorial.get('status')}, highlights={editorial.get('highlight_character_counts')}, submission_ready={editorial.get('submission_ready')}",
    )
    format_checks = editorial.get("submission_format_checks", {})
    docx_paragraphs = [p.text for p in Document(SUBMISSION_MANUSCRIPT_DOCX).paragraphs]
    reference_index = docx_paragraphs.index("References") if "References" in docx_paragraphs else -1
    docx_references = docx_paragraphs[reference_index + 1:reference_index + 19] if reference_index >= 0 else []
    reference_surnames = [ref.split(",", 1)[0] for ref in docx_references]
    check(
        checks,
        "CCE live-guide format limits and author-year references",
        SUBMISSION_MANUSCRIPT_DOCX.exists()
        and format_checks.get("abstract_words") == abstract_words
        and abstract_words <= 250
        and format_checks.get("keyword_count") == 6
        and format_checks.get("highlight_count") == 5
        and max(format_checks.get("highlight_character_counts", [999])) <= 85
        and format_checks.get("graphical_abstract_pixels", [0, 0])[0] >= 1328
        and format_checks.get("graphical_abstract_pixels", [0, 0])[1] >= 531
        and format_checks.get("main_figure_vector_pdf_count") == 6
        and format_checks.get("main_table3_rows") == 8
        and format_checks.get("supplementary_table_s1_rows") == 29
        and format_checks.get("main_table4_rows") == 8
        and format_checks.get("supplementary_table_s2_rows") == 30
        and any("(Khajuria and Pistikopoulos, 2013)" in paragraph for paragraph in docx_paragraphs)
        and len(docx_references) == 18
        and reference_surnames == sorted(reference_surnames, key=str.casefold)
        and not any("[@" in paragraph for paragraph in docx_paragraphs),
        f"abstract={format_checks.get('abstract_words')}/250, keywords={format_checks.get('keyword_count')}, highlights={format_checks.get('highlight_character_counts')}, graphical_abstract={format_checks.get('graphical_abstract_pixels')}, vector_pdfs={format_checks.get('main_figure_vector_pdf_count')}, references={len(docx_references)}",
    )
    supplementary_text = SUPPLEMENTARY_DRAFT.read_text(encoding="utf-8")
    check(
        checks,
        "bounded novelty-search evidence",
        NOVELTY_SEARCH_MD.exists()
        and novelty.get("search_date") == "2026-10-09"
        and len(novelty.get("queries", [])) == 4
        and novelty.get("deduplicated_record_count") == 220
        and novelty.get("direct_psa_qae_match_count") == 0
        and "bounded search observation rather than proof of universal absence" in text
        and "## S9. Bounded literature-search protocol" in supplementary_text,
        f"date={novelty.get('search_date')}, queries={len(novelty.get('queries', []))}, unique={novelty.get('deduplicated_record_count')}, direct={novelty.get('direct_psa_qae_match_count')}",
    )
    with ZipFile(SUBMISSION_MANUSCRIPT_DOCX) as archive:
        document_xml = etree.fromstring(archive.read("word/document.xml"))
    word_ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    docx_tables = document_xml.xpath("//w:tbl", namespaces=word_ns)
    table_shading_nodes = sum(len(table.xpath(".//w:shd", namespaces=word_ns)) for table in docx_tables)
    active_vertical_borders = []
    for table in docx_tables:
        for edge in ("left", "right", "insideV"):
            for border in table.xpath(f".//w:tcBorders/w:{edge}", namespaces=word_ns):
                value = border.get(f"{{{word_ns['w']}}}val")
                if value not in (None, "nil", "none"):
                    active_vertical_borders.append((edge, value))
    figure_refs = {number: text.count(f"Figure {number}") for number in range(1, 7)}
    table_refs = {number: text.count(f"Table {number}") for number in range(1, 5)}
    check(
        checks,
        "CCE table styling and main-text cross-references",
        len(docx_tables) == 4
        and table_shading_nodes == 0
        and not active_vertical_borders
        and all(count == 1 for count in figure_refs.values())
        and all(count == 1 for count in table_refs.values())
        and all(any(paragraph.startswith(f"Figure {number}.") for paragraph in docx_paragraphs) for number in range(1, 7))
        and all(any(paragraph.startswith(f"Table {number}.") for paragraph in docx_paragraphs) for number in range(1, 5)),
        f"tables={len(docx_tables)}, shading={table_shading_nodes}, vertical_rules={len(active_vertical_borders)}, figure_refs={figure_refs}, table_refs={table_refs}",
    )
    cover_text = COVER_LETTER.read_text(encoding="utf-8")
    checklist_text = SUBMISSION_CHECKLIST.read_text(encoding="utf-8")
    check(
        checks,
        "CCE cover letter highlights and checklist",
        EDITORIAL_MD.exists()
        and COVER_LETTER.exists()
        and HIGHLIGHTS.exists()
        and SUBMISSION_CHECKLIST.exists()
        and "do not claim quantum advantage" in cover_text
        and "Confirm before submission" in cover_text
        and "same physical product-recycle control" in checklist_text
        and "submission_ready=false" in checklist_text,
        f"editorial={EDITORIAL_MD.exists()}, cover={COVER_LETTER.exists()}, highlights={HIGHLIGHTS.exists()}, checklist={SUBMISSION_CHECKLIST.exists()}",
    )
    check(
        checks,
        "graphical abstract and claim boundary",
        GRAPHICAL_ABSTRACT_PNG.exists()
        and GRAPHICAL_ABSTRACT_PDF.exists()
        and editorial.get("claim_boundary", {}).get("supported", "").startswith("resource-aware comparison")
        and "end-to-end quantum advantage" in editorial.get("claim_boundary", {}).get("unsupported", "")
        and editorial.get("evidence", {}).get("same_control_h2_validation") is False
        and editorial.get("evidence", {}).get("response_oracle_cx_per_call") == 35160
        and editorial.get("evidence", {}).get("parameter_only_css_event_matches") == 32
        and editorial.get("evidence", {}).get("parameter_only_css_block_logical_qubits") == 118
        and editorial.get("evidence", {}).get("parameter_only_css_50cycle_gate_passes") == 2
        and editorial.get("evidence", {}).get("parameter_only_css_stabilized_50cycle_gate_passes") == 32
        and editorial.get("evidence", {}).get("physical_css_joint_horizon") == 68
        and editorial.get("evidence", {}).get("physical_css_fixed_point_bits") == 16
        and editorial.get("evidence", {}).get("physical_css_safe_horizon") == 85
        and editorial.get("evidence", {}).get("physical_single_state_data_qubits") == 1360
        and editorial.get("evidence", {}).get("physical_out_of_place_state_stream_data_qubits") == 2880
        and editorial.get("evidence", {}).get("qstar_microkernel_bits") == 18
        and editorial.get("evidence", {}).get("qstar_microkernel_logical_qubits") == 266
        and editorial.get("evidence", {}).get("qstar_microkernel_forward_cx") == 127112
        and editorial.get("evidence", {}).get("qstar_microkernel_clean_cx") == 254224
        and float(editorial.get("evidence", {}).get("qstar_microkernel_denominator_p95_relative_error", 1.0)) < 1.0e-3
        and float(editorial.get("evidence", {}).get("qstar_microkernel_qstar_p95_relative_error", 1.0)) < 5.0e-2
        and editorial.get("evidence", {}).get("qstar_ldf_address_bits") == 5
        and editorial.get("evidence", {}).get("qstar_ldf_arithmetic_bits") == 24
        and float(editorial.get("evidence", {}).get("qstar_ldf_qstar_p95_relative_error", 1.0)) < 5.0e-2
        and float(editorial.get("evidence", {}).get("qstar_ldf_next_p95_relative_error", 1.0)) < 1.0e-3
        and editorial.get("evidence", {}).get("qstar_ldf_logical_qubits") == 515
        and editorial.get("evidence", {}).get("qstar_ldf_cx") == 1225138
        and editorial.get("evidence", {}).get("qstar_ldf_depth") == 1919788
        and editorial.get("evidence", {}).get("product_boundary_balance_logical_qubits") == 842
        and editorial.get("evidence", {}).get("product_boundary_balance_cx") == 2348388
        and editorial.get("evidence", {}).get("product_boundary_balance_depth") == 3285605
        and editorial.get("evidence", {}).get("product_boundary_balance_states") == 6464
        and editorial.get("evidence", {}).get("product_boundary_balance_component_balances") == 32320
        and editorial.get("evidence", {}).get("internal_face_balance_logical_qubits") == 1508
        and editorial.get("evidence", {}).get("internal_face_balance_cx") == 8328622
        and editorial.get("evidence", {}).get("internal_face_balance_depth") == 12250291
        and editorial.get("evidence", {}).get("internal_face_balance_states") == 12928
        and editorial.get("evidence", {}).get("internal_face_balance_component_balances") == 64640
        and editorial.get("evidence", {}).get("normalized_internal_face_balance_logical_qubits") == 1651
        and editorial.get("evidence", {}).get("normalized_internal_face_balance_cx") == 14667150
        and editorial.get("evidence", {}).get("normalized_internal_face_balance_depth") == 22143683
        and editorial.get("evidence", {}).get("composition_normalizer_logical_qubits") == 333
        and editorial.get("evidence", {}).get("composition_normalizer_cx") == 1340232
        and editorial.get("evidence", {}).get("composition_normalization_states") == 25856
        and editorial.get("evidence", {}).get("composition_normalization_address_bits") == 8
        and float(editorial.get("evidence", {}).get("composition_normalization_p95_absolute_error_max", 1.0)) < 2.1e-4
        and editorial.get("evidence", {}).get("joint_transport_ldf_component_qubit_range") == [1944, 2039]
        and editorial.get("evidence", {}).get("joint_transport_ldf_component_cx_range") == [20670468, 35947274]
        and editorial.get("evidence", {}).get("joint_transport_ldf_peak_logical_qubits") == 2039
        and editorial.get("evidence", {}).get("joint_transport_ldf_additive_cx_upper_bound") == 128013726
        and editorial.get("evidence", {}).get("product_ldf_valve_component_qubit_range") == [1072, 1195]
        and editorial.get("evidence", {}).get("product_ldf_valve_component_cx_range") == [10060060, 26810396]
        and editorial.get("evidence", {}).get("product_ldf_valve_peak_logical_qubits") == 1195
        and editorial.get("evidence", {}).get("product_ldf_valve_additive_cx_upper_bound") == 88388552
        and len(editorial.get("evidence", {}).get("normalized_product_component_qubit_range", [])) == 2
        and len(editorial.get("evidence", {}).get("normalized_product_component_depth_range", [])) == 2
        and len(editorial.get("evidence", {}).get("normalized_product_component_cx_range", [])) == 2
        and editorial.get("evidence", {}).get("normalized_product_peak_logical_qubits", 0)
        == editorial.get("evidence", {}).get("normalized_product_component_qubit_range", [0, -1])[1]
        and editorial.get("evidence", {}).get("normalized_product_additive_cx_upper_bound", 0)
        > editorial.get("evidence", {}).get("normalized_product_component_cx_range", [0, 0])[1]
        and max(editorial.get("evidence", {}).get("normalized_product_next_p95_range", [1.0])) <= 2.5e-4
        and editorial.get("evidence", {}).get("normalized_product_next_max_error", 1.0) <= 5.0e-4
        and editorial.get("evidence", {}).get("coherent_interface_logical_qubits") == 440
        and editorial.get("evidence", {}).get("coherent_interface_depth") == 324495
        and editorial.get("evidence", {}).get("coherent_interface_cx") == 166189
        and editorial.get("evidence", {}).get("coherent_interface_parameter_checks") == 352
        and editorial.get("evidence", {}).get("coherent_interface_schedule_checks") == 8
        and editorial.get("evidence", {}).get("coherent_interface_tank_checks") == 640
        and editorial.get("evidence", {}).get("coherent_factor_ldf_logical_qubits") == 495
        and editorial.get("evidence", {}).get("coherent_factor_ldf_depth") == 526434
        and editorial.get("evidence", {}).get("coherent_factor_ldf_cx") == 353441
        and editorial.get("evidence", {}).get("coherent_factor_ldf_coefficient_records") == 320
        and editorial.get("evidence", {}).get("coherent_factor_ldf_schedule_flags") == 16
        and editorial.get("evidence", {}).get("coherent_factor_ldf_equilibrium_max", 1.0) <= 5.0e-5
        and editorial.get("evidence", {}).get("coherent_factor_ldf_alpha_max", 1.0) <= 4.4e-5
        and editorial.get("evidence", {}).get("coherent_coefficient_consumer_component_qubit_range") == [1297, 1486]
        and editorial.get("evidence", {}).get("coherent_coefficient_consumer_component_cx_range") == [1855912, 2807252]
        and editorial.get("evidence", {}).get("coherent_coefficient_consumer_peak_logical_qubits") == 1486
        and editorial.get("evidence", {}).get("coherent_coefficient_consumer_additive_depth_upper_bound") == 12387085
        and editorial.get("evidence", {}).get("coherent_coefficient_consumer_additive_cx_upper_bound") == 11911052
        and editorial.get("evidence", {}).get("coherent_coefficient_consumer_component_balance_records") == 64640
        and editorial.get("evidence", {}).get("coherent_coefficient_consumer_max_transfer_erasure_fraction") == 0.0
        and editorial.get("evidence", {}).get("coherent_dynamic_langmuir_component_qubit_range") == [1771, 1960]
        and editorial.get("evidence", {}).get("coherent_dynamic_langmuir_component_cx_range") == [41440216, 42391556]
        and editorial.get("evidence", {}).get("coherent_dynamic_langmuir_peak_logical_qubits") == 1960
        and editorial.get("evidence", {}).get("coherent_dynamic_langmuir_additive_depth_upper_bound") == 338501740
        and editorial.get("evidence", {}).get("coherent_dynamic_langmuir_additive_cx_upper_bound") == 209832572
        and editorial.get("evidence", {}).get("coherent_dynamic_langmuir_component_balance_records") == 64640
        and editorial.get("evidence", {}).get("coherent_dynamic_langmuir_denominator_max_error", 1.0) <= 3.6e-4
        and editorial.get("evidence", {}).get("coherent_normalized_dynamic_component_qubit_range") == [2696, 2885]
        and editorial.get("evidence", {}).get("coherent_normalized_dynamic_component_cx_range") == [55337688, 56289028]
        and editorial.get("evidence", {}).get("coherent_normalized_dynamic_peak_logical_qubits") == 2885
        and editorial.get("evidence", {}).get("coherent_normalized_dynamic_additive_depth_upper_bound") == 445738755
        and editorial.get("evidence", {}).get("coherent_normalized_dynamic_additive_cx_upper_bound") == 279319932
        and editorial.get("evidence", {}).get("coherent_normalized_dynamic_normalization_states") == 25856
        and editorial.get("evidence", {}).get("coherent_normalized_dynamic_component_balance_records") == 64640
        and editorial.get("evidence", {}).get("offledger_tank_records") == 128
        and editorial.get("evidence", {}).get("offledger_tank_common_bits") == 20
        and editorial.get("evidence", {}).get("offledger_tank_saturation_labels") == 128
        and abs(
            float(
                editorial.get("evidence", {}).get(
                    "offledger_tank_minimum_margin_mol", 0.0
                )
            )
            - 1.6244043497948013
        )
        < 1e-12
        and editorial.get("evidence", {}).get("offledger_tank_p95_error", 1.0)
        <= 2.1e-6
        and editorial.get("evidence", {}).get("offledger_tank_logical_qubits")
        == 557
        and editorial.get("evidence", {}).get("offledger_tank_depth") == 327212
        and editorial.get("evidence", {}).get("offledger_tank_cx") == 195276
        and editorial.get("evidence", {}).get("offledger_proportional_observed_saturated") == 128
        and editorial.get("evidence", {}).get("offledger_proportional_counterfactual_unsaturated") == 224
        and editorial.get("evidence", {}).get("offledger_proportional_common_bits") == 18
        and editorial.get("evidence", {}).get("offledger_proportional_address_bits") == 5
        and editorial.get("evidence", {}).get("offledger_proportional_reciprocal_bits") == 16
        and editorial.get("evidence", {}).get("offledger_proportional_p95_error", 1.0) <= 1.7e-4
        and editorial.get("evidence", {}).get("offledger_proportional_max_error", 1.0) <= 3.9e-4
        and editorial.get("evidence", {}).get("offledger_proportional_logical_qubits") == 647
        and editorial.get("evidence", {}).get("offledger_proportional_depth") == 1127046
        and editorial.get("evidence", {}).get("offledger_proportional_cx") == 705194
        and editorial.get("evidence", {}).get("primary_final_event_logical_qubits") == 125
        and editorial.get("evidence", {}).get("primary_final_event_clean_cx") == 182981
        and editorial.get("evidence", {}).get("primary_final_event_labels") == 32
        and editorial.get("evidence", {}).get("policy_stream_event_aggregate_bits") == 19
        and editorial.get("evidence", {}).get("policy_stream_event_candidate_labels") == 96
        and editorial.get("evidence", {}).get("policy_stream_event_ledger_labels") == 32
        and editorial.get("evidence", {}).get("policy_stream_event_logical_qubits") == 510
        and editorial.get("evidence", {}).get("policy_stream_event_clean_cx") == 1286021,
        f"png={GRAPHICAL_ABSTRACT_PNG.exists()}, pdf={GRAPHICAL_ABSTRACT_PDF.exists()}, response_CX={editorial.get('evidence', {}).get('response_oracle_cx_per_call')}",
    )
    check(
        checks,
        "gate package remains reproducible",
        gate.get("status") == "pass"
        and gate.get("qpu_submission") is False
        and len(gate.get("artifacts", [])) == 37,
        f"status={gate.get('status')}, artifacts={len(gate.get('artifacts', []))}, qpu_submission={gate.get('qpu_submission')}",
    )
    check(
        checks,
        "project-wide claim audit remains passing",
        claims.get("status") == "pass"
        and all(row.get("pass") for row in claims.get("checks", [])),
        f"status={claims.get('status')}, checks={len(claims.get('checks', []))}",
    )

    structural_pass = all(row["pass"] for row in checks)
    payload = {
        "schema": "psa-qae-cce-manuscript-draft-audit/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "draft_structure_pass_submission_gates_open"
            if structural_pass
            else "draft_structure_fail"
        ),
        "submission_ready": False,
        "submission_blockers": [
            "calibrated same-policy H2 recycle/event validation; the corrected pyAPEP path is a non-CSS topology-feasibility stress test",
            "multi-backend repeated QPU evidence with a noise-aware interval",
            "a synthesized reversible nonlinear tank/spatial cycle map feeding the compiled policy stream-to-event oracle; the physical 85-cycle horizon, out-of-place register accounting, five parameter-specialized normalized-transport/LDF/interior-balance paths, gas-inventory-generated product-cell LDF/valve/boundary-balance paths, a finite-support coherent run/schedule/tank interface, direct controller-to-five-component coefficient arithmetic, dynamic run-affinity Langmuir denominator/reciprocal generation, response consumption in schedule-gated component LDF/loading/balance paths, pressure-derived saturated plus bounded-counterfactual unsaturated proportional tank allocation, and one short-schedule source-model physical unsaturated control are quantified, while frozen-schedule physical unsaturated coverage, monolithic five-component phase integration, adaptive integration, and remaining workspace remain open",
            "final author approvals and declarations, and a permanent public archive",
        ],
        "word_count": words,
        "abstract_word_count": abstract_words,
        "citation_keys": citations,
        "checks": checks,
        "note": (
            "Passing this audit establishes manuscript structure and internal consistency only. "
            "It does not close the listed external evidence gates or establish acceptance, plant validation, or quantum advantage."
        ),
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# CCE manuscript draft audit",
        "",
        f"Status: **{payload['status']}**",
        "",
        f"Submission ready: **{payload['submission_ready']}**",
        "",
        f"Main-text words: {words}. Abstract words: {abstract_words}. Resolved citation keys: {len(citations)}.",
        "",
        "| check | pass | detail |",
        "|---|---|---|",
    ]
    for row in checks:
        detail = str(row["detail"]).replace("|", "/")
        lines.append(f"| {row['name']} | {row['pass']} | {detail} |")
    lines += ["", "## Open submission gates", ""]
    lines.extend(f"- {value}" for value in payload["submission_blockers"])
    lines += ["", payload["note"]]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "checks": len(checks), "words": words}, indent=2))
    if not structural_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
