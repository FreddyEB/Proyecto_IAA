"""
Motor de Scoring.

Filtros duros/base:
  1. El candidato debe haber aprobado el curso (NOTA >= MIN_PASSING_GRADE in RA311)
  2. No debe haber conflicto de horario entre los ramos inscritos por el candidato y el NRC objetivo (sino se descarta)

Score = P(Aceptado) del modelo Random Forest.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

MIN_PASSING_GRADE = 4.75
MAX_GRADE = 7.0

DEFAULT_WEIGHTS = {"nota": 0.40, "promedio": 0.15, "experiencia": 0.20, "ia": 0.25}

TYPES_REQUIRING_ATTENDANCE = {"de Catedra", "Laboratorio Tipo 1", "Laboratorio Tipo 2"}


def normalize_weights(weights: dict) -> dict:
    total = sum(weights.values())
    if total <= 0:
        n = len(weights)
        return {k: 1.0 / n for k in weights}
    return {k: v / total for k, v in weights.items()}


def compute_hybrid_score(df: pd.DataFrame, p_ia, weights: dict) -> pd.Series:
    w = normalize_weights(weights)
    norm_nota = (df["NOTA_CURSO"] / MAX_GRADE).clip(0, 1)
    norm_prom = (df["PROMEDIO"] / MAX_GRADE).clip(0, 1)
    max_exp = df["EXPERIENCIA"].max()
    if max_exp and max_exp > 0:
        norm_exp = (df["EXPERIENCIA"] / max_exp).clip(0, 1)
    else:
        norm_exp = df["EXPERIENCIA"] * 0.0
    p_ia = pd.Series(list(p_ia), index=df.index)
    score = (w["nota"] * norm_nota + w["promedio"] * norm_prom
             + w["experiencia"] * norm_exp + w["ia"] * p_ia)
    return score.clip(0, 1)


def _parse_time_block(block: str) -> tuple[int, int] | None:
    block = str(block).strip()
    if not block or block == "nan":
        return None
    try:
        parts = block.replace(" ", "").split("-")
        def to_min(t):
            h, m = t.split(":")
            return int(h) * 60 + int(m)
        return to_min(parts[0]), to_min(parts[1])
    except Exception:
        return None


def _has_schedule_conflict(cand_sched: dict, target_sched: dict) -> bool:
    for day, target_blocks in target_sched.items():
        for ts, te in target_blocks:
            for cs, ce in cand_sched.get(day, []):
                if ts < ce and cs < te:
                    return True
    return False


def _build_schedule_map(horarios_df: pd.DataFrame) -> dict:
    day_cols = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"]
    schedule = {}
    for _, row in horarios_df.iterrows():
        nrc = str(row["NRC"]).strip()
        for day in day_cols:
            if day not in row or not row[day]:
                continue
            block = _parse_time_block(row[day])
            if block:
                schedule.setdefault(nrc, {}).setdefault(day, []).append(block)
    return schedule


def schedule_filter_passes(tipo: str, has_conflict: bool) -> bool:
    if tipo in TYPES_REQUIRING_ATTENDANCE:
        return not has_conflict
    return True


def rank_candidates(
    target_nrc: str,
    postulaciones: pd.DataFrame,
    notas: pd.DataFrame,
    promedios: pd.DataFrame,
    horarios: pd.DataFrame,
    ramos_inscritos: pd.DataFrame,
    model: RandomForestClassifier,
    weights: dict = None,
    top_n: int = 5,
) -> pd.DataFrame:
    from model import predict_scores
    from sklearn.preprocessing import LabelEncoder

    weights = weights or DEFAULT_WEIGHTS
    out_cols = ["RUT", "TIPO_AYUDANTE", "NOTA_CURSO", "EXPERIENCIA",
                "PROMEDIO", "SCORE", "FILTRO_NOTA", "FILTRO_HORARIO"]

    nrc_info = horarios[horarios["NRC"] == target_nrc]
    if nrc_info.empty:
        return pd.DataFrame(columns=out_cols)

    materia = str(nrc_info.iloc[0]["MATERIA"]).strip()
    raw_curso = nrc_info.iloc[0]["CURSO"]
    try:
        curso = str(int(float(raw_curso)))
    except (ValueError, TypeError):
        curso = str(raw_curso).strip()

    cands_post = postulaciones[
        (postulaciones["NRC"] == target_nrc) &
        (postulaciones["Estado"].isin(["Pendiente", "Aceptado"]))
    ][["RUT", "Tipo de ayudante"]].drop_duplicates("RUT").rename(
        columns={"Tipo de ayudante": "TIPO_AYUDANTE"})
    if cands_post.empty:
        return pd.DataFrame(columns=out_cols)

    exp_counts = (
        postulaciones[postulaciones["Estado"] == "Aceptado"]
        .groupby("RUT").size().reset_index(name="EXPERIENCIA"))

    course_grades = (
        notas[(notas["MATERIA"] == materia) & (notas["CURSO"] == curso)]
        [["RUT", "NOTA"]].sort_values("NOTA", ascending=False)
        .drop_duplicates("RUT").rename(columns={"NOTA": "NOTA_CURSO"}))

    schedule_map = _build_schedule_map(horarios)
    target_sched = schedule_map.get(target_nrc, {})
    ri = ramos_inscritos.copy()
    ri["RUT"] = ri["RUT"].astype(str).str.strip()
    ri["NRC"] = ri["NRC"].astype(str).str.strip()
    enrolled_by_rut = ri.groupby("RUT")["NRC"].apply(list).to_dict()

    def get_cand_sched(rut):
        merged = {}
        for nrc in enrolled_by_rut.get(rut, []):
            for day, blocks in schedule_map.get(nrc, {}).items():
                merged.setdefault(day, []).extend(blocks)
        return merged

    df = cands_post.copy()
    df = df.merge(course_grades, on="RUT", how="left")
    df = df.merge(exp_counts, on="RUT", how="left")
    df = df.merge(promedios[["RUT", "PROMEDIO  GENERAL  ACUMULADO"]], on="RUT", how="left")
    df["NOTA_CURSO"] = df["NOTA_CURSO"].fillna(0)
    df["EXPERIENCIA"] = df["EXPERIENCIA"].fillna(0)
    df["PROMEDIO"] = df["PROMEDIO  GENERAL  ACUMULADO"].fillna(0)

    le = LabelEncoder()
    le.fit(["Corrector", "Coordinador Tipo 1", "Coordinador Tipo 2",
            "Laboratorio Tipo 1", "Laboratorio Tipo 2", "Proyecto", "de Catedra"])
    df["TIPO_NUM"] = df["TIPO_AYUDANTE"].apply(
        lambda x: le.transform([x])[0] if x in le.classes_ else 0)

    df["FILTRO_NOTA"] = df["NOTA_CURSO"] >= MIN_PASSING_GRADE
    df["_CONFLICT"] = df["RUT"].apply(
        lambda r: _has_schedule_conflict(get_cand_sched(r), target_sched))
    df["FILTRO_HORARIO"] = df.apply(
        lambda r: schedule_filter_passes(r["TIPO_AYUDANTE"], r["_CONFLICT"]), axis=1)

    eligible = df[df["FILTRO_NOTA"] & df["FILTRO_HORARIO"]].copy()
    if eligible.empty:
        df["SCORE"] = 0.0
        return df[out_cols].sort_values("NOTA_CURSO", ascending=False)

    p_ia = predict_scores(model, eligible)
    eligible["SCORE"] = compute_hybrid_score(eligible, p_ia, weights).round(4)
    result = eligible.sort_values("SCORE", ascending=False).head(top_n)
    return result[out_cols]
