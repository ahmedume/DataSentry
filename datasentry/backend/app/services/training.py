from __future__ import annotations

import io
import json
import pickle

import numpy as np
import pandas as pd

from app.core.storage import storage


def _import_sklearn():
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.impute import SimpleImputer
        from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score, roc_auc_score
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
        return {
            "ColumnTransformer": ColumnTransformer,
            "RandomForestClassifier": RandomForestClassifier,
            "RandomForestRegressor": RandomForestRegressor,
            "SimpleImputer": SimpleImputer,
            "accuracy_score": accuracy_score,
            "f1_score": f1_score,
            "mean_absolute_error": mean_absolute_error,
            "r2_score": r2_score,
            "roc_auc_score": roc_auc_score,
            "train_test_split": train_test_split,
            "Pipeline": Pipeline,
            "OneHotEncoder": OneHotEncoder,
            "StandardScaler": StandardScaler,
        }
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "scikit-learn is required for model training. Install it with `pip install scikit-learn`."
        ) from e


def detect_task(df: pd.DataFrame, target: str) -> str:
    y = df[target].dropna()
    if pd.api.types.is_numeric_dtype(y):
        return "regression" if y.nunique() > 20 else "classification"
    return "classification"


def train(df: pd.DataFrame, target: str, task: str = "auto") -> dict:
    sk = _import_sklearn()
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found.")
    df = df.dropna(subset=[target]).copy()
    if df.shape[0] < 20:
        raise ValueError("Need at least 20 rows with a target value to train.")

    resolved_task = task if task in ("classification", "regression") else detect_task(df, target)
    y = df[target]
    X = df.drop(columns=[target])

    numeric = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
    categorical = [c for c in X.columns if c not in numeric]

    transformers = []
    if numeric:
        transformers.append(("num", sk["Pipeline"]([("imp", sk["SimpleImputer"](strategy="median")), ("sc", sk["StandardScaler"]())]), numeric))
    if categorical:
        transformers.append(("cat", sk["Pipeline"]([("imp", sk["SimpleImputer"](strategy="most_frequent")), ("oh", sk["OneHotEncoder"](handle_unknown="ignore"))]), categorical))

    if not transformers:
        raise ValueError("No usable features for training.")

    pre = sk["ColumnTransformer"](transformers)
    if resolved_task == "regression":
        est = sk["RandomForestRegressor"](n_estimators=120, random_state=42, n_jobs=-1)
    else:
        est = sk["RandomForestClassifier"](n_estimators=120, random_state=42, n_jobs=-1)

    pipe = sk["Pipeline"]([("pre", pre), ("est", est)])
    strat = y if (resolved_task == "classification" and y.nunique() > 1 and y.value_counts().min() >= 2) else None
    X_train, X_test, y_train, y_test = sk["train_test_split"](X, y, test_size=0.2, random_state=42, stratify=strat)

    pipe.fit(X_train, y_train)
    preds = pipe.predict(X_test)

    metrics: dict = {"task": resolved_task, "n_samples": int(df.shape[0]), "n_features": int(X.shape[1])}
    if resolved_task == "regression":
        metrics.update({
            "r2": round(float(sk["r2_score"](y_test, preds)), 4),
            "rmse": round(float(np.sqrt(np.mean((y_test - preds) ** 2))), 4),
            "mae": round(float(sk["mean_absolute_error"](y_test, preds)), 4),
        })
    else:
        metrics.update({
            "accuracy": round(float(sk["accuracy_score"](y_test, preds)), 4),
            "f1_macro": round(float(sk["f1_score"](y_test, preds, average="macro", zero_division=0)), 4),
        })
        if y.nunique() == 2:
            try:
                proba = pipe.predict_proba(X_test)[:, 1]
                metrics["roc_auc"] = round(float(sk["roc_auc_score"](y_test, proba)), 4)
            except Exception:
                pass

    importances = {}
    try:
        feat_names = pipe.named_steps["pre"].get_feature_names_out()
        imp = pipe.named_steps["est"].feature_importances_
        top = sorted(zip(feat_names.tolist(), imp.tolist()), key=lambda x: -x[1])[:15]
        importances = {str(k): round(float(v), 4) for k, v in top}
    except Exception:
        importances = {}

    model_bytes = pickle.dumps(pipe)
    return {"metrics": metrics, "feature_importances": importances, "model_bytes": model_bytes}


def save_model(job_id: str, model_bytes: bytes) -> str:
    p = storage.save_model(job_id, model_bytes)
    return str(p)
