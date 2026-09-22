"""Module 07 — Location de-identification for the model stage.

Produces a derived, reproducible corpus (`out/derived/merged_data_masked.csv`)
in which location-based hints are removed from each paragraph so the model
cannot cheat on mission-specific terms (e.g. Georgia -> UNOMIG, Haiti ->
MINUSTAH). The frozen `data/merged_data.csv` is untouched.

What is masked (applied identically at train and eval time):
  1. GPE/LOC named entities detected by NER (dslim/bert-base-NER, English).
  2. The six mission acronyms (MINUSTAH, UNMIK, UNMIT, MINUJUSTH, UNOMIG,
     UNMISET) — treated as location hints per the contract's discretion note.
  3. A gazetteer of geonyms/demonyms for the six missions' countries
     (Haiti, Kosovo, Timor-Leste, Georgia) that NER frequently misses
     (demonyms in particular).

Validation (criterion 3): a mission-predictability probe. A TF-IDF +
LogisticRegression classifier predicts the mission from a paragraph's text.
If masking removed the location shortcut, mission-predictability should fall
from high (near-perfect, because the acronym/location is in the text) toward
chance (1/6). The probe is run 5-fold CV on both corpora.

Run:  python modules/07_location_masking.py [--out out/derived/merged_data_masked.csv]
NER requires the pinned env (see requirements.txt); run on Modal or a machine
with the env installed.
"""
from __future__ import annotations

import argparse
import re

import numpy as np
import pandas as pd

from rework_common import DATA_PATH, MISSIONS, TARGET_CATEGORIES

MASK_TOKEN = "[LOC]"

# Mission acronyms -> the geonym/demonym sets they correspond to.
MISSION_GEO = {
    "MINUSTAH": [
        "Haiti", "Haitian", "Haitians", "Port-au-Prince", "Port au Prince",
        "Cap-Haïtien", "Cap-Haitien", "Jacmel", "Les Cayes", "Gonaïves",
        "Gonaives", "Hinche", "Léogâne", "Leogane", "Petit-Goâve",
        "Croix-des-Bouquets",
    ],
    "UNMIK": [
        "Kosovo", "Kosovar", "Kosovars", "Pristina", "Priština", "Prizren",
        "Mitrovica", "Gnjilane", "Peja", "Peć", "Gjakova", "Ferizaj",
        "Uroševac", "Djakovica",
    ],
    "UNMIT": [
        "Timor-Leste", "Timor Leste", "East Timor", "Timorese", "Dili",
        "Baucau", "Maliana", "Oecusse", "Oecussi", "Ermera", "Suai",
        "Liquiçá", "Liquica", "Aileu",
    ],
    "MINUJUSTH": [
        "Haiti", "Haitian", "Haitians", "Port-au-Prince", "Port au Prince",
        "Cap-Haïtien", "Cap-Haitien", "Jacmel", "Les Cayes", "Gonaïves",
        "Hinche", "Léogâne", "Petit-Goâve",
    ],
    "UNOMIG": [
        "Georgia", "Georgian", "Georgians", "Abkhazia", "Abkhaz", "Abkhazian",
        "South Ossetia", "Sukhumi", "Tbilisi", "Zugdidi", "Gali",
        "Ochamchire", "Kodori", "Gori",
    ],
    "UNMISET": [
        "Timor-Leste", "Timor Leste", "East Timor", "Timorese", "Dili",
        "Baucau", "Maliana", "Oecusse", "Ermera", "Suai", "Liquiçá", "Aileu",
    ],
}


def build_gazetteer() -> list[str]:
    tokens = set(MISSIONS)
    for geo in MISSION_GEO.values():
        tokens.update(geo)
    return sorted(tokens)


def load_ner_pipeline():
    from transformers import pipeline

    return pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")


def _mask_char_ranges(text: str, ranges) -> str:
    """Replace the given [start,end) character ranges with the mask token."""
    if not ranges:
        return text
    ranges = sorted(ranges)
    parts = []
    prev = 0
    for s, e in ranges:
        if s > prev:
            parts.append(text[prev:s])
        parts.append(MASK_TOKEN)
        prev = e
    parts.append(text[prev:])
    return "".join(parts)


def ner_ranges(text: str, ner):
    if ner is None:
        return []
    ranges = []
    for ent in ner(text):
        g = ent.get("entity_group")
        if g in ("GPE", "LOC"):
            ranges.append((ent["start"], ent["end"]))
    return ranges


def gazetteer_ranges(text: str, gazetteer: list[str]) -> list:
    ranges = []
    for token in gazetteer:
        for m in re.finditer(re.escape(token), text, flags=re.IGNORECASE):
            ranges.append((m.start(), m.end()))
    return ranges


def mask_text(text: str, ner, gazetteer: list[str]) -> str:
    ranges = ner_ranges(text, ner) + gazetteer_ranges(text, gazetteer)
    # merge overlapping / abutting ranges to avoid double replacement
    ranges = sorted(set(ranges))
    merged = []
    for s, e in ranges:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return _mask_char_ranges(text, merged)


