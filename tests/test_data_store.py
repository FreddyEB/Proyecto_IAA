from pathlib import Path
import data_store


def test_find_csv_locates_by_code(tmp_path):
    (tmp_path / "RA311 - algo.csv").write_text("a,b\n1,2\n")
    found = data_store.find_csv("RA311", base_dir=tmp_path)
    assert found.name == "RA311 - algo.csv"


def test_find_csv_missing_raises(tmp_path):
    try:
        data_store.find_csv("NOPE", base_dir=tmp_path)
        assert False, "debió lanzar FileNotFoundError"
    except FileNotFoundError:
        pass


def test_validate_columns_reports_missing():
    missing = data_store.validate_columns("notas", ["RUT", "MATERIA"])
    assert "CURSO" in missing and "NOTA" in missing


def test_validate_columns_ok():
    assert data_store.validate_columns("promedios", ["RUT", "PROMEDIO  GENERAL  ACUMULADO"]) == []


def test_present_and_clear(tmp_path):
    (tmp_path / "RA311 x.csv").write_text("x\n")
    (tmp_path / "UG201 y.csv").write_text("x\n")
    present = data_store.present_files(base_dir=tmp_path)
    assert present["notas"] is True and present["horarios"] is True
    assert present["postulaciones"] is False
    deleted = data_store.clear_all(base_dir=tmp_path)
    assert len(deleted) == 2
    assert data_store.present_files(base_dir=tmp_path)["notas"] is False
