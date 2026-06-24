"""Autenticación liviana de profesores por RUT (POC, no es seguridad real)."""
import re
import pandas as pd


def normalize_rut(rut) -> str:
    return re.sub(r"[^0-9kK]", "", str(rut)).upper()


def courses_for_professor(rut, horarios: pd.DataFrame) -> list[str]:
    nr = normalize_rut(rut)
    mask = horarios["RUT PROFESOR"].apply(normalize_rut) == nr
    return sorted(horarios[mask]["NRC"].astype(str).unique())


def authenticate(rut, horarios: pd.DataFrame) -> dict | None:
    nr = normalize_rut(rut)
    matches = horarios[horarios["RUT PROFESOR"].apply(normalize_rut) == nr]
    if matches.empty:
        return None
    return {
        "rut": nr,
        "nombre": str(matches.iloc[0]["PROFESOR"]).strip(),
        "nrcs": sorted(matches["NRC"].astype(str).unique()),
    }
