"""Utilities for the opXRD experimental powder diffraction archive."""

from __future__ import annotations

import json
import math
import zipfile
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DATASET_ID = "opxrd"
ARCHIVE_FILENAME = "opxrd.zip"
DEFAULT_THETA_MIN = 0.0
DEFAULT_THETA_MAX = 180.0
DEFAULT_THETA_POINTS = 4096


@dataclass(frozen=True)
class OpxrdPattern:
    """One parsed opXRD pattern with minimally decoded metadata."""

    member_name: str
    two_theta: np.ndarray
    intensity: np.ndarray
    label: dict[str, object]
    metadata: dict[str, object]

    @property
    def is_labeled(self) -> bool:
        return phase_count(self.label) > 0

    @property
    def phase_count(self) -> int:
        return phase_count(self.label)


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def raw_archive_path(root: Path | None = None) -> Path:
    return (root or project_root()) / "data" / "raw" / DATASET_ID / ARCHIVE_FILENAME


def standard_theta_grid(
    points: int = DEFAULT_THETA_POINTS,
    theta_min: float = DEFAULT_THETA_MIN,
    theta_max: float = DEFAULT_THETA_MAX,
) -> np.ndarray:
    return np.linspace(theta_min, theta_max, points, dtype=np.float32)


def json_member_names(archive_path: Path) -> list[str]:
    with zipfile.ZipFile(archive_path) as archive:
        return [
            info.filename
            for info in archive.infolist()
            if not info.is_dir() and info.filename.lower().endswith(".json")
        ]


def select_member_names(
    member_names: Sequence[str],
    max_spectra: int,
    strategy: str = "spread",
) -> list[str]:
    if max_spectra <= 0:
        raise ValueError("max_spectra must be positive")
    if max_spectra >= len(member_names):
        return list(member_names)
    if strategy == "first":
        return list(member_names[:max_spectra])
    if strategy == "spread":
        indices = np.linspace(0, len(member_names) - 1, num=max_spectra, dtype=np.int64)
        return [member_names[int(index)] for index in indices]
    raise ValueError(f"Unsupported opXRD member selection strategy: {strategy}")


def parse_nested_json(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return {str(k): v for k, v in parsed.items()} if isinstance(parsed, dict) else {}
    return {}


def phase_count(label: dict[str, object]) -> int:
    phases = label.get("phases")
    if isinstance(phases, Sequence) and not isinstance(phases, (str, bytes)):
        return len(phases)
    return 0


def parse_pattern_bytes(member_name: str, raw: bytes) -> OpxrdPattern | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None
    if "two_theta_values" not in data or "intensities" not in data:
        return None

    two_theta = np.asarray(data["two_theta_values"], dtype=np.float32)
    intensity = np.asarray(data["intensities"], dtype=np.float32)
    if two_theta.ndim != 1 or intensity.ndim != 1 or len(two_theta) != len(intensity):
        return None

    label = parse_nested_json(data.get("label"))
    metadata = parse_nested_json(data.get("metadata"))
    return OpxrdPattern(
        member_name=member_name,
        two_theta=two_theta,
        intensity=intensity,
        label=label,
        metadata=metadata,
    )


def iter_patterns_from_archive(
    archive_path: Path,
    *,
    limit: int | None = None,
    member_names: Iterable[str] | None = None,
) -> Iterator[OpxrdPattern]:
    yielded = 0
    selected_names = set(member_names) if member_names is not None else None
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".json"):
                continue
            if selected_names is not None and info.filename not in selected_names:
                continue
            pattern = parse_pattern_bytes(info.filename, archive.read(info))
            if pattern is None:
                continue
            yield pattern
            yielded += 1
            if limit is not None and yielded >= limit:
                return


def standardize_intensity(
    two_theta: np.ndarray,
    intensity: np.ndarray,
    theta_grid: np.ndarray,
    *,
    eps: float = 1e-8,
) -> np.ndarray:
    finite = np.isfinite(two_theta) & np.isfinite(intensity)
    x = two_theta[finite].astype(np.float32)
    y = intensity[finite].astype(np.float32)
    if len(x) < 50:
        raise ValueError("Pattern has fewer than 50 finite points")

    order = np.argsort(x)
    x = x[order]
    y = y[order]
    x, unique_indices = np.unique(x, return_index=True)
    y = y[unique_indices]
    if len(x) < 50 or not x[-1] > x[0]:
        raise ValueError("Pattern has insufficient unique two-theta values")

    interpolated = np.interp(theta_grid, x, y, left=np.nan, right=np.nan).astype(np.float32)
    in_range = (theta_grid >= x[0]) & (theta_grid <= x[-1])
    if np.any(in_range):
        interpolated -= float(np.min(interpolated[in_range]))
    else:
        interpolated -= float(np.min(interpolated))
    interpolated[~in_range] = 0.0
    max_intensity = float(np.max(interpolated))
    if not math.isfinite(max_intensity) or max_intensity <= eps:
        raise ValueError("Pattern has no positive intensity after normalization")
    return interpolated / max_intensity


def pattern_summary(pattern: OpxrdPattern) -> dict[str, object]:
    return {
        "member_name": pattern.member_name,
        "points": int(pattern.two_theta.shape[0]),
        "theta_min": float(np.min(pattern.two_theta)),
        "theta_max": float(np.max(pattern.two_theta)),
        "intensity_min": float(np.min(pattern.intensity)),
        "intensity_max": float(np.max(pattern.intensity)),
        "is_labeled": pattern.is_labeled,
        "phase_count": pattern.phase_count,
        "institution": pattern.metadata.get("institution"),
        "contributor_name": pattern.metadata.get("contributor_name"),
        "original_file_format": pattern.metadata.get("original_file_format"),
        "measurement_date": pattern.metadata.get("measurement_date"),
        "tags": pattern.metadata.get("tags", []),
    }

