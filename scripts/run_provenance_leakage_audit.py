"""Audit a dataset for provenance recoverability.

Unifies the opXRD source-predictability and normalization-control diagnostics behind one
reusable, dataset-agnostic tool. For each feature representation it measures how
recoverable the provenance label (collection source) is, reports a normalized
recoverability score and heuristic risk band, and — with --include-controls — checks
whether a preprocessing control reduces that recoverability.

The audit core lives in ``materials_event_modeling.audit.provenance_leakage`` and is
modality-agnostic; this script only provides dataset *adapters* that turn a corpus into
``{feature_set_name: matrix}`` + provenance labels. Adding a dataset = one adapter
function registered in ``DATASETS``. The ``text`` adapter (multi-source document corpus)
demonstrates the protocol is not XRD-specific.

    .venv/bin/python scripts/run_provenance_leakage_audit.py --dataset opxrd --include-controls

The opXRD adapter is self-contained (numpy + sklearn + pandas only) so the tool stays
portable and free of the project's torch training stack.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from materials_event_modeling.audit.provenance_leakage import (
    audit_feature_sets,
    control_efficacy,
)
from materials_event_modeling.run_identity import run_identity


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------------------
# opXRD adapter — feature builders mirror analyze_opxrd_source_predictability.py and
# analyze_opxrd_normalization_controls.py, kept self-contained so the audit tool has no
# torch dependency.
# --------------------------------------------------------------------------------------


def _local_peak_density(spectra: np.ndarray, threshold: float) -> np.ndarray:
    values = []
    for spectrum in spectra:
        peaks = (
            (spectrum[1:-1] > spectrum[:-2])
            & (spectrum[1:-1] >= spectrum[2:])
            & (spectrum[1:-1] >= threshold)
        )
        values.append(float(np.mean(peaks)))
    return np.asarray(values, dtype=np.float32)


def _spectrum_summary_features(xrd: np.ndarray, peak_threshold: float) -> np.ndarray:
    quantiles = np.quantile(xrd, [0.1, 0.25, 0.5, 0.75, 0.9], axis=1).T
    features = [
        xrd.mean(axis=1),
        xrd.std(axis=1),
        xrd.max(axis=1),
        np.mean(xrd > 0.01, axis=1),
        np.mean(xrd > 0.05, axis=1),
        np.mean(xrd > 0.25, axis=1),
        _local_peak_density(xrd, threshold=peak_threshold),
    ]
    return np.column_stack([*features, quantiles]).astype(np.float32)


def _metadata_frame(samples: pd.DataFrame) -> pd.DataFrame:
    """Measurement-metadata features.

    ``is_labeled`` is deliberately excluded: it is a dataset-curation flag that is
    near-deterministic per opXRD source (labeled fraction 1.0/1.0/1.0/0.04/0.0/0.0),
    so including it partly turns "recover the lab" into a bookkeeping identity. It is
    audited separately as ``metadata_plus_curation`` and in ``--feature-ablation``.
    """
    frame = samples[
        ["points", "theta_min", "theta_max", "intensity_min", "intensity_max", "phase_count"]
    ].copy()
    frame["theta_span"] = frame["theta_max"] - frame["theta_min"]
    return frame.fillna(0)


def _coverage_mask(theta: np.ndarray, samples: pd.DataFrame) -> np.ndarray:
    theta_min = samples["theta_min"].to_numpy(dtype=np.float32)[:, None]
    theta_max = samples["theta_max"].to_numpy(dtype=np.float32)[:, None]
    return ((theta[None, :] >= theta_min) & (theta[None, :] <= theta_max)).astype(np.float32)


def _row_zscore(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    center = x.mean(axis=1, keepdims=True)
    scale = x.std(axis=1, keepdims=True)
    return ((x - center) / np.maximum(scale, eps)).astype(np.float32)


def _row_l1(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    denom = np.sum(np.abs(x), axis=1, keepdims=True)
    return (x / np.maximum(denom, eps)).astype(np.float32)


def _derivative(x: np.ndarray) -> np.ndarray:
    return np.diff(x, axis=1).astype(np.float32)


def load_opxrd(args: argparse.Namespace) -> dict[str, Any]:
    """Return feature sets + provenance labels for the opXRD processed subset."""
    root = project_root()
    manifest_path = root / "data/manifests/opxrd_processed_subset.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            "Processed opXRD subset is missing. Run "
            "`.venv/bin/python scripts/preprocess_opxrd.py --max-spectra 4096 --points 4096`."
        )
    manifest = json.loads(manifest_path.read_text())
    with np.load(root / manifest["arrays_path"]) as data:
        xrd = data["xrd"].astype(np.float32)
        theta = data["theta"].astype(np.float32)
    samples = pd.read_csv(root / manifest["samples_path"])
    samples["top_level_source"] = samples["member_name"].str.split("/", n=1).str[0]

    counts = samples["top_level_source"].value_counts()
    kept = sorted(counts[counts >= args.min_source_samples].index.tolist())
    keep_mask = samples["top_level_source"].isin(kept).to_numpy()
    xrd = xrd[keep_mask]
    samples = samples.loc[keep_mask].reset_index(drop=True)
    labels = samples["top_level_source"].to_numpy()

    metadata = _metadata_frame(samples)
    is_labeled = samples["is_labeled"].astype(bool).astype(float).to_numpy(dtype=np.float32)

    feature_sets: dict[str, np.ndarray] = {
        "metadata": metadata.to_numpy(dtype=np.float32),
        # The original headline set (metadata + the is_labeled curation flag), kept so
        # the curation-flag contribution is measured rather than silently dropped.
        "metadata_plus_curation": np.column_stack(
            [metadata.to_numpy(dtype=np.float32), is_labeled]
        ),
        "spectrum_summary": _spectrum_summary_features(xrd, args.peak_threshold),
        "xrd_pca": xrd,
    }
    # Sets named here are raw matrices; PCA is fit INSIDE each CV fold (train split
    # only) by the audit core. Pre-reducing on the full matrix would let test rows
    # shape the basis — the exact leakage this tool exists to catch.
    pca_spec: dict[str, int] = {"xrd_pca": args.pca_components}

    if args.feature_ablation:
        for column in metadata.columns:
            feature_sets[f"metadata_only_{column}"] = metadata[[column]].to_numpy(
                dtype=np.float32
            )
        feature_sets["metadata_only_is_labeled"] = is_labeled[:, None]

    control_pairs: list[tuple[str, str]] = []
    if args.include_controls:
        coverage = _coverage_mask(theta, samples)
        coverage_fraction = coverage.mean(axis=0)
        crop_mask = coverage_fraction >= args.min_coverage_fraction
        if int(crop_mask.sum()) < args.min_crop_points:
            raise RuntimeError(
                f"Only {int(crop_mask.sum())} theta points meet coverage "
                f"{args.min_coverage_fraction}; lower --min-coverage-fraction."
            )
        cropped = xrd[:, crop_mask]
        for name, matrix in {
            "coverage_mask_pca": coverage,
            "full_xrd_pca": xrd,
            "full_xrd_row_zscore_pca": _row_zscore(xrd),
            "full_xrd_l1_pca": _row_l1(xrd),
            "crop_xrd_pca": cropped,
            "crop_xrd_row_zscore_pca": _row_zscore(cropped),
            "crop_xrd_l1_pca": _row_l1(cropped),
            "crop_xrd_derivative_pca": _derivative(_row_zscore(cropped)),
        }.items():
            feature_sets[name] = matrix
            pca_spec[name] = args.pca_components
        # Does the strongest control reduce source recoverability in the raw representation?
        control_pairs.append(("full_xrd_pca", "crop_xrd_derivative_pca"))

    return {
        "feature_sets": feature_sets,
        "labels": labels,
        "control_pairs": control_pairs,
        "pca_spec": pca_spec,
        "meta": {
            "dataset_id": "opxrd",
            "spectra": int(xrd.shape[0]),
            "theta_points": int(xrd.shape[1]),
            "min_source_samples": args.min_source_samples,
        },
    }


# --------------------------------------------------------------------------------------
# Text adapter — the document-corpus analog, retained as evidence that the protocol is
# modality-agnostic. The provenance label is the document SOURCE (web / wikipedia /
# code / science). Feature sets escalate from trivial surface statistics to topical
# content, so the report shows at which level source identity is recoverable. This is
# the text version of opXRD's "metadata recovers the lab": if even function-word style
# or surface stats recover the source, the corpus carries a pervasive source fingerprint
# that a balanced mix, a quality filter, or a naive train/eval split will silently
# encode.
#
# Known limitation (archived as-is with the 2026-06 text result): tfidf/SVD here are
# fit on the full corpus before CV (transductive), unlike the opXRD path where PCA is
# fit in-fold. Re-fit in-fold before quoting new text numbers.
# --------------------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z]+")
_STOP_WORDS = sorted(ENGLISH_STOP_WORDS)


def _surface_metadata(texts: list[str]) -> np.ndarray:
    rows = []
    for text in texts:
        n_chars = len(text)
        words = text.split()
        n_words = len(words)
        word_lens = np.array([len(w) for w in words], dtype=np.float32) if words else np.zeros(1)
        denom_c = max(n_chars, 1)
        rows.append([
            np.log1p(n_chars),
            np.log1p(n_words),
            float(word_lens.mean()),
            float(word_lens.std()),
            len(set(words)) / max(n_words, 1),                     # type-token ratio
            sum(c in ".,;:!?'\"-()[]{}" for c in text) / denom_c,  # punctuation rate
            sum(c.isdigit() for c in text) / denom_c,              # digit rate
            sum(c.isupper() for c in text) / denom_c,              # uppercase rate
            sum(c.isspace() for c in text) / denom_c,              # whitespace rate
            sum(ord(c) > 127 for c in text) / denom_c,             # non-ascii rate
            sum(c in "{}[]()=;_" for c in text) / denom_c,         # code-ish symbol rate
            n_words / max(text.count(".") + text.count("!") + text.count("?"), 1),  # sent len
        ])
    return np.asarray(rows, dtype=np.float32)


def _function_word_rates(texts: list[str]) -> np.ndarray:
    """Per-doc rate of each English stop word: a topic-agnostic style/register fingerprint."""
    index = {w: i for i, w in enumerate(_STOP_WORDS)}
    out = np.zeros((len(texts), len(_STOP_WORDS)), dtype=np.float32)
    for r, text in enumerate(texts):
        tokens = _WORD_RE.findall(text.lower())
        if not tokens:
            continue
        inv = 1.0 / len(tokens)
        for tok in tokens:
            j = index.get(tok)
            if j is not None:
                out[r, j] += inv
    return out


def _tfidf_svd(
    texts: list[str], *, analyzer: str, ngram_range: tuple[int, int],
    max_features: int, components: int, seed: int, stop_words=None, sublinear: bool = False,
) -> np.ndarray:
    vec = TfidfVectorizer(
        analyzer=analyzer, ngram_range=ngram_range, max_features=max_features,
        min_df=2, stop_words=stop_words, sublinear_tf=sublinear,
    )
    matrix = vec.fit_transform(texts)
    k = min(components, matrix.shape[1] - 1, matrix.shape[0] - 1)
    return TruncatedSVD(n_components=k, random_state=seed).fit_transform(matrix).astype(np.float32)


def load_text(args: argparse.Namespace) -> dict[str, Any]:
    """Return feature sets + provenance (source) labels for a multi-source text corpus."""
    path = project_root() / args.corpus
    if not path.exists():
        raise FileNotFoundError(
            f"Corpus {args.corpus} missing. Build it with "
            "`.venv/bin/python scripts/fetch_text_corpus.py`."
        )
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    sources = pd.Series([r["source"] for r in records])
    counts = sources.value_counts()
    kept = set(counts[counts >= args.min_source_samples].index)
    records = [r for r in records if r["source"] in kept]
    texts = [r["text"] for r in records]
    labels = np.array([r["source"] for r in records])

    feature_sets = {
        "surface_metadata": _surface_metadata(texts),
        "function_words": _function_word_rates(texts),
        "char_ngram_svd": _tfidf_svd(
            texts, analyzer="char_wb", ngram_range=(3, 5),
            max_features=args.max_features, components=args.svd_components, seed=args.seed,
        ),
        "content_tfidf_svd": _tfidf_svd(
            texts, analyzer="word", ngram_range=(1, 2), stop_words="english",
            max_features=args.max_features, components=args.svd_components, seed=args.seed,
            sublinear=True,
        ),
    }
    return {
        "feature_sets": feature_sets,
        "labels": labels,
        # Honest framing: there is no single normalization that removes a source
        # fingerprint present at the surface/style level, so we claim no remediation
        # control — the layered feature sets ARE the finding.
        "control_pairs": [],
        "meta": {
            "dataset_id": "text",
            "corpus": str(args.corpus),
            "documents": len(texts),
            "sources": {str(k): int(v) for k, v in sources.value_counts().items() if k in kept},
        },
    }


# --------------------------------------------------------------------------------------
# RRUFF adapter — the SECOND EXPERIMENTAL DATASET for the protocol (mineral Raman).
# Provenance label: the laser line (514/532/780/785 nm) = the instrument axis. Rows are
# one Processed spectrum per (specimen, wavelength) from the grammar events; folds are
# GROUPED BY SPECIMEN so specimen identity never straddles train/test. The decisive
# extra is --rruff-paired: restrict to specimens measured at >=2 usable wavelengths, so
# chemistry is IDENTICAL across label classes within each group — any recovery above
# chance is instrument imprint, not composition. This is the chemistry-matched control
# the opXRD archive could not provide (its sources measured different materials).
# --------------------------------------------------------------------------------------

RAMAN_GRID = (150.0, 1300.0, 600)  # cm^-1 range + points, matching data.rruff.load()
USABLE_WAVELENGTHS = (514.0, 532.0, 780.0, 785.0)


def load_rruff(args: argparse.Namespace) -> dict[str, Any]:
    import zipfile

    from materials_event_modeling.data.rruff import _parse

    root = project_root()
    events_path = root / "data/interim/event_grammar_v1/rruff/events.json"
    if not events_path.exists():
        raise FileNotFoundError("Run scripts/adapters/adapt_rruff.py first.")
    events = json.loads(events_path.read_text())

    wanted: list[tuple[str, float, str]] = []  # (specimen, wavelength, zip member)
    for event in events:
        for obs in event["observations"]:
            wl = obs["payload"].get("rruff.raman_wavelength_nm")
            if wl in USABLE_WAVELENGTHS and not obs["payload"].get("rruff.variant_note"):
                wanted.append((event["event_id"], float(wl), obs["payload"]["rruff.zip_member"]))
    if args.rruff_paired:
        by_specimen: dict[str, set[float]] = {}
        for rid, wl, _ in wanted:
            by_specimen.setdefault(rid, set()).add(wl)
        multi = {rid for rid, wls in by_specimen.items() if len(wls) >= 2}
        wanted = [w for w in wanted if w[0] in multi]

    gmin, gmax, n_grid = RAMAN_GRID
    grid = np.linspace(gmin, gmax, n_grid, dtype=np.float32)
    spectra, coverage, meta_rows, labels_list, groups_list = [], [], [], [], []
    zip_path = root / "data/raw/rruff/excellent_unoriented.zip"
    with zipfile.ZipFile(zip_path) as zf:
        for rid, wl, member in wanted:
            try:
                raw = zf.read(member).decode("utf-8")
            except UnicodeDecodeError:
                raw = zf.read(member).decode("latin-1")
            _, xs, ys = _parse(raw)
            if xs.size < 10:
                continue
            peak = float(np.max(np.abs(ys))) or 1.0
            gridded = np.interp(grid, xs, ys / peak, left=0.0, right=0.0).astype(np.float32)
            spectra.append(gridded)
            coverage.append(((grid >= xs.min()) & (grid <= xs.max())).astype(np.float32))
            meta_rows.append([
                float(xs.size), float(xs.min()), float(xs.max()),
                float(xs.max() - xs.min()), float(ys.min()), float(ys.max()),
            ])
            labels_list.append(f"{wl:g}nm")
            groups_list.append(rid)

    xrd = np.asarray(spectra)
    coverage_arr = np.asarray(coverage)
    labels = np.asarray(labels_list)
    counts = pd.Series(labels).value_counts()
    kept = counts[counts >= args.min_source_samples].index
    keep = np.isin(labels, kept)
    xrd, coverage_arr, labels = xrd[keep], coverage_arr[keep], labels[keep]
    metadata = np.asarray(meta_rows, dtype=np.float32)[keep]
    groups = np.asarray(groups_list)[keep]

    feature_sets: dict[str, np.ndarray] = {
        "metadata": metadata,
        "spectrum_summary": _spectrum_summary_features(xrd, args.peak_threshold),
        "raman_pca": xrd,
    }
    pca_spec: dict[str, int] = {"raman_pca": args.pca_components}
    control_pairs: list[tuple[str, str]] = []
    if args.include_controls:
        coverage_fraction = coverage_arr.mean(axis=0)
        crop_mask = coverage_fraction >= args.min_coverage_fraction
        cropped = xrd[:, crop_mask]
        for name, matrix in {
            "coverage_mask_pca": coverage_arr,
            "full_raman_row_zscore_pca": _row_zscore(xrd),
            "full_raman_l1_pca": _row_l1(xrd),
            "crop_raman_pca": cropped,
            "crop_raman_row_zscore_pca": _row_zscore(cropped),
            "crop_raman_derivative_pca": _derivative(_row_zscore(cropped)),
        }.items():
            feature_sets[name] = matrix
            pca_spec[name] = args.pca_components
        control_pairs.append(("raman_pca", "crop_raman_derivative_pca"))

    return {
        "feature_sets": feature_sets,
        "labels": labels,
        "groups": groups,
        "control_pairs": control_pairs,
        "pca_spec": pca_spec,
        "meta": {
            "dataset_id": "rruff_paired" if args.rruff_paired else "rruff",
            "spectra": int(xrd.shape[0]),
            "specimens": int(len(set(groups.tolist()))),
            "grid": list(RAMAN_GRID),
            "paired_chemistry_control": bool(args.rruff_paired),
        },
    }


# --------------------------------------------------------------------------------------
# Severson adapter — protocol MODALITY-GENERALITY check on the project's own A/B
# features (battery cycling, not spectra). Provenance label: collection batch date.
# Feature sets are EXACTLY the A/B's representations (imported from the shared module,
# not re-implemented): the recorded follow-on of the rung-3 replication, replacing the
# ad-hoc 94.5% batch-identifiability probe with the protocol tool. Also audits the
# paper-shape (policy) features: the sweep DESIGN nests in batch, so even the recipe
# may recover the batch — a designed-confound measurement, not a surprise.
# --------------------------------------------------------------------------------------


def load_severson_ab(args: argparse.Namespace) -> dict[str, Any]:
    from materials_event_modeling.eval.severson_ab import load_cells, representation

    root = project_root()
    events_path = root / "data/interim/event_grammar_v1/severson_battery/events.json"
    if not events_path.exists():
        raise FileNotFoundError("Run scripts/adapters/adapt_severson_battery.py first.")
    cells = load_cells(events_path)
    labels = np.array([c["batch"] for c in cells])

    k = 100
    a_traj = np.array([representation(c, "A_trajectory", k) for c in cells], dtype=np.float32)
    b_policy = np.array([representation(c, "B_policy", k) for c in cells], dtype=np.float32)

    # Raw trajectory analog of a spectrum: QDischarge over a fixed early-cycle grid.
    cycle_grid = np.arange(2, k + 1, dtype=float)
    curves = []
    for c in cells:
        mask = (c["cycles"] >= 2) & (c["cycles"] <= k)
        curves.append(np.interp(cycle_grid, c["cycles"][mask],
                                c["series"]["qdischarge_ah"][mask]).astype(np.float32))
    qd_curve = np.asarray(curves)

    return {
        "feature_sets": {
            "a_trajectory_k100": a_traj,
            "b_policy": b_policy,
            "qd_curve_pca": qd_curve,
        },
        "labels": labels,
        "control_pairs": [],
        "pca_spec": {"qd_curve_pca": args.pca_components},
        "meta": {
            "dataset_id": "severson_ab",
            "cells": len(cells),
            "batches": sorted(set(labels.tolist())),
            "note": "policies nest within batches by design; b_policy recoverability "
                    "measures that designed confound",
        },
    }


DATASETS: dict[str, Callable[[argparse.Namespace], dict[str, Any]]] = {
    "opxrd": load_opxrd,
    "text": load_text,
    "rruff": load_rruff,
    "severson_ab": load_severson_ab,
}


def print_report(report: dict[str, Any], meta: dict[str, Any], efficacy: list[dict[str, Any]]) -> None:
    chance = report["results"][0]["chance_balanced_accuracy"] if report["results"] else 0.0
    print(
        f"\nProvenance-recoverability audit — {meta.get('dataset_id', '?')}  "
        f"({report['n_classes']} sources, {report['n_items']} items, "
        f"chance bal-acc {chance:.3f}, {report['n_splits']}-fold x "
        f"{report.get('n_repeats', 1)} repeats)\n"
    )
    print(f"  {'feature_set':<32}{'recover':>9}{'bal_acc':>9}{'+-std':>7}  risk")
    print(f"  {'-' * 32}{'-' * 9}{'-' * 9}{'-' * 7}  {'-' * 8}")
    for r in report["results"]:
        print(
            f"  {r['feature_set']:<32}{r['leakage_score']:>9.3f}"
            f"{r['balanced_accuracy']:>9.3f}{r.get('balanced_accuracy_std', 0.0):>7.3f}"
            f"  {r['severity']}"
        )
    print(
        f"\n  worst: {report['worst_feature_set']} "
        f"(score {report['worst_leakage_score']:.3f}, {report['worst_severity']})"
    )
    print(f"  {report['recommendation']}")
    for e in efficacy:
        verdict = "NEUTRALIZED" if e["neutralized"] else f"still {e['control_severity']}"
        print(
            f"\n  control efficacy: {e['baseline']} ({e['baseline_leakage_score']:.3f}) "
            f"-> {e['control']} ({e['control_leakage_score']:.3f}): "
            f"{e['relative_reduction'] * 100:.0f}% recoverability reduction, {verdict}"
        )
    print()


def run(args: argparse.Namespace) -> dict[str, Any]:
    bundle = DATASETS[args.dataset](args)
    report = audit_feature_sets(
        bundle["feature_sets"],
        bundle["labels"],
        n_splits=args.n_splits,
        seed=args.seed,
        n_repeats=args.cv_repeats,
        pca_components=bundle.get("pca_spec"),
        groups=bundle.get("groups"),
    )
    efficacy = [
        control_efficacy(report, baseline, control)
        for baseline, control in bundle["control_pairs"]
    ]
    report["dataset"] = args.dataset
    report["dataset_meta"] = bundle["meta"]
    report["control_efficacy"] = efficacy
    report["created_at"] = datetime.now(timezone.utc).isoformat()
    report["run_identity"] = run_identity()

    print_report(report, bundle["meta"], efficacy)

    rel = args.output or Path(f"data/manifests/provenance_leakage_audit_{args.dataset}.json")
    output = Path(rel) if Path(rel).is_absolute() else project_root() / rel
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    try:
        shown = output.relative_to(project_root())
    except ValueError:
        shown = output
    print(f"  wrote {shown}\n")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="opxrd")
    parser.add_argument("--include-controls", action="store_true",
                        help="Also audit normalization/coverage controls and report efficacy.")
    parser.add_argument("--feature-ablation", action="store_true",
                        help="Also audit each metadata feature alone (incl. is_labeled) "
                        "to decompose the metadata recoverability.")
    parser.add_argument("--min-source-samples", type=int, default=15)
    parser.add_argument("--n-splits", type=int, default=3)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--cv-repeats", type=int, default=1,
                        help="Repeat the CV with shifted seeds and pool fold metrics; "
                        "use >=3 for any threshold-adjacent verdict.")
    parser.add_argument("--pca-components", type=int, default=32)
    parser.add_argument("--peak-threshold", type=float, default=0.05)
    parser.add_argument("--min-coverage-fraction", type=float, default=0.95)
    parser.add_argument("--min-crop-points", type=int, default=256)
    # text adapter
    parser.add_argument("--corpus", type=Path, default=Path("data/raw/text_corpus/mix.jsonl"))
    parser.add_argument("--svd-components", type=int, default=64)
    parser.add_argument("--max-features", type=int, default=20000)
    # rruff adapter
    parser.add_argument("--rruff-paired", action="store_true",
                        help="Chemistry-matched control: only specimens measured at >=2 "
                        "usable wavelengths, so composition is identical across classes "
                        "within each fold group.")
    parser.add_argument("--output", type=Path, default=None,
                        help="Default: data/manifests/provenance_leakage_audit_<dataset>.json")
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
