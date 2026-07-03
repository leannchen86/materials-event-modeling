"""Adapt the NIST MDS2-2301 combinatorial diffraction dataset to event-grammar v1 envelopes.

Source: data/raw/nist_mds2_2301 (Nb-doped VO2 composition-spread library; 352 XRD spectra =
44 compositions x 8 measurement temperatures), loaded via materials_event_modeling.data.nist.

Event mapping choice
--------------------
One event per composition sample (44 events), with its 8-temperature XRD series as the
trajectory. Rationale: the material-making event is the deposition of one composition point
on the spread wafer; the variable-temperature XRD scan of that point is a genuine ordered
trace (the phase transition unfolds across it), whereas one-event-per-spectrum would collapse
this dataset into 352 single-observation rows (a measurement archive, the RRUFF degenerate
shape). One-event-per-wafer was rejected because every label, composition, and spectrum in
the source is keyed to the (composition, temperature) grid point, not to the wafer.

Slot mapping
------------
- intent: null. The source records no synthesis plan: no deposition recipe, no target
  compositions distinct from measured ones, no pre-registered design. The composition/temp
  grid in "VO2 - Nb2O3 Composition and temp Combiview.txt" describes measurements made, so it
  is kept as measured context (event.sample / observation payload), not as intent.
- observations: one per (composition, temperature) XRD spectrum, modality "xrd",
  kind "measurement". The 3841-point spectrum stays on disk: file_path points at the raw
  Combiview matrix and payload["xrd"] records the 1-based data-row index into it, plus small
  scalars (temp_c, composition, two-theta range). order_index = global measurement order
  (the Readme states rows are "in the order of measurement": composition scan repeated at
  each ascending temperature).
- outcome: status "unknown" for every event. The source publishes no success/failure/abort
  record; all 352 grid points have spectra, and any filtering that happened upstream is
  invisible.
- provenance: all axes null. No operator, lab, batch/lot, instrument id, session, or date
  appears in the data files (Readme names institutions and a contact but ties nothing to
  individual measurements). Only source_dataset is set, from the DOI-backed dataset id.
- labels: the showcase. For each of the 24 human-labeled compositions, one entries item per
  human labeler (HL1..HL5) per labeled temperature row -- disagreement is preserved verbatim
  -- plus "human_consensus" (majority vote, ties -> lower code, computed by the repo loader,
  marked derivation="adapter_majority_vote"). For the 19 machine-labeled compositions, one
  entry per ML method column in "Compare ML Labels.csv" and a "machine_consensus" entry
  (same vote rule). Numeric codes 0/1/2 map to the Readme's phase meanings; the raw code is
  kept on each entry. assigned_after_raw_data_frozen: null -- the labeling workflow's timing
  relative to raw-data freezing is not verifiable from the source.

Not derivable (mapping gaps)
----------------------------
Synthesis intent/recipe; any provenance axis (operator, lab, batch, lot, instrument,
session, measurement day, per-event run order); outcome status; timestamps; wafer spatial
coordinates (composition is recorded, physical x/y position is not); label freezing.
Per-method log-likelihoods (cluster_assignment_loglik_all.csv) are left out: they score ML
labels against the human consensus rather than stating a labeler's own confidence.

No sampling: all 352 spectra / 44 compositions are emitted. Deterministic; reads only data/.

Usage:
    .venv/bin/python scripts/adapters/adapt_nist.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from materials_event_modeling.data import nist

DATASET = "nist"
SYSTEM = "nb_doped_vo2_composition_spread"
XRD_RELPATH = f"data/raw/{nist.DATASET_ID}/{nist.XRD_FILENAME}"

HUMAN_LABELER_COLUMNS = ("HL1", "HL2", "HL3", "HL4", "HL5")
MACHINE_LABELER_COLUMNS = (
    "Comp-Distance-Spectral",
    "Cosine-Local-Scaling-Spectral",
    "Cosine-Spectral",
    "VAE-Spectral",
)


def label_text(code: int) -> str:
    return nist.LABEL_MEANINGS[int(code)]


def build_observation(row, theta) -> dict:
    sample_index = int(row.sample_index)
    return {
        "observation_id": f"{nist.DATASET_ID}:v{int(row.v_percent):02d}:t{int(row.temp_c)}c",
        "modality": "xrd",
        "kind": "measurement",
        "stage": None,
        "timestamp": None,
        "order_index": sample_index,
        "spatial_position": None,
        "file_path": XRD_RELPATH,
        "raw_export_format": "combiview_txt_matrix",
        "instrument_id": None,
        "instrument_session_id": None,
        "payload": {
            "xrd": {
                # 1-based data row in the Combiview matrix (row 1 of the file is two-theta).
                "combiview_data_row": sample_index + 1,
                "n_points": int(theta.shape[0]),
                "two_theta_min": float(theta.min()),
                "two_theta_max": float(theta.max()),
            },
            "condition": {
                "temp_c": int(row.temp_c),
                "v_percent": int(row.v_percent),
                "nb_percent": int(row.nb_percent),
            },
        },
        "notes": None,
    }


def label_entries(rows) -> list[dict]:
    """One entry per labeler per labeled (composition, temperature) row."""
    entries: list[dict] = []
    for row in rows.itertuples():
        obs_id = f"{nist.DATASET_ID}:v{int(row.v_percent):02d}:t{int(row.temp_c)}c"
        common = {
            "sample_index": int(row.sample_index),
            "temp_c": int(row.temp_c),
            "observation_id": obs_id,
            "confidence": None,
            "stage": None,
        }
        if row.human_consensus_label == row.human_consensus_label:  # not NaN
            for column in HUMAN_LABELER_COLUMNS:
                code = int(getattr(row, column))
                entries.append({
                    "labeler_id": column, "label": label_text(code), "label_code": code,
                    "labeler_kind": "human", **common,
                })
            code = int(row.human_consensus_label)
            entries.append({
                "labeler_id": "human_consensus", "label": label_text(code), "label_code": code,
                "labeler_kind": "consensus", "derivation": "adapter_majority_vote", **common,
            })
        if row.machine_consensus_label == row.machine_consensus_label:  # not NaN
            for column in MACHINE_LABELER_COLUMNS:
                code = int(getattr(row, column.replace("-", "_")))
                entries.append({
                    "labeler_id": column, "label": label_text(code), "label_code": code,
                    "labeler_kind": "machine", **common,
                })
            code = int(row.machine_consensus_label)
            entries.append({
                "labeler_id": "machine_consensus", "label": label_text(code), "label_code": code,
                "labeler_kind": "consensus", "derivation": "adapter_majority_vote", **common,
            })
    return entries


def build_events(dataset: nist.NistDataset) -> list[dict]:
    samples = dataset.samples
    # Machine-label columns arrive with hyphens; itertuples mangles them, so pre-rename.
    renames = {c: c.replace("-", "_") for c in MACHINE_LABELER_COLUMNS if c in samples.columns}
    samples = samples.rename(columns=renames)

    events: list[dict] = []
    for v_percent, rows in samples.groupby("v_percent", sort=True):
        rows = rows.sort_values("sample_index")
        entries = label_entries(rows)
        events.append({
            "event_id": f"{nist.DATASET_ID}:v{int(v_percent):02d}",
            "system": SYSTEM,
            "created_at": None,
            "sample": {
                "v_percent": int(v_percent),
                "nb_percent": int(100 - v_percent),
                "library": "vo2_nb2o3_composition_spread_wafer",
            },
            "intent": None,
            "observations": [build_observation(row, dataset.theta) for row in rows.itertuples()],
            "outcome": {"status": "unknown", "summary": None, "notes": None},
            "provenance": {
                "operator_id": None,
                "lab_id": None,
                "batch_id": None,
                "lot_id": None,
                "instrument_id": None,
                "instrument_session_id": None,
                "measurement_day": None,
                "run_order": None,
                "source_dataset": nist.DATASET_ID,
                "raw_export_profile": "nist_mds2_2301_combiview_txt",
            },
            "labels": (
                {"assigned_after_raw_data_frozen": None, "entries": entries} if entries else None
            ),
        })
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=Path(f"data/interim/event_grammar_v1/{DATASET}/events.json"),
        help="Output events JSON path, relative to the repo root unless absolute.",
    )
    args = parser.parse_args()

    root = nist.project_root()
    dataset = nist.load_dataset(root)
    events = build_events(dataset)

    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(events, indent=2) + "\n")

    n_obs = sum(len(e["observations"]) for e in events)
    n_labeled = sum(1 for e in events if e["labels"])
    n_entries = sum(len(e["labels"]["entries"]) for e in events if e["labels"])
    print(f"wrote {len(events)} events ({n_obs} observations, "
          f"{n_labeled} events with labels, {n_entries} label entries) -> {output}")


if __name__ == "__main__":
    main()
