# just for Google Colab Notebook
# !pip install transformers datasets evaluate scikit-learn scikit-multilearn --quiet

from skmultilearn.model_selection import IterativeStratification

# Set up Iterative Stratification
n_splits = 5
stratifier = IterativeStratification(n_splits=n_splits, order=1)

import torch
import pandas as pd
import numpy as np
from datasets import Dataset, Features, Sequence, Value
from transformers import XLMRobertaTokenizer, XLMRobertaForSequenceClassification, Trainer, TrainingArguments
from sklearn.metrics import f1_score, multilabel_confusion_matrix, classification_report, precision_score, recall_score, accuracy_score

df = pd.read_csv("data/merged_data.csv")

target_categories = [
    "PoliceReform",
    "Operations_PatrolsInterventions",
    "StateAdministration",
    "RefugeeAssistance",
    "ElectionAssistance",
    "LegalReform",
    "CivilSocietyAssistance"
]

X = np.array(df["paragraph"].tolist())
Y = np.array(df[target_categories].fillna(False).astype(float).values)

# Tokenizer & Encoding
tokenizer = XLMRobertaTokenizer.from_pretrained("xlm-roberta-base")

all_folds = []

for fold, (train_idx, val_idx) in enumerate(stratifier.split(X, Y)):
    print(f"\n📂 FOLD {fold + 1}")

    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = Y[train_idx], Y[val_idx]

    features = Features{
        "text": Value("string"),
        "labels": Sequence(Value("float32"))
    }

    train_dataset = Dataset.from_dict({"text": X_train.tolist(), "labels": y_train.tolist()}).cast(features)
    val_dataset = Dataset.from_dict({"text": X_val.tolist(), "labels": y_val.tolist()}).cast(features)

    def tokenize(example):
        tokenized = tokenizer(
            example["text"],
            truncation=True,
            padding="max_length",
            max_length=256
        )
        return tokenized
    
    train_dataset = train_dataset.map(tokenize)
    val_dataset = val_dataset.map(tokenize)

    num_labels = Y.shape[1]
    model = XLMRobertaForSequenceClassification.from_pretrained(
        "xlm-roberta-base",
        num_labels=num_labels,
        problem_type="multi_label_classification"
    )

    training_args = TrainingArguments(
        output_dir=f"./results/fold_{fold+1}",
        eval_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=4,
        weight_decay=0.01,
        logging_steps=50,
        disable_tqdm=False,
        logging_dir=f"./logs/fold_{fold+1}",
        save_strategy="no"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer
    )

    trainer.train()

    # Predict
    preds = trainer.predict(val_dataset)
    probs = torch.sigmoid(torch.tensor(preds.predictions)).numpy()
    Y_pred = (probs > 0.5).astype(int)
    Y_true = preds.label_ids

    # Confusion Metrics
    cm = multilabel_confusion_matrix(Y_true, Y_pred)

    rows = []
    for i, label in enumerate(label_names):
        tn, fp, fn, tp = cm[i].ravel()
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
        tnr = tn / (tn + fp) if (tn + fp) > 0 else 0

        rows.append({
            'Model': 'XLM-RoBERTa',
            'Fold': fold + 1,
            'Label': label,
            'F1_micro': f1_score(Y_true, Y_pred, average='micro'),
            'F1_macro': f1_score(Y_true, Y_pred, average='macro'),
            'FPR': fpr,
            'FNR': fnr,
            'TPR': tpr,
            'TNR': tnr,
            'TP': tp,
            'FP': fp,
            'FN': fn,
            'TN': tn
        })

    print(classification_report(Y_true, Y_pred, target_names=label_names, zero_division=0))
    
    fold_df = pd.DataFrame(rows)
    all_folds.append(fold_df)

final_results_df = pd.concat(all_folds, ignore_index=True)

# Summary per label
summary_df = final_results_df.groupby(['Model', 'Label']).agg({
    'F1_micro': 'mean',
    'F1_macro': 'mean',
    'FPR': 'mean',
    'FNR': 'mean',
    'TPR': 'mean',
    'TNR': 'mean',
}).reset_index()

summary_df.to_csv("model_performance_summary_bert.csv", index=False)
print("📁 Results saved as model_performance_summary_bert.csv")


model.save_pretrained("./multilabel_model_xlmr")
tokenizer.save_pretrained("./multilabel_model_xlmr")
