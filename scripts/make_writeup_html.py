"""Build the self-contained HTML writeup with matplotlib figures from RRUFF data.

Figures (generated from real data / our run manifests):
  1. Calcite vs aragonite mean Raman spectra (same formula, different fingerprint).
  2. Garnet raw-spectrum PCA map, coloured by family (real joint) vs species (continuum bins).
  3. Measured accuracies: polymorphs (raw vs composition) and garnet (family vs species).
Saves PNGs to docs/writeup/figures/ and embeds them (base64) in a portable HTML.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from materials_event_modeling.data.rruff import load

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "data/raw/rruff/excellent_unoriented.zip"
FIGDIR = ROOT / "docs/writeup/figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.size": 10, "axes.titlesize": 10, "figure.facecolor": "white",
                     "axes.spines.top": False, "axes.spines.right": False})
GARNET = {"Almandine": "pyralspite", "Pyrope": "pyralspite", "Spessartine": "pyralspite",
          "Grossular": "ugrandite", "Andradite": "ugrandite"}


def save(fig, name):
    path = FIGDIR / name
    fig.savefig(path, dpi=130, bbox_inches="tight")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def fig_caco3(data):
    q, y, X = data.grid, data.mineral, data.X
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for name, color, off in [("Calcite", "#1f77b4", 1.15), ("Aragonite", "#d62728", 0.0)]:
        S = X[y == name]
        m = S.mean(0)
        m = m / m.max()
        ax.plot(q, m + off, color=color, lw=1.5, label=f"{name}  (n={len(S)})")
    ax.set_yticks([])
    ax.set_xlabel("Raman shift (cm$^{-1}$)")
    ax.set_title("Same formula (CaCO$_3$) — different Raman fingerprint")
    ax.legend(frameon=False, loc="upper right")
    ax.text(0.01, 0.97, "identical composition;\nstructure-sensitive fingerprint differs",
            transform=ax.transAxes, va="top", fontsize=8.5, color="#555")
    return save(fig, "fig1_caco3.png")


def fig_garnet(data):
    y, X = data.mineral, data.X
    mask = np.isin(y, list(GARNET))
    Xg, yg = X[mask], y[mask]
    Z = (Xg - Xg.mean(0)) / (Xg.std(0) + 1e-9)
    P = PCA(n_components=2, random_state=0).fit_transform(Z)
    fam = np.array([GARNET[m] for m in yg])
    sil_fam = silhouette_score(P, fam)
    sil_sp = silhouette_score(P, yg)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 4.2), sharex=True, sharey=True)
    for f, c in [("pyralspite", "#2ca02c"), ("ugrandite", "#9467bd")]:
        a1.scatter(P[fam == f, 0], P[fam == f, 1], s=22, c=c, alpha=0.8, label=f)
    a1.set_title(f"by FAMILY — real structural joint\n(separates; silhouette {sil_fam:.2f})")
    a1.legend(frameon=False, fontsize=8.5, loc="best")
    sp_colors = {"Almandine": "#1b9e77", "Pyrope": "#66c2a5", "Spessartine": "#a6d854",
                 "Grossular": "#7570b3", "Andradite": "#c2a5cf"}
    for sp, c in sp_colors.items():
        if (yg == sp).any():
            a2.scatter(P[yg == sp, 0], P[yg == sp, 1], s=22, c=c, alpha=0.8, label=sp)
    a2.set_title(f"by SPECIES — names on a continuum\n(blend within family; silhouette {sil_sp:.2f})")
    a2.legend(frameon=False, fontsize=7.5, loc="best")
    for a in (a1, a2):
        a.set_xlabel("PC1")
        a.set_ylabel("PC2")
        a.set_xticks([])
        a.set_yticks([])
    fig.suptitle("Garnet, raw-spectrum map (unsupervised PCA of the spectra)", y=1.02)
    print(f"[garnet PCA] family silhouette={sil_fam:.3f}  species silhouette={sil_sp:.3f}  n={len(yg)}")
    return save(fig, "fig2_garnet_pca.png")


def fig_bars():
    poly = json.loads((ROOT / "data/manifests/rruff_polymorph_probe.json").read_text())
    lossy = json.loads((ROOT / "data/manifests/rruff_lossy_probe.json").read_text())
    groups = [g for g in poly["groups"] if "raw_acc_mean" in g]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.8))

    labels = [g["formula"] for g in groups]
    raw = [g["raw_acc_mean"] for g in groups]
    maj = [g["majority_baseline"] for g in groups]
    x = np.arange(len(labels))
    w = 0.38
    a1.bar(x - w / 2, raw, w, label="raw spectrum", color="#1f77b4")
    a1.bar(x + w / 2, maj, w, label="composition (best it can do)", color="#cccccc")
    a1.set_xticks(x)
    a1.set_xticklabels(labels, fontsize=9)
    a1.set_ylim(0, 1.05)
    a1.set_ylabel("accuracy")
    a1.set_title("Polymorphs: label is a natural coordinate\nraw recovers it; composition is blind")
    a1.legend(frameon=False, fontsize=8.5, loc="lower right")

    g = lossy["garnet"]
    a2.bar(["family\n(real joint)", "species\n(continuum bins)"],
           [g["family_acc_2way"], g["species_acc_5way"]], color=["#2ca02c", "#d62728"], width=0.6)
    a2.axhline(g["majority_species"], ls="--", c="#888", lw=1)
    a2.text(1.4, g["majority_species"] + 0.02, "species\nmajority", fontsize=7.5, color="#888")
    a2.set_ylim(0, 1.05)
    a2.set_ylabel("accuracy")
    a2.set_title("Garnet: family faithful, species lossy\n(every species error stays within family)")
    return save(fig, "fig3_accuracies.png")


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>When is a label faithful to reality?</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         line-height: 1.65; color: #1a1a1a; max-width: 760px; margin: 0 auto; padding: 2.2rem 1.2rem; }}
  h1 {{ font-size: 2rem; line-height: 1.2; margin-bottom: .2rem; }}
  .sub {{ color:#666; font-style: italic; margin-top:0; }}
  h2 {{ margin-top: 2.2rem; font-size: 1.3rem; }}
  figure {{ margin: 1.6rem 0; text-align: center; }}
  figure img {{ max-width: 100%; height: auto; border: 1px solid #eee; border-radius: 6px; }}
  figcaption {{ color:#666; font-size: .9rem; margin-top: .5rem; text-align: left; }}
  blockquote {{ border-left: 3px solid #ddd; margin: 1.2rem 0; padding: .2rem 1rem; color:#444; }}
  em {{ color:#333; }}
  code {{ background:#f4f4f4; padding:0 .25rem; border-radius:3px; }}
  .note {{ background:#fafafa; border:1px solid #eee; border-radius:6px; padding:.8rem 1rem; font-size:.92rem; color:#444; }}
  a {{ color:#1f6feb; }}
</style></head><body>

<h1>When is a label faithful to reality?</h1>
<p class="sub">A lens from minerals — and a question about chemistry itself. (Draft; exploratory work from a data/AI angle.)</p>

<p>Every ML practitioner has felt the worry: <strong>are my labels signal, or a lossy human prior?</strong>
We hand models categories — "cat," "toxic," "stable" — and quietly hope they carve the data at real
joints. Sometimes they do. Often they're a convenient bucketing of something continuous, and we
never find out.</p>

<p>Materials science is a great place to actually <em>measure</em> this, because two things sit side
by side at scale: a <strong>raw physical measurement</strong> (how a material scatters X-rays or
laser light — its structural fingerprint) and a <strong>human label</strong> (its name). So you can
ask, concretely: how faithful is the label as a coordinate of the raw signal? We did, on thousands
of minerals.</p>

<h2>The hook: same formula, different thing</h2>
<p>Calcite and aragonite have the <em>identical</em> chemical formula — CaCO<sub>3</sub>. One is
blackboard chalk; the other is what seashells and pearls are made of. The formula literally cannot
tell them apart. But their raw spectra separate them instantly — they're different <em>arrangements</em>
of the same atoms ("polymorphs"). "CaCO<sub>3</sub>" is a <strong>lossy label</strong>: one token for
two genuinely different things.</p>

<figure><img src="data:image/png;base64,{fig1}">
<figcaption><b>Figure 1.</b> Mean Raman spectra of calcite vs aragonite from RRUFF (stacked for
clarity). Same composition; the structure-sensitive fingerprint differs. The cheap human feature
(formula) is blind to this; the raw measurement is not.</figcaption></figure>

<h2>Two regimes</h2>
<p>Give a method only the raw fingerprints — no names, no formulas — and ask how the human labels
relate to the structure. Two clean regimes appear:</p>
<p><strong>1. The label is a faithful coordinate</strong> when it marks a <em>real discontinuity</em>.
Polymorphs separate cleanly in raw-measurement space while the compositional shortcut is at chance.
<em>(ML translation: two classes with identical hand-features but separable raw input — the feature
is lossy, the raw is faithful.)</em></p>
<p><strong>2. The label is a lossy bin</strong> when it's an arbitrary cut on a <em>continuum</em>.
Garnet species — almandine, pyrope, spessartine — are names for where you sit on a smooth
iron–magnesium–manganese mixing dial. The raw signal recovers the real <em>structural family</em>
perfectly but <strong>blends the species</strong>, and every misclassification stays <em>inside</em>
the right family. <em>(ML translation: discretizing a continuous latent into classes — the boundary
is noise.)</em></p>

<figure><img src="data:image/png;base64,{fig2}">
<figcaption><b>Figure 2.</b> Unsupervised PCA of garnet raw spectra (no labels used to build it).
<b>Left:</b> coloured by structural <i>family</i> — a real joint, it separates. <b>Right:</b> coloured
by <i>species</i> — names on a continuum, they blend <i>within</i> a family. Same points, two
colourings.</figcaption></figure>

<figure><img src="data:image/png;base64,{fig3}">
<figcaption><b>Figure 3.</b> Measured (specimen-grouped k-NN, our runs). <b>Left:</b> for polymorphs,
the raw spectrum recovers the label while composition can only guess the majority. <b>Right:</b> for
garnet, the <i>family</i> is recovered perfectly but <i>species</i> blend — and 100% of species
errors stay within the family.</figcaption></figure>

<p>Philosophers have a name for this split — <em>natural kinds vs. conventional kinds.</em> We
stumbled into a way to measure it.</p>

<h2>We tried hard to kill it</h2>
<p>Overfitting? instrument artifact? "more classes are harder"? We checked: it reproduces on
<strong>two unrelated measurements</strong> (X-ray diffraction <em>and</em> Raman); it survives
<strong>capacity-free</strong> nearest-neighbour methods and a <strong>structure-blind control</strong>
(the signal lives in the sharp fingerprint, not broad/baseline features); and five <em>distinct</em>
minerals classify at 0.99 while garnet species sit at 0.73 — so the blending is the continuum, not
difficulty. It held. (Where it <em>didn't</em> generalise cleanly — battery degradation, where a
single "lifetime" number is a threshold on a continuous curve — we found out why: an <em>extrinsic</em>
variable, the charging recipe, confounds everything. The clean question needs <em>intrinsic</em>
labels. That boundary is part of the finding.)</p>

<h2>The part that zooms out</h2>
<p>Here's where it stops being about minerals. <strong>Chemistry itself is one of these label
systems.</strong> The formula is a lossy compression (calcite ≠ aragonite proved it). And the
periodic table behaves like a <em>learned embedding</em>: people ran word2vec on chemical compounds
(<a href="https://www.pnas.org/doi/10.1073/pnas.1801181115">Atom2Vec</a>) and it
<strong>re-derived the periodic table from data alone.</strong></p>
<p>So is the periodic table "real"? <em>Partly.</em> Atomic number is genuinely quantized — you can't
have 6.5 protons — so <em>elements</em> are a real joint. But the formula throws away structure, and
the "similarity" groupings are a soft compression a continuous embedding refines. And the catch that
matters most: Atom2Vec trained on <strong>human-curated</strong> compound databases. It's
GPT-trained-on-human-text — it <em>mirrors</em> human knowledge, it doesn't transcend it. A
representation faithful to <em>reality</em> rather than to <em>us</em> would need data no human
ontology pre-compressed — raw measurement of matter as it forms — which mostly doesn't exist
publicly.</p>
<blockquote>An alien civilisation that recorded reality as embeddings instead of element-boxes might
have no periodic table at all — and might be more right than us.</blockquote>

<h2>Why this might matter beyond rocks</h2>
<p>Strip away the minerals and it's a question that haunts all of ML: are my labels signal or a lossy
human prior? when does a representation learned from raw data beat the human feature? does my training
data's <em>provenance</em> cap how faithful my model can be — mirror, or alien? Materials is a rare
place where the "raw signal" is a physical measurement, not another human artifact — so you can
separate "faithful to reality" from "faithful to humans," which you usually can't in language or
vision.</p>

<div class="note"><b>What's new / known / open.</b> <b>Solid:</b> the natural-kind vs lossy-bin
distinction is real, measured, and modality-general. <b>Known</b> (credited): Raman/XRD distinguish
polymorphs (textbook); embeddings recover the periodic table (Atom2Vec 2018, Mat2Vec 2019);
metastability is a continuum (Sun et al. 2016). <b>Contribution:</b> a measurable criterion for when
a label is a faithful coordinate vs a lossy bin, and the reframe that chemistry's own labels sit on
the same spectrum. <b>Frontier:</b> data <i>below</i> human curation — raw, un-curated measurement of
matter as it forms — where any genuinely new, faithful-to-reality representation must come from.</div>

</body></html>
"""


def main():
    data = load(ZIP, wavelength="any", filetype="Processed")
    print(f"loaded {data.X.shape[0]} spectra")
    f1 = fig_caco3(data)
    f2 = fig_garnet(data)
    f3 = fig_bars()
    out = ROOT / "docs/writeup/when_is_a_label_faithful.html"
    out.write_text(HTML.format(fig1=f1, fig2=f2, fig3=f3))
    print("wrote", out.relative_to(ROOT))
    print("figures in", FIGDIR.relative_to(ROOT))


if __name__ == "__main__":
    main()
