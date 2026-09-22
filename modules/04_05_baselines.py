"""Recalculate the classical baseline models (BoW + TF-IDF) on a given corpus.

Headless reproduction of the original notebook pipeline (modules/04 & 05):
  - CountVectorizer / TfidfVectorizer(stop_words='english', min_df=5, max_df=0.95)
  - Logistic Regression (C=1.0, l1, liblinear), Balanced LR (class_weight='balanced',
    C=0.1, l1, liblinear), Random Forest (max_depth=None, min_samples_split=2,
    n_estimators=75), each wrapped for multi-label via OneVsRestClassifier.
  - 5-fold IterativeStratification (order=1), deterministic (no shuffle).
  - Per-fold, per-label metrics (same schema as the committed CSVs).
  - Seeds fixed to 161 (matches the original notebook).

Usage:
  python modules/04_05_baselines.py --source bow   --data <corpus.csv> --out out/model_performance_summary_masked.csv
  python modules/04_05_baselines.py --source tfidf --data <corpus.csv> --out out/model_performance_summary_tf_idf_masked.csv
"""
from __future__ import annotations

import argparse
import os
import random
import sys

import numpy as np

random.seed(161)
np.random.seed(161)
os.environ["PYTHONHASHSEED"] = "161"

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    f1_score,
    multilabel_confusion_matrix,
    precision_score,
    recall_score,
)
from sklearn.multiclass import OneVsRestClassifier
from skmultilearn.model_selection import IterativeStratification

TARGET = [
    "PoliceReform",
    "Operations_PatrolsInterventions",
    "StateAdministration",
    "RefugeeAssistance",
    "ElectionAssistance",
    "LegalReform",
    "CivilSocietyAssistance",
]


def build_models(source: str) -> dict:
    rf_params = {"max_depth": None, "min_samples_split": 2, "n_estimators": 75}
    if source == "bow":
        # modules/04: LR C=1.0 l1 liblinear; Balanced LR C=0.1 l1 liblinear
        lr = dict(C=1.0, penalty="l1")
        blr = dict(C=0.1, penalty="l1")
    else:
        # modules/05 (tfidf): LR C=10.0 l1 liblinear; Balanced LR C=1.0 l2 liblinear
        lr = dict(C=10.0, penalty="l1")
        blr = dict(C=1.0, penalty="l2")
    return {
        "Logistic Regression": OneVsRestClassifier(
            LogisticRegression(max_iter=1000, solver="liblinear", **lr)
        ),
        "Balanced Logistic Regression": OneVsRestClassifier(
            LogisticRegression(
                class_weight="balanced", max_iter=1000,
                solver="liblinear", **blr,
            )
        ),
        "Random Forest": RandomForestClassifier(**rf_params),
    }


def run(source: str, data_path: str, out_path: str) -> None:
    merged = pd.read_csv(data_path)
    label_names = [c for c in TARGET if c in merged.columns]
    Y = merged[label_names].fillna(False).astype(int).values
    text = merged["paragraph"].astype(str)

    vec = (
        CountVectorizer(stop_words="english", min_df=5, max_df=0.95)
        if source == "bow"
        else TfidfVectorizer(stop_words="english", min_df=5, max_df=0.95)
    )
    X = vec.fit_transform(text)

    stratifier = IterativeStratification(n_splits=5, order=1)
    models = build_models(source)
    results = []

    for model_name, model in models.items():
        fold_metrics = []
        f1_scores = []
        for train_idx, test_idx in stratifier.split(X, Y):
            X_tr, X_te = X[train_idx], X[test_idx]
            Y_tr, Y_te = Y[train_idx], Y[test_idx]
            model.fit(X_tr, Y_tr)
            Y_pred = model.predict(X_te)
            Y_pred = Y_pred.toarray() if hasattr(Y_pred, "toarray") else Y_pred

            f1_micro = f1_score(Y_te, Y_pred, average="micro")
            f1_macro = f1_score(Y_te, Y_pred, average="macro")
            f1_scores.append({"f1_micro": f1_micro, "f1_macro": f1_macro})

            cm = multilabel_confusion_matrix(Y_te, Y_pred)
            prec = precision_score(Y_te, Y_pred, average=None, zero_division=0)
            rec = recall_score(Y_te, Y_pred, average=None, zero_division=0)

            fold = len(fold_metrics) // len(label_names) + 1
            for i, label in enumerate(label_names):
                tn, fp, fn, tp = cm[i].ravel()
                fold_metrics.append({
                    "Model": model_name, "Fold": fold, "Label": label,
                    "F1_micro": f1_micro, "F1_macro": f1_macro,
                    "Precision": prec[i], "Recall": rec[i],
                    "FPR": fp / (fp + tn) if (fp + tn) > 0 else 0,
                    "FNR": fn / (fn + tp) if (fn + tp) > 0 else 0,
                    "TPR": tp / (tp + fn) if (tp + fn) > 0 else 0,
                    "TNR": tn / (tn + fp) if (tn + fp) > 0 else 0,
                    "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                })
        results.append(pd.DataFrame(fold_metrics))
        s = pd.DataFrame(f1_scores)
        print(f"[{model_name}] mean micro {s.f1_micro.mean():.4f} / macro {s.f1_macro.mean():.4f}")

    final = pd.concat(results, ignore_index=True)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    final.to_csv(out_path, index=False)
    print(f"wrote {out_path} ({len(final)} rows)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=["bow", "tfidf"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    run(a.source, a.data, a.out)
