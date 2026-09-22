"""Regenerate all exploratory-data-analysis figures from the MASKED corpus.

Headless reproduction of the original report's R EDA cells in Python:
  Text corpus: paragraph-length histograms, vocabulary/TTR, Zipf plot,
               top bigrams & trigrams.
  Category-specific: type-token ratio per category, label co-occurrence,
                     label distribution by mission, word clouds by category,
                     distinctive (TF-IDF) terms by category.

Usage:
  python modules/08_eda.py --data out/derived/merged_data_masked.csv --orig data/merged_data.csv
Outputs go to report/figures/eda/.
"""
from __future__ import annotations

import argparse
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from wordcloud import WordCloud

TARGET = [
    "PoliceReform",
    "Operations_PatrolsInterventions",
    "StateAdministration",
    "RefugeeAssistance",
    "ElectionAssistance",
    "LegalReform",
    "CivilSocietyAssistance",
]
C = "#4472C4"
OUT = None


def setup_ax(ax):
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)


def tokenize_words(series):
    """Lowercase, keep alphabetic tokens length>2, drop stopwords (matches R pipeline).
    The de-identification placeholder [LOC] is excluded (it is a redaction marker,
    not a real word)."""
    toks = []
    for p in series.astype(str):
        p = p.replace("[LOC]", " ")
        for t in re.findall(r"[a-z]{3,}", p.lower()):
            if t not in ENGLISH_STOP_WORDS:
                toks.append(t)
    return toks


def fig_text_lengths(merged, orig):
    def hist(series, ax, title, color):
        wc = series.astype(str).str.split().str.len()
        ax.hist(wc, bins=range(0, 501, 10), color=color, alpha=0.7, edgecolor="white")
        mean, med = wc.mean(), wc.median()
        ax.axvline(mean, color="red", ls="--", lw=1.2)
        ax.axvline(med, color="darkgreen", ls="--", lw=1.2)
        ax.text(mean + 20, ax.get_ylim()[1] * 0.95, f"Mean: {mean:.1f}", color="red")
        ax.text(max(20, med - 120), ax.get_ylim()[1] * 0.7, f"Median: {med:.0f}", color="darkgreen")
        ax.set_title(title)
        ax.set_xlim(0, 500)
        ax.set_xlabel("Words per paragraph"); ax.set_ylabel("Count")
        setup_ax(ax)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    hist(orig["paragraph"], axes[0], "Original corpus", C)
    hist(merged["paragraph"], axes[1], "Location-masked corpus", C)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_text_lengths.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("fig_text_lengths")


def vocab_ttr(merged):
    toks = tokenize_words(merged["paragraph"])
    total = len(toks)
    uniq = len(set(toks))
    print(f"TTR: total={total} unique={uniq} ttr={uniq/total:.4f}")


def fig_zipf(merged):
    toks = tokenize_words(merged["paragraph"])
    from collections import Counter
    freqs = Counter(toks)
    df = pd.DataFrame(freqs.most_common(500), columns=["word", "n"])
    df["rank"] = range(1, len(df) + 1)
    df["freq"] = df["n"] / df["n"].sum()
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.loglog(df["rank"], df["freq"], ".", color=C, alpha=0.7)
    ideal = df["freq"].iloc[0] / df["rank"]
    ax.loglog(df["rank"], ideal, "--", color="red")
    ax.set_xlabel("Rank (log)"); ax.set_ylabel("Frequency (log)")
    ax.set_title("Zipf's Law Plot: Word Frequency vs Rank (Log-Log)")
    setup_ax(ax)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_zipf.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("fig_zipf")


def fig_ngrams(merged):
    # Drop the de-identification placeholder so it does not dominate the n-grams.
    text = merged["paragraph"].astype(str).str.replace("[LOC]", " ")

    def top(ngram, n):
        vec = CountVectorizer(ngram_range=(ngram, ngram), stop_words="english")
        m = vec.fit_transform(text)
        counts = np.asarray(m.sum(axis=0)).ravel()
        order = counts.argsort()[::-1][:n]
        return [vec.get_feature_names_out()[i] for i in order], counts[order]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, ng, title, n in [
        (axes[0], 2, "Top 20 Bigrams", 20), (axes[1], 3, "Top 15 Trigrams", 15),
    ]:
        words, counts = top(ng, n)
        ax.barh(range(len(words))[::-1], counts, color=C)
        ax.set_yticks(range(len(words))[::-1], labels=words)
        ax.set_title(title); setup_ax(ax)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_ngrams.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("fig_ngrams")


