import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent

def _find_csv(pattern: str) -> Path:
    matches = list(DATA_DIR.glob(f"*{pattern}*.csv"))
    if not matches:
        raise FileNotFoundError(f"No CSV found matching '*{pattern}*'")
    return matches[0]


def load_postulaciones() -> pd.DataFrame:
    """Candidatos"""
    df = pd.read_csv(_find_csv("reportePostulaciones"))
    df["RUT"] = df["RUT"].astype(str).str.strip()
    df["NRC"] = df["NRC"].astype(str).str.strip()
    return df


def load_notas() -> pd.DataFrame:
    """RA311 historial académico"""
    df = pd.read_csv(_find_csv("RA311"))
    df["RUT"] = df["RUT"].astype(str).str.strip()
    df["NOTA"] = pd.to_numeric(df["NOTA"], errors="coerce")
    df["MATERIA"] = df["MATERIA"].astype(str).str.strip()
    # Normalize CURSO: RA311 stores as float
    df["CURSO"] = df["CURSO"].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).strip() not in ("", "nan") else "")
    return df[df["NOTA"].notna()]


def load_promedios() -> pd.DataFrame:
    """UG305 GPA de cada alumno"""
    df = pd.read_csv(_find_csv("UG305"))
    df["RUT"] = df["RUT"].astype(str).str.strip()
    # Grades use comma as decimal separator
    for col in ["PROMEDIO RAMOS APROBADOS", "PROMEDIO  GENERAL  ACUMULADO"]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "."), errors="coerce"
        )
    return df[["RUT", "PROMEDIO RAMOS APROBADOS", "PROMEDIO  GENERAL  ACUMULADO"]]


def load_carga() -> pd.DataFrame:
    """UG307 cursos inscritos"""
    df = pd.read_csv(_find_csv("UG307"))
    df["RUT"] = df["RUT"].astype(str).str.strip()
    carga = df.groupby("RUT")["NRC"].count().reset_index()
    carga.columns = ["RUT", "CARGA_ACTUAL"]
    return carga


def load_horarios() -> pd.DataFrame:
    """UG201 horarios del semestre"""
    df = pd.read_csv(_find_csv("UG201"), skiprows=4)
    df.columns = df.columns.str.strip()
    df["NRC"] = df["NRC"].astype(str).str.strip()
    # Keep only class rows (not exams)
    df = df[df["TIPO"] == "CLAS"].copy()
    day_cols = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"]
    for col in day_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", "")
    return df[["NRC", "MATERIA", "CURSO", "TITULO", "SECC."] + [c for c in day_cols if c in df.columns]]


def load_all():
    return {
        "postulaciones": load_postulaciones(),
        "notas": load_notas(),
        "promedios": load_promedios(),
        "carga": load_carga(),
        "horarios": load_horarios(),
    }
