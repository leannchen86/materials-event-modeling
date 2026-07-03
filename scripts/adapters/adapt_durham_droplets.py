"""Adapt the Durham IPA droplet-evaporation dataset into event-grammar v1 envelopes.

Source: https://collections.durham.ac.uk/files/r12801pg44n , extracted locally under
``data/raw/durham_ipa_droplets/extracted``. The release is 9 compressed high-speed
drying movies (V1..V9), 3 figure-specific xlsx workbooks, 1 .dat file, and a README
.docx. One drying movie == one droplet-drying event, so this adapter emits 9 events.

Slot mapping (how each grammar slot was derived, and what could NOT be derived)
------------------------------------------------------------------------------
intent  -- FILLED from the real recorded plan, which lives in the movie filenames and
    the README.docx (both shipped in the archive). ``intent.planned`` carries, per
    movie, namespaced keys:
      * droplet.solvent               = "IPA"          (README: "IPA droplet drying")
      * droplet.relative_humidity_pct = e.g. 38.0      (filename "RH38" and README
                                                        "Movie 1 ... RH of 38%")
      * droplet.nozzle_diameter_um    = 30.0 / 50.0    (filename "30umNozzle" and README
                                                        "Droplets are generated from 30 m
                                                        nozzle")
      * droplet.substrate             = "glass"        (filename "onGlass")
      * droplet.trace_particles       = bool           (filename "-Particles" suffix and
                                                        README "drying with trace particles")
      * droplet.acquisition_fps       = 5000 / 1000    (README "Frame rate for Movie 1-5
                                                        is 5000 fps"; Movie 6 = 5000;
                                                        Movies 7-9 = 1000)
    ``intent.plan_id`` / ``event_group_id`` are null: the source assigns no plan or
    replicate-group identifiers -- each movie is a distinct single condition.

observations -- FILLED, two kinds per event, both time/frame ordered:
      * one modality="video" observation referencing the raw .avi by ``file_path``
        (relative to the repo root), with small scalars inline (released_frame_count,
        acquisition_frame_rate_fps, feature_frame_size_px — the 96px analysis downscale,
        not the native resolution). order_index=0. The README's per-group scalebar values
        (30 um for Movies 1-5, 50 um for 6-9) are NOT carried into events (mapping gap:
        no pixel-size calibration mapped).
      * one modality="video_trace" observation per decoded frame (kind="process"),
        ordered by ``frame_index``, carrying a small vector of per-frame grayscale
        image-analysis features under the ``droplet`` namespace (mean/std/quantile
        intensity, contrast, edge energy, dark/bright area fraction). These are DERIVED
        by this adapter from the raw video (ffmpeg decode -> downscale -> features),
        cited as such; they are a reproducible reduction of the raw pixels, not a source
        table. Determinism: fixed ffmpeg scale filter + fixed feature functions.
    NOT derivable: an absolute acquisition timestamp per frame. The released movies are
    compressed and decimated (they probe at ~30 fps / a few hundred frames, not the
    5000/1000 fps stated for the original capture), so a compressed frame index does not
    map cleanly to real seconds. We therefore order by ``frame_index`` (honest: index in
    the released compressed movie) and do not synthesize ``time_s``.

outcome -- status="unknown". The README describes conditions and imaging setup but
    records no per-run outcome, success/failure flag, or completion assertion. Marking
    these "success" would be an inference from the fact that a movie exists, so we do
    not. summary=null.

provenance -- NEARLY EMPTY, by the source's own limits. Only ``source_dataset`` is set.
    operator_id, lab_id, batch_id, lot_id, instrument_id, instrument_session_id,
    measurement_day, and run_order are all null: none are recorded per movie. The movie
    numbering (V1..V9) is figure/movie numbering, not a logged acquisition order, so it
    is NOT used as run_order. File mtimes exist but are archive-save dates, not
    experiment dates, so they are NOT used as measurement_day. No provenance is invented.

labels -- null. The source carries no post-hoc human/machine labels attached after the
    raw record was frozen.

Not mapped: the 3 xlsx workbooks (D-t Fig.1c, h-r Fig.1b, VLE Fig.S2) and Instability
Fig.2c.dat are figure-specific extracted data. Per the README they derive "mainly from
image analysis of Movie 1-5" and additional movies are "provided under request", so they
do not map 1:1 onto the 9 released movies (e.g. the h-r workbook has RH sheets 17% and
48% with no movie, and movies 6-9 have no h-r sheet). Force-joining them by RH would be a
fabricated correspondence, so they are left out and logged as a mapping gap.

Usage:
    .venv/bin/python scripts/adapters/adapt_durham_droplets.py \
        --output data/interim/event_grammar_v1/durham_droplets/events.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np

DATASET = "durham_droplets"
SYSTEM = "drying_droplet"
DEFAULT_VIDEO_DIR = Path("data/raw/durham_ipa_droplets/extracted/Videos")
DEFAULT_OUTPUT = Path(f"data/interim/event_grammar_v1/{DATASET}/events.json")

# Real acquisition frame rate stated in README.docx (compressed movies play back slower).
README_ACQUISITION_FPS = {1: 5000, 2: 5000, 3: 5000, 4: 5000, 5: 5000, 6: 5000,
                          7: 1000, 8: 1000, 9: 1000}

VIDEO_RE = re.compile(
    r"V(?P<movie_id>\d+)-R[hH](?P<humidity_percent>\d+)-"
    r"(?P<nozzle_um>\d+)umNozzle-on(?P<substrate>[^-]+)"
    r"(?P<particle_suffix>-Particles)?-compressed\.avi$"
)

FEATURE_NAMES = [
    "mean_intensity", "std_intensity", "q05_intensity", "q50_intensity", "q95_intensity",
    "contrast_q95_q05", "edge_energy", "dark_fraction_lt_045", "bright_fraction_gt_075",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-dir", type=Path, default=DEFAULT_VIDEO_DIR,
                        help="Directory of extracted V*.avi movies (relative to repo root).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--frame-size", type=int, default=96,
                        help="Square downscale size for deterministic frame features.")
    return parser.parse_args()


def parse_video_conditions(name: str) -> dict[str, object]:
    match = VIDEO_RE.match(name)
    if match is None:
        raise ValueError(f"Could not parse video filename: {name}")
    groups = match.groupdict()
    return {
        "movie_id": int(groups["movie_id"]),
        "relative_humidity_percent": float(groups["humidity_percent"]),
        "nozzle_um": float(groups["nozzle_um"]),
        "substrate": groups["substrate"].lower(),
        "trace_particles": groups["particle_suffix"] is not None,
    }


def decode_gray_video(path: Path, frame_size: int) -> np.ndarray:
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(path),
        "-vf", f"scale={frame_size}:{frame_size},format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    raw = subprocess.check_output(cmd)
    pixels = frame_size * frame_size
    if len(raw) % pixels != 0:
        raise ValueError(f"Decoded byte count not divisible by frame size for {path}")
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, frame_size, frame_size)
    return frames.astype(np.float32) / 255.0


def frame_feature_trace(frames: np.ndarray) -> np.ndarray:
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
    return trace.astype(np.float32)


def build_event(path: Path, repo_root: Path, frame_size: int) -> dict[str, object]:
    name = path.name
    cond = parse_video_conditions(name)
    movie_id = int(cond["movie_id"])
    fps = README_ACQUISITION_FPS[movie_id]

    frames = decode_gray_video(path, frame_size=frame_size)
    trace = frame_feature_trace(frames)
    rel_path = path.resolve().relative_to(repo_root).as_posix()

    observations: list[dict[str, object]] = [
        {
            "observation_id": f"durham_droplet_movie_{movie_id}_video",
            "modality": "video",
            "kind": "measurement",
            "stage": "in_situ",
            "order_index": 0,
            "file_path": rel_path,
            "raw_export_format": "avi",
            "payload": {
                "droplet": {
                    "released_frame_count": int(frames.shape[0]),
                    "acquisition_frame_rate_fps": fps,
                    "feature_frame_size_px": frame_size,
                }
            },
            "notes": (
                "Raw compressed high-speed drying movie. Original capture "
                f"{fps} fps per README; released movie is compressed/decimated so frame "
                "index does not map to absolute seconds."
            ),
        }
    ]
    for i in range(trace.shape[0]):
        payload = {name_: round(float(trace[i, j]), 6) for j, name_ in enumerate(FEATURE_NAMES)}
        observations.append(
            {
                "observation_id": f"durham_droplet_movie_{movie_id}_frame_{i:04d}",
                "modality": "video_trace",
                "kind": "process",
                "stage": "in_situ",
                "frame_index": i,
                "payload": {"droplet": payload},
                "notes": None,
            }
        )

    return {
        "event_id": f"durham_droplet_movie_{movie_id}",
        "system": SYSTEM,
        "created_at": None,
        "intent": {
            "plan_id": None,
            "event_group_id": None,
            "planned": {
                "droplet.solvent": "IPA",
                "droplet.relative_humidity_percent": cond["relative_humidity_percent"],
                "droplet.nozzle_diameter_um": cond["nozzle_um"],
                "droplet.substrate": cond["substrate"],
                "droplet.trace_particles": cond["trace_particles"],
                "droplet.acquisition_fps": fps,
            },
        },
        "observations": observations,
        "outcome": {
            "status": "unknown",
            "summary": None,
            "notes": (
                "Source records drying conditions and imaging setup but no per-run "
                "outcome, success/failure flag, or completion assertion."
            ),
        },
        "provenance": {
            "operator_id": None,
            "lab_id": None,
            "batch_id": None,
            "lot_id": None,
            "instrument_id": None,
            "instrument_session_id": None,
            "measurement_day": None,
            "run_order": None,
            "source_dataset": DATASET,
            "raw_export_profile": None,
        },
        "labels": None,
    }


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    video_dir = args.video_dir if args.video_dir.is_absolute() else repo_root / args.video_dir
    if not video_dir.exists():
        raise FileNotFoundError(f"Video directory not found: {video_dir}")

    videos = sorted(p for p in video_dir.iterdir() if p.suffix.lower() == ".avi")
    if not videos:
        raise FileNotFoundError(f"No .avi movies under {video_dir}")

    events = [build_event(path, repo_root, args.frame_size) for path in videos]

    output = args.output if args.output.is_absolute() else repo_root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(events, indent=2) + "\n")

    total_obs = sum(len(e["observations"]) for e in events)
    print(f"Wrote {len(events)} events, {total_obs} observations -> {output}")


if __name__ == "__main__":
    main()
