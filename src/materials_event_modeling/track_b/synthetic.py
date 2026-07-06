"""Synthetic Track B event generator.

The synthetic data is not a chemistry model. It is a harness for testing whether the
Track B analysis code can work with event histories, raw measurements, replicates, missing
fields, and lossy downstream labels before a real lab dataset exists.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

REGIMES = [
    "low_signal_sparse",
    "rapid_mixture",
    "slow_aging_conversion",
    "additive_shifted_pathway",
    "reference_like_crystalline",
    "replicate_sensitive_pathway",
]

REGIME_TO_LABELS = {
    "low_signal_sparse": ["ambiguous_low_signal", "failed_or_low_signal"],
    "rapid_mixture": ["mixed_or_impure", "possible_mixture"],
    "slow_aging_conversion": ["mixed_or_impure", "delayed_conversion_possible"],
    "additive_shifted_pathway": ["possible_mixture", "delayed_conversion_possible"],
    "reference_like_crystalline": ["reference_like"],
    "replicate_sensitive_pathway": ["reference_like", "replicate_variation"],
}

REGIME_PROCESS_CENTERS = {
    "low_signal_sparse": {
        "temperature": 20.0,
        "aging": 30.0,
        "mixing": 0.25,
        "additive": 0.0,
    },
    "rapid_mixture": {
        "temperature": 25.0,
        "aging": 60.0,
        "mixing": 0.9,
        "additive": 0.0,
    },
    "slow_aging_conversion": {
        "temperature": 35.0,
        "aging": 200.0,
        "mixing": 0.5,
        "additive": 0.0,
    },
    "additive_shifted_pathway": {
        "temperature": 25.0,
        "aging": 140.0,
        "mixing": 0.55,
        "additive": 1.0,
    },
    "reference_like_crystalline": {
        "temperature": 35.0,
        "aging": 240.0,
        "mixing": 0.6,
        "additive": 0.0,
    },
    "replicate_sensitive_pathway": {
        "temperature": 25.0,
        "aging": 120.0,
        "mixing": 0.85,
        "additive": 0.5,
    },
}


@dataclass(frozen=True)
class SyntheticTrackBDataset:
    events: list[dict[str, object]]
    event_table: pd.DataFrame
    spectra: np.ndarray
    theta: np.ndarray


def provenance_for_group(
    *,
    group_idx: int,
    replicate_idx: int,
    n_groups: int,
    assignment_mode: str,
    rng: np.random.Generator,
) -> tuple[str, str, str]:
    """Assign synthetic provenance fields for a planned condition/replicate."""

    operators = ["operator_a", "operator_b"]
    reagent_lots = ["lot_A", "lot_B", "lot_C"]

    if assignment_mode == "random_group":
        batch_id = f"synthetic_batch_{1 + group_idx // 8:02d}"
        operator_id = str(rng.choice(operators))
        reagent_lot = str(rng.choice(reagent_lots))
    elif assignment_mode == "confounded_operator":
        regime_idx = group_idx % len(REGIMES)
        batch_id = f"synthetic_batch_{1 + int(regime_idx >= len(REGIMES) // 2):02d}"
        operator_id = operators[int(regime_idx >= len(REGIMES) // 2)]
        reagent_lot = reagent_lots[regime_idx % len(reagent_lots)]
    elif assignment_mode == "balanced_replicate":
        batch_id = f"synthetic_batch_{1 + (group_idx + replicate_idx) % 4:02d}"
        operator_id = operators[(group_idx + replicate_idx) % len(operators)]
        reagent_lot = reagent_lots[(group_idx + 2 * replicate_idx) % len(reagent_lots)]
    elif assignment_mode == "balanced_plan":
        batch_id = f"synthetic_batch_{1 + group_idx % 4:02d}"
        operator_id = operators[group_idx % len(operators)]
        reagent_lot = reagent_lots[group_idx % len(reagent_lots)]
    else:
        raise ValueError(f"unknown provenance assignment mode: {assignment_mode}")

    return batch_id, operator_id, reagent_lot


def gaussian_grid(theta: np.ndarray, center: float, width: float) -> np.ndarray:
    return np.exp(-0.5 * ((theta - center) / width) ** 2)


def regime_basis(theta: np.ndarray) -> dict[str, np.ndarray]:
    bases = {
        "low_signal_sparse": (
            0.4 * gaussian_grid(theta, 24.0, 0.25)
            + 0.2 * gaussian_grid(theta, 43.0, 0.5)
        ),
        "rapid_mixture": (
            1.0 * gaussian_grid(theta, 29.4, 0.18)
            + 0.8 * gaussian_grid(theta, 36.0, 0.22)
            + 0.7 * gaussian_grid(theta, 39.5, 0.2)
            + 0.45 * gaussian_grid(theta, 47.5, 0.3)
        ),
        "slow_aging_conversion": (
            0.7 * gaussian_grid(theta, 26.2, 0.25)
            + 0.9 * gaussian_grid(theta, 29.4, 0.2)
            + 0.5 * gaussian_grid(theta, 33.1, 0.28)
            + 0.5 * gaussian_grid(theta, 48.6, 0.32)
        ),
        "additive_shifted_pathway": (
            0.6 * gaussian_grid(theta, 27.1, 0.25)
            + 0.85 * gaussian_grid(theta, 32.8, 0.2)
            + 0.55 * gaussian_grid(theta, 45.9, 0.24)
            + 0.35 * gaussian_grid(theta, 50.0, 0.4)
        ),
        "reference_like_crystalline": (
            1.2 * gaussian_grid(theta, 29.4, 0.16)
            + 0.65 * gaussian_grid(theta, 39.4, 0.18)
            + 0.55 * gaussian_grid(theta, 43.1, 0.18)
            + 0.45 * gaussian_grid(theta, 47.5, 0.2)
        ),
        "replicate_sensitive_pathway": (
            0.95 * gaussian_grid(theta, 29.2, 0.18)
            + 0.45 * gaussian_grid(theta, 35.8, 0.22)
            + 0.7 * gaussian_grid(theta, 42.9, 0.18)
            + 0.4 * gaussian_grid(theta, 49.2, 0.28)
        ),
    }
    return {name: basis / max(float(basis.max()), 1e-8) for name, basis in bases.items()}


def choose_label(regime: str, aging_time: float, additive_level: float, rng: np.random.Generator) -> str:
    labels = REGIME_TO_LABELS[regime]
    if len(labels) == 1:
        return labels[0]
    if regime == "slow_aging_conversion" and aging_time > 160:
        weights = [0.25, 0.75]
    elif regime == "additive_shifted_pathway" and additive_level > 0:
        weights = [0.35, 0.65]
    elif regime == "replicate_sensitive_pathway":
        weights = [0.65, 0.35]
    else:
        weights = [0.55, 0.45]
    return str(rng.choice(labels, p=weights))


def generate_synthetic_track_b(
    *,
    n_groups: int = 32,
    replicates_per_group: int = 3,
    n_theta: int = 512,
    seed: int = 17,
    provenance_assignment: str = "random_group",
) -> SyntheticTrackBDataset:
    rng = np.random.default_rng(seed)
    theta = np.linspace(15.0, 60.0, n_theta, dtype=np.float32)
    bases = regime_basis(theta)

    events: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    spectra = []

    for group_idx in range(n_groups):
        regime = REGIMES[group_idx % len(REGIMES)]
        center = REGIME_PROCESS_CENTERS[regime]
        plan_id = f"synthetic_plan_{group_idx:03d}"
        base_temperature = center["temperature"] + float(rng.normal(0.0, 1.2))
        base_aging = center["aging"] + float(rng.normal(0.0, 12.0))
        base_mixing = center["mixing"] + float(rng.normal(0.0, 0.04))
        base_additive = center["additive"] + float(rng.normal(0.0, 0.04))

        for replicate_idx in range(replicates_per_group):
            batch_id, operator_id, reagent_lot = provenance_for_group(
                group_idx=group_idx,
                replicate_idx=replicate_idx,
                n_groups=n_groups,
                assignment_mode=provenance_assignment,
                rng=rng,
            )
            event_idx = group_idx * replicates_per_group + replicate_idx
            event_id = f"synthetic_cc_{event_idx:04d}"
            temperature = base_temperature + float(rng.normal(0.0, 1.0))
            aging = max(5.0, base_aging + float(rng.normal(0.0, 8.0)))
            mixing = float(np.clip(base_mixing + rng.normal(0.0, 0.06), 0.05, 1.0))
            additive = float(max(0.0, base_additive + rng.normal(0.0, 0.05)))
            initial_ph = 9.0 + 0.4 * additive + float(rng.normal(0.0, 0.25))
            final_ph = initial_ph - 0.25 - 0.001 * aging + float(rng.normal(0.0, 0.15))
            early_turbidity = float(
                np.clip(
                    0.2
                    + 0.5 * mixing
                    + 0.002 * aging
                    + 0.15 * (regime in {"rapid_mixture", "reference_like_crystalline"})
                    + rng.normal(0.0, 0.08),
                    0.0,
                    1.0,
                )
            )

            peak_shift = 0.015 * (temperature - 25.0) + 0.03 * additive
            shifted_theta = theta - peak_shift
            spectrum = np.interp(theta, shifted_theta, bases[regime], left=0.0, right=0.0)
            amplitude = 0.45 + 0.5 * early_turbidity + 0.0015 * aging + 0.08 * mixing
            background = 0.04 + 0.08 * np.sin(theta / 8.0 + group_idx) ** 2
            noise = rng.normal(0.0, 0.025, size=theta.shape)
            measured = np.clip(amplitude * spectrum + background + noise, 0.0, None)
            measured = measured / max(float(measured.max()), 1e-8)
            spectra.append(measured.astype(np.float32))

            label = choose_label(regime, aging, additive, rng)
            missing_fields = []
            if rng.random() < 0.2:
                missing_fields.append("final_ph")
                final_ph_value: float | None = None
            else:
                final_ph_value = round(final_ph, 3)
            if rng.random() < 0.1:
                missing_fields.append("early_turbidity")
                early_turbidity_value: float | None = None
            else:
                early_turbidity_value = round(early_turbidity, 3)

            row: dict[str, object] = {
                "event_id": event_id,
                "system": "calcium_carbonate_synthetic",
                "batch_id": batch_id,
                "replicate_group": plan_id,
                "operator_id": operator_id,
                "reagent_lot": reagent_lot,
                "hidden_regime": regime,
                "legacy_label": label,
                "planned_temperature_c": round(base_temperature, 3),
                "planned_aging_time_minutes": round(max(5.0, base_aging), 3),
                "planned_mixing_intensity": round(float(np.clip(base_mixing, 0.05, 1.0)), 3),
                "planned_additive_level": round(max(0.0, base_additive), 3),
                "observed_temperature_c": round(temperature, 3),
                "observed_aging_time_minutes": round(aging, 3),
                "observed_mixing_intensity": round(mixing, 3),
                "observed_additive_level": round(additive, 3),
                "initial_ph": round(initial_ph, 3),
                "final_ph": final_ph_value,
                "early_turbidity": early_turbidity_value,
                "include_in_raw_objective": True,
                "missing_fields": ";".join(missing_fields),
            }
            rows.append(row)
            events.append(
                {
                    "event_id": event_id,
                    "system": row["system"],
                    "created_at": f"2026-06-{1 + event_idx // 24:02d}T09:00:00Z",
                    "operator_id": operator_id,
                    "lab_id": "synthetic_lab",
                    "batch_id": batch_id,
                    "pre_registered_plan_id": plan_id,
                    "process": {
                        "precursors": [
                            {
                                "name": "calcium_source_solution",
                                "lot_id": reagent_lot,
                                "prepared_solution_id": f"synthetic_ca_{reagent_lot}",
                                "nominal_concentration": None,
                                "concentration_unit": None,
                            },
                            {
                                "name": "carbonate_source_solution",
                                "lot_id": reagent_lot,
                                "prepared_solution_id": f"synthetic_co3_{reagent_lot}",
                                "nominal_concentration": None,
                                "concentration_unit": None,
                            },
                        ],
                        "planned_conditions": {
                            "target_temperature_c": row["planned_temperature_c"],
                            "target_aging_time_minutes": row["planned_aging_time_minutes"],
                            "target_mixing_intensity": row["planned_mixing_intensity"],
                            "target_additive_level": row["planned_additive_level"],
                            "drying_route": "synthetic_standardized_route",
                        },
                        "observed_trajectory": {
                            "temperature_c": row["observed_temperature_c"],
                            "initial_ph": row["initial_ph"],
                            "final_ph": final_ph_value,
                            "mixing_description": (
                                f"synthetic_intensity_{row['observed_mixing_intensity']}"
                            ),
                            "mixing_intensity": row["observed_mixing_intensity"],
                            "aging_time_minutes": row["observed_aging_time_minutes"],
                            "additive_level": row["observed_additive_level"],
                            "early_turbidity": early_turbidity_value,
                        },
                        "timeline": [
                            {
                                "timestamp": f"2026-06-{1 + event_idx // 24:02d}T09:00:00Z",
                                "event_type": "event_started",
                                "notes": "Synthetic event for Track B analysis scaffolding.",
                            },
                            {
                                "timestamp": f"2026-06-{1 + event_idx // 24:02d}T11:00:00Z",
                                "event_type": "measurement_ready",
                                "notes": f"Synthetic hidden regime: {regime}.",
                            },
                        ],
                    },
                    "measurements": {
                        "xrd": [
                            {
                                "file_path": f"synthetic/track_b/{event_id}/xrd.npy",
                                "instrument_id": "synthetic_xrd",
                                "measurement_time": f"2026-06-{1 + event_idx // 24:02d}T12:00:00Z",
                                "raw_export_format": "synthetic_array",
                            }
                        ],
                        "spectroscopy": [],
                        "microscopy": [],
                        "photos": [],
                    },
                    "labels": {
                        "assigned_after_raw_data_frozen": True,
                        "human_labels": [
                            {
                                "labeler_id": "synthetic_labeler",
                                "label": label,
                                "confidence": None,
                                "notes": "Synthetic lossy projection label.",
                            }
                        ],
                    },
                    "data_quality": {
                        "include_in_raw_objective": True,
                        "deviations": [],
                        "missing_fields": missing_fields,
                    },
                }
            )

    return SyntheticTrackBDataset(
        events=events,
        event_table=pd.DataFrame(rows),
        spectra=np.vstack(spectra).astype(np.float32),
        theta=theta,
    )
