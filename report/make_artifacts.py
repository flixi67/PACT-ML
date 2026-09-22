"""Generate report tables and figures from the run artifacts in out/.

Reads the model-performance CSVs (BoW, TF-IDF, BERT baseline, BERT improved)
and the masking probe results, and writes:

  report/tables/*.md        markdown tables (model ranking, per-label F1)
  report/figures/*.png      figures (fold variance, per-label comparison, masking)

Every number in these outputs is derived programmatically from the committed run
artifacts, so the report stays traceable to a run (criterion 7).

Usage:  python report/make_artifacts.py
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
TABLES = os.path.join(HERE, "tables")
FIGURES = os.path.join(HERE, "figures")
os.makedirs(TABLES, exist_ok=True)
os.makedirs(FIGURES, exist_ok=True)

LABELS = [
    "PoliceReform", "Operations_PatrolsInterventions", "StateAdministration",
    "RefugeeAssistance", "ElectionAssistance", "LegalReform",
    "CivilSocietyAssistance",
]

FILES = {
    "Bag-of-Words": "model_performance_summary_masked.csv",
    "TF-IDF": "model_performance_summary_tf_idf_masked.csv",
    "BERT (baseline)": "model_performance_summary_bert_masked.csv",
    "BERT (improved)": "model_performance_summary_bert_improved_masked.csv",
}

SHORT = {
    "Bag-of-Words": "BoW",
    "TF-IDF": "TF-IDF",
    "BERT (baseline)": "BERT-base",
    "BERT (improved)": "BERT",
}


def load(source: str) -> pd.DataFrame | None:
    path = os.path.join(OUT, FILES[source])
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def fold_level_macro(df: pd.DataFrame) -> pd.Series:
    """Mean over labels (per fold) of fold-level F1_macro, then mean over folds."""
    return df.groupby("Fold")["F1_macro"].first().mean()


def fold_level_micro(df: pd.DataFrame) -> pd.Series:
    return df.groupby("Fold")["F1_micro"].first().mean()


def model_aggregates(df: pd.DataFrame) -> dict:
    by = df.groupby(["Fold", "Label"])
    prec = by["Precision"].first().groupby("Label").mean().mean()
    rec = by["Recall"].first().groupby("Label").mean().mean()
    return {
        "macro_f1": fold_level_macro(df),
        "micro_f1": fold_level_micro(df),
        "precision": prec,
        "recall": rec,
        "fold_macro": df.groupby("Fold")["F1_macro"].first().tolist(),
    }


def per_label_f1(df: pd.DataFrame) -> pd.Series:
    g = df.groupby("Label")
    p = g["Precision"].mean()
    r = g["Recall"].mean()
    denom = (p + r).replace(0, np.nan)
    f1 = 2 * p * r / denom
    return f1.fillna(0.0)


def build_ranking() -> None:
    rows = []
    for src, fname in FILES.items():
        df = load(src)
        if df is None:
            continue
        for model in sorted(df["Model"].unique()):
            mdf = df[df["Model"] == model]
            a = model_aggregates(mdf)
            rows.append({
                "Source": SHORT[src], "Model": model,
                "Macro-F1": round(a["macro_f1"], 3), "Micro-F1": round(a["micro_f1"], 3),
                "Precision": round(a["precision"], 3), "Recall": round(a["recall"], 3),
                "Folds": "; ".join(f"{x:.3f}" for x in a["fold_macro"]),
            })
    rdf = pd.DataFrame(rows).sort_values("Macro-F1", ascending=False)
    lines = [
        "| Rank | Model | Source | Macro-F1 | Micro-F1 | Precision | Recall |",
        "|---|---|---|---|---|---|---|",
    ]
    for rank, (_, r) in enumerate(rdf.iterrows(), start=1):
        lines.append(
            f"| {rank} | {r['Model']} | {r['Source']} | {r['Macro-F1']} | "
            f"{r['Micro-F1']} | {r['Precision']} | {r['Recall']} |"
        )
    with open(os.path.join(TABLES, "model_ranking.md"), "w") as f:
        f.write("\n".join(lines) + "\n\n")
        f.write(": Model performance ranking. Macro-F1, micro-F1, precision and recall "
                "are means over the five cross-validation folds. {#tbl-model-ranking}\n")
    print("[artifacts] model_ranking.md written")


def build_per_label() -> None:
    cols = ["Label", "BERT-base P", "BERT-base R", "BERT-base F1",
            "BERT P", "BERT R", "BERT F1"]
    rows = []
    base = load("BERT (baseline)")
    imp = load("BERT (improved)")
    for lab in LABELS:
        row = [lab]
        for df in (base, imp):
            if df is None:
                row += ["", "", ""]
                continue
            sub = df[df["Label"] == lab]
            p = sub["Precision"].mean()
            r = sub["Recall"].mean()
            f1 = 2 * p * r / (p + r) if (p + r) else 0.0
            row += [f"{p:.3f}", f"{r:.3f}", f"{f1:.3f}"]
        rows.append(row)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in rows:
        lines.append("| " + " | ".join(map(str, row)) + " |")
    with open(os.path.join(TABLES, "bert_per_label.md"), "w") as f:
        f.write("\n".join(lines) + "\n\n")
        f.write(": Per-label precision, recall and F1 (means over five folds) for the "
                "naively fine-tuned BERT model and the improved BERT model, both on the "
                "location-deidentified corpus. {#tbl-bert-per-label}\n")
    print("[artifacts] bert_per_label.md written")


def fig_fold_variance() -> None:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    present = {src: load(src) for src in FILES if load(src) is not None}
    labels = []
    data = []
    for src, df in present.items():
        labels.append(SHORT[src])
        data.append(df.groupby("Fold")["F1_macro"].first().tolist())
    ax.boxplot(data, showmeans=True)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Fold-level Macro-F1")
    ax.set_title("Macro-F1 across 5 folds by model")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "fig_fold_variance.png"), dpi=150)
    plt.close(fig)
    print("[artifacts] fig_fold_variance.png written")


def fig_per_label() -> None:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(LABELS))
    width = 0.35
    base = load("BERT (baseline)")
    imp = load("BERT (improved)")
    pairs = []
    if base is not None:
        pairs.append(("BERT-base", base, "#b0bec5"))
    if imp is not None:
        pairs.append(("BERT", imp, "#4a148c"))
    for i, (name, df, color) in enumerate(pairs):
        f1 = per_label_f1(df)
        vals = [f1.get(l, 0.0) for l in LABELS]
        ax.bar(x + (i - 0.5) * width, vals, width, label=name, color=color)
    ax.set_xticks(x)
    ax.set_xticklabels([l.replace("_", "\n") for l in LABELS], fontsize=7)
    ax.set_ylabel("Per-label F1")
    ax.set_title("Per-label F1: BERT baseline vs improved (deidentified corpus)")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "fig_per_label.png"), dpi=150)
    plt.close(fig)
    print("[artifacts] fig_per_label.png written")


def build_masking_probe() -> None:
    import json

    path = os.path.join(OUT, "derived", "masking_probe.json")
    if not os.path.exists(path):
        print("[artifacts] masking_probe.json not found; skipping masking table")
        return
    d = json.load(open(path))
    rows = [
        ["Mission predictability (full text, 5-fold CV acc)", f"{d['unmasked_full']:.3f}",
         f"{d['masked_full']:.3f}", f"chance = {d['chance']:.3f}"],
        ["Mission predictability (location tokens only)", f"{d['unmasked_loc']:.3f}",
         "chance", f"chance = {d['chance']:.3f}"],
        ["Location spans masked", "-", f"{d['spans_masked']:,}", f"{d['docs_affected']:,}/{d['n_paragraphs']:,} docs"],
    ]
    lines = [
        "| Probe | Unmasked | Masked | Note |",
        "|---|---|---|---|",
    ]
    for a, b, c, dd in rows:
        lines.append(f"| {a} | {b} | {c} | {dd} |")
    with open(os.path.join(TABLES, "masking_probe.md"), "w") as f:
        f.write("\n".join(lines) + "\n\n")
        f.write(": Location-masking validation. Mission predictability is a 5-fold CV "
                "classifier accuracy; 'location tokens only' uses location features "
                "alone. {#tbl-masking-probe}\n")
    print("[artifacts] masking_probe.md written")


def main() -> None:
    build_ranking()
    build_per_label()
    build_masking_probe()
    fig_fold_variance()
    fig_per_label()
    print("[artifacts] done")


if __name__ == "__main__":
    main()
