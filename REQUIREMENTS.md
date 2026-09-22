# PACT-ML Rework — Autonomous Agent Contract (walk-away)

Status: DRAFT v0.1 (2026-09-22) — awaiting human sign-off
Experiment: fully autonomous LLM coding agent reworks the BERT model stage of PACT-ML
Thesis framing: this document IS the treatment — a human writes requirements, an agent runs without interaction, we measure what comes back.

## 1. Context

PACT-ML (`github.com/flixi67/PACT-ML`) codes UN peacekeeping report paragraphs into 7
activity categories (multi-label text classification). The repo has a working pipeline:
PDF parsing (modules 01-03), classical baselines (04-05), and a BERT-class model
(module 06: xlm-roberta-base, 5-fold CV, 4 epochs, batch 16, seq 256, lr 2e-5, HF Trainer).

The report (`report/PACT-ML Report.qmd`, Quarto, JASA format) is the paper describing the
whole project. This rework concerns the BERT model stage ONLY, followed by a full
re-write and re-render of the report.

## 2. Human decisions (locked 2026-09-22)

- D1 Compute: Modal (per-second GPU billing). Agent brain stays on its hosted API; Modal is the rented muscle.
- D2 Target: this repo, branch `rework/autonomous-2026-09`. Work in this branch; never touch `main`.
- D3 Budget: hard caps below. Expected spend is single-digit dollars; caps are safety rails.
- D4 Autonomy: FULL. After the human signs off, the agent runs with no interaction until done, blocked, or over budget.

## 3. Scope

### In scope
- Module 06 (the BERT-class model): reproduce, then improve.
- The environment specification for the model stage (current `environment.yml` is empty — must be made real and pinned).
- `out/model_performance_summary_bert.csv` and any new result artifacts.
- Location de-identification for the model stage: mask location-based hints (countries, cities, regions, demonyms — GPE/LOC named entities) so the model cannot cheat on mission-specific terms (e.g. Georgia → UNMIK). The frozen `data/` CSVs are untouched; masking produces a derived, reproducible training set, applied identically at train and eval time. Mission-acronym handling (MINUSTAH, UNMIK, ...) is the agent's documented discretion.
- The report: FULL re-authoring (see criterion 7) + re-render to HTML via Quarto, with tables/figures generated from actual runs.
- README updates describing the reworked model stage and how to reproduce it.

### Out of scope (do NOT touch)
- Modules 01-05 (clustering, PDF parsing, TF-IDF baselines) and their outputs.
- `data/` (all CSVs and PDFs are frozen inputs).
- The `wandb/`, `logs/`, `modules/archive/` directories.
- The task definition: same 7 categories, same labels, same train/val split mechanism (IterativeStratification).
- Any change to `main` or to the report's core claims about the DATA (only the model stage + its results/interpretation are reworked).

## 4. Baseline to beat (measured, from the committed run)

The committed `out/model_performance_summary_bert.csv` (xlm-roberta-base, current config):

- F1_micro per fold ≈ 0.49 / 0.39 / 0.40 / 0.38 / 0.21
- Per-label recall shows class-collapse: StateAdministration, RefugeeAssistance, LegalReform,
  CivilSocietyAssistance reach 0.0 recall in most folds. Only PoliceReform and
  Operations_PatrolsInterventions are predicted meaningfully.

The rework must (a) reproduce this configuration first and record whether the numbers
match (report any divergence — do not silently assume the committed CSV is correct), and
(b) beat it honestly.

## 5. Acceptance criteria (hard, all must hold)

1. REPRODUCE FIRST: re-run the original module-06 configuration on the frozen data, same
   5-fold IterativeStratification, and write `out/model_performance_summary_bert.csv`
   (or equivalent) from the actual run. Record fold-level F1_micro/F1_macro/per-label
   metrics. If numbers diverge from the committed CSV by more than noise, document why.
2. IMPROVE: the new model must beat the reproduced baseline. Primary metric: macro-F1
   (5-fold mean). Secondary: micro-F1, and per-label F1 for the minority classes —
   a model that still predicts 0.0 for 4 of 7 labels is NOT an improvement even with
   higher micro-F1. At minimum one previously-zero label must reach a non-trivial F1
   without degrading PoliceReform/Operations.
3. LOCATION MASKING: build a reproducible de-identification step for the model-stage
   corpus that removes location-based hints — countries, cities, regions, demonyms
   (at minimum GPE/LOC named entities via NER). Frozen `data/` CSVs stay untouched;
   masking produces a derived training set, applied identically at train and eval time.
   Mission acronyms (MINUSTAH, UNMIK, ...) are the agent's documented discretion.
   Validate that the shortcut is actually gone (feature attribution / ablation, and/or
   a mission-level hold-out), and report the masking's effect on metrics.
4. HONEST VALIDATION: all hyperparameter, threshold, loss, and architecture choices must
   be tuned ONLY inside each training fold's validation split (nested discipline).
   Final fold-level numbers must come from the held-out test portion. No tuning on test.
   Fix every seed that can be fixed; report seeds.
5. HEADLESS: the model stage must run as scripts (no notebooks required to execute).
   Notebooks may remain as documentation but must not be the executable path.
6. ENV: a real, pinned environment (e.g. `requirements.txt` and/or a working
   `environment.yml`) with exact package versions, verified by a fresh install.
7. REPORT — FULL RE-AUTHORING: every section of `report/PACT-ML Report.qmd` is re-written
   from scratch with new prose (Introduction, Data, Methods, Results, Discussion,
   Conclusion) — no section retains the original wording. Data and baseline facts stay
   consistent with the repo (parsing/clustering/TF-IDF values are committed and remain);
   model-stage numbers come from the new runs; `bibliography.bib` is reused. Quarto
   render to HTML must succeed, and every number in the report must be traceable to a
   run artifact.
8. COMMIT: everything on the branch, committed with clear messages, including a
   `RUN_LOG.md` documenting the agent's own run (steps, failures, fixes, costs).

## 6. Budget & safety rails (hard)

- Modal: $30 hard cap. GPU-hours: 8 hard cap. Prefer L4; a single L4 covers the expected work.
- Agent tokens: ~$10 hard cap.
- Wall-clock: 24 h hard cap.
- If a cap is hit or a genuine blocker appears: STOP, write the state into `RUN_LOG.md`
  and the branch, and finish with a summary of what was and wasn't done. Do not burn
  budget retrying the same failure more than twice.

## 7. Autonomy rules (the walk-away part)

- The agent self-recovers: on error, diagnose, fix, retry — log each incident in RUN_LOG.md.
- Never stop to ask the human anything. If a decision is genuinely ambiguous, pick the
  option most consistent with this contract and note it in RUN_LOG.md.
- Preserve negative results: if an improvement attempt fails, keep the evidence and say so.
- Do not touch credentials, `~`, or anything outside this repo and Modal's billing page.

## 8. Deliverables

- Branch with all code, pinned env, regenerated results, re-rendered report, README, RUN_LOG.md.
- A short final summary (what was changed, what improved, what didn't, spend).
