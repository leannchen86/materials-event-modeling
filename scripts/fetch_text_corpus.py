"""Fetch a small, multi-source text corpus that mirrors an LLM pretraining mix.

Pulls a few hundred documents each from genuinely distinct pretraining sources — web
(FineWeb / CommonCrawl), scientific abstracts (arXiv), encyclopedic (Wikipedia), and
code (The Stack) — and writes them to a JSONL with a ``source`` label per document:

    {"text": "...", "source": "web", "doc_id": "web-0"}

The point is downstream: feed this to the provenance-leakage audit and show that the
*incidental* ``source`` label is trivially recoverable from document features — the text
analog of "models learn the lab", and the reason a "balanced" pretraining mix can still
let a model shortcut on source identity (and why quality filters / dedup must be
source-aware).

Network only; no extra dependencies (urllib + json + xml). Each source degrades
gracefully — if one endpoint is unreachable, it is skipped and the rest proceed.

    .venv/bin/python scripts/fetch_text_corpus.py --per-source 250
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

UA = {"User-Agent": "provenance-leakage-audit/0.1 (research; contact via repo)"}
HF_ROWS = "https://datasets-server.huggingface.co/rows"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _get(url: str, timeout: int = 20) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def _clean(text: str, min_chars: int, max_chars: int) -> str | None:
    text = " ".join(str(text).split())
    if len(text) < min_chars:
        return None
    return text[:max_chars]


def fetch_hf_rows(
    dataset: str, config: str, split: str, *, n: int, min_chars: int, max_chars: int
) -> list[str]:
    """Page the HuggingFace datasets-server /rows API (max 100 rows/call)."""
    texts: list[str] = []
    offset = 0
    text_keys = ("text", "content", "code", "document", "abstract")
    while len(texts) < n:
        params = urllib.parse.urlencode(
            {"dataset": dataset, "config": config, "split": split,
             "offset": offset, "length": 100}
        )
        rows = json.loads(_get(f"{HF_ROWS}?{params}")).get("rows", [])
        if not rows:
            break
        for entry in rows:
            row = entry.get("row", {})
            value = next((row[k] for k in text_keys if isinstance(row.get(k), str)), None)
            if value is None:  # fall back to the longest string field
                strings = [v for v in row.values() if isinstance(v, str)]
                value = max(strings, key=len) if strings else None
            cleaned = _clean(value, min_chars, max_chars) if value else None
            if cleaned:
                texts.append(cleaned)
        offset += 100
        time.sleep(0.2)
    return texts[:n]


def fetch_arxiv(n: int, min_chars: int, max_chars: int) -> list[str]:
    """Scientific abstracts via the arXiv Atom API."""
    ns = {"a": "http://www.w3.org/2005/Atom"}
    texts: list[str] = []
    queries = ["cat:cond-mat.supr-con", "cat:cs.LG", "cat:physics.chem-ph", "cat:math.NT"]
    for q in queries:
        if len(texts) >= n:
            break
        url = (
            "http://export.arxiv.org/api/query?"
            + urllib.parse.urlencode(
                {"search_query": q, "start": 0, "max_results": max(20, n // len(queries) + 5)}
            )
        )
        feed = ET.fromstring(_get(url))
        for entry in feed.findall("a:entry", ns):
            summary = entry.findtext("a:summary", default="", namespaces=ns)
            cleaned = _clean(summary, min_chars, max_chars)
            if cleaned:
                texts.append(cleaned)
        time.sleep(1.0)  # arXiv asks for >=3s; we keep it polite across few calls
    return texts[:n]


SOURCES = {
    "web": lambda n, lo, hi: fetch_hf_rows(
        "HuggingFaceFW/fineweb", "sample-10BT", "train", n=n, min_chars=lo, max_chars=hi
    ),
    "wikipedia": lambda n, lo, hi: fetch_hf_rows(
        "wikimedia/wikipedia", "20231101.en", "train", n=n, min_chars=lo, max_chars=hi
    ),
    "code": lambda n, lo, hi: fetch_hf_rows(
        "Nan-Do/code-search-net-python", "default", "train", n=n, min_chars=lo, max_chars=hi
    ),
    "science": fetch_arxiv,
}


def run(args: argparse.Namespace) -> None:
    out = project_root() / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    summary: dict[str, int] = {}
    for source, fetch in SOURCES.items():
        try:
            texts = fetch(args.per_source, args.min_chars, args.max_chars)
        except Exception as exc:  # graceful per-source degradation
            print(f"  [skip] {source}: {type(exc).__name__}: {str(exc)[:80]}")
            summary[source] = 0
            continue
        summary[source] = len(texts)
        print(f"  [ok]   {source}: {len(texts)} docs")
        for i, text in enumerate(texts):
            records.append({"doc_id": f"{source}-{i}", "source": source, "text": text})

    live = [s for s, c in summary.items() if c > 0]
    if len(live) < 2:
        raise RuntimeError(f"Need >=2 sources; only got {live}. Check network access.")

    with out.open("w") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    print(f"\n  wrote {len(records)} docs across {len(live)} sources -> "
          f"{out.relative_to(project_root())}")
    print(f"  per-source: {summary}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--per-source", type=int, default=250)
    p.add_argument("--min-chars", type=int, default=200)
    p.add_argument("--max-chars", type=int, default=20000)
    p.add_argument("--output", type=Path, default=Path("data/raw/text_corpus/mix.jsonl"))
    return p.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
