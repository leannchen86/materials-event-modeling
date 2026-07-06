"""Ingest the oleogel SAXS/WAXS deposit (zenodo 15268752) into the event-field abstraction.

Each run folder ``MAGs/<run>/{SAXS,WAXS}/..._NNNN_sub.csv`` becomes an event whose
observations are time-ordered frames. We expose the same ``(event_ids, coords, spectra)``
representation the masked-event harness already consumes, with ``coord = [normalized_time, 0]``
and ``spectrum = `` the (q-resampled) intensity vector of one frame.

This is the refined-a real-trajectory loader; see docs/event-method/refined_a_oleogel_dataset.md.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np

RUN_NAMES = [
    "s_dmhr_1s_10Cmin_10c",
    "s_dmhr_25s_10Cmin_10c",
    "s_dmhr_50s_10Cmin_10c",
    "s_mopv_1s_10Cmin_10c",
    "s_mopv_25s_10Cmin_10C_redo",
    "s_mopv_50s_10Cmin_10c",
]

_FRAME_RE = re.compile(r"_(\d+)_sub\.csv$")


def parse_run_conditions(run: str) -> dict:
    """Parse planned conditions out of a run folder name (``s_<sample>_<shear>_<rate>_<temp>``)."""
    parts = run.split("_")
    return {
        "sample": parts[1] if len(parts) > 1 else None,
        "shear": parts[2] if len(parts) > 2 else None,
        "cooling": parts[3] if len(parts) > 3 else None,
        "temperature": parts[4] if len(parts) > 4 else None,
        "replicate": run.endswith("redo"),
    }


@dataclass(frozen=True)
class EventField:
    event_ids: np.ndarray  # (N,) run name per frame
    coords: np.ndarray     # (N, 2): [normalized_time, 0]
    spectra: np.ndarray    # (N, n_q) frame intensities on a shared q grid
    q: np.ndarray          # (n_q,) shared q grid


def _frame_members(zf: zipfile.ZipFile, run: str, modality: str) -> list[str]:
    prefix = f"MAGs/{run}/{modality}/"
    members = [m for m in zf.namelist() if m.startswith(prefix) and m.endswith(".csv")]

    def frame_index(member: str) -> int:
        match = _FRAME_RE.search(member)
        return int(match.group(1)) if match else -1

    return sorted(members, key=frame_index)


def _read_frame(zf: zipfile.ZipFile, member: str) -> tuple[np.ndarray, np.ndarray]:
    arr = np.genfromtxt(BytesIO(zf.read(member)), delimiter=",")
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr[:, 0], arr[:, 1]


def load_run(zip_path: str | Path, run: str, modality: str = "WAXS") -> EventField:
    """Load one run's frame trajectory for a modality into an :class:`EventField`.

    Early all-NaN frames (pre-signal / masked detector) are kept as zero rows so the
    time axis stays uniform; finite-q interpolation puts every frame on a shared grid.
    """
    with zipfile.ZipFile(zip_path) as zf:
        members = _frame_members(zf, run, modality)
        if not members:
            raise ValueError(f"no {modality} frames found for run {run!r}")
        frames = [_read_frame(zf, m) for m in members]

    # Reference q grid: the frame with the most finite intensities (late, full-signal frame).
    ref_q = max(frames, key=lambda qi: int(np.isfinite(qi[1]).sum()))[0]
    spectra = np.zeros((len(frames), ref_q.size), dtype=np.float32)
    for i, (q, intensity) in enumerate(frames):
        finite = np.isfinite(intensity) & np.isfinite(q)
        if int(finite.sum()) >= 2:
            spectra[i] = np.interp(ref_q, q[finite], intensity[finite], left=0.0, right=0.0)

    times = np.linspace(0.0, 1.0, len(frames), dtype=np.float32)
    coords = np.stack([times, np.zeros_like(times)], axis=1)
    event_ids = np.array([run] * len(frames))
    return EventField(event_ids=event_ids, coords=coords, spectra=spectra, q=ref_q.astype(np.float32))


def load_event_field(
    zip_path: str | Path, runs: list[str] | None = None, modality: str = "WAXS"
) -> EventField:
    """Concatenate several runs into one event field (each run is one event)."""
    runs = runs or RUN_NAMES
    fields = [load_run(zip_path, run, modality) for run in runs]
    ref = fields[0].q
    # All runs from one beamtime share calibration; resample defensively onto run-0's grid.
    spectra = []
    for field in fields:
        if field.q.shape == ref.shape and np.allclose(field.q, ref):
            spectra.append(field.spectra)
        else:
            spectra.append(
                np.stack([np.interp(ref, field.q, row) for row in field.spectra]).astype(np.float32)
            )
    return EventField(
        event_ids=np.concatenate([f.event_ids for f in fields]),
        coords=np.concatenate([f.coords for f in fields]),
        spectra=np.concatenate(spectra).astype(np.float32),
        q=ref,
    )
