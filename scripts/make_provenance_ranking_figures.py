"""Build straightforward figures for the provenance-stressed Severson story.

Every plotted value is read from a committed or working-tree manifest. The figures are
designed as communication artifacts: one claim per figure, direct labels, and no
decorative chart furniture.

Outputs (PNG + SVG in docs/controlled-collection/figures/):
  fig_ranking_batch_local       — primary ridge result on the pair-rich third batch
  fig_batch_pair_balance        — where the 160 ranking pairs come from
  fig_transfer_all_models       — within-corpus versus held-out-batch by model
  fig_skill_decoupling          — lifetime-level skill versus sibling-ranking skill
  fig_where_provenance_lives    — provenance carriers across three datasets
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parents[1]
FIGDIR = ROOT / "docs/controlled-collection/figures"
MANIFESTS = ROOT / "data/manifests"

# A small, colorblind-friendly visual language.
INK = "#17212B"
MUTED = "#66727D"
GRID = "#DCE2E6"
PAPER = "#F6F7F8"
NAVY = "#24557A"
TEAL = "#2A8C82"
AMBER = "#E4A11B"
CORAL = "#D95F59"
LIGHT_CORAL = "#F4D8D5"
LIGHT_TEAL = "#D9EEEA"

MODEL_LABELS = {
    "ridge": "Ridge",
    "knn": "k-nearest neighbors",
    "svr_rbf": "RBF support vector",
    "forest": "Random forest",
    "gradient_boosting": "Gradient boosting",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.labelcolor": INK,
            "axes.edgecolor": INK,
            "axes.titlecolor": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": INK,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def load(name: str) -> dict:
    return json.loads((MANIFESTS / name).read_text())


def title_block(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.08, 0.95, title, ha="left", va="top", fontsize=18, fontweight="bold")
    fig.text(0.08, 0.895, subtitle, ha="left", va="top", fontsize=10.5, color=MUTED)


def source_note(fig: plt.Figure, text: str) -> None:
    fig.text(0.08, 0.025, text, ha="left", va="bottom", fontsize=7.5, color=MUTED)


def save(fig: plt.Figure, stem: str) -> None:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGDIR / f"{stem}.png", dpi=220, bbox_inches="tight")
    fig.savefig(FIGDIR / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)


def clean_axis(ax: plt.Axes, *, grid_axis: str | None = None) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)


def fig_ranking_batch_local() -> None:
    """The single result that changes the claim: ridge on the pair-rich batch."""
    manifest = load("severson_heldout_batch_ranking.json")
    batch = "2018-04-12"
    result = manifest["results"]["ridge"]["per_batch"][batch]
    within = result["loo_policy_accuracy"]
    held = result["held_out_batch_accuracy"]
    low, high = result["held_out_batch_cluster_ci95"]
    n_pairs = result["n_pairs"]

    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    fig.subplots_adjust(left=0.12, right=0.95, top=0.78, bottom=0.19)
    title_block(
        fig,
        "The ranking signal disappears on an unseen collection batch",
        f"Ridge model · same {n_pairs} within-recipe pairs from Severson batch 3",
    )

    x = np.array([0.0, 1.0])
    y = np.array([within, held])
    ax.plot(x, y, color=MUTED, linewidth=2.3, zorder=2)
    ax.scatter(x[0], y[0], s=250, color=NAVY, edgecolor="white", linewidth=1.5, zorder=3)
    ax.errorbar(
        x[1],
        y[1],
        yerr=[[held - low], [high - held]],
        fmt="o",
        markersize=13,
        color=CORAL,
        ecolor=CORAL,
        elinewidth=2.2,
        capsize=7,
        capthick=2.2,
        markeredgecolor="white",
        markeredgewidth=1.5,
        zorder=3,
    )
    ax.axhline(0.5, color=INK, linewidth=1.2, linestyle=(0, (4, 4)))

    ax.text(x[0], within + 0.035, f"{within:.3f}", ha="center", fontsize=16, fontweight="bold")
    ax.text(x[1], held - 0.075, f"{held:.3f}", ha="center", fontsize=16, fontweight="bold")
    ax.text(
        1.04,
        high,
        f"95% CI\n{low:.3f}–{high:.3f}",
        ha="left",
        va="center",
        fontsize=9.5,
        color=CORAL,
    )
    ax.text(
        0.5,
        (within + held) / 2 + 0.045,
        f"−{within - held:.3f}",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=CORAL,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 2},
    )
    ax.text(
        -0.32,
        0.505,
        "chance = paper-shaped recipe (0.500)",
        ha="left",
        va="bottom",
        fontsize=9,
        color=MUTED,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            "Model has seen batch 3\nleave-one-policy-out",
            "Batch 3 is unseen\ntrain on batches 1 + 2",
        ],
        fontsize=11,
        color=INK,
    )
    ax.set_xlim(-0.35, 1.42)
    ax.set_ylim(0.25, 0.88)
    ax.set_ylabel("Sibling-ranking accuracy")
    clean_axis(ax, grid_axis="y")
    source_note(
        fig,
        "Source: severson_heldout_batch_ranking.json · cluster bootstrap over policy groups",
    )
    save(fig, "fig_ranking_batch_local")


def fig_batch_pair_balance() -> None:
    """Make the effective evidence imbalance impossible to miss."""
    manifest = load("severson_heldout_batch_ranking.json")
    counts = manifest["pairs_per_batch"]
    batches = ["2018-04-12", "2017-05-12", "2017-06-30"]
    labels = ["Batch 3", "Batch 1", "Batch 2"]
    values = np.array([counts[b] for b in batches], dtype=float)
    total = int(values.sum())
    shares = values / total
    colors = [NAVY, TEAL, AMBER]

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    fig.subplots_adjust(left=0.08, right=0.95, top=0.72, bottom=0.21)
    title_block(
        fig,
        "One batch supplies 85% of the ranking evidence",
        f"Distribution of all {total} resolvable within-recipe pairs",
    )

    left = 0.0
    for label, count, share, color in zip(labels, values, shares, colors, strict=True):
        ax.barh(0, share, left=left, height=0.42, color=color, edgecolor="white", linewidth=2)
        if share > 0.08:
            ax.text(
                left + share / 2,
                0,
                f"{label}\n{int(count)} pairs · {share:.0%}",
                ha="center",
                va="center",
                color="white",
                fontsize=11,
                fontweight="bold",
            )
        left += share

    # Direct labels for the two narrow segments.
    ax.annotate(
        f"Batch 2\n{int(values[2])} pairs · {shares[2]:.0%}",
        xy=(1 - shares[2] / 2, 0.22),
        xytext=(0.89, 0.59),
        ha="center",
        va="bottom",
        fontsize=9.5,
        color=INK,
        arrowprops={"arrowstyle": "-", "color": AMBER, "lw": 1.3},
    )
    ax.text(
        0,
        -0.57,
        "Only batch 3 has enough pairs for a meaningful transfer test.",
        ha="left",
        va="center",
        fontsize=12,
        fontweight="bold",
        color=CORAL,
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.9, 0.82)
    ax.axis("off")
    source_note(fig, "Source: severson_heldout_batch_ranking.json")
    save(fig, "fig_batch_pair_balance")


def fig_transfer_all_models() -> None:
    """Show the transfer loss for every model without asking the legend to do the work."""
    manifest = load("severson_heldout_batch_ranking.json")
    batch = "2018-04-12"
    order = ["ridge", "knn", "svr_rbf", "forest", "gradient_boosting"]
    y = np.arange(len(order))[::-1]

    within = np.array(
        [manifest["results"][model]["per_batch"][batch]["loo_policy_accuracy"] for model in order]
    )
    held = np.array(
        [
            manifest["results"][model]["per_batch"][batch]["held_out_batch_accuracy"]
            for model in order
        ]
    )
    cis = np.array(
        [
            manifest["results"][model]["per_batch"][batch]["held_out_batch_cluster_ci95"]
            for model in order
        ]
    )

    fig, ax = plt.subplots(figsize=(10.2, 6.2))
    fig.subplots_adjust(left=0.25, right=0.94, top=0.78, bottom=0.17)
    title_block(
        fig,
        "No model family carries the ranking rule to a new batch",
        "Batch 3 · 136 pairs · navy = model saw batch 3 · coral = batch 3 held out",
    )

    ax.axvspan(0.47, 0.53, color=PAPER, zorder=0)
    ax.axvline(0.5, color=INK, linewidth=1.2, linestyle=(0, (4, 4)))
    for i in range(len(order)):
        ax.plot([held[i], within[i]], [y[i], y[i]], color=GRID, linewidth=5, zorder=1)
        ax.scatter(within[i], y[i], s=105, color=NAVY, edgecolor="white", zorder=3)
        low, high = cis[i]
        ax.errorbar(
            held[i],
            y[i],
            xerr=[[held[i] - low], [high - held[i]]],
            fmt="o",
            markersize=8,
            color=CORAL,
            ecolor=CORAL,
            elinewidth=1.8,
            capsize=4,
            markeredgecolor="white",
            zorder=3,
        )
        ax.text(within[i] + 0.012, y[i] + 0.12, f"{within[i]:.3f}", color=NAVY, fontsize=9)
        ax.text(held[i] - 0.012, y[i] - 0.24, f"{held[i]:.3f}", color=CORAL, fontsize=9, ha="right")

    ax.text(0.503, len(order) - 0.22, "chance", color=MUTED, fontsize=9, ha="left")
    ax.set_yticks(y)
    ax.set_yticklabels([MODEL_LABELS[m] for m in order], fontsize=11, color=INK)
    ax.set_xlim(0.25, 0.84)
    ax.set_ylim(-0.65, len(order) - 0.35)
    ax.set_xlabel("Sibling-ranking accuracy")
    clean_axis(ax, grid_axis="x")
    source_note(
        fig,
        "Source: severson_heldout_batch_ranking.json · coral intervals are cluster-bootstrap 95% CIs",
    )
    save(fig, "fig_transfer_all_models")


def fig_skill_decoupling() -> None:
    """Two aligned task columns make the task mismatch more literal than a scatter plot."""
    manifest = load("severson_ranking_robustness.json")
    order = ["knn", "ridge", "svr_rbf", "gradient_boosting", "forest"]
    model_colors = {
        "ridge": NAVY,
        "knn": NAVY,
        "svr_rbf": NAVY,
        "forest": CORAL,
        "gradient_boosting": CORAL,
    }
    left_label_y = {
        "knn": 0.868,
        "ridge": 0.835,
        "svr_rbf": 0.808,
        "gradient_boosting": 0.783,
        "forest": 0.752,
    }
    right_label_y = {
        "ridge": 0.758,
        "knn": 0.638,
        "svr_rbf": 0.610,
        "forest": 0.580,
        "gradient_boosting": 0.535,
    }

    fig, ax = plt.subplots(figsize=(10.2, 6.4))
    fig.subplots_adjust(left=0.12, right=0.91, top=0.75, bottom=0.15)
    title_block(
        fig,
        "Predicting lifetime levels is not the same as ranking siblings",
        "The same five models, evaluated on two different questions",
    )

    for model in order:
        result = manifest["results"][model]
        left = result["held_out_policy_spearman"]
        right = result["pairwise_accuracy"]
        color = model_colors[model]
        ax.plot([0, 1], [left, right], color=color, alpha=0.75, linewidth=2)
        ax.scatter([0, 1], [left, right], s=90, color=color, edgecolor="white", zorder=3)
        left_y = left_label_y[model]
        right_y = right_label_y[model]
        ax.plot([-0.03, 0], [left_y, left], color=color, linewidth=0.9, alpha=0.6)
        ax.plot([1, 1.03], [right, right_y], color=color, linewidth=0.9, alpha=0.6)
        ax.text(
            -0.04,
            left_y,
            f"{MODEL_LABELS[model]}  {left:.3f}",
            ha="right",
            va="center",
            fontsize=9.5,
        )
        ax.text(
            1.04,
            right_y,
            f"{right:.3f}  {MODEL_LABELS[model]}",
            ha="left",
            va="center",
            fontsize=9.5,
        )

    ax.axhline(0.5, xmin=0.52, xmax=1.0, color=INK, linewidth=1, linestyle=(0, (4, 4)))
    ax.text(1.03, 0.5, "chance", ha="left", va="center", fontsize=9, color=MUTED)
    ax.text(
        0.5,
        0.555,
        "Gradient boosting:\nstrong level prediction,\nnear-chance sibling ranking",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color=CORAL,
        bbox={"facecolor": "white", "edgecolor": LIGHT_CORAL, "boxstyle": "round,pad=0.5"},
    )

    ax.set_xlim(-0.28, 1.28)
    ax.set_ylim(0.48, 0.89)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(
        [
            "Lifetime-level prediction\nheld-out-policy Spearman",
            "Same-recipe sibling ranking\npairwise accuracy",
        ],
        fontsize=11,
        color=INK,
    )
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    source_note(fig, "Source: severson_ranking_robustness.json · coral lines are tree ensembles")
    save(fig, "fig_skill_decoupling")


def risk_class(score: float | None) -> int:
    if score is None:
        return 0
    if score < 0.15:
        return 1
    if score < 0.50:
        return 2
    return 3


def fig_where_provenance_lives() -> None:
    """A semantic matrix is easier to compare than three differently shaped bar charts."""
    op = {
        row["feature_set"]: row["provenance_recoverability_score"]
        for row in load("provenance_leakage_audit_opxrd_r2.json")["results"]
    }
    rruff = {
        row["feature_set"]: row["provenance_recoverability_score"]
        for row in load("provenance_leakage_audit_rruff_paired.json")["results"]
    }
    severson = {
        row["feature_set"]: row["provenance_recoverability_score"]
        for row in load("provenance_leakage_audit_severson_ab.json")["results"]
    }

    values: list[list[float | None]] = [
        [op["metadata"], rruff["metadata"], None],
        [op["coverage_mask_pca"], rruff["coverage_mask_pca"], None],
        [op["xrd_pca"], rruff["raman_pca"], severson["a_trajectory_k100"]],
        [op["crop_xrd_derivative_pca"], rruff["crop_raman_derivative_pca"], None],
        [None, None, severson["b_policy"]],
    ]
    row_labels = [
        "Acquisition metadata",
        "Coverage / sampling geometry",
        "Measurement content",
        "After strongest processing control",
        "Recipe / policy",
    ]
    col_labels = [
        "opXRD\nsource / lab",
        "RRUFF Raman\nlaser · chemistry matched",
        "Severson\ncollection batch",
    ]
    classes = np.array([[risk_class(value) for value in row] for row in values])
    cmap = ListedColormap([PAPER, LIGHT_TEAL, "#F7E7B7", LIGHT_CORAL])

    fig, ax = plt.subplots(figsize=(10.2, 6.2))
    fig.subplots_adjust(left=0.34, right=0.94, top=0.76, bottom=0.17)
    title_block(
        fig,
        "Provenance is recoverable—but the carrier changes by dataset",
        "Normalized recoverability: 0 = chance, 1 = perfect · blank = not applicable",
    )

    ax.imshow(classes, cmap=cmap, vmin=0, vmax=3, aspect="auto")
    for row_idx, row in enumerate(values):
        for col_idx, value in enumerate(row):
            if value is None:
                ax.text(col_idx, row_idx, "—", ha="center", va="center", color="#AAB2B8", fontsize=15)
                continue
            ax.text(
                col_idx,
                row_idx,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=15,
                fontweight="bold",
                color=INK,
            )

    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, fontsize=10.5, color=INK)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", pad=12, length=0)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=10.5, color=INK)
    ax.tick_params(axis="y", length=0)
    ax.set_xticks(np.arange(-0.5, len(col_labels), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(row_labels), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=5)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.text(0.34, 0.09, "clean < 0.15", color=TEAL, fontsize=9, fontweight="bold")
    fig.text(0.48, 0.09, "elevated 0.15–0.49", color="#A87300", fontsize=9, fontweight="bold")
    fig.text(0.67, 0.09, "severe ≥ 0.50", color=CORAL, fontsize=9, fontweight="bold")
    source_note(
        fig,
        "Sources: provenance_leakage_audit_opxrd_r2.json, "
        "provenance_leakage_audit_rruff_paired.json, provenance_leakage_audit_severson_ab.json",
    )
    save(fig, "fig_where_provenance_lives")


def main() -> None:
    configure_style()
    fig_ranking_batch_local()
    fig_batch_pair_balance()
    fig_transfer_all_models()
    fig_skill_decoupling()
    fig_where_provenance_lives()
    print(f"Wrote 5 figures (PNG + SVG) to {FIGDIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