def probe_mission_accuracy(paragraphs: np.ndarray, missions: np.ndarray) -> float:
    """5-fold CV accuracy of a TF-IDF + LogisticRegression mission classifier."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold
    from sklearn.pipeline import make_pipeline

    pipe = make_pipeline(TfidfVectorizer(max_features=20000), LogisticRegression(max_iter=1000))
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    accs = []
    for tr, te in skf.split(paragraphs, missions):
        pipe.fit(paragraphs[tr], missions[tr])
        accs.append(float((pipe.predict(paragraphs[te]) == missions[te]).mean()))
    return float(np.mean(accs))


def location_only_features(paragraphs: np.ndarray) -> np.ndarray:
    """Per-paragraph feature vector = count of location tokens per mission geo-set.

    This isolates the *location shortcut*: if a paragraph mentions 'Haiti' or
    'MINUSTAH', the feature for the MINUSTAH geo-set is >0. After masking these
    tokens are removed, so the features collapse to zeros and mission can no
    longer be predicted from location hints alone.
    """
    n = len(paragraphs)
    keys = sorted(MISSION_GEO.keys())
    feats = np.zeros((n, len(keys)))
    for i, text in enumerate(paragraphs):
        for j, k in enumerate(keys):
            feats[i, j] = sum(text.count(t) for t in MISSION_GEO[k])
    return feats


def probe_location_only(paragraphs: np.ndarray, missions: np.ndarray) -> float:
    """5-fold CV accuracy of a mission classifier using ONLY location tokens."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold

    feats = location_only_features(paragraphs)
    if feats.sum() == 0:
        return None  # no location signal left
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    accs = []
    for tr, te in skf.split(feats, missions):
        clf = LogisticRegression(max_iter=1000)
        clf.fit(feats[tr], missions[tr])
        accs.append(float((clf.predict(feats[te]) == missions[te]).mean()))
    return float(np.mean(accs))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/derived/merged_data_masked.csv")
    ap.add_argument("--ner-batch", type=int, default=64)
    ap.add_argument("--skip-ner", action="store_true",
                    help="Use gazetteer+acronym masking only (no transformer NER).")
    args = ap.parse_args()

    df = pd.read_csv(DATA_PATH)
    print(f"[masking] loaded {len(df)} paragraphs from {DATA_PATH}")

    gazetteer = build_gazetteer()
    ner = None if args.skip_ner else load_ner_pipeline()

    total_tokens = 0
    masked_texts = []
    for i, text in enumerate(df["paragraph"].astype(str)):
        masked = mask_text(text, ner, gazetteer)
        masked_texts.append(masked)
        total_tokens += text.count(MASK_TOKEN)
    df["paragraph"] = masked_texts
    df["paragraph"] = df["paragraph"].str.replace(MASK_TOKEN, MASK_TOKEN, regex=False)

    import os

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"[masking] wrote {args.out} ({len(df)} rows)")

    # Validation probe: mission predictability, unmasked vs masked.
    missions = df["fileName"].str.split("_").str[0].to_numpy()
    orig = pd.read_csv(DATA_PATH)["paragraph"].astype(str).to_numpy()
    acc_orig = probe_mission_accuracy(orig, missions)
    acc_masked = probe_mission_accuracy(np.array(masked_texts), missions)
    chance = 1.0 / len(set(missions))

    # Location-shortcut probe: mission predicted from location tokens alone.
    loc_orig = probe_location_only(orig, missions)
    loc_masked = probe_location_only(np.array(masked_texts), missions)
    print(f"[probe] mission-predictability (5-fold CV acc) unmasked={acc_orig:.3f} "
          f"masked={acc_masked:.3f} chance={chance:.3f}")
    print(f"[probe] reduction: {acc_orig - acc_masked:.3f}")
    print(f"[probe] location-only probe unmasked={loc_orig} masked={loc_masked} "
          f"(None = no location signal left)")

    # Log masking summary
    n_mask = sum(t.count(MASK_TOKEN) for t in masked_texts)
    n_docs = sum(1 for t in masked_texts if MASK_TOKEN in t)
    print(f"[masking] total masked spans={n_mask}, docs affected={n_docs}/{len(df)}")

    # Persist probe summary for the report
    import json

    summary = {
        "unmasked_full": acc_orig,
        "masked_full": acc_masked,
        "chance": chance,
        "unmasked_loc": (loc_orig if loc_orig is not None else 0.0),
        "masked_loc": (loc_masked if loc_masked is not None else 0.0),
        "reduction_full": acc_orig - acc_masked,
        "spans_masked": int(n_mask),
        "docs_affected": int(n_docs),
        "n_paragraphs": int(len(df)),
        "missions": sorted(set(missions.tolist())),
    }
    probe_json = os.path.join(os.path.dirname(args.out), "masking_probe.json")
    with open(probe_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[masking] wrote {probe_json}")


if __name__ == "__main__":
    main()
