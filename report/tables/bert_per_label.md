| Label | BERT-base P | BERT-base R | BERT-base F1 | BERT-imp P | BERT-imp R | BERT-imp F1 | BERT-imp-mask P | BERT-imp-mask R | BERT-imp-mask F1 |
|---|---|---|---|---|---|---|---|---|---|
| PoliceReform | 0.612 | 0.602 | 0.607 | 0.553 | 0.691 | 0.614 | 0.551 | 0.663 | 0.602 |
| Operations_PatrolsInterventions | 0.703 | 0.313 | 0.433 | 0.661 | 0.695 | 0.678 | 0.690 | 0.668 | 0.679 |
| StateAdministration | 0.120 | 0.014 | 0.024 | 0.583 | 0.524 | 0.552 | 0.536 | 0.461 | 0.495 |
| RefugeeAssistance | 0.000 | 0.000 | 0.000 | 0.174 | 0.264 | 0.210 | 0.273 | 0.244 | 0.258 |
| ElectionAssistance | 0.200 | 0.017 | 0.032 | 0.627 | 0.679 | 0.652 | 0.636 | 0.696 | 0.665 |
| LegalReform | 0.000 | 0.000 | 0.000 | 0.301 | 0.269 | 0.284 | 0.286 | 0.340 | 0.311 |
| CivilSocietyAssistance | 0.050 | 0.006 | 0.011 | 0.432 | 0.478 | 0.454 | 0.380 | 0.466 | 0.419 |

: Per-label precision, recall and F1 (means over five folds) for the reproduced BERT baseline, the improved model on the original corpus, and the improved model on the masked corpus. {#tbl-bert-per-label}
