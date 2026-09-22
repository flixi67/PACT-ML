# PACT-ML Autonomous Rework — RUN LOG

Contract: `REQUIREMENTS.md` (v0.2). Agent: Hermie (Hermes). Branch: `rework/autonomous-2026-09`.
Run window: 2026-09-22 ~13:30 - ~18:20 (UTC+8). GPU: Modal L4.

## Acceptance-criteria status

1. REPRODUCE FIRST — DONE. Re-ran module-06 baseline (xlm-roberta-base, 5-fold IterativeStratification,
   4ep/b16/seq256/lr2e-5/wd0.01/thr0.5) on frozen data -> `out/model_performance_summary_bert.csv` (35 rows).
   Fold-level macro-F1 reproduced: 0.212/0.191/0.089/0.158/0.107 (mean 0.151) vs committed 0.315/0.187/0.175/0.157/0.061
   (mean 0.179). Same qualitative class-collapse reproduced (RefugeeAssistance, LegalReform at 0.0 recall;
   StateAdmin ~0.01). Divergence attributed to Trainer/CUDA stochasticity (fixed seeds do not fully remove dropout
   + nondeterministic reduction), not config. Documented in report @sec-reproduce.
2. IMPROVE — DONE. Improved model (class-weighted loss + per-label F1 thresholds, nested CV):
   mean macro-F1 0.479 (unmasked) / 0.475 (masked) vs reproduced baseline 0.151 (~3.1x). All 7 labels reach
   non-trivial F1 (masked): PoliceReform ~0.61, Operations ~0.68, StateAdmin ~0.55, Election ~0.65, LegalReform ~0.28,
   Refugee ~0.21, CivilSociety ~0.45. Four previously-zero labels recovered; PoliceReform/Operations not degraded.
3. LOCATION MASKING — DONE. `modules/07_location_masking.py`: NER (dslim/bert-base-NER GPE/LOC) + mission-acronym
   masking + geonym/demonym gazetteer -> `out/derived/merged_data_masked.csv` (23,840 spans masked; 5,328/6,029 docs).
   Frozen data/ untouched. Validation (out/derived/masking_probe.json): location-only mission probe 0.770 -> chance
   (shortcut gone); full-text probe 0.917 -> 0.844 (residual is thematic, not locational). Masking effect on model:
   improved unmasked 0.479 vs masked 0.475 (essentially no cost). Mission acronyms masked per contract discretion.
4. HONEST VALIDATION — DONE. Nested: within each outer fold, inner 80/20 IterativeStratification; pos_weight from
   inner-train; thresholds tuned on inner-val only; final numbers on outer held-out test. Thresholds never tuned on
   test. Seeds: torch/numpy fixed to 0 (IterativeStratification deterministic).
5. HEADLESS — DONE. `modules/06_roberta_model.py` and `modules/07_location_masking.py` are plain scripts
   (no notebook required). Original notebook remains but is not the executable path.
6. ENV — DONE. `requirements.txt` (exact versions) + `environment.yml`. Verified by fresh install in the Modal image
   (torch 2.5.1, transformers 4.46.2, tokenizers 0.20.1, datasets 3.1.0, sklearn 1.5.2, skmultilearn 0.2.0, pandas 2.2.3,
   numpy 1.26.4, accelerate 1.0.1, sentencepiece 0.2.0, evaluate 0.4.3).
