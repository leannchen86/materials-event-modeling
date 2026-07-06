"""Compare provenance assignment strategies for a Track B pilot design.

The goal is to stress-test whether a planned 48-event pilot is counterbalanced enough to
survive provenance-blocked ablations.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from materials_event_modeling.track_b.synthetic import generate_synthetic_track_b

DEFAULT_SEEDS = [17, 29, 41, 53, 67]
ASSIGNMENT_MODES = [
    "confounded_operator",
    "random_group",
    "balanced_plan",
    "balanced_replicate",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_event_analysis_module() -> Any:
    script_path = project_root() / "scripts" / "run_track_b_event_analysis.py"
    spec = importlib.util.spec_from_file_location("track_b_event_analysis", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def provenance_balance_audit(table: pd.DataFrame) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for column in ["batch_id", "operator_id", "reagent_lot"]:
        crosstab = pd.crosstab(table[column], table["hidden_regime"])
        normalized = crosstab.div(crosstab.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
        rows[column] = {
            "counts": crosstab.to_dict(),
            "max_hidden_regime_share_within_group": float(normalized.max(axis=1).max()),
            "group_count": int(crosstab.shape[0]),
        }
    return rows


def get_improvement(
    analysis: dict[str, Any],
    *,
    split: str,
    view: str,
    residualized: bool = False,
) -> float | None:
    section = analysis["provenance_ablation_audit"].get(split, {})
    if not section or "skipped" in section:
        return None
    if residualized:
        view_result = section["target_residualized_against_provenance"].get(view)
        if view_result is None:
            return None
        return float(view_result["mse_improvement_vs_residual_train_mean"])
    view_result = section["original_prediction"].get(view)
    if view_result is None:
        return None
    return float(view_result["mse_improvement_vs_train_mean"])


def get_shuffle_improvement(analysis: dict[str, Any], view: str) -> float | None:
    section = analysis["provenance_ablation_audit"].get(
        "within_provenance_feature_shuffle_on_heldout_plan", {}
    )
    view_result = section.get(view)
    if view_result is None:
        return None
    return float(view_result["mean_mse_improvement_vs_train_mean"])


def run_single(
    *,
    assignment_mode: str,
    seed: int,
    groups: int,
    replicates_per_group: int,
    theta_points: int,
    event_analysis: Any,
) -> dict[str, Any]:
    dataset = generate_synthetic_track_b(
        n_groups=groups,
        replicates_per_group=replicates_per_group,
        n_theta=theta_points,
        seed=seed,
        provenance_assignment=assignment_mode,
    )
    analysis = event_analysis.analyze_table(
        events=dataset.events,
        table=dataset.event_table,
        spectra=dataset.spectra,
        theta=dataset.theta,
        seed=seed,
        include_only_raw_objective=True,
        bundle_name=f"in_memory:{assignment_mode}:{seed}",
    )
    return {
        "assignment_mode": assignment_mode,
        "seed": seed,
        "event_count": len(dataset.event_table),
        "planned_condition_count": groups,
        "replicates_per_group": replicates_per_group,
        "provenance_balance": provenance_balance_audit(dataset.event_table),
        "metrics": {
            "heldout_plan_full_event": get_improvement(
                analysis, split="heldout_plan", view="full_event"
            ),
            "heldout_plan_label_only": get_improvement(
                analysis, split="heldout_plan", view="label_only"
            ),
            "heldout_operator_full_event": get_improvement(
                analysis, split="heldout_operator", view="full_event"
            ),
            "heldout_operator_observed": get_improvement(
                analysis, split="heldout_operator", view="observed_trajectory"
            ),
            "heldout_reagent_lot_full_event": get_improvement(
                analysis, split="heldout_reagent_lot", view="full_event"
            ),
            "heldout_provenance_combo_full_event": get_improvement(
                analysis, split="heldout_provenance_combo", view="full_event"
            ),
            "residual_heldout_plan_full_event": get_improvement(
                analysis, split="heldout_plan", view="full_event", residualized=True
            ),
            "residual_heldout_operator_full_event": get_improvement(
                analysis, split="heldout_operator", view="full_event", residualized=True
            ),
            "residual_heldout_provenance_combo_full_event": get_improvement(
                analysis,
                split="heldout_provenance_combo",
                view="full_event",
                residualized=True,
            ),
            "shuffle_full_event": get_shuffle_improvement(analysis, "full_event"),
        },
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat_rows = []
    for row in rows:
        flat = {
            "assignment_mode": row["assignment_mode"],
            "seed": row["seed"],
            "event_count": row["event_count"],
            "planned_condition_count": row["planned_condition_count"],
            "replicates_per_group": row["replicates_per_group"],
        }
        flat.update(row["metrics"])
        for column in ["batch_id", "operator_id", "reagent_lot"]:
            flat[f"{column}_max_regime_share"] = row["provenance_balance"][column][
                "max_hidden_regime_share_within_group"
            ]
        flat_rows.append(flat)

    df = pd.DataFrame(flat_rows)
    metric_columns = [column for column in df.columns if column not in {"assignment_mode", "seed"}]
    summary_rows = []
    for mode, mode_df in df.groupby("assignment_mode", sort=False):
        summary: dict[str, Any] = {"assignment_mode": mode, "seeds": len(mode_df)}
        for column in metric_columns:
            if column in {"event_count", "planned_condition_count", "replicates_per_group"}:
                summary[column] = int(mode_df[column].iloc[0])
            else:
                values = mode_df[column].astype(float)
                summary[f"{column}_mean"] = float(values.mean())
                summary[f"{column}_std"] = float(values.std(ddof=0))
        summary["operator_collapse_rate"] = float(
            (mode_df["heldout_operator_full_event"].astype(float) < 0.0).mean()
        )
        summary["provenance_combo_positive_rate"] = float(
            (mode_df["heldout_provenance_combo_full_event"].astype(float) > 0.0).mean()
        )
        summary["residual_combo_positive_rate"] = float(
            (mode_df["residual_heldout_provenance_combo_full_event"].astype(float) > 0.0).mean()
        )
        summary_rows.append(summary)
    return summary_rows


def run(args: argparse.Namespace) -> dict[str, Any]:
    event_analysis = load_event_analysis_module()
    seeds = DEFAULT_SEEDS[: args.seed_count]
    rows = []
    for assignment_mode in ASSIGNMENT_MODES:
        for seed in seeds:
            rows.append(
                run_single(
                    assignment_mode=assignment_mode,
                    seed=seed,
                    groups=args.groups,
                    replicates_per_group=args.replicates_per_group,
                    theta_points=args.theta_points,
                    event_analysis=event_analysis,
                )
            )

    summary = summarize(rows)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "track_b_counterbalanced_pilot_stress",
        "groups": args.groups,
        "replicates_per_group": args.replicates_per_group,
        "event_count": args.groups * args.replicates_per_group,
        "theta_points": args.theta_points,
        "seeds": seeds,
        "assignment_modes": ASSIGNMENT_MODES,
        "hypotheses": [
            "A deliberately confounded operator assignment should fail or become unstable on held-out-operator splits.",
            "Counterbalanced replicate-level assignment should reduce held-out-operator collapse while preserving held-out-plan event signal.",
            "Replicate-level counterbalancing should keep provenance-combo and provenance-residualized performance positive more often than plan-level or confounded assignment.",
        ],
        "rows": rows,
        "summary": summary,
        "caveats": [
            "This is synthetic pilot-design evidence, not chemistry evidence.",
            "Counterbalancing reduces shortcut risk but cannot prove shortcuts are impossible.",
            "Real labs may not have multiple operators or lots; if not, those variables must be logged as limitations rather than ignored.",
        ],
    }

    output_path = project_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", type=int, default=16)
    parser.add_argument("--replicates-per-group", type=int, default=3)
    parser.add_argument("--theta-points", type=int, default=512)
    parser.add_argument("--seed-count", type=int, default=len(DEFAULT_SEEDS))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/track_b_counterbalanced_pilot_stress.json"),
    )
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    printable = {
        "task": result["task"],
        "hypotheses": result["hypotheses"],
        "summary": result["summary"],
        "caveats": result["caveats"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
