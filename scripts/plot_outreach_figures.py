"""Create outreach figures from event-modeling manifests."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "docs" / "figures"


def load_manifest(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def percent(value: float) -> float:
    return 100.0 * value


def clean_axis(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#d7d7d7", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)


def annotate_bars(ax: plt.Axes, bars, fmt: str = "{:+.1f}%") -> None:
    for bar in bars:
        value = bar.get_height()
        if value >= 0:
            y_value = value + 1.2
            va = "bottom"
            color = "#222222"
        else:
            y_value = value + 1.2
            va = "bottom"
            color = "white" if abs(value) > 12 else "#222222"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y_value,
            fmt.format(value),
            ha="center",
            va=va,
            fontsize=8,
            color=color,
        )


def figure_static_vs_event() -> None:
    proxy = load_manifest("data/manifests/htem_event_proxy_xrd_prediction_cu_s_sn.json")
    controls = load_manifest("data/manifests/htem_event_field_hard_controls_cu_s_sn.json")

    static_models = [
        ("Recipe", "recipe_only"),
        ("Recipe+xy", "recipe_plus_position"),
        ("Sample ID", "sample_id_only"),
        ("Provenance", "provenance_only"),
    ]
    static_values = [
        percent(
            proxy["results"]["held_out_library"]["models"][model][
                "mse_improvement_vs_train_mean"
            ]["mean"]
        )
        for _, model in static_models
    ]

    event_splits = [
        ("Space-fill", "space_filling_32"),
        ("Random", "random_32"),
        ("Held-out row", "held_out_row"),
        ("Held-out quad", "held_out_quadrant"),
    ]
    event_values = [
        percent(
            controls["summary"][split]["models"]["idw_all"][
                "mse_improvement_vs_event_mean"
            ]
        )
        for _, split in event_splits
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), constrained_layout=False)
    fig.suptitle(
        "Static rows do not transfer; partial event fields do reconstruct",
        fontsize=15,
        fontweight="bold",
    )
    fig.subplots_adjust(left=0.08, right=0.98, top=0.82, bottom=0.26, wspace=0.28)

    ax = axes[0]
    bars = ax.bar(
        [label for label, _ in static_models],
        static_values,
        color=["#d95f02" if value < 0 else "#999999" for value in static_values],
    )
    ax.axhline(0, color="#333333", linewidth=1)
    ax.set_title("Held-out HTEM libraries", fontsize=11)
    ax.set_ylabel("MSE improvement vs train mean")
    ax.set_ylim(-24, 8)
    clean_axis(ax)
    annotate_bars(ax, bars)
    ax.text(
        0.5,
        -0.18,
        "Static material-row metadata cannot predict unseen libraries.",
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        color="#333333",
    )

    ax = axes[1]
    bars = ax.bar(
        [label for label, _ in event_splits],
        event_values,
        color=["#1b9e77", "#66a61e", "#7570b3", "#7570b3"],
    )
    ax.axhline(0, color="#333333", linewidth=1)
    ax.set_title("Within-library missing XRD", fontsize=11)
    ax.set_ylabel("MSE improvement vs observed event mean")
    ax.set_ylim(0, 25)
    clean_axis(ax)
    annotate_bars(ax, bars)
    ax.text(
        0.5,
        -0.18,
        "Partial raw measurements reconstruct the event field.",
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        color="#333333",
    )

    fig.text(
        0.5,
        0.05,
        "Note: panels use different baselines because they test different claims: transfer across events vs reconstruction within an event.",
        ha="center",
        fontsize=8,
        color="#555555",
    )
    fig.savefig(FIG_DIR / "htem_static_vs_event_field.png", dpi=220)
    plt.close(fig)


def figure_hard_controls() -> None:
    controls = load_manifest("data/manifests/htem_event_field_hard_controls_cu_s_sn.json")
    splits = [
        ("Space-fill", "space_filling_32"),
        ("Random", "random_32"),
        ("Held-out row", "held_out_row"),
        ("Held-out quad", "held_out_quadrant"),
    ]
    metrics = [
        ("MSE vs event mean", "mse_improvement_vs_event_mean", "#1b9e77"),
        ("MSE vs shuffled xy", "mse_improvement_vs_idw_shuffled_coords", "#377eb8"),
        ("Peak MAE vs event mean", "peak_mae_improvement_vs_event_mean", "#e6ab02"),
    ]
    x = np.arange(len(splits))
    width = 0.24

    fig, ax = plt.subplots(figsize=(10.5, 4.8), constrained_layout=True)
    fig.suptitle(
        "Hard controls: the signal is spatial field structure",
        fontsize=15,
        fontweight="bold",
    )
    for offset, (label, key, color) in zip([-width, 0, width], metrics, strict=False):
        values = [
            percent(controls["summary"][split]["models"]["idw_all"][key])
            for _, split in splits
        ]
        bars = ax.bar(x + offset, values, width=width, label=label, color=color)
        annotate_bars(ax, bars)

    ax.set_xticks(x, [label for label, _ in splits])
    ax.set_ylabel("Improvement")
    ax.set_ylim(0, 65)
    ax.legend(loc="upper right", frameon=False)
    clean_axis(ax)
    ax.text(
        0.02,
        -0.21,
        "Correct coordinates beat shuffled-coordinate IDW; contiguous row/quadrant holdouts are harder but still positive.",
        transform=ax.transAxes,
        fontsize=9,
        color="#333333",
    )
    fig.savefig(FIG_DIR / "htem_event_field_hard_controls.png", dpi=220)
    plt.close(fig)


def figure_neural_guardrail() -> None:
    masked = load_manifest("data/manifests/htem_masked_event_model_cu_s_sn.json")
    summary = masked["summary"]
    rows = {
        row["model"]: row
        for row in summary
        if row["observed_count"] == 32 and row["strategy"] == "space_filling"
    }
    models = [
        ("IDW", "idw_all"),
        ("Raw residual NN", "masked_event_raw_residual"),
        ("Linear xy", "xy_ridge_linear"),
        ("Event mean", "observed_event_mean"),
        ("Raw-set NN", "masked_event_raw_set"),
        ("Coord-only NN", "masked_event_coord_only"),
    ]
    values = [
        percent(rows[model]["improvement_vs_event_mean_mean"])
        for _, model in models
    ]
    colors = ["#1b9e77", "#66a61e", "#7570b3", "#999999", "#d95f02", "#d95f02"]

    fig, ax = plt.subplots(figsize=(10, 4.8), constrained_layout=True)
    fig.suptitle(
        "Neural guardrail: architecture is not the current headline",
        fontsize=15,
        fontweight="bold",
    )
    bars = ax.bar([label for label, _ in models], values, color=colors)
    ax.axhline(0, color="#333333", linewidth=1)
    ax.set_ylabel("MSE improvement vs observed event mean")
    ax.set_ylim(-155, 30)
    clean_axis(ax)
    annotate_bars(ax, bars)
    ax.text(
        0.5,
        -0.22,
        "The residual NN nearly matches IDW, but does not beat it; coord-only collapses. This supports event-objective design, not an architecture claim.",
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        color="#333333",
    )
    fig.savefig(FIG_DIR / "htem_neural_guardrail.png", dpi=220)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    figure_static_vs_event()
    figure_hard_controls()
    figure_neural_guardrail()
    print(f"wrote figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
