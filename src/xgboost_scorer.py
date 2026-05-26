import os
import json
import numpy as np
from pathlib import Path

import xgboost as xgb

# Model lives at <repo_root>/models/xgboost_model.json.
# Falls back to /tmp/models/ when the repo path is not writable (e.g. Docker :ro mount).
_REPO_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "xgboost_model.json"
_TMP_MODEL_PATH  = Path("/tmp/models/xgboost_model.json")

WEIGHTS = {"skills": 0.40, "experience": 0.30, "education": 0.15, "projects": 0.15}


def _model_path() -> Path:
    """Return the first writable model path, preferring the repo location."""
    for p in (_REPO_MODEL_PATH, _TMP_MODEL_PATH):
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            # Check writeability with a probe
            probe = p.parent / ".write_probe"
            probe.touch()
            probe.unlink()
            return p
        except OSError:
            continue
    raise RuntimeError("No writable path found for XGBoost model.")


def _weighted_overall(row: dict) -> float:
    return (
        row["skills"]     * WEIGHTS["skills"]
        + row["experience"] * WEIGHTS["experience"]
        + row["education"]  * WEIGHTS["education"]
        + row["projects"]   * WEIGHTS["projects"]
    )


# ── STEP 1: Synthetic training data ──────────────────────────────────────────

def generate_synthetic_data(n: int = 500, seed: int = 42):
    """Generate synthetic labelled candidates to bootstrap the model."""
    rng = np.random.default_rng(seed)

    skills     = rng.uniform(0, 100, n)
    experience = rng.uniform(0, 100, n)
    education  = rng.uniform(0, 100, n)
    projects   = rng.uniform(0, 100, n)
    missing_kw = rng.integers(0, 9, n).astype(float)  # 0-8

    overall = (
        skills     * WEIGHTS["skills"]
        + experience * WEIGHTS["experience"]
        + education  * WEIGHTS["education"]
        + projects   * WEIGHTS["projects"]
    )

    X, y = [], []
    for i in range(n):
        score = overall[i]
        if score >= 60:
            label = 1
        elif score < 40:
            label = 0
        else:
            continue  # discard ambiguous middle band
        X.append([skills[i], experience[i], education[i], projects[i], missing_kw[i]])
        y.append(label)

    return np.array(X, dtype=float), np.array(y, dtype=int)


# ── STEP 2: Train and save ───────────────────────────────────────────────────

def train_and_save() -> xgb.XGBClassifier:
    """Train XGBoost on synthetic data, save to disk, return model."""
    X, y = generate_synthetic_data()

    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X, y)

    path = _model_path()
    model.save_model(str(path))
    print(f"[xgboost_scorer] Model trained on {len(y)} synthetic samples, saved to {path}")
    return model


def _load_model() -> xgb.XGBClassifier:
    """Load model from disk, training from scratch if not found."""
    for p in (_REPO_MODEL_PATH, _TMP_MODEL_PATH):
        if p.exists():
            m = xgb.XGBClassifier()
            m.load_model(str(p))
            return m
    print("[xgboost_scorer] No saved model found — training now.")
    return train_and_save()


# ── STEP 3: score_candidate ───────────────────────────────────────────────────

def score_candidate(section_scores: dict, missing_keywords: list) -> float:
    """
    Return fit probability (0.0–1.0) from XGBoost.

    Args:
        section_scores:   dict with keys skills, experience, education, projects (0-100)
        missing_keywords: list of missing skill strings
    """
    model = _load_model()

    features = np.array([[
        float(section_scores.get("skills",     50)),
        float(section_scores.get("experience", 50)),
        float(section_scores.get("education",  50)),
        float(section_scores.get("projects",   50)),
        float(len(missing_keywords)),
    ]])

    prob = model.predict_proba(features)[0][1]  # P(fit=1)
    return round(float(prob), 4)


# ── Train on first run ────────────────────────────────────────────────────────

if __name__ == "__main__":
    train_and_save()
    # Smoke test
    test_scores = {"skills": 85, "experience": 70, "education": 100, "projects": 65}
    test_missing = ["Docker", "Airflow"]
    prob = score_candidate(test_scores, test_missing)
    print(f"[xgboost_scorer] Smoke test — fit probability: {prob}")
