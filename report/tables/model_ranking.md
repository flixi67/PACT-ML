| Rank | Model | Source | Macro-F1 | Micro-F1 | Precision | Recall |
|---|---|---|---|---|---|---|
| 1 | Balanced Logistic Regression | TF-IDF | 0.502 | 0.525 | 0.394 | 0.707 |
| 2 | XLM-RoBERTa-improved | BERT | 0.475 | 0.513 | 0.479 | 0.505 |
| 3 | Logistic Regression | BoW | 0.462 | 0.483 | 0.56 | 0.398 |
| 4 | Logistic Regression | TF-IDF | 0.454 | 0.482 | 0.602 | 0.371 |
| 5 | Balanced Logistic Regression | BoW | 0.433 | 0.457 | 0.312 | 0.733 |
| 6 | Random Forest | BoW | 0.14 | 0.188 | 0.693 | 0.081 |
| 7 | Random Forest | TF-IDF | 0.124 | 0.164 | 0.674 | 0.071 |
| 8 | XLM-RoBERTa | BERT-base | 0.115 | 0.33 | 0.13 | 0.107 |

: Model performance ranking. Macro-F1, micro-F1, precision and recall are means over the five cross-validation folds. {#tbl-model-ranking}
