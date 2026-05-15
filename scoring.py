"""
Scoring engine for teaching assistant recommendations.

Score(p, c) = w_nota * Nota(p,c) + w_exp * Exp(p) + w_prom * Promedio(p) + w_carga * Carga(p)

All variables normalized to [0, 1] before weighting.
Hard filters (applied before scoring):
  1. Candidate must have passed the course (NOTA >= MIN_PASSING_GRADE in RA311)
  2. No schedule conflict between candidate's enrolled courses and the target NRC
"""

import pandas as pd

# --- Weights (must sum to 1.0) ---
W_NOTA = 0.35
W_EXP = 0.20
W_PROM = 0.10
W_CARGA = 0.05
# Horario is a hard binary filter (not a weighted variable)

MIN_PASSING_GRADE = 4.0
MAX_GRADE = 7.0
HIGH_LOAD_THRESHOLD = 6  # ramos — penalizes candidates above this


def _parse_time_block(block: str) -> tuple[int, int] | None:
    """Parse '10:30 -13:20' → (630, 800) minutes from midnight."""
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


def _has_schedule_conflict(candidate_ruts_schedule: dict, target_schedule: dict) -> bool:
    """
    candidate_ruts_schedule: {day: [(start, end), ...]}
    target_schedule: {day: [(start, end), ...]}
    Returns True if any block overlaps.
    """
    for day, target_blocks in target_schedule.items():
        cand_blocks = candidate_ruts_schedule.get(day, [])
        for ts, te in target_blocks:
            for cs, ce in cand_blocks:
                if ts < ce and cs < te:  # overlap
                    return True
    return False


def _build_schedule_map(horarios_df: pd.DataFrame) -> dict:
    """Returns {nrc: {day: [(start, end)]}}"""
    day_cols = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"]
    schedule = {}
    for _, row in horarios_df.iterrows():
        nrc = str(row["NRC"]).strip()
        if nrc not in schedule:
            schedule[nrc] = {}
        for day in day_cols:
            if day not in row or not row[day]:
                continue
            block = _parse_time_block(row[day])
            if block:
                schedule[nrc].setdefault(day, []).append(block)
    return schedule


def _get_candidate_schedule(rut: str, enrolled_nrcs: list, schedule_map: dict) -> dict:
    """Merge all schedule blocks for a candidate's enrolled courses."""
    merged = {}
    for nrc in enrolled_nrcs:
        for day, blocks in schedule_map.get(nrc, {}).items():
            merged.setdefault(day, []).extend(blocks)
    return merged


