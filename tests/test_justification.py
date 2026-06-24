import justification


def base_row():
    return {"RUT": "1", "NOTA_CURSO": 6.5, "EXPERIENCIA": 2, "PROMEDIO": 5.8, "SCORE": 0.8}


def test_no_carga_reference():
    txt = justification.generate(base_row(), course_name="Cálculo")
    assert "carga" not in txt.lower()
    assert "Cálculo" in txt


def test_mentions_grade_always():
    txt = justification.generate(base_row())
    assert "nota" in txt.lower()


def test_weights_change_emphasis():
    row = base_row()
    heavy_exp = justification.generate(row, weights={"nota": 0.3, "promedio": 0.0, "experiencia": 0.7, "ia": 0.0})
    assert "experiencia" in heavy_exp.lower()
