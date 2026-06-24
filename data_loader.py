import pandas as pd
from data_store import find_csv


def load_postulaciones() -> pd.DataFrame:
    df = pd.read_csv(find_csv("reportePostulaciones"))
    df["RUT"] = df["RUT"].astype(str).str.strip()
    df["NRC"] = df["NRC"].astype(str).str.strip()
    return df


def load_notas() -> pd.DataFrame:
    df = pd.read_csv(find_csv("RA311"))
    df["RUT"] = df["RUT"].astype(str).str.strip()
    df["NOTA"] = pd.to_numeric(df["NOTA"], errors="coerce")
    df["MATERIA"] = df["MATERIA"].astype(str).str.strip()
    df["CURSO"] = df["CURSO"].apply(
        lambda x: str(int(float(x))) if pd.notna(x) and str(x).strip() not in ("", "nan") else "")
    return df[df["NOTA"].notna()]


def load_promedios() -> pd.DataFrame:
    df = pd.read_csv(find_csv("UG305"))
    df["RUT"] = df["RUT"].astype(str).str.strip()
    for col in ["PROMEDIO RAMOS APROBADOS", "PROMEDIO  GENERAL  ACUMULADO"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors="coerce")
    return df[["RUT", "PROMEDIO RAMOS APROBADOS", "PROMEDIO  GENERAL  ACUMULADO"]]


def load_ramos_inscritos() -> pd.DataFrame:
    """UG307 crudo: ramos inscritos por RUT (para el filtro de conflicto horario)."""
    df = pd.read_csv(find_csv("UG307"))
    df["RUT"] = df["RUT"].astype(str).str.strip()
    df["NRC"] = df["NRC"].astype(str).str.strip()
    return df[["RUT", "NRC"]]


def load_horarios() -> pd.DataFrame:
    df = pd.read_csv(find_csv("UG201"), skiprows=4)
    df.columns = df.columns.str.strip()
    df["NRC"] = df["NRC"].astype(str).str.strip()
    df = df[df["TIPO"] == "CLAS"].copy()
    day_cols = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"]
    for col in day_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", "")
    keep = ["NRC", "MATERIA", "CURSO", "TITULO", "SECC.", "RUT PROFESOR", "PROFESOR"]
    keep = [c for c in keep if c in df.columns] + [c for c in day_cols if c in df.columns]
    return df[keep]


def load_all():
    return {
        "postulaciones": load_postulaciones(),
        "notas": load_notas(),
        "promedios": load_promedios(),
        "horarios": load_horarios(),
        "ramos_inscritos": load_ramos_inscritos(),
    }
