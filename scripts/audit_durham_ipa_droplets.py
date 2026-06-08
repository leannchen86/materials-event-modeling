"""Audit the Durham IPA droplet dataset for event-native learning readiness."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


DEFAULT_ARCHIVE = Path("data/raw/durham_ipa_droplets/ipa_droplets_in_moist_air.zip")
DEFAULT_OUTPUT = Path("data/manifests/durham_ipa_droplet_audit.json")

VIDEO_RE = re.compile(
    r"V(?P<movie_id>\d+)-R[hH](?P<humidity_percent>\d+)-"
    r"(?P<nozzle_um>\d+)umNozzle-on(?P<substrate>[^-]+)"
    r"(?P<particle_suffix>-Particles)?-compressed\.avi$"
)

WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
XLSX_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=DEFAULT_ARCHIVE,
        help="Downloaded Durham IPA droplet ZIP archive.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def read_docx_paragraphs(zf: ZipFile, member: str) -> list[str]:
    docx_bytes = zf.read(member)
    with tempfile.NamedTemporaryFile(suffix=".docx") as tmp:
        tmp.write(docx_bytes)
        tmp.flush()
        with ZipFile(tmp.name) as docx:
            xml = docx.read("word/document.xml")

    root = ET.fromstring(xml)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NS))
        text = text.strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def read_xlsx_sheets(zf: ZipFile, member: str) -> list[dict[str, object]]:
    workbook_bytes = zf.read(member)
    with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
        tmp.write(workbook_bytes)
        tmp.flush()
        with ZipFile(tmp.name) as xlsx:
            workbook = ET.fromstring(xlsx.read("xl/workbook.xml"))
            rels = ET.fromstring(xlsx.read("xl/_rels/workbook.xml.rels"))
            relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
            sheets: list[dict[str, object]] = []
            for sheet in workbook.findall(".//main:sheet", XLSX_NS):
                title = sheet.attrib["name"]
                rid = sheet.attrib[
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                ]
                target = relmap[rid]
                target_path = "xl/" + target if not target.startswith("/") else target[1:]
                xml = ET.fromstring(xlsx.read(target_path))
                dimension = xml.find("main:dimension", XLSX_NS)
                rows = xml.findall(".//main:row", XLSX_NS)
                sheets.append(
                    {
                        "name": title,
                        "dimension": dimension.attrib.get("ref") if dimension is not None else None,
                        "row_count": len(rows),
                    }
                )
    return sheets


def parse_video_conditions(member: str) -> dict[str, object]:
    name = Path(member).name
    match = VIDEO_RE.match(name)
    if match is None:
        return {"parse_status": "unparsed", "filename": name}

    groups = match.groupdict()
    return {
        "parse_status": "parsed",
        "movie_id": int(groups["movie_id"]),
        "relative_humidity_percent": float(groups["humidity_percent"]),
        "nozzle_um": float(groups["nozzle_um"]),
        "substrate": groups["substrate"],
        "trace_particles": groups["particle_suffix"] is not None,
    }


def probe_video(zf: ZipFile, member: str) -> dict[str, object]:
    suffix = Path(member).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(zf.read(member))
        tmp.flush()
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,nb_frames,duration",
            "-of",
            "json",
            tmp.name,
        ]
        result = subprocess.check_output(cmd)
    stream = json.loads(result).get("streams", [{}])[0]
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "avg_frame_rate": stream.get("avg_frame_rate"),
        "duration_s": float(stream["duration"]) if stream.get("duration") else None,
        "frame_count": int(stream["nb_frames"]) if stream.get("nb_frames") else None,
    }


def audit_archive(archive: Path) -> dict[str, object]:
    with ZipFile(archive) as zf:
        members = zf.infolist()
        names = [member.filename for member in members]
        videos = [name for name in names if name.lower().endswith(".avi")]
        spreadsheets = [name for name in names if name.lower().endswith(".xlsx")]
        docx_files = [name for name in names if name.lower().endswith(".docx")]

        video_records = []
        for member in sorted(videos):
            info = zf.getinfo(member)
            record = {
                "file": member,
                "size_bytes": info.file_size,
                "conditions_from_filename": parse_video_conditions(member),
                "video": probe_video(zf, member),
            }
            video_records.append(record)

        spreadsheet_records = []
        for member in sorted(spreadsheets):
            info = zf.getinfo(member)
            spreadsheet_records.append(
                {
                    "file": member,
                    "size_bytes": info.file_size,
                    "sheets": read_xlsx_sheets(zf, member),
                }
            )

        readme_paragraphs = read_docx_paragraphs(zf, docx_files[0]) if docx_files else []

    under_request = [
        paragraph
        for paragraph in readme_paragraphs
        if "under request" in paragraph.lower() or "provided under request" in paragraph.lower()
    ]

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "durham_ipa_droplet_event_audit",
        "source_url": "https://collections.durham.ac.uk/files/r12801pg44n",
        "archive": str(archive),
        "archive_file_count": len(members),
        "video_count": len(video_records),
        "spreadsheet_count": len(spreadsheet_records),
        "docx_count": len(docx_files),
        "videos": video_records,
        "spreadsheets": spreadsheet_records,
        "readme_paragraphs": readme_paragraphs,
        "under_request_notes": under_request,
        "event_native_readiness": {
            "has_time_indexed_raw_observations": len(video_records) > 0,
            "has_condition_fields": all(
                video["conditions_from_filename"].get("parse_status") == "parsed"
                for video in video_records
            ),
            "has_machine_readable_event_manifest": False,
            "has_obvious_replicate_groups": False,
            "has_failed_or_ambiguous_attempt_log": False,
            "has_operator_session_or_run_order_provenance": False,
            "has_complete_released_trace_set": len(under_request) == 0,
            "can_smoke_test_early_trace_prediction": len(video_records) >= 5,
            "can_support_decisive_event_benchmark": False,
        },
        "preliminary_verdict": (
            "Useful first event-trace smoke test, but not a decisive event-native "
            "benchmark because repeats, complete released traces, failed/ambiguous "
            "attempts, and provenance are incomplete."
        ),
    }


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    archive = args.archive if args.archive.is_absolute() else repo_root / args.archive
    if not archive.exists():
        raise FileNotFoundError(
            f"Archive not found: {archive}. Download it from "
            "https://collections.durham.ac.uk/files/r12801pg44n"
        )

    audit = audit_archive(archive)
    output = args.output if args.output.is_absolute() else repo_root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
