"""Module 06 — BERT-class model (headless).

Replaces the original notebook-only path with a deterministic, headless CLI.
Two modes:

  --mode baseline  Reproduce the committed xlm-roberta-base configuration exactly:
                   5-fold IterativeStratification, 4 epochs, batch 16, seq 256,
                   lr 2e-5, wd 0.01, fixed 0.5 threshold, no class weighting.
  --mode improved  Same architecture, but with class-weighted loss (pos_weight)
                   and per-label F1-optimal thresholds, chosen under nested
                   discipline: within each outer fold the training split is
                   further split into inner-train / inner-val; the model is
                   trained on inner-train, thresholds are tuned on inner-val,
                   and the final numbers come from the outer held-out test split.
                   Nothing is tuned on test.

Determinism: IterativeStratification is deterministic; we additionally fix
torch/numpy seeds (--seed, default 0). Report the seed in RUN_LOG / the report.

Usage examples:
  python modules/06_roberta_model.py --mode baseline --out out/model_performance_summary_bert.csv
  python modules/06_roberta_model.py --mode improved --masked \
      --out out/model_performance_summary_bert_improved_masked.csv
"""
from __future__ import annotations

import argparse
import os
import time

import numpy as np
import pandas as pd
import torch
from datasets import Dataset, Features, Sequence, Value
from transformers import (
    Trainer,
    TrainingArguments,
    XLMRobertaForSequenceClassification,
    XLMRobertaTokenizer,
)

from rework_common import (
    DATA_PATH,
    TARGET_CATEGORIES,
    get_X_Y,
    iterstrat_splits,
    load_data,
    metrics_for,
    per_label_thresholds,
)

LABELS = TARGET_CATEGORIES


class WeightedTrainer(Trainer):
    """Trainer with optional class-weighted BCE (BCEWithLogitsLoss + pos_weight)."""

    def __init__(self, pos_weight=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pos_weight = pos_weight

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None, **kwargs):
        outputs = model(**inputs)
        logits = outputs.logits
        labels = inputs["labels"]
        if self._pos_weight is not None:
            loss_fct = torch.nn.BCEWithLogitsLoss(
                pos_weight=self._pos_weight.to(logits.device))
            loss = loss_fct(logits.float(), labels.float())
        else:
            loss = outputs.loss
        return (loss, outputs) if return_outputs else loss


def make_tokenizer():
    return XLMRobertaTokenizer.from_pretrained("xlm-roberta-base")


def make_dataset(texts, labels, tokenizer, seq_len: int):
    features = Features({"text": Value("string"), "labels": Sequence(Value("float32"))})
    ds = Dataset.from_dict({"text": list(texts), "labels": [list(map(float, r)) for r in labels]})
    ds = ds.cast(features)

    def tokenize(ex):
        return tokenizer(ex["text"], truncation=True, padding="max_length", max_length=seq_len)

    return ds.map(tokenize)


def pos_weight_from(y: np.ndarray, cap: float = 15.0) -> torch.Tensor:
    n = y.shape[0]
    pos = y.sum(axis=0) + 1e-9
    neg = n - y.sum(axis=0)
    w = np.minimum(neg / pos, cap)
    return torch.tensor(w, dtype=torch.float32)


def fit_model(Xtr, Ytr, tokenizer, args, pos_weight):
    train_ds = make_dataset(Xtr, Ytr, tokenizer, args.seq)
    model = XLMRobertaForSequenceClassification.from_pretrained(
        "xlm-roberta-base", num_labels=len(LABELS), problem_type="multi_label_classification"
    )
    train_args = TrainingArguments(
        output_dir=f"/tmp/pact_results/fold",
        eval_strategy="no",
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        num_train_epochs=args.epochs,
        weight_decay=args.weight_decay,
        logging_steps=500,
        logging_dir=f"/tmp/pact_logs",
        save_strategy="no",
        report_to=[],
        seed=args.seed,
        disable_tqdm=True,
    )
    trainer = WeightedTrainer(
        model=model, args=train_args, train_dataset=train_ds, tokenizer=tokenizer,
        pos_weight=pos_weight,
    )
    trainer.train()
    return trainer


def predict_probs(trainer, X, Y, tokenizer, args):
    ds = make_dataset(X, Y, tokenizer, args.seq)
    preds = trainer.predict(ds)
    probs = torch.sigmoid(torch.tensor(preds.predictions)).numpy()
    y_true = np.array(preds.label_ids)
    return probs, y_true


def metric_rows(probs, y_true, thresholds, model_name, fold):
    y_pred = (probs > thresholds).astype(int)
    rows = metrics_for(y_true, y_pred)
    for r, label in zip(rows, LABELS):
        r["Model"] = model_name
        r["Fold"] = fold
        r["Label"] = label
        r["Threshold"] = float(thresholds[LABELS.index(label)])
    return rows


def run(args) -> None:
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    model_name = "XLM-RoBERTa" if args.mode == "baseline" else "XLM-RoBERTa-improved"

    df = load_data(args.data)
    X, Y = get_X_Y(df)
    tokenizer = make_tokenizer()

    all_rows = []
    t0 = time.time()
    splits = list(iterstrat_splits(X, Y, n_splits=5))
    for k, (tr_idx, te_idx) in enumerate(splits):
        fold = k + 1
        if fold > args.max_fold:
            break
        print(f"[06] FOLD {fold}/{args.max_fold} mode={args.mode} masked={args.masked}")
        Xtr, Ytr = X[tr_idx], Y[tr_idx]
        Xte, Yte = X[te_idx], Y[te_idx]

        if args.mode == "improved":
            # nested: split training fold -> inner_train / inner_val
            itr, iva = list(iterstrat_splits(Xtr, Ytr, n_splits=5))[0]
            pos_weight = pos_weight_from(Ytr[itr], cap=args.pos_cap)
            trainer = fit_model(Xtr[itr], Ytr[itr], tokenizer, args, pos_weight)
            vprobs, vtrue = predict_probs(trainer, Xtr[iva], Ytr[iva], tokenizer, args)
            thresholds = per_label_thresholds(vprobs, vtrue)  # tuned on inner-val only
            tprobs, ttrue = predict_probs(trainer, Xte, Yte, tokenizer, args)
            all_rows.extend(metric_rows(tprobs, ttrue, thresholds, model_name, fold))
        else:
            trainer = fit_model(Xtr, Ytr, tokenizer, args, pos_weight=None)
            tprobs, ttrue = predict_probs(trainer, Xte, Yte, tokenizer, args)
            thresholds = np.full(len(LABELS), 0.5)
            all_rows.extend(metric_rows(tprobs, ttrue, thresholds, model_name, fold))

        print(f"[06] fold {fold} done in {time.time()-t0:.1f}s cumulative")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    cols = ["Model", "Fold", "Label", "F1_micro", "F1_macro", "Precision", "Recall",
            "FPR", "FNR", "TPR", "TNR", "TP", "FP", "FN", "TN", "Threshold"]
    pdf = pd.DataFrame(all_rows)[cols]
    pdf.to_csv(args.out, index=False)
    print(f"[06] wrote {args.out} ({len(pdf)} rows) in {time.time()-t0:.1f}s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["baseline", "improved"], default="baseline")
    ap.add_argument("--masked", action="store_true", help="Use masked derived corpus")
    ap.add_argument("--data", default=DATA_PATH)
    ap.add_argument("--out", default="out/model_performance_summary_bert.csv")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--seq", type=int, default=256)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--pos-cap", type=float, default=15.0)
    ap.add_argument("--max-fold", type=int, default=5)
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
