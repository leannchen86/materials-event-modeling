"""Download public datasets used by the computational prototype."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


NIST_MDS2_2301_METADATA_URL = "https://data.nist.gov/od/id/mds2-2301"
OPXRD_CONCEPT_RECORD_ID = "14254270"
OPXRD_METADATA_URL = f"https://zenodo.org/api/records/{OPXRD_CONCEPT_RECORD_ID}"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json_url(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def hash_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    return hash_file(path, "sha256")


def download_file(url: str, destination: Path, expected_size: int | None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")

    with urllib.request.urlopen(url, timeout=120) as response, tmp.open("wb") as handle:
        downloaded = 0
        last_reported = -1
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            if expected_size:
                downloaded += len(chunk)
                percent = int(downloaded * 100 / expected_size)
                if percent >= last_reported + 5:
                    print(f"  {percent:3d}% {destination.name}", file=sys.stderr)
                    last_reported = percent

    if expected_size is not None and tmp.stat().st_size != expected_size:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"Size mismatch for {destination.name}: expected {expected_size}, "
            f"got {tmp.stat().st_size}"
        )

    tmp.replace(destination)


def nist_downloadable_components(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    components = []
    for component in metadata.get("components", []):
        filepath = component.get("filepath", "")
        if not component.get("downloadURL") or filepath.endswith(".sha256"):
            continue
        components.append(component)
    return sorted(components, key=lambda item: item["filepath"])


def download_nist_mds2_2301(force: bool) -> Path:
    root = project_root()
    raw_dir = root / "data" / "raw" / "nist_mds2_2301"
    manifest_path = root / "data" / "manifests" / "nist_mds2_2301_files.json"
    metadata = load_json_url(NIST_MDS2_2301_METADATA_URL)
    files = []

    for component in nist_downloadable_components(metadata):
        filename = component["filepath"]
        destination = raw_dir / filename
        expected_size = component.get("size")
        expected_sha256 = component.get("checksum", {}).get("hash")

        if force or not destination.exists():
            print(f"Downloading {filename}", file=sys.stderr)
            download_file(component["downloadURL"], destination, expected_size)
        else:
            print(f"Using existing {filename}", file=sys.stderr)

        actual_sha256 = sha256_file(destination)
        if expected_sha256 and actual_sha256 != expected_sha256:
            raise RuntimeError(
                f"Checksum mismatch for {filename}: expected {expected_sha256}, "
                f"got {actual_sha256}"
            )

        files.append(
            {
                "filename": filename,
                "local_path": str(destination.relative_to(root)),
                "download_url": component["downloadURL"],
                "media_type": component.get("mediaType"),
                "size_bytes": destination.stat().st_size,
                "sha256": actual_sha256,
            }
        )

    manifest = {
        "dataset_id": "nist_mds2_2301",
        "title": metadata.get("title"),
        "doi": metadata.get("doi"),
        "landing_page": metadata.get("landingPage"),
        "metadata_url": NIST_MDS2_2301_METADATA_URL,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {manifest_path.relative_to(root)}", file=sys.stderr)
    return manifest_path


def download_opxrd(force: bool, metadata_only: bool) -> Path:
    root = project_root()
    raw_dir = root / "data" / "raw" / "opxrd"
    manifest_path = root / "data" / "manifests" / "opxrd_files.json"
    metadata = load_json_url(OPXRD_METADATA_URL)
    files = []

    for file_metadata in sorted(metadata.get("files", []), key=lambda item: item["key"]):
        filename = file_metadata["key"]
        destination = raw_dir / filename
        expected_size = file_metadata.get("size")
        checksum = file_metadata.get("checksum")
        checksum_algorithm = None
        expected_checksum = None
        if checksum and ":" in checksum:
            checksum_algorithm, expected_checksum = checksum.split(":", 1)

        if metadata_only:
            print(f"Metadata only for {filename}", file=sys.stderr)
        elif force or not destination.exists():
            print(f"Downloading {filename}", file=sys.stderr)
            download_file(file_metadata["links"]["self"], destination, expected_size)
        else:
            print(f"Using existing {filename}", file=sys.stderr)

        actual_checksum = None
        local_size = None
        if destination.exists():
            local_size = destination.stat().st_size
            if checksum_algorithm:
                actual_checksum = hash_file(destination, checksum_algorithm)
                if expected_checksum and actual_checksum != expected_checksum:
                    raise RuntimeError(
                        f"Checksum mismatch for {filename}: expected {expected_checksum}, "
                        f"got {actual_checksum}"
                    )

        files.append(
            {
                "filename": filename,
                "local_path": str(destination.relative_to(root)),
                "download_url": file_metadata["links"]["self"],
                "size_bytes": expected_size,
                "local_size_bytes": local_size,
                "checksum_algorithm": checksum_algorithm,
                "expected_checksum": expected_checksum,
                "actual_checksum": actual_checksum,
                "downloaded": destination.exists(),
            }
        )

    manifest = {
        "dataset_id": "opxrd",
        "title": metadata.get("metadata", {}).get("title"),
        "doi": metadata.get("doi"),
        "conceptdoi": metadata.get("conceptdoi"),
        "record_id": metadata.get("id"),
        "concept_record_id": metadata.get("conceptrecid"),
        "metadata_url": OPXRD_METADATA_URL,
        "landing_page": metadata.get("links", {}).get("html"),
        "publication_date": metadata.get("metadata", {}).get("publication_date"),
        "license": metadata.get("metadata", {}).get("license", {}).get("id"),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "metadata_only": metadata_only,
        "files": files,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {manifest_path.relative_to(root)}", file=sys.stderr)
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset",
        choices=["nist_mds2_2301", "opxrd"],
        help="Dataset identifier to download.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download files even if they already exist.",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Write source metadata without downloading large files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dataset == "nist_mds2_2301":
        download_nist_mds2_2301(force=args.force)
        return
    if args.dataset == "opxrd":
        download_opxrd(force=args.force, metadata_only=args.metadata_only)
        return
    raise AssertionError(f"Unhandled dataset: {args.dataset}")


if __name__ == "__main__":
    main()
