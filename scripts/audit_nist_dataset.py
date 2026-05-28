"""Audit the NIST MDS2-2301 diffraction dataset after download."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile


DATASET_ID = "nist_mds2_2301"
DATASET_DIR = Path("data/raw") / DATASET_ID


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + ord(char.upper()) - ord("A") + 1
    return index - 1


def read_xlsx_first_sheet(path: Path) -> list[list[str]]:
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("main:si", ns):
                shared_strings.append(
                    "".join(text.text or "" for text in item.findall(".//main:t", ns))
                )

        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall(".//main:sheetData/main:row", ns):
            values: list[str] = []
            for cell in row.findall("main:c", ns):
                ref = cell.attrib.get("r", "")
                while len(values) <= col_index(ref):
                    values.append("")
                value = cell.find("main:v", ns)
                raw = value.text if value is not None else ""
                if cell.attrib.get("t") == "s" and raw:
                    raw = shared_strings[int(raw)]
                values[col_index(ref)] = raw
            rows.append(values)
        return rows


def summarize_xrd(path: Path) -> dict[str, Any]:
    row_count = 0
    column_counts: Counter[int] = Counter()
    two_theta_min = None
    two_theta_max = None
    with path.open() as handle:
        for line in handle:
            values = line.rstrip("\n").split("\t")
            row_count += 1
            column_counts[len(values)] += 1
            if row_count == 1:
                two_theta = [float(value) for value in values]
                two_theta_min = min(two_theta)
                two_theta_max = max(two_theta)

    return {
        "rows_total": row_count,
        "spectra_rows": row_count - 1,
        "column_counts": dict(sorted(column_counts.items())),
        "two_theta_min": two_theta_min,
        "two_theta_max": two_theta_max,
    }


def read_composition_rows(path: Path) -> list[dict[str, int]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [{"V": int(row["V"]), "temp": int(row["temp"])} for row in reader]


def shannon_entropy(labels: list[int]) -> float:
    counts = Counter(labels)
    total = len(labels)
    return -sum((count / total) * math.log(count / total) for count in counts.values())


def summarize_human_labels(path: Path, composition_rows: list[dict[str, int]]) -> dict[str, Any]:
    rows = read_xlsx_first_sheet(path)
    header = rows[0]
    data_rows = rows[1:]
    labeler_columns = [idx for idx, name in enumerate(header) if name.startswith("HL")]

    entropies = []
    consensus_labels = []
    disagreeing_rows = 0
    label_counts: Counter[int] = Counter()
    aligned_rows = 0
    sample_indices = []

    for row in data_rows:
        labels = [int(float(row[idx])) for idx in labeler_columns]
        label_counts.update(labels)
        entropies.append(shannon_entropy(labels))
        consensus_labels.append(Counter(labels).most_common(1)[0][0])
        if len(set(labels)) > 1:
            disagreeing_rows += 1

        sample_index = int(float(row[0])) - 1
        sample_indices.append(sample_index)
        if 0 <= sample_index < len(composition_rows):
            human_v = int(float(row[2]))
            human_temp = int(float(row[3]))
            comp = composition_rows[sample_index]
            if human_v == comp["V"] and human_temp == comp["temp"]:
                aligned_rows += 1

    return {
        "rows": len(data_rows),
        "columns": header,
        "labeler_columns": [header[idx] for idx in labeler_columns],
        "label_counts": dict(sorted(label_counts.items())),
        "consensus_label_counts": dict(sorted(Counter(consensus_labels).items())),
        "disagreeing_rows": disagreeing_rows,
        "max_entropy": max(entropies),
        "mean_entropy": sum(entropies) / len(entropies),
        "sample_index_base": "one_based_in_workbook_zero_based_in_audit",
        "sample_index_min": min(sample_indices),
        "sample_index_max": max(sample_indices),
        "rows_aligned_to_composition_by_sample_index": aligned_rows,
    }


def summarize_csv_labels(path: Path, composition_rows: list[dict[str, int]]) -> dict[str, Any]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    header = list(rows[0].keys()) if rows else []
    sample_indices = [int(row[""]) for row in rows if row.get("") not in (None, "")]
    aligned_rows = 0
    for row in rows:
        sample_index = int(row[""])
        if 0 <= sample_index < len(composition_rows):
            comp = composition_rows[sample_index]
            row_v = float(row["V"])
            row_v_percent = int(round(row_v * 100)) if row_v <= 1 else int(round(row_v))
            if row_v_percent == comp["V"] and int(float(row["temp"])) == comp["temp"]:
                aligned_rows += 1
    return {
        "rows": len(rows),
        "columns": header,
        "sample_index_base": "zero_based",
        "sample_index_min": min(sample_indices) if sample_indices else None,
        "sample_index_max": max(sample_indices) if sample_indices else None,
        "rows_aligned_to_composition_by_sample_index": aligned_rows,
    }


def audit() -> dict[str, Any]:
    root = project_root()
    data_dir = root / DATASET_DIR
    composition_rows = read_composition_rows(
        data_dir / "VO2 - Nb2O3 Composition and temp Combiview.txt"
    )

    return {
        "dataset_id": DATASET_ID,
        "raw_data_dir": str(DATASET_DIR),
        "xrd": summarize_xrd(data_dir / "VO2 -Nb2O3 XRD Combiview.txt"),
        "composition_temperature": {
            "rows": len(composition_rows),
            "v_min": min(row["V"] for row in composition_rows),
            "v_max": max(row["V"] for row in composition_rows),
            "temps": dict(sorted(Counter(row["temp"] for row in composition_rows).items())),
        },
        "human_labels": summarize_human_labels(data_dir / "Human Labels.xlsx", composition_rows),
        "machine_labels": summarize_csv_labels(
            data_dir / "Compare ML Labels.csv", composition_rows
        ),
        "machine_loglik": summarize_csv_labels(
            data_dir / "cluster_assignment_loglik_all.csv", composition_rows
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manifests/nist_mds2_2301_audit.json"),
        help="Path for the JSON audit summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    summary = audit()
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
