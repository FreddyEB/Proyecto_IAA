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


def rank_candidates(
    target_nrc: str,
    postulaciones: pd.DataFrame,
    notas: pd.DataFrame,
    promedios: pd.DataFrame,
    carga: pd.DataFrame,
    horarios: pd.DataFrame,
    ug307: pd.DataFrame,
    model: RandomForestClassifier,
    top_n: int = 5,
) -> pd.DataFrame:
    """
    Retorna un DF con los candidatos top para el target_nrc.
    Score = P(Aceptado) del modelo Random Forest.
    """
    nrc_info = horarios[horarios["NRC"] == target_nrc]
    if nrc_info.empty:
        return pd.DataFrame()

    materia = str(nrc_info.iloc[0]["MATERIA"]).strip()
    raw_curso = nrc_info.iloc[0]["CURSO"]
    try:
        curso = str(int(float(raw_curso)))
    except (ValueError, TypeError):
        curso = str(raw_curso).strip()

    # Candidatos con postulaciones activas
    cands_post = postulaciones[
        (postulaciones["NRC"] == target_nrc) &
        (postulaciones["Estado"].isin(["Pendiente", "Aceptado"]))
    ][["RUT", "Tipo de ayudante"]].drop_duplicates("RUT").rename(
        columns={"Tipo de ayudante": "TIPO_AYUDANTE"}
    )

    if cands_post.empty:
        return pd.DataFrame()

    # Experiencia previa
    exp_counts = (
        postulaciones[postulaciones["Estado"] == "Aceptado"]
        .groupby("RUT").size().reset_index(name="EXPERIENCIA")
    )

    # Mejor nota para este curso
    course_grades = (
        notas[(notas["MATERIA"] == materia) & (notas["CURSO"] == curso)]
        [["RUT", "NOTA"]].sort_values("NOTA", ascending=False)
        .drop_duplicates("RUT")
        .rename(columns={"NOTA": "NOTA_CURSO"})
    )

    # Conflicto horario
    schedule_map = _build_schedule_map(horarios)
    target_sched = schedule_map.get(target_nrc, {})
    ug307 = ug307.copy()
    ug307["RUT"] = ug307["RUT"].astype(str).str.strip()
    ug307["NRC"] = ug307["NRC"].astype(str).str.strip()
    enrolled_by_rut = ug307.groupby("RUT")["NRC"].apply(list).to_dict()

    def get_cand_sched(rut):
        merged = {}
        for nrc in enrolled_by_rut.get(rut, []):
            for day, blocks in schedule_map.get(nrc, {}).items():
                merged.setdefault(day, []).extend(blocks)
        return merged

    # feature matrix
    df = cands_post.copy()
    df = df.merge(course_grades, on="RUT", how="left")
    df = df.merge(exp_counts, on="RUT", how="left")
    df = df.merge(promedios[["RUT", "PROMEDIO  GENERAL  ACUMULADO"]], on="RUT", how="left")
    df = df.merge(carga, on="RUT", how="left")

    df["NOTA_CURSO"] = df["NOTA_CURSO"].fillna(0)
    df["EXPERIENCIA"] = df["EXPERIENCIA"].fillna(0)
    df["PROMEDIO"] = df["PROMEDIO  GENERAL  ACUMULADO"].fillna(0)
    df["CARGA_ACTUAL"] = df["CARGA_ACTUAL"].fillna(0)

    # Encode tipo de ayudante
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    le.fit(["Corrector", "Coordinador Tipo 1", "Coordinador Tipo 2",
            "Laboratorio Tipo 1", "Laboratorio Tipo 2", "Proyecto", "de Catedra"])
    df["TIPO_NUM"] = df["TIPO_AYUDANTE"].apply(
        lambda x: le.transform([x])[0] if x in le.classes_ else 0
    )

    # Filtros duros/base
    df["FILTRO_NOTA"] = df["NOTA_CURSO"] >= MIN_PASSING_GRADE
    df["FILTRO_HORARIO"] = ~df["RUT"].apply(
        lambda r: _has_schedule_conflict(get_cand_sched(r), target_sched)
    )

    eligible = df[df["FILTRO_NOTA"] & df["FILTRO_HORARIO"]].copy()

    if eligible.empty:
        df["SCORE"] = 0.0
        return df[["RUT", "TIPO_AYUDANTE", "NOTA_CURSO", "EXPERIENCIA", "PROMEDIO", "CARGA_ACTUAL",
                    "SCORE", "FILTRO_NOTA", "FILTRO_HORARIO"]].sort_values("NOTA_CURSO", ascending=False)

    # Score = P(Aceptado) del Random Forest
    from model import predict_scores, FEATURES
    eligible["SCORE"] = predict_scores(model, eligible).round(4)

    result = eligible.sort_values("SCORE", ascending=False).head(top_n)
    return result[["RUT", "TIPO_AYUDANTE", "NOTA_CURSO", "EXPERIENCIA", "PROMEDIO", "CARGA_ACTUAL",
                   "SCORE", "FILTRO_NOTA", "FILTRO_HORARIO"]]
