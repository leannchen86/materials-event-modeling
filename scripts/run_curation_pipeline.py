"""End-to-end pretraining-corpus curation pipeline -> versioned data card.

Runs the canonical stages on the multi-source text mix and emits a machine-readable data
card (per-stage removals, per-source distribution before/after, thresholds, content hash):

    exact dedup -> MinHash near-dedup -> heuristic quality filter -> decontamination

By default it injects a controlled set of duplicates, near-duplicates, low-quality docs,
and benchmark-contaminated docs so each stage visibly fires and can be scored against
ground truth (a self-check). Pass --no-inject to curate the raw corpus only.

    .venv/bin/python scripts/run_curation_pipeline.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from materials_event_modeling.curate import (
    exact_dedup,
    fuzzy_contamination,
    minhash_dedup,
    ngram_contamination,
    quality_filter,
)
from materials_event_modeling.curate.demo_eval import EVAL_ITEMS


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_corpus(corpus: Path) -> list[dict]:
    path = project_root() / corpus
    if not path.exists():
        raise FileNotFoundError(
            f"Corpus {corpus} missing. Build it with scripts/fetch_text_corpus.py."
        )
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def inject(records: list[dict], rng: random.Random) -> tuple[list[dict], dict[str, str]]:
    """Plant labeled duplicates / near-dups / junk / contamination. Returns recs + truth."""
    recs = list(records)
    truth: dict[str, str] = {}
    prose = [r for r in records if r["source"] in ("web", "wikipedia") and len(r["text"]) > 400]

    for i, base in enumerate(rng.sample(prose, min(10, len(prose)))):  # exact duplicates
        did = f"inject_dup_exact_{i}"
        recs.append({"doc_id": did, "source": base["source"], "text": base["text"]})
        truth[did] = "exact_dup"
    for i, base in enumerate(rng.sample(prose, min(10, len(prose)))):  # near-duplicates
        did = f"inject_dup_near_{i}"
        recs.append({"doc_id": did, "source": base["source"],
                     "text": base["text"] + " This copy was edited slightly for clarity."})
        truth[did] = "near_dup"
    junk = ["CLICK HERE !!! " * 25, "$$$ " * 60, "ok", "buy now buy now buy now " * 30,
            "lorem " * 5, "###### " * 40]
    for i, text in enumerate(junk):  # low quality
        did = f"inject_lowq_{i}"
        recs.append({"doc_id": did, "source": "web", "text": text})
        truth[did] = "low_quality"
    # benchmark contamination: hide a verbatim eval item inside a normal-length doc. Each
    # gets DISTINCT padding (so it is not a mutual near-duplicate and survives dedup +
    # quality) and must therefore be caught by the decontamination stage itself.
    fillers = [
        "A reader emailed this in asking for a careful walkthrough of the solution.",
        "Someone posted the following on the class discussion board this afternoon.",
        "During the weekly tutoring session a student raised this exact question.",
        "This appeared on a flashcard a friend was using to revise for an exam.",
        "An old textbook in the library margin had scribbled this very prompt.",
        "A podcast host read this out as a challenge for listeners to try at home.",
        "The quiz night organizer slipped this one into the science round again.",
        "My younger cousin asked me this while we were cooking dinner together.",
        "A colleague mentioned it over coffee as a puzzle that had stumped her team.",
        "It showed up in an online course forum with a long thread of replies below.",
        "Someone chalked this on the cafe blackboard under the menu specials today.",
        "A travel companion posed it to pass the time on a very long train ride north.",
    ]
    for i, (eid, text) in enumerate(EVAL_ITEMS.items()):
        did = f"inject_contam_{i}"
        lead, tail = fillers[i % len(fillers)], fillers[(i + 5) % len(fillers)]
        body = (f"{lead} {lead} The question was: {text} {tail} Several people then "
                f"shared how they reasoned about it and what answer they reached. {tail}")
        recs.append({"doc_id": did, "source": "web", "text": body})
        truth[did] = "contamination"
    return recs, truth


def source_counts(recs: list[dict], ids: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in recs:
        if r["doc_id"] in ids:
            counts[r["source"]] = counts.get(r["source"], 0) + 1
    return dict(sorted(counts.items()))


def run(args: argparse.Namespace) -> dict[str, Any]:
    records = load_corpus(args.corpus)
    truth: dict[str, str] = {}
    if not args.no_inject:
        records, truth = inject(records, random.Random(args.seed))
    by_id = {r["doc_id"]: r["text"] for r in records}

    def as_docs(ids: list[str]) -> list[tuple[str, str]]:
        return [(i, by_id[i]) for i in ids]

    alive = [r["doc_id"] for r in records]
    stages: list[dict[str, Any]] = []

    # 1. exact dedup
    s1 = exact_dedup(as_docs(alive))
    removed_exact = {r["doc_id"] for r in s1["removed"]}
    after1 = [i for i in alive if i not in removed_exact]
    stages.append({"stage": "exact_dedup", "input": len(alive),
                   "removed": s1["removed_count"], "output": len(after1)})

    # 2. minhash near-dedup
    s2 = minhash_dedup(as_docs(after1), num_perm=args.num_perm, bands=args.bands,
                       threshold=args.minhash_threshold, seed=args.seed)
    removed_near = {r["doc_id"] for r in s2["removed"]}
    after2 = [i for i in after1 if i not in removed_near]
    stages.append({"stage": "minhash_dedup", "input": len(after1),
                   "removed": s2["removed_count"], "output": len(after2),
                   "duplicate_clusters": len(s2["duplicate_clusters"])})

    # 3. quality filter
    s3 = quality_filter(as_docs(after2))
    removed_quality = {r["doc_id"] for r in s3["removed"]}
    after3 = [i for i in after2 if i not in removed_quality]
    stages.append({"stage": "quality_filter", "input": len(after2),
                   "removed": s3["removed_count"], "output": len(after3),
                   "removed_by_rule": s3["removed_by_rule"]})

    # 4. decontamination (n-gram + fuzzy)
    ng = ngram_contamination(as_docs(after3), EVAL_ITEMS, n=args.ngram)
    fz = fuzzy_contamination(as_docs(after3), EVAL_ITEMS, threshold=args.fuzzy_threshold)
    removed_contam = set(ng["flagged_doc_ids"]) | set(fz["flagged_doc_ids"])
    after4 = [i for i in after3 if i not in removed_contam]
    stages.append({"stage": "decontamination", "input": len(after3),
                   "removed": len(removed_contam), "output": len(after4),
                   "ngram_flagged": ng["contaminated_doc_count"],
                   "fuzzy_flagged": fz["contaminated_doc_count"]})

    final_ids = set(after4)
    self_check = {}
    if truth:
        planted: dict[str, int] = {}
        caught: dict[str, int] = {}
        for did, kind in truth.items():
            planted[kind] = planted.get(kind, 0) + 1
            if did not in final_ids:
                caught[kind] = caught.get(kind, 0) + 1
        self_check = {kind: {"planted": planted[kind], "removed": caught.get(kind, 0)}
                      for kind in planted}

    card = {
        "task": "curation_pipeline_data_card",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus": str(args.corpus),
        "injected_demo_records": bool(truth),
        "input_documents": len(records),
        "output_documents": len(final_ids),
        "retained_fraction": round(len(final_ids) / max(len(records), 1), 3),
        "stages": stages,
        "source_distribution_before": source_counts(records, set(by_id)),
        "source_distribution_after": source_counts(records, final_ids),
        "self_check_injected": self_check,
        "params": {"num_perm": args.num_perm, "bands": args.bands,
                   "minhash_threshold": args.minhash_threshold, "ngram": args.ngram,
                   "fuzzy_threshold": args.fuzzy_threshold, "seed": args.seed},
        "content_hash": hashlib.sha1(
            "\n".join(sorted(final_ids)).encode()
        ).hexdigest(),
        "note": "From-scratch reference pipeline (mirrors datatrove/Dolma stages). "
                "Prose quality heuristics intentionally penalize code -> see "
                "source_distribution_after; production routes code through code-specific filters.",
    }

    print(f"\nCuration pipeline  ({len(records)} docs in -> {len(final_ids)} out, "
          f"{card['retained_fraction']:.0%} retained)\n")
    print(f"  {'stage':<18}{'input':>8}{'removed':>9}{'output':>8}")
    print(f"  {'-'*18}{'-'*8:>8}{'-'*9:>9}{'-'*8:>8}")
    for s in stages:
        print(f"  {s['stage']:<18}{s['input']:>8}{s['removed']:>9}{s['output']:>8}")
    print(f"\n  source mix before: {card['source_distribution_before']}")
    print(f"  source mix after:  {card['source_distribution_after']}")
    if self_check:
        print("\n  self-check (planted -> removed):")
        for kind, v in self_check.items():
            print(f"    {kind:<14} {v['removed']}/{v['planted']}")
    print()

    out = project_root() / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n")
    print(f"  wrote {out.relative_to(project_root())}\n")
    return card


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", type=Path, default=Path("data/raw/text_corpus/mix.jsonl"))
    p.add_argument("--no-inject", action="store_true", help="Curate the raw corpus only.")
    p.add_argument("--num-perm", type=int, default=64)
    p.add_argument("--bands", type=int, default=16)
    p.add_argument("--minhash-threshold", type=float, default=0.7)
    p.add_argument("--ngram", type=int, default=13)
    p.add_argument("--fuzzy-threshold", type=float, default=0.5)
    p.add_argument("--seed", type=int, default=17)
    p.add_argument("--output", type=Path,
                   default=Path("data/manifests/curation_pipeline_card.json"))
    return p.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
