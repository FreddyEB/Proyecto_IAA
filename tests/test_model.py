import pandas as pd
import model


def test_features_have_no_carga():
    assert "CARGA_ACTUAL" not in model.FEATURES
    assert model.FEATURES == ["NOTA_CURSO", "PROMEDIO", "EXPERIENCIA", "TIPO_NUM"]
    assert "CARGA_ACTUAL" not in model.FEATURE_LABELS


def test_build_training_data_columns():
    post = pd.DataFrame({
        "RUT": ["1", "2"], "NRC": ["100", "100"], "Materia": ["ICS", "ICS"],
        "Curso": ["1102", "1102"], "Estado": ["Aceptado", "Rechazado"],
        "Tipo de ayudante": ["de Catedra", "Corrector"],
    })
    notas = pd.DataFrame({"RUT": ["1", "2"], "MATERIA": ["ICS", "ICS"],
                          "CURSO": ["1102", "1102"], "NOTA": [6.0, 5.0]})
    prom = pd.DataFrame({"RUT": ["1", "2"], "PROMEDIO  GENERAL  ACUMULADO": [5.5, 5.0]})
    td = model.build_training_data(post, notas, prom)
    assert list(td.columns) == model.FEATURES + ["label"]
    assert "CARGA_ACTUAL" not in td.columns
