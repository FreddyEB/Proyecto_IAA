"""
Random Forest model.

Label: 
1 = Aceptado 
0 = Rechazado

Features: NOTA_CURSO, PROMEDIO, EXPERIENCIA, TIPO_NUM
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import LabelEncoder

FEATURES = ["NOTA_CURSO", "PROMEDIO", "EXPERIENCIA", "TIPO_NUM"]
FEATURE_LABELS = {
    "NOTA_CURSO": "Nota en el curso",
    "PROMEDIO": "Promedio acumulado",
    "EXPERIENCIA": "Experiencia previa",
    "TIPO_NUM": "Tipo de ayudantía",
}


def build_training_data(
    postulaciones: pd.DataFrame,
    notas: pd.DataFrame,
    promedios: pd.DataFrame,
) -> pd.DataFrame:

    """
    Une las postulaciones historicas (Aceptado/Rechazado) con las features academicas.
     Devuelve un DataFrame listo para entrenar el modelo, con columnas FEATURES + "label".
     Solo incluye filas con label conocido (Aprobado/Rechazado).
     Si hay múltiples notas para el mismo RUT+MATERIA+CURSO, se queda con la mejor.
     Asume que postulaciones tiene columnas: RUT, Curso, Materia, Estado (Aceptado/Rechazado), Tipo de ayudante.
     Asume que notas tiene columnas: RUT, MATERIA, CURSO, NOTA.
     Asume que promedios tiene columnas: RUT, PROMEDIO  GENERAL  ACUMULADO.
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

    exp = (
        postulaciones[postulaciones["Estado"] == "Aceptado"]
        .groupby("RUT")
        .size()
        .reset_index(name="EXPERIENCIA")
    )
    exp["RUT"] = exp["RUT"].astype(str)
    df = df.merge(exp, on="RUT", how="left")
    df["EXPERIENCIA"] = df["EXPERIENCIA"].fillna(0)

    # Encode tipo de ayudante
    le = LabelEncoder()
    df["TIPO_NUM"] = le.fit_transform(df["Tipo de ayudante"].fillna("Desconocido"))

    return df[FEATURES + ["label"]].dropna()


def train(training_data: pd.DataFrame) -> tuple[RandomForestClassifier, dict]:
    """
    Random Forest con la data de entrenamiento (data de 2026-01)
    Return(model, metrics_dict)
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
    cv_f1 = cross_val_score(model, X, y, cv=cv, scoring="f1")

    # Fit on full data for production use
    model.fit(X, y)

    metrics = {
        "cv_accuracy_mean": float(cv_accuracy.mean()),
        "cv_accuracy_std": float(cv_accuracy.std()),
        "cv_roc_auc_mean": float(cv_roc_auc.mean()),
        "cv_roc_auc_std": float(cv_roc_auc.std()),
        "cv_f1_mean": float(cv_f1.mean()),
        "cv_f1_std": float(cv_f1.std()),
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
    X = candidates[FEATURES].fillna(0).values
    return pd.Series(
        model.predict_proba(X)[:, 1],
        index=candidates.index,
        name="SCORE",
    )
