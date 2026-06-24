import pandas as pd
import data_loader
import data_store


def test_load_all_has_no_carga_and_has_ramos(monkeypatch, tmp_path):
    # CSV sintéticos mínimos
    (tmp_path / "reportePostulaciones x.csv").write_text(
        "RUT,NRC,Materia,Curso,Estado,Tipo de ayudante,Profesor\n1,100,ICS,1102,Aceptado,de Catedra,X\n")
    (tmp_path / "RA311 x.csv").write_text("RUT,MATERIA,CURSO,NOTA\n1,ICS,1102.0,6.0\n")
    (tmp_path / "UG305 x.csv").write_text(
        "RUT,PROMEDIO RAMOS APROBADOS,PROMEDIO  GENERAL  ACUMULADO\n1,\"5,5\",\"5,0\"\n")
    (tmp_path / "UG307 x.csv").write_text("RUT,NRC\n1,200\n")
    # UG201 tiene 4 filas de cabecera antes del header real
    (tmp_path / "UG201 x.csv").write_text(
        "h\nh\nh\nh\nNRC,MATERIA,CURSO,TITULO,SECC.,LUNES,TIPO,RUT PROFESOR,PROFESOR\n"
        "100,ICS,1102,Calc,1,08:30-10:00,CLAS,162863010,PEREZ/SOTO JUAN\n")

    monkeypatch.setattr(data_store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(data_loader, "find_csv", lambda code: data_store.find_csv(code, tmp_path))

    data = data_loader.load_all()
    assert "carga" not in data
    assert "ramos_inscritos" in data
    assert list(data["ramos_inscritos"].columns) == ["RUT", "NRC"]
    hor = data["horarios"]
    assert "RUT PROFESOR" in hor.columns and "PROFESOR" in hor.columns
    assert (hor["NRC"] == "100").all()