def fig_ttr(merged):
    rows = []
    for cat in TARGET:
        sub = merged[merged[cat] == 1]["paragraph"]
        toks = tokenize_words(sub)
        rows.append({"Category": cat, "TTR": len(set(toks)) / len(toks) if toks else 0})
    df = pd.DataFrame(rows).sort_values("TTR", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(df["Category"], df["TTR"], color=C)
    for i, v in enumerate(df["TTR"]):
        ax.text(i, v + 0.005, f"{v:.3f}", ha="center")
    ax.set_ylabel("Type-Token Ratio")
    ax.set_ylim(0, df["TTR"].max() * 1.2)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    setup_ax(ax)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_ttr.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("fig_ttr")


def fig_cooccurrence(merged):
    L = merged[TARGET].fillna(False).astype(int).values
    co = L.T @ L
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(co, cmap="Blues")
    ax.set_xticks(range(len(TARGET)), labels=[t.replace("_", " ") for t in TARGET], rotation=45, ha="right")
    ax.set_yticks(range(len(TARGET)), labels=[t.replace("_", " ") for t in TARGET])
    for i in range(len(TARGET)):
        for j in range(len(TARGET)):
            ax.text(j, i, int(co[i, j]), ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Label Co-occurrence (location-masked corpus)")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_cooccurrence.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("fig_cooccurrence")


def fig_label_mission(merged):
    mission = merged["fileName"].str.split("_").str[0]
    d = pd.DataFrame({"Mission": mission})
    for cat in TARGET:
        d[cat] = merged[cat].fillna(False).astype(int)
    agg = d.groupby("Mission")[TARGET].sum()
    pct = agg.div(agg.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(10, 5))
    bottom = np.zeros(len(pct))
    for cat in TARGET:
        ax.bar(pct.index, pct[cat], bottom=bottom, label=cat.replace("_", " "))
        bottom += pct[cat].values
    ax.set_ylabel("Percentage of labels (%)")
    ax.set_xlabel("Mission")
    ax.legend(ncol=2, fontsize=8, loc="upper right")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    setup_ax(ax)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_label_mission.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("fig_label_mission")


def fig_wordclouds(merged):
    fig, axes = plt.subplots(3, 3, figsize=(15, 15))
    axes = axes.ravel()
    for ax, cat in zip(axes, TARGET):
        sub = merged[merged[cat] == 1]["paragraph"]
        freqs = Counter(tokenize_words(sub))
        if freqs:
            wc = WordCloud(width=500, height=350, background_color="white",
                           max_words=50, random_state=1).generate_from_frequencies(freqs)
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
        else:
            ax.text(0.5, 0.5, "No data", ha="center")
        ax.set_title(cat.replace("_", " "), fontsize=11)
    axes[-1].axis("off")
    fig.suptitle("Word Clouds by Category", fontsize=14)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_wordclouds.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("fig_wordclouds")


def fig_distinctive_terms(merged):
    docs, cats = [], []
    for cat in TARGET:
        for p in merged[merged[cat] == 1]["paragraph"].astype(str):
            docs.append(" ".join(tokenize_words(pd.Series([p]))))
            cats.append(cat)
    vec = TfidfVectorizer()
    X = vec.fit_transform(docs)
    feat = vec.get_feature_names_out()
    fig, axes = plt.subplots(3, 3, figsize=(15, 13))
    axes = axes.ravel()
    for ax, cat in zip(axes, TARGET):
        idx = [i for i, c in enumerate(cats) if c == cat]
        if not idx:
            ax.axis("off"); continue
        scores = np.asarray(X[idx].sum(axis=0)).ravel()
        order = scores.argsort()[::-1][:10]
        words = [feat[i] for i in order][::-1]
        vals = scores[order][::-1]
        ax.barh(range(len(words)), vals, color=C)
        ax.set_yticks(range(len(words)), labels=words)
        ax.set_title(cat.replace("_", " "))
        setup_ax(ax)
    axes[-1].axis("off")
    fig.suptitle("Distinctive Terms by Category (TF-IDF)", fontsize=14)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_distinctive_terms.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("fig_distinctive_terms")


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="masked corpus csv")
    ap.add_argument("--orig", default="data/merged_data.csv")
    ap.add_argument("--out", default="report/figures/eda")
    a = ap.parse_args()
    OUT = a.out
    os.makedirs(OUT, exist_ok=True)
    merged = pd.read_csv(a.data)
    orig = pd.read_csv(a.orig)
    from collections import Counter
    globals()["Counter"] = Counter
    fig_text_lengths(merged, orig)
    vocab_ttr(merged)
    fig_zipf(merged)
    fig_ngrams(merged)
    fig_ttr(merged)
    fig_cooccurrence(merged)
    fig_label_mission(merged)
    fig_wordclouds(merged)
    fig_distinctive_terms(merged)
    print("EDA figures done ->", OUT)


if __name__ == "__main__":
    main()
