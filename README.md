# PACT-ML

Code for the ML (Group) Project @Hertie. PACT-ML codes UN peacekeeping report
paragraphs into 7 activity categories (multi-label text classification).

## Pipeline

- Modules 01-03: PDF parsing (report pre-selection, PDF parsing, paragraph extraction).
- Modules 04-05: classical baselines — bag-of-words and TF-IDF (Logistic Regression,
  Balanced Logistic Regression, Random Forest).
- Module 06: BERT-class model (`xlm-roberta-base`), headless and reproducible.
- Module 07: location de-identification (NER + mission-acronym + gazetteer masking).

This branch reworks the **model stage only** (module 06), adds a location
de-identification step (module 07), pins the environment, and re-authors the
report. The `data/` CSVs are frozen and untouched.

## Reproducing the model stage

The environment is pinned in `requirements.txt` (exact versions) and
`environment.yml`. The model stage runs as plain Python scripts on a GPU:

```bash
# 1. Location de-identification -> out/derived/merged_data_masked.csv
python modules/07_location_masking.py

# 2. Reproduce the committed BERT baseline (5-fold IterativeStratification)
python modules/06_roberta_model.py --mode baseline \
    --out out/model_performance_summary_bert.csv

# 3. Improved model on the deidentified corpus (class-weighted loss + per-label
#    thresholds, chosen under nested cross-validation)
python modules/06_roberta_model.py --mode improved \
    --data out/derived/merged_data_masked.csv \
    --out out/model_performance_summary_bert_improved_masked.csv

# 4. Optional: improved model on the original (unmasked) corpus, to measure the
#    effect of masking on the final model
python modules/06_roberta_model.py --mode improved \
    --data data/merged_data.csv \
    --out out/model_performance_summary_bert_improved.csv
```

### Running on Modal (L4 GPU)

`modal/run_pact_ml.py` builds a pinned image, bundles the repo, and runs any
module command on an L4 GPU, writing artifacts to a persistent Modal volume
(`pact-ml-artifacts`) mounted at `/artifacts`:

```bash
modal run modal/run_pact_ml.py \
  --cmd "python modules/06_roberta_model.py --mode baseline \
         --out /artifacts/out/model_performance_summary_bert.csv"
modal volume get pact-ml-artifacts out/model_performance_summary_bert.csv out/
```

### Reproducing the report

Tables and figures are generated from the run artifacts in `out/`, then Quarto
renders the report to HTML:

```bash
python report/make_artifacts.py          # writes report/tables/*.md, report/figures/*.png
quarto render "report/PACT-ML Report.qmd" # -> report/PACT-ML Report.html
```

## Model-stage results (summary)

- The reproduced BERT baseline confirms the committed class-collapse: four of
  seven categories reach near-zero recall.
- The improved model (class-weighted loss + per-label thresholds, nested CV)
  raises macro-F1 above the baseline and recovers non-trivial F1 on previously
  zero-recall categories without degrading PoliceReform / Operations.
- Location masking removes the geographic shortcut (mission-predictability
  drops to chance for location-only features) at no cost to task performance.

See `report/PACT-ML Report.qmd` and `RUN_LOG.md` for full details and the agent
run log.

## Disclaimer

The fine-tuned RoBERTa model is ~1GB and, even with Git LFS, could not be
uploaded here; it is saved as a `.zip` for reference. The reworked model stage
re-fine-tunes `xlm-roberta-base` from the Hugging Face hub rather than shipping
weights. All errors are the author's own.
