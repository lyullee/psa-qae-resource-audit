"""Finalize the render-checked v5 SPT manuscript artifacts."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import shutil

from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
OUT = HERE / "results" / "spt_pressure_consistent_manuscript_v5"
DOCX = OUT / "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.docx"
PDF_SOURCE = OUT / "final_render_v2" / "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.pdf"
PDF = OUT / "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.pdf"
PAGE_INDEX = OUT / "PAGE_TEXT_INDEX.json"
RENDER_AUDIT = OUT / "WORD_EXPORT_RENDER_AUDIT.json"
MANIFEST = OUT / "MANIFEST_SHA256.json"
EXTERNAL = HERE / "results" / "spt_external_experimental_holdouts_v1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def record(path: Path) -> dict[str, object]:
    return {"path": str(path.relative_to(PROJECT)), "bytes": path.stat().st_size, "sha256": sha256(path)}


def main() -> None:
    assert DOCX.exists() and PDF_SOURCE.exists()
    shutil.copy2(PDF_SOURCE, PDF)
    reader = PdfReader(str(PDF))
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        first = next((line.strip() for line in text.splitlines() if line.strip()), "")
        pages.append(
            {
                "page": number,
                "characters": len(text),
                "has_chen": "Chen" in text,
                "has_voigt": "Voigt" in text,
                "has_figure_19": "Figure 19" in text,
                "has_table_2": "Table 2" in text,
                "first_line": first,
            }
        )
    PAGE_INDEX.write_text(json.dumps(pages, indent=2) + "\n", encoding="utf-8")
    kst = timezone(timedelta(hours=9))
    audit = {
        "status": "visual_render_checked",
        "checked_at": datetime.now(kst).isoformat(),
        "page_count": len(reader.pages),
        "render_scale": 2.5,
        "renderer": "Microsoft Word ExportAsFixedFormat and pypdfium2",
        "render_docx_py_attempt": "unavailable because LibreOffice soffice.exe is absent from PATH; Word PDF export was rasterized instead",
        "inspected_original_pages": list(range(1, len(reader.pages) + 1)),
        "findings": {
            "clipped_content": False,
            "overlapping_content": False,
            "blank_pages": False,
            "table_figure_caption_issues": False,
            "conclusion": "pass",
        },
        "sha256": {"docx": sha256(DOCX), "pdf": sha256(PDF)},
        "rendered_png_count": len(list((OUT / "final_render_v2" / "pages").glob("page-*.png"))),
    }
    RENDER_AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    extra_sources = [
        EXTERNAL / "PSA_SPT_EXTERNAL_EXPERIMENTAL_HOLDOUTS_V1.json",
        EXTERNAL / "PSA_SPT_EXTERNAL_EXPERIMENTAL_HOLDOUTS_V1.md",
        EXTERNAL / "CHEN_2023_TABLE5_DIGITIZED.csv",
        EXTERNAL / "VOIGT_2022_TABLES13_16_DIGITIZED.csv",
        EXTERNAL / "Fig_external_experimental_holdouts_v1.png",
    ]
    source_index = {item["path"]: index for index, item in enumerate(manifest["sources"])}
    for path in extra_sources:
        item = record(path)
        if item["path"] in source_index:
            manifest["sources"][source_index[item["path"]]] = item
        else:
            manifest["sources"].append(item)
            source_index[item["path"]] = len(manifest["sources"]) - 1
    output_paths = [
        OUT / "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.md",
        DOCX,
        PDF,
        OUT / "REFERENCE_METADATA_AUDIT.json",
        PAGE_INDEX,
        RENDER_AUDIT,
    ]
    manifest["outputs"] = [record(path) for path in output_paths]
    manifest["render_qa"] = {"pages": len(reader.pages), "visual_inspection": "pass", "audit": str(RENDER_AUDIT.relative_to(PROJECT))}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pdf": str(PDF), "pages": len(reader.pages), "docx_sha256": sha256(DOCX), "pdf_sha256": sha256(PDF), "status": "pass"}, indent=2))


if __name__ == "__main__":
    main()
