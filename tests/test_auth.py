import pandas as pd
import auth


def horarios():
    return pd.DataFrame({
        "NRC": ["100", "101", "200"],
        "RUT PROFESOR": ["162863010", "162863010", "171169674"],
        "PROFESOR": ["PEREZ/SOTO JUAN", "PEREZ/SOTO JUAN", "LARRAIN/HURTADO MARIA"],
    })


def test_normalize_rut_strips_symbols():
    assert auth.normalize_rut("16.286.301-0") == "162863010"
    assert auth.normalize_rut("12345678-k") == "12345678K"


def test_authenticate_returns_courses():
    res = auth.authenticate("16.286.301-0", horarios())
    assert res is not None
    assert res["nombre"] == "PEREZ/SOTO JUAN"
    assert res["nrcs"] == ["100", "101"]


def test_authenticate_unknown_rut():
    assert auth.authenticate("99999999", horarios()) is None
