import pandas as pd
import scoring


def test_normalize_weights_sums_to_one():
    w = scoring.normalize_weights({"nota": 2, "promedio": 1, "experiencia": 1, "ia": 0})
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["nota"] == 0.5


def test_default_weights_nota_gt_promedio():
    assert scoring.DEFAULT_WEIGHTS["nota"] > scoring.DEFAULT_WEIGHTS["promedio"]


def test_hybrid_score_range_and_monotonic():
    df = pd.DataFrame({
        "NOTA_CURSO": [7.0, 5.0],
        "PROMEDIO": [6.0, 5.0],
        "EXPERIENCIA": [2, 0],
    })
    p_ia = [0.9, 0.4]
    s = scoring.compute_hybrid_score(df, p_ia, scoring.DEFAULT_WEIGHTS)
    assert (s >= 0).all() and (s <= 1).all()
    assert s.iloc[0] > s.iloc[1]  # mejor perfil => mayor score


def test_attendance_types():
    assert "de Catedra" in scoring.TYPES_REQUIRING_ATTENDANCE
    assert "Laboratorio Tipo 1" in scoring.TYPES_REQUIRING_ATTENDANCE
    assert "Corrector" not in scoring.TYPES_REQUIRING_ATTENDANCE
