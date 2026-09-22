"""Shared utilities for the PACT-ML model stage (module 06 rework).

Headless, deterministic data loading / splitting / metric computation used by
both the baseline reproduce path and the improved (nested-validation) path.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from skmultilearn.model_selection import IterativeStratification
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    multilabel_confusion_matrix,
    precision_score,
    recall_score,
)

TARGET_CATEGORIES = [
    "PoliceReform",
    "Operations_PatrolsInterventions",
    "StateAdministration",
    "RefugeeAssistance",
    "ElectionAssistance",
    "LegalReform",
    "CivilSocietyAssistance",
]

DATA_PATH = "data/merged_data.csv"
MASKED_PATH = "out/derived/merged_data_masked.csv"

MISSIONS = ["MINUSTAH", "UNMIK", "UNMIT", "MINUJUSTH", "UNOMIG", "UNMISET"]


def load_data(data_path: str = DATA_PATH, masked: bool = False) -> pd.DataFrame:
    """Load the (optionally masked) paragraph corpus with the 7 label columns."""
    path = MASKED_PATH if masked else data_path
    if masked and not os.path.exists(path):
        raise FileNotFoundError(
            f"Masked corpus not found at {path}. Run modules/07_location_masking.py first."
        )
    df = pd.read_csv(path)
    df["paragraph"] = df["paragraph"].astype(str)
    return df


def get_X_Y(df: pd.DataFrame):
    X = np.array(df["paragraph"].tolist())
    Y = np.array(df[TARGET_CATEGORIES].fillna(False).astype(float).values)
    return X, Y


def iterstrat_splits(X, Y, n_splits: int = 5, order: int = 1):
    """Yield (train_idx, test_idx) for each fold (deterministic).

    IterativeStratification with n_splits=k yields each fold's held-out portion
    as 1/k of the data, so an inner n_splits=5 split of a training fold gives an
    80/20 inner train/validation split (nested discipline) with no train_size arg.
    """
    strat = IterativeStratification(n_splits=n_splits, order=order)
    return strat.split(X, Y)


def per_label_thresholds(probs: np.ndarray, y_true: np.ndarray, grid=None) -> np.ndarray:
    """Pick per-label probability thresholds maximizing F1 on the given (validation) set."""
    if grid is None:
        grid = np.arange(0.05, 0.95, 0.05)
    n_labels = y_true.shape[1]
    best = np.full(n_labels, 0.5)
    for j in range(n_labels):
        best_f1 = -1.0
        yj = y_true[:, j]
        for t in grid:
            pred = (probs[:, j] > t).astype(int)
            f1 = f1_score(yj, pred, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best[j] = t
    return best


def label_stats(y_true: np.ndarray):
    n = y_true.shape[0]
    return {c: int(y_true[:, i].sum()) for i, c in enumerate(TARGET_CATEGORIES)}


def metrics_for(Y_true: np.ndarray, Y_pred: np.ndarray):
    """Full per-fold metric set, one row per label (mirrors committed CSV schema)."""
    f1_micro = f1_score(Y_true, Y_pred, average="micro", zero_division=0)
    f1_macro = f1_score(Y_true, Y_pred, average="macro", zero_division=0)
    p = precision_score(Y_true, Y_pred, average=None, zero_division=0)
    r = recall_score(Y_true, Y_pred, average=None, zero_division=0)
    cm = multilabel_confusion_matrix(Y_true, Y_pred)
    rows = []
    for i, label in enumerate(TARGET_CATEGORIES):
        tn, fp, fn, tp = cm[i].ravel()
        rows.append(
            {
                "F1_micro": f1_micro,
                "F1_macro": f1_macro,
                "Precision": p[i],
                "Recall": r[i],
                "FPR": fp / (fp + tn) if (fp + tn) else 0.0,
                "FNR": fn / (fn + tp) if (fn + tp) else 0.0,
                "TPR": tp / (tp + fn) if (tp + fn) else 0.0,
                "TNR": tn / (tn + fp) if (tn + fp) else 0.0,
                "TP": int(tp),
                "FP": int(fp),
                "FN": int(fn),
                "TN": int(tn),
                "_label": label,
            }
        )
    return rows
