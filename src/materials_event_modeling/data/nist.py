"""Load and align the NIST MDS2-2301 combinatorial diffraction dataset."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


DATASET_ID = "nist_mds2_2301"
LABEL_MEANINGS = {
    0: "low_temperature_phase",
    1: "two_phase_region",
    2: "high_temperature_phase",
}

XRD_FILENAME = "VO2 -Nb2O3 XRD Combiview.txt"
COMPOSITION_FILENAME = "VO2 - Nb2O3 Composition and temp Combiview.txt"
HUMAN_LABELS_FILENAME = "Human Labels.xlsx"
MACHINE_LABELS_FILENAME = "Compare ML Labels.csv"
MACHINE_LOGLIK_FILENAME = "cluster_assignment_loglik_all.csv"


@dataclass(frozen=True)
class NistDataset:
    """Aligned NIST arrays and per-sample metadata."""

    theta: np.ndarray
    xrd: np.ndarray
    samples: pd.DataFrame


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def raw_dataset_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "data" / "raw" / DATASET_ID


def read_xrd(raw_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.loadtxt(raw_dir / XRD_FILENAME, delimiter="\t", dtype=np.float32)
    theta = matrix[0].astype(np.float32)
    xrd = matrix[1:].astype(np.float32)
    return theta, xrd


def read_composition_temperature(raw_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(raw_dir / COMPOSITION_FILENAME, sep="\t")
    frame = frame.rename(columns={"V": "v_percent", "temp": "temp_c"})
    frame.insert(0, "sample_index", np.arange(len(frame), dtype=np.int64))
    frame["nb_percent"] = 100 - frame["v_percent"]
    frame["v_fraction"] = frame["v_percent"] / 100.0
    frame["nb_fraction"] = frame["nb_percent"] / 100.0
    return frame


def _entropy(labels: list[int]) -> float:
    counts = Counter(labels)
    total = len(labels)
    return float(-sum((count / total) * np.log(count / total) for count in counts.values()))


def _consensus_label(labels: list[int]) -> int:
    counts = Counter(labels)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def read_human_labels(raw_dir: Path) -> pd.DataFrame:
    frame = pd.read_excel(raw_dir / HUMAN_LABELS_FILENAME)
    frame = frame.rename(
        columns={
            frame.columns[0]: "sample_index_one_based",
            frame.columns[1]: "v_fraction_human_file",
            frame.columns[2]: "v_percent_human_file",
            "temp": "temp_c_human_file",
        }
    )
    frame["sample_index"] = frame["sample_index_one_based"].astype(int) - 1

    label_columns = [column for column in frame.columns if str(column).startswith("HL")]
    for column in label_columns:
        frame[column] = frame[column].astype(int)

    labels = frame[label_columns].to_numpy(dtype=int)
    frame["human_label_entropy"] = [_entropy(row.tolist()) for row in labels]
    frame["human_consensus_label"] = [_consensus_label(row.tolist()) for row in labels]
    frame["human_disagree"] = np.array([len(set(row.tolist())) > 1 for row in labels], dtype=bool)

    keep_columns = [
        "sample_index",
        "sample_index_one_based",
        "v_percent_human_file",
        "temp_c_human_file",
        *label_columns,
        "human_consensus_label",
        "human_label_entropy",
        "human_disagree",
    ]
    return frame[keep_columns]


def read_machine_labels(raw_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(raw_dir / MACHINE_LABELS_FILENAME)
    frame = frame.rename(
        columns={
            frame.columns[0]: "sample_index",
            "V": "v_percent_machine_file",
            "Nb": "nb_percent_machine_file",
            "temp": "temp_c_machine_file",
        }
    )
    frame["sample_index"] = frame["sample_index"].astype(int)

    method_columns = [
        column
        for column in frame.columns
        if column not in {"sample_index", "v_percent_machine_file", "nb_percent_machine_file", "temp_c_machine_file"}
    ]
    for column in method_columns:
        frame[column] = frame[column].astype(int)

    labels = frame[method_columns].to_numpy(dtype=int)
    frame["machine_label_entropy"] = [_entropy(row.tolist()) for row in labels]
    frame["machine_consensus_label"] = [_consensus_label(row.tolist()) for row in labels]
    frame["machine_disagree"] = np.array([len(set(row.tolist())) > 1 for row in labels], dtype=bool)
    return frame


def read_machine_loglik(raw_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(raw_dir / MACHINE_LOGLIK_FILENAME)
    frame = frame.rename(
        columns={
            frame.columns[0]: "sample_index",
            "V": "v_fraction_loglik_file",
            "Nb": "nb_fraction_loglik_file",
            "temp": "temp_c_loglik_file",
        }
    )
    frame["sample_index"] = frame["sample_index"].astype(int)
    return frame


def validate_alignment(theta: np.ndarray, xrd: np.ndarray, samples: pd.DataFrame) -> None:
    if theta.ndim != 1:
        raise ValueError(f"theta must be one-dimensional, got shape {theta.shape}")
    if xrd.ndim != 2:
        raise ValueError(f"xrd must be two-dimensional, got shape {xrd.shape}")
    if xrd.shape[0] != len(samples):
        raise ValueError(f"{xrd.shape[0]} XRD rows for {len(samples)} sample rows")
    if xrd.shape[1] != len(theta):
        raise ValueError(f"{xrd.shape[1]} XRD columns for {len(theta)} theta points")

    human = samples[samples["human_consensus_label"].notna()]
    if not human.empty:
        human_v = human["v_percent_human_file"].astype(int)
        human_temp = human["temp_c_human_file"].astype(int)
        if not (human_v.to_numpy() == human["v_percent"].to_numpy()).all():
            raise ValueError("Human-label V percentages are not aligned by sample_index")
        if not (human_temp.to_numpy() == human["temp_c"].to_numpy()).all():
            raise ValueError("Human-label temperatures are not aligned by sample_index")

    machine = samples[samples["machine_consensus_label"].notna()]
    if not machine.empty:
        machine_v = machine["v_percent_machine_file"].astype(int)
        machine_temp = machine["temp_c_machine_file"].astype(int)
        if not (machine_v.to_numpy() == machine["v_percent"].to_numpy()).all():
            raise ValueError("Machine-label V percentages are not aligned by sample_index")
        if not (machine_temp.to_numpy() == machine["temp_c"].to_numpy()).all():
            raise ValueError("Machine-label temperatures are not aligned by sample_index")


def load_dataset(root: Path | None = None) -> NistDataset:
    raw_dir = raw_dataset_dir(root)
    theta, xrd = read_xrd(raw_dir)
    samples = read_composition_temperature(raw_dir)

    samples = samples.merge(read_human_labels(raw_dir), on="sample_index", how="left")
    samples = samples.merge(read_machine_labels(raw_dir), on="sample_index", how="left")
    samples = samples.merge(read_machine_loglik(raw_dir), on="sample_index", how="left")
    samples = samples.sort_values("sample_index").reset_index(drop=True)

    validate_alignment(theta, xrd, samples)
    return NistDataset(theta=theta, xrd=xrd, samples=samples)


def area_normalize_xrd(xrd: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    shifted = xrd.astype(np.float32) - np.nanmin(xrd, axis=1, keepdims=True)
    area = np.nansum(shifted, axis=1, keepdims=True)
    return shifted / np.maximum(area, eps)

