"""Smoke-test event-trace prediction on the Durham IPA droplet dataset."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_ARCHIVE = Path("data/raw/durham_ipa_droplets/ipa_droplets_in_moist_air.zip")
DEFAULT_OUTPUT = Path("data/manifests/durham_ipa_droplet_smoke_test.json")

VIDEO_RE = re.compile(
    r"V(?P<movie_id>\d+)-R[hH](?P<humidity_percent>\d+)-"
    r"(?P<nozzle_um>\d+)umNozzle-on(?P<substrate>[^-]+)"
    r"(?P<particle_suffix>-Particles)?-compressed\.avi$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--frame-size", type=int, default=64)
    parser.add_argument("--timeline-steps", type=int, default=64)
    parser.add_argument("--early-fraction", type=float, default=0.25)
    parser.add_argument("--late-fraction", type=float, default=0.25)
    return parser.parse_args()


def parse_video_conditions(member: str) -> dict[str, object]:
    name = Path(member).name
    match = VIDEO_RE.match(name)
    if match is None:
        raise ValueError(f"Could not parse video filename: {name}")

    groups = match.groupdict()
    return {
        "movie_id": int(groups["movie_id"]),
        "relative_humidity_percent": float(groups["humidity_percent"]),
        "nozzle_um": float(groups["nozzle_um"]),
        "trace_particles": groups["particle_suffix"] is not None,
    }


def decode_gray_video(zf: ZipFile, member: str, frame_size: int) -> np.ndarray:
    suffix = Path(member).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(zf.read(member))
        tmp.flush()
        cmd = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            tmp.name,
            "-vf",
            f"scale={frame_size}:{frame_size},format=gray",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ]
        raw = subprocess.check_output(cmd)

    pixels_per_frame = frame_size * frame_size
    if len(raw) % pixels_per_frame != 0:
        raise ValueError(f"Decoded byte count is not divisible by frame size for {member}")
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, frame_size, frame_size)
    return frames.astype(np.float32) / 255.0


def frame_feature_trace(frames: np.ndarray) -> tuple[np.ndarray, list[str]]:
    flat = frames.reshape(frames.shape[0], -1)
    mean = flat.mean(axis=1)
    std = flat.std(axis=1)
    q05 = np.quantile(flat, 0.05, axis=1)
    q50 = np.quantile(flat, 0.50, axis=1)
    q95 = np.quantile(flat, 0.95, axis=1)
    contrast = q95 - q05
    edge_x = np.abs(np.diff(frames, axis=2)).mean(axis=(1, 2))
    edge_y = np.abs(np.diff(frames, axis=1)).mean(axis=(1, 2))
    edge_energy = edge_x + edge_y
    dark_fraction = (frames < 0.45).mean(axis=(1, 2))
    bright_fraction = (frames > 0.75).mean(axis=(1, 2))
    trace = np.column_stack(
        [mean, std, q05, q50, q95, contrast, edge_energy, dark_fraction, bright_fraction]
    )
    names = [
        "mean_intensity",
        "std_intensity",
        "q05_intensity",
        "q50_intensity",
        "q95_intensity",
        "contrast_q95_q05",
        "edge_energy",
        "dark_fraction_lt_045",
        "bright_fraction_gt_075",
    ]
    return trace.astype(np.float32), names


def resample_trace(trace: np.ndarray, steps: int) -> np.ndarray:
    if trace.shape[0] == steps:
        return trace
    old_x = np.linspace(0.0, 1.0, trace.shape[0])
    new_x = np.linspace(0.0, 1.0, steps)
    resampled = np.column_stack(
        [np.interp(new_x, old_x, trace[:, col]) for col in range(trace.shape[1])]
    )
    return resampled.astype(np.float32)


def summarize_segment(segment: np.ndarray) -> np.ndarray:
    x = np.linspace(0.0, 1.0, len(segment), dtype=np.float32)
    centered_x = x - x.mean()
    denom = float((centered_x**2).sum())
    slopes = (centered_x[:, None] * (segment - segment.mean(axis=0))).sum(axis=0) / denom
    return np.concatenate([segment.mean(axis=0), segment.std(axis=0), segment[-1], slopes])


def load_events(archive: Path, frame_size: int, timeline_steps: int) -> tuple[list[dict], list[str]]:
    events = []
    with ZipFile(archive) as zf:
        videos = sorted(name for name in zf.namelist() if name.lower().endswith(".avi"))
        feature_names: list[str] | None = None
        for member in videos:
            conditions = parse_video_conditions(member)
            frames = decode_gray_video(zf, member, frame_size=frame_size)
            trace, feature_names = frame_feature_trace(frames)
            event = {
                "event_id": f"durham_movie_{conditions['movie_id']}",
                "file": member,
                "conditions": conditions,
                "frame_count": int(frames.shape[0]),
                "trace": resample_trace(trace, timeline_steps),
            }
            events.append(event)
    return events, feature_names or []


def metadata_matrix(events: list[dict]) -> np.ndarray:
    return np.array(
        [
            [
                event["conditions"]["relative_humidity_percent"],
                event["conditions"]["nozzle_um"],
                float(event["conditions"]["trace_particles"]),
            ]
            for event in events
        ],
        dtype=np.float32,
    )


def segment_vectors(
    events: list[dict], early_fraction: float, late_fraction: float
) -> tuple[np.ndarray, np.ndarray]:
    early_vectors = []
    late_vectors = []
    for event in events:
        trace = event["trace"]
        early_steps = max(2, int(round(len(trace) * early_fraction)))
        late_steps = max(2, int(round(len(trace) * late_fraction)))
        early_vectors.append(summarize_segment(trace[:early_steps]))
        late_vectors.append(summarize_segment(trace[-late_steps:]))
    return np.vstack(early_vectors), np.vstack(late_vectors)


def loo_predictions(
    features: np.ndarray, targets: np.ndarray, model_kind: str
) -> tuple[np.ndarray, np.ndarray]:
    predictions = []
    truths = []
    for test_idx in range(len(targets)):
        train_idx = np.array([idx for idx in range(len(targets)) if idx != test_idx])
        x_train, x_test = features[train_idx], features[test_idx : test_idx + 1]
        y_train, y_test = targets[train_idx], targets[test_idx : test_idx + 1]

        y_scaler = StandardScaler()
        y_train_z = y_scaler.fit_transform(y_train)
        y_test_z = y_scaler.transform(y_test)

        if model_kind == "train_mean":
            pred_z = np.zeros_like(y_test_z)
        elif model_kind == "ridge":
            model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            model.fit(x_train, y_train_z)
            pred_z = model.predict(x_test)
        elif model_kind == "nearest_neighbor":
            x_scaler = StandardScaler()
            x_train_z = x_scaler.fit_transform(x_train)
            x_test_z = x_scaler.transform(x_test)
            nn = NearestNeighbors(n_neighbors=1)
            nn.fit(x_train_z)
            neighbor_idx = nn.kneighbors(x_test_z, return_distance=False)[0, 0]
            pred_z = y_train_z[neighbor_idx : neighbor_idx + 1]
        elif model_kind == "copy_early":
            if x_test.shape[1] != y_test.shape[1]:
                raise ValueError("copy_early requires feature and target dimensions to match")
            pred_z = y_scaler.transform(x_test)
        else:
            raise ValueError(f"Unknown model kind: {model_kind}")

        predictions.append(pred_z[0])
        truths.append(y_test_z[0])
    return np.vstack(predictions), np.vstack(truths)


def evaluate_models(
    metadata: np.ndarray, early_vectors: np.ndarray, late_targets: np.ndarray
) -> dict[str, dict[str, float]]:
    model_inputs = {
        "train_mean": (metadata, "train_mean"),
        "metadata_ridge": (metadata, "ridge"),
        "metadata_nearest_neighbor": (metadata, "nearest_neighbor"),
        "early_trace_ridge": (early_vectors, "ridge"),
        "early_trace_nearest_neighbor": (early_vectors, "nearest_neighbor"),
        "early_plus_metadata_ridge": (np.hstack([early_vectors, metadata]), "ridge"),
        "copy_early_summary": (early_vectors, "copy_early"),
    }

    raw_metrics = {}
    for name, (features, model_kind) in model_inputs.items():
        pred, truth = loo_predictions(features, late_targets, model_kind=model_kind)
        raw_metrics[name] = {
            "mse": float(mean_squared_error(truth, pred)),
            "mae": float(mean_absolute_error(truth, pred)),
        }

    mean_mse = raw_metrics["train_mean"]["mse"]
    mean_mae = raw_metrics["train_mean"]["mae"]
    for values in raw_metrics.values():
        values["mse_improvement_vs_train_mean"] = float(1.0 - values["mse"] / mean_mse)
        values["mae_improvement_vs_train_mean"] = float(1.0 - values["mae"] / mean_mae)
    return raw_metrics


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    archive = args.archive if args.archive.is_absolute() else repo_root / args.archive
    if not archive.exists():
        raise FileNotFoundError(
            f"Archive not found: {archive}. Download it from "
            "https://collections.durham.ac.uk/files/r12801pg44n"
        )

    events, trace_feature_names = load_events(
        archive, frame_size=args.frame_size, timeline_steps=args.timeline_steps
    )
    metadata = metadata_matrix(events)
    early_vectors, late_targets = segment_vectors(
        events, early_fraction=args.early_fraction, late_fraction=args.late_fraction
    )
    metrics = evaluate_models(metadata, early_vectors, late_targets)

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "durham_ipa_droplet_early_trace_smoke_test",
        "source_url": "https://collections.durham.ac.uk/files/r12801pg44n",
        "archive": str(archive),
        "hypothesis": (
            "If the released videos contain usable event traces, early video-derived "
            "signals should predict late trace summaries better than condition metadata "
            "alone. With only nine videos, any positive result is a smoke-test signal, "
            "not decisive evidence."
        ),
        "event_count": len(events),
        "frame_size": args.frame_size,
        "timeline_steps": args.timeline_steps,
        "early_fraction": args.early_fraction,
        "late_fraction": args.late_fraction,
        "metadata_features": [
            "relative_humidity_percent",
            "nozzle_um",
            "trace_particles",
        ],
        "trace_feature_names": trace_feature_names,
        "target": "late segment summary: mean, std, last value, and slope per trace feature",
        "events": [
            {
                "event_id": event["event_id"],
                "file": event["file"],
                "conditions": event["conditions"],
                "frame_count": event["frame_count"],
            }
            for event in events
        ],
        "metrics": metrics,
        "verdict": {
            "early_trace_beats_metadata_ridge_mse": (
                metrics["early_trace_ridge"]["mse"] < metrics["metadata_ridge"]["mse"]
            ),
            "early_trace_beats_metadata_nearest_neighbor_mse": (
                metrics["early_trace_nearest_neighbor"]["mse"]
                < metrics["metadata_nearest_neighbor"]["mse"]
            ),
            "dataset_supports_only_smoke_test": True,
            "main_caveat": (
                "Leave-one-video-out has only eight training events per fold, and the "
                "released archive lacks replicate groups, failed/ambiguous attempt logs, "
                "and session/run-order provenance."
            ),
        },
    }

    output = args.output if args.output.is_absolute() else repo_root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
