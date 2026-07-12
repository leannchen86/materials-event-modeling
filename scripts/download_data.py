"""Download the opXRD archive and record its source metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

    actual_size = tmp.stat().st_size
    if expected_size is not None and actual_size != expected_size:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"Size mismatch for {destination.name}: expected {expected_size}, "
            f"got {actual_size}"
        )

    tmp.replace(destination)


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
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"Wrote {manifest_path.relative_to(root)}", file=sys.stderr)
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
    download_opxrd(force=args.force, metadata_only=args.metadata_only)


if __name__ == "__main__":
    main()
