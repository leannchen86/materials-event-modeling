"""Audit the Dryad gelation active-learning dataset for event-native readiness."""

from __future__ import annotations

import argparse
import html
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATASET_URL = "https://datadryad.org/dataset/doi%3A10.5061/dryad.8w9ghx3xn"
DATASET_API_URL = "https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.8w9ghx3xn"
VERSION_API_URL = "https://datadryad.org/api/v2/versions/338756"
FILES_API_URL = "https://datadryad.org/api/v2/versions/338756/files"
DEFAULT_OUTPUT = Path("data/manifests/dryad_gelation_audit.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check-downloads",
        action="store_true",
        help="Probe individual download URLs without downloading file bodies.",
    )
    return parser.parse_args()


def fetch_text(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "materials-event-modeling-audit/0.1",
            "Accept": "text/html,application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url: str) -> dict:
    return json.loads(fetch_text(url))


def probe_url(url: str, timeout: int = 15) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "materials-event-modeling-audit/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "url": url,
                "status": response.status,
                "content_length": response.headers.get("Content-Length"),
                "accept_ranges": response.headers.get("Accept-Ranges"),
                "content_type": response.headers.get("Content-Type"),
            }
    except urllib.error.HTTPError as exc:
        return {
            "url": url,
            "status": exc.code,
            "content_length": exc.headers.get("Content-Length"),
            "accept_ranges": exc.headers.get("Accept-Ranges"),
            "content_type": exc.headers.get("Content-Type"),
        }
    except urllib.error.URLError as exc:
        return {"url": url, "status": "url_error", "reason": str(exc.reason)}


def extract_readme_text(page_html: str) -> str:
    match = re.search(r'<div id="readme-sec"[^>]*>(.*?)</div>', page_html, flags=re.S)
    if match is None:
        return ""
    block = match.group(1)
    block = re.sub(r"<br\s*/?>", "\n", block)
    block = re.sub(r"</(p|li|h[1-6]|ul|ol|hr)>", "\n", block)
    block = re.sub(r"<[^>]+>", "", block)
    block = html.unescape(block)
    lines = [line.strip() for line in block.splitlines()]
    return "\n".join(line for line in lines if line)


def keyword_hits(text: str, keywords: list[str]) -> dict[str, int]:
    lowered = text.lower()
    return {keyword: lowered.count(keyword.lower()) for keyword in keywords}


def audit_dataset(check_downloads: bool) -> dict[str, object]:
    dataset = fetch_json(DATASET_API_URL)
    version = fetch_json(VERSION_API_URL)
    files_json = fetch_json(FILES_API_URL)
    page_html = fetch_text(DATASET_URL)
    readme = extract_readme_text(page_html)

    files = files_json.get("_embedded", {}).get("stash:files", [])
    file_records = []
    for file_record in files:
        links = file_record.get("_links", {})
        download_path = links.get("stash:download", {}).get("href")
        download_url = f"https://datadryad.org{download_path}" if download_path else None
        record = {
            "path": file_record.get("path"),
            "size": file_record.get("size"),
            "mime_type": file_record.get("mimeType"),
            "digest_type": file_record.get("digestType"),
            "digest": file_record.get("digest"),
            "download_url": download_url,
        }
        if check_downloads and download_url:
            record["download_probe"] = probe_url(download_url)
        file_records.append(record)

    readme_keywords = keyword_hits(
        readme,
        [
            "raw data",
            "processed data",
            "figure",
            "time-dependent",
            "microrheology",
            "rheology",
            "uv-vis",
            "gaussian process",
            "gpr",
            "active learning",
            "pH",
            "temperature",
            "concentration",
            "README",
        ],
    )

    event_native_readiness = {
        "has_public_file_metadata": len(file_records) > 0,
        "has_large_data_archive": any(
            (record.get("path") or "").lower().endswith(".zip") and record.get("size", 0) > 1e9
            for record in file_records
        ),
        "has_readme_without_full_download": bool(readme),
        "claims_raw_data_where_applicable": "raw data" in readme.lower(),
        "claims_processed_csvs": "processed" in readme.lower() and "csv" in readme.lower(),
        "claims_scripts_for_modeling": "gaussian process" in readme.lower()
        or "gpr" in readme.lower(),
        "is_organized_by_figure": "organized by figure" in readme.lower(),
        "has_time_dependent_measurements": "time-dependent" in readme.lower(),
        "has_active_learning_context": "active learning" in readme.lower(),
        "has_machine_readable_event_manifest": False,
        "has_obvious_replicate_groups_from_top_level_metadata": False,
        "can_audit_internal_files_without_large_download": False,
        "can_define_benchmark_from_top_level_metadata_only": False,
    }

    preliminary_verdict = (
        "Richer than Durham at the study level because it includes active learning, "
        "process variables, time-dependent measurements, raw/processed data claims, and "
        "modeling scripts. But the public top-level structure is still paper-shaped: one "
        "large archive plus README, organized by figures rather than event records. A "
        "decisive event-native audit requires either inspecting the 5.14 GB archive or "
        "getting a file manifest / subset from the authors."
    )

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "dryad_gelation_event_native_audit",
        "source_url": DATASET_URL,
        "dataset_api_url": DATASET_API_URL,
        "version_api_url": VERSION_API_URL,
        "files_api_url": FILES_API_URL,
        "title": dataset.get("title"),
        "doi": dataset.get("identifier"),
        "publication_date": dataset.get("publicationDate"),
        "license": dataset.get("license"),
        "storage_size": dataset.get("storageSize"),
        "keywords": dataset.get("keywords", []),
        "related_works": dataset.get("relatedWorks", []),
        "version_number": version.get("versionNumber"),
        "file_count": files_json.get("count"),
        "files": file_records,
        "readme_excerpt": readme[:1800],
        "readme_keyword_hits": readme_keywords,
        "hypothesis": (
            "Dryad gelation should be richer than Durham because it comes from an "
            "active-learning experimental workflow with process and response variables, "
            "but it may still be organized around publication figures rather than reusable "
            "material-making event records."
        ),
        "event_native_readiness": event_native_readiness,
        "preliminary_verdict": preliminary_verdict,
        "next_decision": (
            "Do not download the full 5.14 GB archive by default. First decide whether to "
            "request or obtain a file manifest/subset. If the internal archive contains "
            "per-condition raw traces plus repeated conditions, run a small event benchmark; "
            "if it only contains figure-specific processed outputs, record it as another "
            "paper-shaped-data ceiling."
        ),
    }


def main() -> None:
    args = parse_args()
    audit = audit_dataset(check_downloads=args.check_downloads)
    repo_root = Path(__file__).resolve().parents[1]
    output = args.output if args.output.is_absolute() else repo_root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
