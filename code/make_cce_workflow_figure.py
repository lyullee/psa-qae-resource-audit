"""Create the reviewer-facing workflow figure for the CCE PSA-QAE paper."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
PNG = OUT / "PSA_QAE_CCE_WORKFLOW_FIGURE.png"
PDF = OUT / "PSA_QAE_CCE_WORKFLOW_FIGURE.pdf"


def box(ax, xy, width, height, title, body, color, edge="#243447"):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=1.25,
        edgecolor=edge,
        facecolor=color,
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height * 0.69,
        title,
        ha="center",
        va="center",
        fontsize=10.3,
        weight="bold",
        color="#14202b",
        zorder=3,
    )
    ax.text(
        x + width / 2,
        y + height * 0.34,
        body,
        ha="center",
        va="center",
        fontsize=8.1,
        color="#263747",
        linespacing=1.22,
        zorder=3,
    )
    return patch


def arrow(ax, start, end, color="#495867", style="-|>", lw=1.45):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=12,
            linewidth=lw,
            color=color,
            shrinkA=4,
            shrinkB=4,
            connectionstyle="arc3",
            zorder=1,
        )
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13.2, 7.2), constrained_layout=True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.955,
        "Resource-aware PSA chance-constraint workflow",
        ha="center",
        va="center",
        fontsize=17,
        weight="bold",
        color="#14202b",
    )

    # Primary decision path.
    y = 0.62
    h = 0.205
    w = 0.165
    xs = [0.025, 0.225, 0.425, 0.625, 0.825]
    box(
        ax,
        (xs[0], y),
        w,
        h,
        "Process evidence",
        "32 CSS PSA runs\n+ physical and public\nvalidation controls",
        "#dceef8",
    )
    box(
        ax,
        (xs[1], y),
        w,
        h,
        "Conditional model",
        "Affine purity/recovery\nresponse + regularized\nempirical copula",
        "#dceef8",
    )
    box(
        ax,
        (xs[2], y),
        w,
        h,
        "Classical outer policy",
        "Recycle candidates\n0.420 / 0.427 / 0.430",
        "#e9e1f7",
    )
    box(
        ax,
        (xs[3], y),
        w,
        h,
        "Matched inner estimators",
        "MC  |  RQMC  |  IS\nMLAE on the same event",
        "#fff0cf",
    )
    box(
        ax,
        (xs[4], y),
        w,
        h,
        "Chance decision",
        "Largest policy with\nP(purity & recovery)\n≥ 0.50",
        "#dff2df",
    )
    for i in range(4):
        arrow(ax, (xs[i] + w, y + h / 2), (xs[i + 1], y + h / 2))

    # Resource-audit path.
    y2 = 0.235
    h2 = 0.195
    xs2 = [0.125, 0.335, 0.545, 0.755]
    w2 = 0.145
    box(
        ax,
        (xs2[0], y2),
        w2,
        h2,
        "State preparation",
        "Correlated prior\nlow-bit dense control\nand structured gap",
        "#f8dfe4",
    )
    box(
        ax,
        (xs2[1], y2),
        w2,
        h2,
        "Reversible oracle",
        "Fixed-point response\ncomparator, phase mark,\nuncomputation",
        "#f8dfe4",
    )
    box(
        ax,
        (xs2[2], y2),
        w2,
        h2,
        "Amplification & QPU",
        "MLAE powers, compiled\ngates, hardware counts\nand calibration",
        "#f8dfe4",
    )
    box(
        ax,
        (xs2[3], y2),
        w2,
        h2,
        "Decision boundary",
        "Accuracy, total work,\nmodel discrepancy\nand noise",
        "#f4e6d2",
    )
    for i in range(3):
        arrow(ax, (xs2[i] + w2, y2 + h2 / 2), (xs2[i + 1], y2 + h2 / 2))

    # Couple the estimator to the resource implementation and return the
    # resource conclusion to the decision.
    arrow(
        ax,
        (xs[3] + w / 2, y),
        (xs2[0] + w2 / 2, y2 + h2),
        color="#8b3a50",
    )
    arrow(
        ax,
        (xs2[3] + w2 / 2, y2 + h2),
        (xs[4] + w / 2, y),
        color="#8b3a50",
    )

    ax.text(
        0.035,
        0.51,
        "Primary decision evidence",
        fontsize=10,
        weight="bold",
        color="#2f5f7a",
        va="center",
    )
    ax.plot([0.195, 0.965], [0.51, 0.51], color="#8aa9bc", lw=1.0)
    ax.text(
        0.035,
        0.485,
        "Conditional on the declared response surface and prior",
        fontsize=8.3,
        color="#526b7a",
        va="center",
    )

    ax.text(
        0.035,
        0.125,
        "Resource and validity audit",
        fontsize=10,
        weight="bold",
        color="#8b3a50",
        va="center",
    )
    ax.plot([0.195, 0.965], [0.125, 0.125], color="#c997a5", lw=1.0)
    ax.text(
        0.035,
        0.098,
        "Separates ideal queries from loader, reversible arithmetic, hardware noise, and process-model error",
        fontsize=8.3,
        color="#6e4b56",
        va="center",
    )

    ax.text(
        0.5,
        0.035,
        "Outcome: current PSA case favors RQMC; QAE remains a conditional future regime with explicit closure requirements.",
        ha="center",
        va="center",
        fontsize=9.4,
        weight="bold",
        color="#263747",
    )

    fig.savefig(PNG, dpi=300, bbox_inches="tight")
    fig.savefig(PDF, bbox_inches="tight")
    plt.close(fig)
    print(PNG)
    print(PDF)


if __name__ == "__main__":
    main()
