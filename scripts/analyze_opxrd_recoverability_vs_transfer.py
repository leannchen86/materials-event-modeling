"""Does per-source provenance recoverability predict downstream transfer difficulty?

The provenance branch's open question (PROJECTS.md): connect recoverability (a probe) to
a downstream evaluation, not just report the probe. This correlates, per opXRD source,
how identifiable the source is (per-class recall from the source-predictability audit)
against how hard the residual CNN transfers to it when it is held out (conv-minus-
interpolation MSE from the leave-one-source-out transfer run). Both are committed
manifests; this runs no model — it is analysis over existing numbers, and at n=6 sources
it is descriptive, not inferential.

Reads:  data/manifests/opxrd_source_predictability.json (per-source recall)
        data/manifests/opxrd_source_transfer_a100.json (per-source transfer)
Writes: data/manifests/opxrd_recoverability_vs_transfer.json (with run identity)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from materials_event_modeling.run_identity import run_identity


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> None:
    root = project_root()
    pred = json.loads((root / "data/manifests/opxrd_source_predictability.json").read_text())
    transfer = json.loads(
        (root / "data/manifests/opxrd_source_transfer_a100.json").read_text()
    )["summary"]

    recall = {r["feature_set"]: r["per_class_recall"] for r in pred["results"]}
    spec_recall = recall["xrd_pca"]          # recoverability from the spectrum
    meta_recall = recall["metadata"]         # recoverability from acquisition metadata
    counts = pred["source_counts"]

    sources = sorted(s for s in spec_recall if s in transfer)
    rows = []
    for s in sources:
        # conv_minus_interpolation_mse mean: POSITIVE = CNN loses to interpolation on the
        # held-out source = harder transfer. Use it directly as "transfer_badness".
        badness = transfer[s]["conv_minus_interpolation_mse"]["mean"]
        rows.append({
            "source": s,
            "n_samples": counts[s],
            "spectral_recoverability": spec_recall[s],
            "metadata_recoverability": meta_recall[s],
            "transfer_badness_mse": badness,
            "cnn_beats_interpolation": transfer[s]["conv_mse_win_rate_vs_interpolation"] >= 0.5,
        })

    spec = np.array([r["spectral_recoverability"] for r in rows])
    meta = np.array([r["metadata_recoverability"] for r in rows])
    bad = np.array([r["transfer_badness_mse"] for r in rows])
    logn = np.log(np.array([r["n_samples"] for r in rows]))

    correlations = {
        "spearman_spectral_recoverability_vs_transfer_badness": float(spearmanr(spec, bad).statistic),
        "spearman_metadata_recoverability_vs_transfer_badness": float(spearmanr(meta, bad).statistic),
        "spearman_log_n_vs_transfer_badness": float(spearmanr(logn, bad).statistic),
        "spearman_spectral_recoverability_vs_log_n": float(spearmanr(spec, logn).statistic),
    }

    report = {
        "task": "opxrd_recoverability_vs_transfer",
        "question": "does per-source provenance recoverability predict transfer difficulty?",
        "n_sources": len(rows),
        "per_source": rows,
        "correlations": correlations,
        "interpretation": (
            "At n=6, spectral recoverability does NOT predict transfer difficulty "
            f"(rho={correlations['spearman_spectral_recoverability_vs_transfer_badness']:+.3f}); "
            "source SIZE does "
            f"(rho={correlations['spearman_log_n_vs_transfer_badness']:+.3f}). The two "
            "sources the CNN loses on (EMPA, HKUST) are small, not especially recoverable; "
            "LBNL is the most recoverable yet transfers well. Recoverability is a screening "
            "/ risk signal, not a downstream-performance predictor."
        ),
        "caveats": [
            "n=6 sources: Spearman is descriptive, not inferential.",
            "Single architecture (residual CNN), single mask width (1024), 2 seeds.",
            "transfer_badness and recoverability come from separate runs on the same subset.",
            "Source size confounds both axes; not deconfounded at this n.",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_identity": run_identity(),
    }

    out = root / "data/manifests/opxrd_recoverability_vs_transfer.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"\n{'source':7}{'n':>6}{'spec_recov':>12}{'meta_recov':>12}"
          f"{'transfer_bad':>14}  cnn_wins")
    for r in sorted(rows, key=lambda r: r["transfer_badness_mse"]):
        print(f"{r['source']:7}{r['n_samples']:>6}{r['spectral_recoverability']:>12.3f}"
              f"{r['metadata_recoverability']:>12.3f}{r['transfer_badness_mse']:>+14.5f}"
              f"  {'yes' if r['cnn_beats_interpolation'] else 'NO'}")
    print()
    for k, v in correlations.items():
        print(f"  {k} = {v:+.3f}")
    print(f"\n  wrote {out.relative_to(root)}\n")


if __name__ == "__main__":
    main()
