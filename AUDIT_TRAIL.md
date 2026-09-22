# PACT-ML Autonomous Rework — Full Audit Trail

This is a faithful, chronological record of every tool call, argument, result,
failure, and internal decision made by the agent (Hermie / Hermes) while executing
`REQUIREMENTS.md`. It is reconstructed from the agent's own session context so the
work can be audited end-to-end. Companion files: `run_logs/*.txt` (per-run Modal
outputs), `RUN_LOG.md` (acceptance-criteria status + spend).

Branch: `rework/autonomous-2026-09`  |  Final commit: `2eb6956`  |  Run: 2026-09-22 ~13:30–18:20 (UTC+8)

---

## Phase 0 — Reconnaissance (read-only)

1. `read_file REQUIREMENTS.md` — full contract read. Established: reproduce first, improve,
   location-masking, honest nested validation, headless, pinned env, full report re-author,
   commit + RUN_LOG; hard caps Modal $30 / 8 GPU-hr, ~$10 tokens, 24 h.
2. `terminal git status/branch/ls` — confirmed clean tree on `rework/autonomous-2026-09`.
3. `terminal ls -R modules, multilabel_model_xlmr, modal, out, data, report` + `cat environment.yml, README`
   — mapped repo: module 06 (BERT), data/merged_data.csv, committed bert CSV, report (Quarto/R, JASA).
4. `read_file modules/06_roberta_model.py` — the baseline script (xlm-roberta-base, 5-fold
   IterativeStratification, 4ep/b16/seq256/lr2e-5, thr 0.5, HF Trainer).
5. `read_file out/model_performance_summary_bert.csv` — committed baseline (class-collapse confirmed).
6. `read_file modal/hello_gpu.py` — existing Modal pattern.
7. `tool_search todo` — attempted task tracking; the todo tool kept rejecting my JSON, so I dropped it
   and tracked via RUN_LOG.md instead (noted as a minor tooling quirk, no impact).
8. `terminal python pkg check + modal + quarto + git log` — local python 3.11 has only numpy; modal CLI
   (flixi67) and quarto 1.4.554 present; no pandas locally.
9. `terminal` data inspection — merged_data.csv: 6029 paragraphs, 7 labels, 6 missions
   (MINUSTAH, UNMIK, UNMIT, MINUJUSTH, UNOMIG, UNMISET); minority labels very rare (1.7–3.6%).
10. `terminal report headings + gitignore` — report structure; `.gitignore` reviewed.
11. `read_file report sections (796–955, 1096–1170)` — Methods/Results/Conclusion/Annex.
12. `terminal R check` — R is NOT installed. **Decision**: re-author the report using static tables
    + figures + `{{< include >}}` (no R/jupyter at render) so Quarto renders reliably.
13. `terminal quarto check + test render` — Quarto works; markdown-only render OK.
14. `read_file/report front matter (1–130)` — PACT 2.0 context, class-distribution facts.

## Phase 1 — Env + shared code (local, no GPU)

15. `write_file requirements.txt` — pinned: torch 2.5.1, transformers 4.46.2, tokenizers 0.20.1,
    datasets 3.1.0, accelerate 1.0.1, sentencepiece 0.2.0, sklearn 1.5.2, skmultilearn 0.2.0,
    pandas 2.2.3, numpy 1.26.4, evaluate 0.4.3.
16. `write_file environment.yml` — conda wrapper installing requirements.txt.
17. `write_file modules/rework_common.py` — data load, 5-fold IterativeStratification, per-label
    thresholds, metrics (matches committed CSV schema).
18. `write_file modules/07_location_masking.py` — NER (dslim/bert-base-NER) + mission-acronym +
    geonym/demonym gazetteer masking; mission-predictability + location-only probes.
19. `write_file modules/06_roberta_model.py` (rewrite) — headless CLI, `--mode baseline|improved`,
    nested inner 80/20 split, pos_weight (cap 15), per-label thresholds on inner-val only.
20. `uv venv + pip install` (local test venv) — installed pandas/numpy/sklearn/skmultilearn/matplotlib
    for quick non-GPU logic testing.
21. Local tests (`test_logic.py` via test venv): deterministic 5-fold splits verified; pos_weight;
    threshold tuning; location-only probe 0.93 (with location tokens) vs chance 0.167 — design works.
22. `patch` fixes while testing masking probe (None-guard, np.array for list, location_only_features
    signature). Local gazetteer-only run: probe 0.917→0.851, location-only 0.77→None.

## Phase 2 — Modal runner (iterative debugging)

23. `write_file modal/run_pact_ml.py` (v1) — used `modal.Mount.from_local_dir` +
    `Image.copy_local_file`. **FAILED** at import: `module 'modal' has no attribute 'Mount'`.
