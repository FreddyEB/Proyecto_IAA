"""
Random Forest model for teaching assistant recommendation.

Label: 1 = Aceptado, 0 = Rechazado (from historical postulaciones)
Features: NOTA_CURSO, PROMEDIO, CARGA_ACTUAL, EXPERIENCIA, TIPO_NUM

The model replaces the fixed linear weights with learned probabilities.
predict_proba(X)[:,1] is used as the candidate score.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import LabelEncoder

FEATURES = ["NOTA_CURSO", "PROMEDIO", "CARGA_ACTUAL", "EXPERIENCIA", "TIPO_NUM"]
FEATURE_LABELS = {
    "NOTA_CURSO": "Nota en el curso",
    "PROMEDIO": "Promedio acumulado",
    "CARGA_ACTUAL": "Carga académica",
    "EXPERIENCIA": "Experiencia previa",
    "TIPO_NUM": "Tipo de ayudantía",
}


def build_training_data(
    postulaciones: pd.DataFrame,
    notas: pd.DataFrame,
    promedios: pd.DataFrame,
    carga: pd.DataFrame,
) -> pd.DataFrame:
    """
    Joins historical postulaciones (Aceptado/Rechazado) with academic features.
    Returns a DataFrame with FEATURES + 'label' column.
    """
    labeled = postulaciones[postulaciones["Estado"].isin(["Aceptado", "Rechazado"])].copy()
    labeled["label"] = (labeled["Estado"] == "Aceptado").astype(int)
    labeled["RUT"] = labeled["RUT"].astype(str)
    labeled["Curso"] = labeled["Curso"].astype(str).str.strip()
    labeled["Materia"] = labeled["Materia"].astype(str).str.strip()

    # Best grade per RUT+MATERIA+CURSO
    notas2 = notas.copy()
    notas2["RUT"] = notas2["RUT"].astype(str)
    best_nota = (
        notas2.groupby(["RUT", "MATERIA", "CURSO"])["NOTA"]
        .max()
        .reset_index(name="NOTA_CURSO")
    )

    df = labeled.merge(
        best_nota,
        left_on=["RUT", "Materia", "Curso"],
        right_on=["RUT", "MATERIA", "CURSO"],
        how="left",
    )
    df = df.merge(
        promedios.rename(columns={"PROMEDIO  GENERAL  ACUMULADO": "PROMEDIO"}),
        on="RUT",
        how="left",
    )
    df = df.merge(carga, on="RUT", how="left")

    exp = (
        postulaciones[postulaciones["Estado"] == "Aceptado"]
        .groupby("RUT")
        .size()
        .reset_index(name="EXPERIENCIA")
    )
    exp["RUT"] = exp["RUT"].astype(str)
    df = df.merge(exp, on="RUT", how="left")
    df["EXPERIENCIA"] = df["EXPERIENCIA"].fillna(0)
    df["CARGA_ACTUAL"] = df["CARGA_ACTUAL"].fillna(0)

    # Encode tipo de ayudante
    le = LabelEncoder()
    df["TIPO_NUM"] = le.fit_transform(df["Tipo de ayudante"].fillna("Desconocido"))

    return df[FEATURES + ["label"]].dropna()


def train(training_data: pd.DataFrame) -> tuple[RandomForestClassifier, dict]:
    """
    Trains a Random Forest on the training data.
    Returns (model, metrics_dict).
    """
    X = training_data[FEATURES].values
    y = training_data["label"].values

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
    )

    # Cross-validation metrics
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_accuracy = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
    cv_roc_auc = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")

    # Fit on full data for production use
    model.fit(X, y)

    metrics = {
        "cv_accuracy_mean": float(cv_accuracy.mean()),
        "cv_accuracy_std": float(cv_accuracy.std()),
        "cv_roc_auc_mean": float(cv_roc_auc.mean()),
        "cv_roc_auc_std": float(cv_roc_auc.std()),
        "n_samples": len(y),
        "n_accepted": int(y.sum()),
        "n_rejected": int((y == 0).sum()),
        "feature_importances": dict(
            zip(FEATURES, model.feature_importances_.round(4))
        ),
    }

    return model, metrics


def predict_scores(
    model: RandomForestClassifier,
    candidates: pd.DataFrame,
) -> pd.Series:
    """
    Returns P(Aceptado) for each row in candidates.
    candidates must have all FEATURES columns (NaN → 0).
    """
    X = candidates[FEATURES].fillna(0).values
    return pd.Series(
        model.predict_proba(X)[:, 1],
        index=candidates.index,
        name="SCORE",
    )