def rank_candidates(
    target_nrc: str,
    postulaciones: pd.DataFrame,
    notas: pd.DataFrame,
    promedios: pd.DataFrame,
    carga: pd.DataFrame,
    horarios: pd.DataFrame,
    ug307: pd.DataFrame,
    top_n: int = 5,
) -> pd.DataFrame:
    """
    Returns a ranked DataFrame of the top_n candidates for target_nrc.
    Columns: RUT, NOTA_CURSO, EXPERIENCIA, PROMEDIO, CARGA_ACTUAL,
             SCORE, FILTRO_NOTA, FILTRO_HORARIO
    """
    # --- Identify the course for this NRC ---
    nrc_info = horarios[horarios["NRC"] == target_nrc]
    if nrc_info.empty:
        return pd.DataFrame()

    materia = str(nrc_info.iloc[0]["MATERIA"]).strip()
    # CURSO may be stored as float (e.g. 1100.0) in RA311 — normalize to int string
    raw_curso = nrc_info.iloc[0]["CURSO"]
    try:
        curso = str(int(float(raw_curso)))
    except (ValueError, TypeError):
        curso = str(raw_curso).strip()

    # --- Candidates: only Pendiente or Aceptado postulations for this NRC ---
    candidates = postulaciones[
        (postulaciones["NRC"] == target_nrc) &
        (postulaciones["Estado"].isin(["Pendiente", "Aceptado"]))
    ][["RUT"]].drop_duplicates()

    if candidates.empty:
        return pd.DataFrame()

    # --- Experiencia previa: count of 'Aceptado' rows per RUT across ALL NRCs ---
    exp_counts = (
        postulaciones[postulaciones["Estado"] == "Aceptado"]
        .groupby("RUT")
        .size()
        .reset_index(name="EXPERIENCIA")
    )

    # --- Nota en el curso (MATERIA + CURSO match) ---
    course_grades = notas[
        (notas["MATERIA"] == materia) & (notas["CURSO"] == curso)
    ][["RUT", "NOTA"]].sort_values("NOTA", ascending=False).drop_duplicates("RUT")
    course_grades = course_grades.rename(columns={"NOTA": "NOTA_CURSO"})

    # --- Build schedule map ---
    schedule_map = _build_schedule_map(horarios)
    target_sched = schedule_map.get(target_nrc, {})

    # --- Enrolled NRCs per candidate (for conflict check) ---
    ug307["RUT"] = ug307["RUT"].astype(str).str.strip()
    ug307["NRC"] = ug307["NRC"].astype(str).str.strip()
    enrolled_by_rut = ug307.groupby("RUT")["NRC"].apply(list).to_dict()

    # --- Merge all features ---
    df = candidates.copy()
    df = df.merge(course_grades, on="RUT", how="left")
    df = df.merge(exp_counts, on="RUT", how="left")
    df = df.merge(promedios[["RUT", "PROMEDIO  GENERAL  ACUMULADO"]], on="RUT", how="left")
    df = df.merge(carga, on="RUT", how="left")

    df["NOTA_CURSO"] = df["NOTA_CURSO"].fillna(0)
    df["EXPERIENCIA"] = df["EXPERIENCIA"].fillna(0)
    df["PROMEDIO  GENERAL  ACUMULADO"] = df["PROMEDIO  GENERAL  ACUMULADO"].fillna(0)
    df["CARGA_ACTUAL"] = df["CARGA_ACTUAL"].fillna(0)

    # --- Hard filter 1: passed the course ---
    df["FILTRO_NOTA"] = df["NOTA_CURSO"] >= MIN_PASSING_GRADE

    # --- Hard filter 2: no schedule conflict ---
    def check_conflict(rut):
        enrolled = enrolled_by_rut.get(rut, [])
        cand_sched = _get_candidate_schedule(rut, enrolled, schedule_map)
        return _has_schedule_conflict(cand_sched, target_sched)

    df["FILTRO_HORARIO"] = ~df["RUT"].apply(check_conflict)

    # --- Eligible candidates only ---
    eligible = df[df["FILTRO_NOTA"] & df["FILTRO_HORARIO"]].copy()

    if eligible.empty:
        # Return all with scores=0 so UI can show why nobody qualifies
        df["SCORE"] = 0.0
        return df.sort_values("NOTA_CURSO", ascending=False)

    # --- Normalize variables to [0, 1] ---
    max_exp = eligible["EXPERIENCIA"].max() or 1
    max_carga = eligible["CARGA_ACTUAL"].max() or 1

    eligible["n_nota"] = eligible["NOTA_CURSO"] / MAX_GRADE
    eligible["n_exp"] = eligible["EXPERIENCIA"] / max_exp
    eligible["n_prom"] = eligible["PROMEDIO  GENERAL  ACUMULADO"] / MAX_GRADE
    # Carga: inverted — more courses = lower score
    eligible["n_carga"] = 1 - (eligible["CARGA_ACTUAL"] / (max_carga + 1))

    eligible["SCORE"] = (
        W_NOTA * eligible["n_nota"]
        + W_EXP * eligible["n_exp"]
        + W_PROM * eligible["n_prom"]
        + W_CARGA * eligible["n_carga"]
    ).round(4)

    result = eligible.sort_values("SCORE", ascending=False).head(top_n)
    result = result.rename(columns={"PROMEDIO  GENERAL  ACUMULADO": "PROMEDIO"})
    return result[["RUT", "NOTA_CURSO", "EXPERIENCIA", "PROMEDIO", "CARGA_ACTUAL", "SCORE", "FILTRO_NOTA", "FILTRO_HORARIO"]]
