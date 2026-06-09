"""Audit OpenCrystalData Kaggle datasets for event-native learning readiness."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


KAGGLE_LIST_URL = "https://www.kaggle.com/api/v1/datasets/list?user=opencrystaldata"
KAGGLE_VIEW_URL = "https://www.kaggle.com/api/v1/datasets/view/{ref}"
ORG_URL = "https://www.kaggle.com/opencrystaldata/datasets"
PAPER_URL = "https://doi.org/10.1016/j.dche.2024.100150"
DEFAULT_OUTPUT = Path("data/manifests/opencrystaldata_audit.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def fetch_json(url: str) -> object:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "materials-event-modeling-audit/0.1",
            "Accept": "application/json,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def keyword_hits(text: str, keywords: list[str]) -> dict[str, int]:
    lowered = text.lower()
    return {keyword: lowered.count(keyword.lower()) for keyword in keywords}


def infer_problem_types(description: str) -> list[str]:
    text = description.lower()
    candidates = [
        "image classification",
        "anomaly detection",
        "object detection",
        "instance segmentation",
        "image segmentation",
        "segmentation",
        "classification",
    ]
    return sorted({candidate for candidate in candidates if candidate in text})


def infer_event_signals(description: str) -> dict[str, bool]:
    text = description.lower()
    return {
        "has_in_situ_images": "in-situ" in text or "in situ" in text,
        "has_raw_images": "raw image" in text or "raw images" in text,
        "has_cropped_or_processed_images": "cropped" in text or "processed" in text,
        "has_conditions": any(
            word in text
            for word in [
                "concentration",
                "solid loading",
                "batch",
                "slurry",
                "seeded",
                "mother liquor",
            ]
        ),
        "has_other_measurements": any(
            word in text
            for word in [
                "offline",
                "off-line",
                "particle size distribution",
                "chord length",
                "cld",
                "ground-truth",
            ]
        ),
        "mentions_batches": "batch" in text,
        "mentions_incremental_addition": "increment" in text or "increasing" in text,
        "mentions_time_sequence": "time" in text or "video" in text or "sequence" in text,
        "mentions_event_manifest": "event" in text and "manifest" in text,
        "mentions_failed_or_ambiguous": "failed" in text or "ambiguous" in text,
        "mentions_provenance": "session" in text or "run order" in text or "operator" in text,
    }


def extract_number_of_images(description: str) -> str | None:
    match = re.search(r"Number of images\|\s*([^\n|]+)", description)
    if match:
        return match.group(1).strip()
    match = re.search(r"Number of images\|\\t([^\n|]+)", description)
    if match:
        return match.group(1).strip()
    return None


def summarize_dataset(view: dict) -> dict[str, object]:
    description = view.get("description") or view.get("descriptionNullable") or ""
    signals = infer_event_signals(description)
    keyword_counts = keyword_hits(
        description,
        [
            "in-situ",
            "raw",
            "cropped",
            "processed",
            "classification",
            "segmentation",
            "object detection",
            "anomaly detection",
            "concentration",
            "solid loading",
            "batch",
            "particle size distribution",
            "chord length",
            "ground-truth",
            "offline",
            "time",
            "sequence",
            "event",
            "session",
            "failed",
            "ambiguous",
        ],
    )
    return {
        "ref": view.get("ref"),
        "title": view.get("title"),
        "subtitle": view.get("subtitle"),
        "url": f"https://www.kaggle.com/datasets/{view.get('ref')}",
        "size_bytes": view.get("totalBytes"),
        "license": view.get("licenseName"),
        "last_updated": view.get("lastUpdated"),
        "download_count": view.get("downloadCount"),
        "usability_rating": view.get("usabilityRating"),
        "problem_types": infer_problem_types(description),
        "number_of_images_text": extract_number_of_images(description),
        "event_signals": signals,
        "keyword_counts": keyword_counts,
        "description_excerpt": description[:1600],
    }


def audit_opencrystaldata() -> dict[str, object]:
    listed = fetch_json(KAGGLE_LIST_URL)
    if not isinstance(listed, list):
        raise ValueError("Expected Kaggle list API to return a list.")

    summaries = []
    for item in sorted(listed, key=lambda row: row.get("ref", "")):
        ref = item["ref"]
        view = fetch_json(KAGGLE_VIEW_URL.format(ref=ref))
        if not isinstance(view, dict):
            raise ValueError(f"Expected Kaggle view API to return an object for {ref}")
        summaries.append(summarize_dataset(view))

    total_size = sum(dataset.get("size_bytes") or 0 for dataset in summaries)
    all_text = "\n".join(dataset["description_excerpt"] for dataset in summaries).lower()
    event_native_readiness = {
        "has_programmatic_metadata": True,
        "dataset_count": len(summaries),
        "has_in_situ_images": any(d["event_signals"]["has_in_situ_images"] for d in summaries),
        "has_raw_images": any(d["event_signals"]["has_raw_images"] for d in summaries),
        "has_conditions": any(d["event_signals"]["has_conditions"] for d in summaries),
        "has_other_measurements": any(
            d["event_signals"]["has_other_measurements"] for d in summaries
        ),
        "has_batches_or_incremental_process": any(
            d["event_signals"]["mentions_batches"]
            or d["event_signals"]["mentions_incremental_addition"]
            for d in summaries
        ),
        "has_machine_readable_event_manifest_from_metadata": False,
        "has_time_sequence_from_metadata": "time" in all_text or "sequence" in all_text,
        "has_failed_or_ambiguous_attempts_from_metadata": False,
        "has_provenance_session_run_order_from_metadata": False,
        "primary_framing_is_image_analysis": all(
            bool(dataset["problem_types"]) for dataset in summaries
        ),
        "can_define_event_forecast_from_metadata_only": False,
        "can_define_image_task_from_metadata": True,
    }

    preliminary_verdict = (
        "OpenCrystalData is much more programmatically inspectable than Dryad and is useful "
        "for image-analysis baselines. It preserves in-situ images, some process conditions, "
        "and auxiliary measurements. But the public metadata frames the datasets as image "
        "classification, segmentation, object-detection, anomaly-detection, or particle-size "
        "tasks. It does not expose an event manifest, time-ordered traces, failed/ambiguous "
        "attempts, or session/run-order provenance at the metadata level."
    )

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "opencrystaldata_event_native_audit",
        "source_url": ORG_URL,
        "paper_url": PAPER_URL,
        "kaggle_list_url": KAGGLE_LIST_URL,
        "hypothesis": (
            "OpenCrystalData should be more ML-ready than Durham or Dryad, but likely more "
            "image-analysis-ready than event-learning-ready."
        ),
        "dataset_count": len(summaries),
        "total_size_bytes": total_size,
        "datasets": summaries,
        "event_native_readiness": event_native_readiness,
        "preliminary_verdict": preliminary_verdict,
        "next_decision": (
            "Use OpenCrystalData as a comparison case for image-task-ready public data. "
            "Do not treat it as the main event-native benchmark unless internal file "
            "inspection reveals time/order/session structure. The optional concrete next "
            "step is to download the smallest 448 MB EasyViewer dataset and inspect whether "
            "its files can be reorganized into condition-indexed events."
        ),
    }


def main() -> None:
    args = parse_args()
    audit = audit_opencrystaldata()
    repo_root = Path(__file__).resolve().parents[1]
    output = args.output if args.output.is_absolute() else repo_root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