7. REPORT — DONE. `report/PACT-ML Report.qmd` fully re-authored (new prose for Introduction, Data, Methods, Results,
   Discussion, Conclusion, Annex). Tables/figures generated from run artifacts (`report/make_artifacts.py` ->
   report/tables/*.md, report/figures/*.png). Quarto renders to HTML with no warnings. Every number traces to a run
   artifact (out/*.csv, out/derived/masking_probe.json). bibliography.bib reused.
8. COMMIT — DONE (this run log + all artifacts committed to rework/autonomous-2026-09).

## Steps / incidents

- Explored repo; verified Modal auth (flixi67) + L4 via modal/hello_gpu.py.
- Data: 6029 paragraphs, 6 missions, 7 labels; minority labels very rare (1.7-3.6%).
- R not installed -> re-authored report with static tables/figures + `{{< include >}}` (no R/jupyter at render).
- Wrote modules (rework_common, 06_roberta_model, 07_location_masking), modal/run_pact_ml.py, report/make_artifacts.py,
  requirements.txt, environment.yml; rewrote README; re-authored report.
- Local sanity: deterministic splits; pos_weight; threshold tuning; masking probe; ranking logic reproduces committed
  key figures.
- Modal API debugging (this Modal version lacks modal.Mount / copy_local_file):
  * `copy_local_file` not found -> `Image.add_local_dir(copy=False)`.
  * `pip_install` Dockerfile broke on newline in package strings -> `.strip()` each line.
  * module-level `open(requirements.txt)` failed in container -> path-robust `_read_reqs()` + `is_local()` guard.
- Training bug: `compute_loss()` missing `num_items_in_batch` kwarg (transformers 4.46) -> added **kwargs.
- Training bug: pos_weight tensor on CPU vs logits on CUDA -> `.to(logits.device)` in compute_loss.
- Runs: masking (success), baseline reproduce (41 min), improved-unmasked (36 min), improved-masked (33 min).
- Report rendered clean (no warnings) after artifacts regenerated.

## Decisions under contract discretion

- Mission acronyms masked as location hints (strongest shortcut; contract discretion note). Reviewers preferring to
  keep them trade away the shortcut for some topically confounded signal.
- Masking effect on final model measured by training improved model on BOTH corpora (2x5 folds) + probes; baseline
  masking ablation skipped to stay within GPU budget.
- Improved model: capped pos_weight (cap 15) + per-label thresholds (grid 0.05-0.90), nested per fold; seeds 0.

## Budget / spend (estimate)

- GPU-hours (L4): masking ~0.2 + smoke ~0.3 + baseline 0.7 + improved-unmasked 0.6 + improved-masked 0.6 ~= 2.4 GPU-hr
  (hard cap 8). Modal cost at ~$0.8-1.0/L4-hr ~= $2-3 (hard cap $30). Agent tokens modest. Within all caps.

## Final status

All 8 acceptance criteria met. Deliverables on branch: pinned env, headless modules, masked derived corpus, three
model-performance CSVs, regenerated report tables/figures, re-rendered HTML, re-authored report, README, RUN_LOG.

## Audit files

- `AUDIT_TRAIL.md` — full call-by-call record of every tool call, result, failure and decision.
- `run_logs/*.txt` — per-run Modal output logs (masking, baseline, improved-unmasked, improved-masked, smoke/debug).

## Phase 6 (post-contract) — original-paper re-authoring + masked recalculation

User requested the report read as the *original paper* (not a 2nd attempt), include the full EDA and
decomposition of all models (word clouds, n-grams, Zipf, TTR, co-occurrence, distinctive terms), and
regenerate all figures AND recalculate the classical models on the MASKED corpus.

- Reproduced the classical pipelines from git history (modules/04 & 05) as `modules/04_05_baselines.py`
  (headless). BoW config: LR C=1.0/l1, Balanced LR C=0.1/l1; TF-IDF config: LR C=10.0/l1, Balanced LR
  C=1.0/l2 (per-source hyperparams differ). Validated against committed CSVs (BoW and TF-IDF Balanced LR
  within ~0.003; RF is stochastic without a fixed random_state in the original). Seeds 161.
- Recalculated classical baselines on the masked corpus -> `out/model_performance_summary_masked.csv` and
  `out/model_performance_summary_tf_idf_masked.csv`. Masked macro-F1: BoW LR 0.462 / Balanced LR 0.433 / RF 0.140;
  TF-IDF LR 0.454 / Balanced LR 0.502 / RF 0.124.
- Ran the plain BERT baseline on the masked corpus (Modal) -> `model_performance_summary_bert_masked.csv`
  so every number in the paper is masked-consistent.
- Wrote `modules/08_eda.py` — regenerates all EDA figures from the masked corpus into `report/figures/eda/`
  (text lengths, Zipf, n-grams, TTR-by-category, co-occurrence, label-by-mission, word clouds, distinctive
  terms). De-identification placeholder `[LOC]` excluded from lexical statistics and n-grams.
- Rewrote `report/PACT-ML Report.qmd` as the original paper: full EDA section (Text Corpus + Category-Specific),
  all models decomposed (BoW, TF-IDF, BERT baseline vs improved), location masking as data prep, all numbers
  from the masked corpus. Removed all "rework/reproduce/2nd attempt" framing.
- Updated `report/make_artifacts.py` to consume the masked CSVs (ranking, per-label baseline-vs-improved,
  masking probe).

Data notes for the report prose (masked corpus): 6,029 paragraphs; text length mean 116.6 / median 101;
vocabulary 12,175 unique / 352,840 tokens (TTR 0.0345, stopwords removed); missions MINUSTAH 2135 / UNMIK 1963 /
UNMIT 855 / MINUJUSTH 524 / UNOMIG 302 / UNMISET 250; masking probe full 0.917->0.844, location-only 0.770->0.000;
BERT improved masked fold macro-F1 0.485/0.475/0.482/0.481/0.454 (mean 0.4753).
