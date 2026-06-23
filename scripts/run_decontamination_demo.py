"""Benchmark-decontamination demo: n-gram overlap vs a fuzzy pass.

Builds a small "training corpus" from the web slice, injects controlled contamination —
half the eval items verbatim, half paraphrased — and shows that n-gram decontamination
catches the verbatim copies but misses paraphrases, while a char-cosine fuzzy pass
recovers them. The lesson (arXiv 2311.04850): string-overlap decontamination alone leaves
rephrased eval data in the corpus.

    .venv/bin/python scripts/run_decontamination_demo.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from materials_event_modeling.curate.decontamination import (
    fuzzy_contamination,
    ngram_contamination,
)
from materials_event_modeling.curate.demo_eval import EVAL_ITEMS, PARAPHRASES


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_web_docs(corpus: Path, limit: int) -> list[tuple[str, str]]:
    path = project_root() / corpus
    if not path.exists():
        raise FileNotFoundError(
            f"Corpus {corpus} missing. Build it with scripts/fetch_text_corpus.py."
        )
    docs = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("source") == "web":
            docs.append((rec["doc_id"], rec["text"]))
        if len(docs) >= limit:
            break
    return docs


def inject_contamination(clean: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], dict[str, str]]:
    """Add short docs embedding eval items (verbatim or paraphrased). Returns corpus + truth."""
    injected = list(clean)
    truth: dict[str, str] = {}  # injected doc_id -> "verbatim" | "paraphrase"
    filler = "Posted in the community forum earlier today. "
    for eid, text in EVAL_ITEMS.items():
        if eid in PARAPHRASES:
            doc_id = f"inject_paraphrase_{eid}"
            injected.append((doc_id, filler + PARAPHRASES[eid]))
            truth[doc_id] = "paraphrase"
        else:
            doc_id = f"inject_verbatim_{eid}"
            injected.append((doc_id, filler + text + " Thanks for any help."))
            truth[doc_id] = "verbatim"
    return injected, truth


def run(args: argparse.Namespace) -> dict[str, Any]:
    clean = load_web_docs(args.corpus, args.web_docs)
    corpus, truth = inject_contamination(clean)
    n_verbatim = sum(v == "verbatim" for v in truth.values())
    n_paraphrase = sum(v == "paraphrase" for v in truth.values())

    ngram = ngram_contamination(corpus, EVAL_ITEMS, n=args.ngram)
    fuzzy = fuzzy_contamination(corpus, EVAL_ITEMS, threshold=args.fuzzy_threshold)

    ngram_flagged = set(ngram["flagged_doc_ids"])
    fuzzy_flagged = set(fuzzy["flagged_doc_ids"])
    clean_ids = {d for d, _ in clean}

    def breakdown(flagged: set[str]) -> dict[str, int]:
        return {
            "verbatim_caught": sum(truth.get(d) == "verbatim" for d in flagged),
            "paraphrase_caught": sum(truth.get(d) == "paraphrase" for d in flagged),
            "false_positives_on_clean": len(flagged & clean_ids),
        }

    combined = ngram_flagged | fuzzy_flagged
    report = {
        "task": "decontamination_demo",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus": {"clean_web_docs": len(clean), "injected_verbatim": n_verbatim,
                   "injected_paraphrase": n_paraphrase, "eval_items": len(EVAL_ITEMS)},
        "ngram": {"n": args.ngram, **breakdown(ngram_flagged),
                  "eval_recall": ngram["eval_recall"]},
        "fuzzy": {"threshold": args.fuzzy_threshold, **breakdown(fuzzy_flagged),
                  "eval_recall": fuzzy["eval_recall"]},
        "combined": {**breakdown(combined),
                     "total_contaminated_docs_caught": len(combined - clean_ids),
                     "total_contaminated_docs": len(truth)},
    }

    print(f"\nDecontamination demo  ({len(clean)} clean web docs + "
          f"{n_verbatim} verbatim + {n_paraphrase} paraphrased eval injections)\n")
    print(f"  {'pass':<10}{'verbatim':>10}{'paraphrase':>12}{'false-pos':>11}")
    print(f"  {'-'*10}{'-'*10:>10}{'-'*12:>12}{'-'*11:>11}")
    for name, key in (("n-gram", "ngram"), ("fuzzy", "fuzzy")):
        b = report[key]
        print(f"  {name:<10}{b['verbatim_caught']:>10}{b['paraphrase_caught']:>12}"
              f"{b['false_positives_on_clean']:>11}")
    residual = n_paraphrase - report["fuzzy"]["paraphrase_caught"]
    report["residual_paraphrases_evading_fuzzy"] = residual
    print(f"\n  n-gram alone misses ALL {n_paraphrase} paraphrased items; the char-cosine "
          f"fuzzy pass recovers {report['fuzzy']['paraphrase_caught']} (the lexically-close ones).")
    print(f"  combined caught {report['combined']['total_contaminated_docs_caught']}/"
          f"{len(truth)} contaminated docs, "
          f"{report['combined']['false_positives_on_clean']} false positives on clean web.")
    if residual:
        print(f"  {residual} heavily-reworded paraphrases still evade char-cosine -> the "
              f"residual that motivates an embedding/semantic decontamination pass.\n")
    else:
        print()

    out = project_root() / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"  wrote {out.relative_to(project_root())}\n")
    return report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", type=Path, default=Path("data/raw/text_corpus/mix.jsonl"))
    p.add_argument("--web-docs", type=int, default=200)
    p.add_argument("--ngram", type=int, default=13)
    p.add_argument("--fuzzy-threshold", type=float, default=0.35)
    p.add_argument("--output", type=Path,
                   default=Path("data/manifests/decontamination_demo.json"))
    return p.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
