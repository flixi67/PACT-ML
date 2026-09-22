| Rank | Model | Source | Macro-F1 | Micro-F1 | Precision | Recall |
|---|---|---|---|---|---|---|
| 4 | Balanced Logistic Regression | TF-IDF | 0.506 | 0.528 | 0.394 | 0.716 |
| 8 | XLM-RoBERTa-improved | BERT-imp | 0.479 | 0.526 | 0.476 | 0.514 |
| 9 | XLM-RoBERTa-improved | BERT-imp-mask | 0.475 | 0.513 | 0.479 | 0.505 |
| 5 | Logistic Regression | TF-IDF | 0.466 | 0.499 | 0.62 | 0.382 |
| 2 | Logistic Regression | BoW | 0.464 | 0.49 | 0.567 | 0.4 |
| 1 | Balanced Logistic Regression | BoW | 0.446 | 0.466 | 0.321 | 0.745 |
| 7 | XLM-RoBERTa | BERT-base | 0.151 | 0.369 | 0.241 | 0.136 |
| 3 | Random Forest | BoW | 0.131 | 0.183 | 0.611 | 0.075 |
| 6 | Random Forest | TF-IDF | 0.131 | 0.174 | 0.664 | 0.075 |

: Model performance ranking. Macro-F1, micro-F1, precision and recall are means over the five cross-validation folds. {#tbl-model-ranking}