24. **Decision**: inspected the installed Modal package (`modal/__init__.py`, `image.pyi`) — this Modal
    version exports no `Mount`; the API is `Image.add_local_dir(copy=False)` + `Volume`. Rewrote runner.
25. v2 `pip_install(REQS)` (list) — **FAILED** Dockerfile parse `' 'datasets==3.1.0`. Root cause: each
    requirements line retained its trailing `\n`. Fixed by `.strip()` each line + `pip_install(*REQS)`.
26. v3 — **FAILED** in container: `FileNotFoundError /requirements.txt`. The runner is re-imported inside
    the container where ROOT_LOCAL isn't the repo root. Fixed with path-robust `_read_reqs()` +
    `is_local()` guard for the `add_local_dir` root. Verified local import OK.
27. First successful masking run (proc_8f68d8202f69) — see `run_logs/01_masking.txt`. Downloaded
    masked corpus + probe JSON via `modal volume get`.

## Phase 3 — Training runs

28. Baseline 1-fold smoke — **FAILED** with `compute_loss() got unexpected kwarg 'num_items_in_batch'`
    (transformers 4.46 API). Fixed: added `num_items_in_batch=None, **kwargs` to `compute_loss`.
29. Baseline 1-fold smoke — OK (fold-1 macro 0.353). Downloaded/verified CSV schema.
30. **Full baseline reproduce** (proc_81c7836ed689, ~41 min) — see `run_logs/02_`. Result macro-F1
    mean 0.151 vs committed 0.179; same class-collapse. Downloaded over committed CSV.
31. Improved 1-fold — **FAILED** `RuntimeError: tensors on cuda:0 and cpu` (pos_weight on CPU). Fixed:
    `.to(logits.device)` in `compute_loss`.
32. Improved 1-fold — OK: all 7 labels recovered (fold-1 macro 0.535). Verified the improvement approach.
33. **Full improved (unmasked)** (proc_58f105db7462, ~36 min) — see `run_logs/03_`. macro-F1 0.479.
34. **Full improved (masked)** (proc_67e2ebb8f112, ~33 min) — see `run_logs/04_`. macro-F1 0.475.
35. Downloaded all three CSVs into `out/` (used `--force` to overwrite the committed bert CSV with the
    actual reproduction).

## Phase 4 — Report + artifacts

36. `write_file report/make_artifacts.py` — generates tables (ranking, per-label) + figures from the
    out/*.csv; fixed boxplot `labels` kwarg, per-label F1 NaN handling, ranking at (Model, Source)
    level, and added captions+`{#tbl-...}` labels to each table so Quarto crossrefs resolve.
37. `write_file report/PACT-ML Report.qmd` (full re-author; old file removed first) — new prose for
    Introduction, Data (incl. location de-identification), Methods (nested discipline), Results,
    Discussion, Conclusion, Annex; bibliography.bib reused.
38. `quarto render` — iterated: first failed (missing masking_probe.md → added placeholder), then
    crossref warnings (tables lacked captions → added caption+label), finally **rendered with zero
    warnings**. Re-rendered after real artifacts.
39. `write_file README.md` — reworked model stage + reproduction steps.
40. `write_file RUN_LOG.md` — acceptance-criteria status, incidents, decisions, spend estimate.

## Phase 5 — Cleanup + commit

41. `terminal` — removed test/scratch CSVs; added `.venv*` to `.gitignore`; removed local test venvs.
42. `git add -A && git commit` — commit `2eb6956` on `rework/autonomous-2026-09` (tree clean).
43. Verified: branch, clean tree, re-rendered HTML, all CSVs + tables present.

## Phase 6 — Audit log (this request)

44. Created `run_logs/*.txt` (per-run Modal outputs) + this `AUDIT_TRAIL.md`; will commit.

---

## Key results (all traceable to run artifacts)

| Metric | Baseline (repro) | Improved (unmasked) | Improved (masked) |
|---|---|---|---|
| Macro-F1 (5-fold mean) | 0.151 | 0.479 | 0.475 |
| Micro-F1 | 0.369 | 0.526 | 0.513 |
| Labels at F1≈0 | 4 | 0 | 0 |
| Location-only mission probe | 0.770 | — | chance (0.167) |

Spend estimate: ~2.4 L4 GPU-hr ≈ $2–3 (caps: 8 GPU-hr, $30). Committed locally, NOT pushed.

## Known tooling quirks (for the audit)

- The `todo` tool rejected my JSON payloads consistently; I tracked progress in RUN_LOG.md instead.
- `process_manage` session logs are retained only ~7 days / latest 64; several older process IDs returned
  "not_found" when I tried to re-fetch them after the run — hence this audit trail + run_logs were
  reconstructed from in-context outputs.
- Local `python` (Hermes venv) has no pandas; all non-GPU analysis used a scratch venv, since removed.
