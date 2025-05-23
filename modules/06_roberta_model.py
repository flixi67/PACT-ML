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

all_results = []

for fold, (train_idx, val_idx) in enumerate(stratifier.split(X, Y)):
    print(f"\n📂 FOLD {fold + 1}")

    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = Y[train_idx], Y[val_idx]

    features = Features({
        "text": Value("string"),
        "labels": Sequence(Value("float32"))
    })

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

    f1_micro = f1_score(Y_true, Y_pred, average='micro')
    f1_macro = f1_score(Y_true, Y_pred, average='macro')

    # Confusion Metrics
    cm = multilabel_confusion_matrix(Y_true, Y_pred)
    precision_per_label = precision_score(Y_true, Y_pred, average=None, zero_division=0)
    recall_per_label = recall_score(Y_true, Y_pred, average=None, zero_division=0)
    
    for i, label in enumerate(target_categories):
        tn, fp, fn, tp = cm[i].ravel()

        # Use sklearn's calculated metrics
        precision = precision_per_label[i]
        recall = recall_per_label[i]

        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
        tnr = tn / (tn + fp) if (tn + fp) > 0 else 0

        all_results.append({
            'Model': 'XLM-RoBERTa',
            'Fold': fold + 1,
            'Label': label,
            'F1_micro': f1_micro,
            'F1_macro': f1_macro,
            'Precision': precision,
            'Recall': recall,
            'FPR': fpr,
            'FNR': fnr,
            'TPR': tpr,
            'TNR': tnr,
            'TP': tp,
            'FP': fp,
            'FN': fn,
            'TN': tn
        })

    print(classification_report(Y_true, Y_pred, target_names=target_categories, zero_division=0))
    
    results_df = pd.DataFrame(all_results)


results_df.to_csv("model_performance_summary_bert.csv", index=False)
print("📁 Results saved as model_performance_summary_bert.csv")


model.save_pretrained("./multilabel_model_xlmr")
tokenizer.save_pretrained("./multilabel_model_xlmr")
