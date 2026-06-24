# Ajustes del MVP según feedback del cliente — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajustar el sistema de recomendación de ayudantes a un score híbrido configurable por el profesor, redefinir los KPIs, y convertir la app Streamlit en multipágina con login por profesor y carga persistente de CSV.

**Architecture:** Se mantiene Streamlit + Random Forest. El RF pasa a ser una señal (`P_IA`) dentro de un score híbrido lineal con pesos ajustables por el profesor. La app se reestructura con `st.navigation` (login → ranking → carga de datos). La lógica pura (data_store, scoring, auth, justification, model) se separa en módulos testeables con pytest; las vistas Streamlit se verifican manualmente.

**Tech Stack:** Python 3.12, Streamlit ≥1.36, scikit-learn, pandas, pytest.

## Global Constraints

- Umbral de aprobación `MIN_PASSING_GRADE = 4.75` (fijado por el usuario, no cambiar).
- Nota máxima de escala = `7.0` (normalización).
- La feature `CARGA_ACTUAL` se ELIMINA del modelo, del score y de la UI. **PERO UG307 se mantiene** porque provee los ramos inscritos para el filtro de conflicto horario.
- Tipos de ayudantía que exigen asistencia (choque de horario → descarta): `de Catedra`, `Laboratorio Tipo 1`, `Laboratorio Tipo 2`. El resto (`Corrector`, `Coordinador Tipo 1`, `Coordinador Tipo 2`, `Proyecto`) NO se filtran por horario.
- Pesos por defecto del score: `{"nota": 0.40, "promedio": 0.15, "experiencia": 0.20, "ia": 0.25}` (se cumple `w_nota > w_promedio`).
- Los CSV viven en la carpeta del proyecto (`ayudantes_mvp/`), reconocidos por código: `reportePostulaciones`, `RA311`, `UG305`, `UG307`, `UG201`.
- Todos los tests usan DataFrames/CSV sintéticos pequeños en `tmp_path`, nunca los CSV reales.

---

### Task 1: Infra de tests + módulo `data_store`

**Files:**
- Modify: `requirements.txt`
- Create: `data_store.py`
- Create: `tests/__init__.py` (vacío)
- Test: `tests/test_data_store.py`

**Interfaces:**
- Produces:
  - `FILE_CODES: dict[str, str]` — mapea clave lógica → código de archivo. Claves: `postulaciones, notas, promedios, ramos_inscritos, horarios`.
  - `DATA_DIR: Path` — carpeta del proyecto (`Path(__file__).parent`).
  - `find_csv(code: str, base_dir: Path = DATA_DIR) -> Path` — primer CSV que contiene `code` en el nombre; `FileNotFoundError` si no hay.
  - `EXPECTED_COLUMNS: dict[str, list[str]]` — columnas mínimas por clave lógica.
  - `validate_columns(code: str, columns: list[str]) -> list[str]` — devuelve columnas faltantes (lista vacía = OK).
  - `present_files(base_dir: Path = DATA_DIR) -> dict[str, bool]` — qué claves lógicas tienen archivo presente.
  - `clear_all(base_dir: Path = DATA_DIR) -> list[str]` — borra los CSV reconocidos; devuelve nombres borrados.

- [ ] **Step 1: Añadir dependencias**

En `requirements.txt`, dejarlo así:

```
streamlit==1.39.0
pandas==2.2.2
openpyxl==3.1.2
xlsxwriter==3.2.0
scikit-learn==1.5.0
pytest==8.2.0
```

- [ ] **Step 2: Escribir el test que falla**

`tests/test_data_store.py`:

```python
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
```

- [ ] **Step 3: Verificar que falla**

Run: `python -m pytest tests/test_data_store.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'data_store'`.

- [ ] **Step 4: Implementar `data_store.py`**

```python
"""Resolución, validación y persistencia de los CSV de entrada."""
from pathlib import Path

DATA_DIR = Path(__file__).parent

FILE_CODES = {
    "postulaciones": "reportePostulaciones",
    "notas": "RA311",
    "promedios": "UG305",
    "ramos_inscritos": "UG307",
    "horarios": "UG201",
}

EXPECTED_COLUMNS = {
    "postulaciones": ["RUT", "NRC", "Materia", "Curso", "Estado", "Tipo de ayudante", "Profesor"],
    "notas": ["RUT", "MATERIA", "CURSO", "NOTA"],
    "promedios": ["RUT", "PROMEDIO  GENERAL  ACUMULADO"],
    "ramos_inscritos": ["RUT", "NRC"],
    "horarios": ["NRC", "MATERIA", "CURSO", "TIPO", "RUT PROFESOR", "PROFESOR"],
}


def find_csv(code: str, base_dir: Path = DATA_DIR) -> Path:
    matches = sorted(Path(base_dir).glob(f"*{code}*.csv"))
    if not matches:
        raise FileNotFoundError(f"No CSV found matching '*{code}*' en {base_dir}")
    return matches[0]


def validate_columns(code: str, columns) -> list[str]:
    expected = EXPECTED_COLUMNS[code]
    present = {str(c).strip() for c in columns}
    return [c for c in expected if c not in present]


def present_files(base_dir: Path = DATA_DIR) -> dict[str, bool]:
    result = {}
    for key, code in FILE_CODES.items():
        try:
            find_csv(code, base_dir)
            result[key] = True
        except FileNotFoundError:
            result[key] = False
    return result


def clear_all(base_dir: Path = DATA_DIR) -> list[str]:
    deleted = []
    for code in FILE_CODES.values():
        for path in Path(base_dir).glob(f"*{code}*.csv"):
            path.unlink()
            deleted.append(path.name)
    return deleted
```

- [ ] **Step 5: Verificar que pasa**

Run: `python -m pytest tests/test_data_store.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add requirements.txt data_store.py tests/__init__.py tests/test_data_store.py
git commit -m "feat: módulo data_store (paths, validación, persistencia) + pytest"
```

---

### Task 2: Refactor `data_loader` (rutas, columnas de profesor, ramos inscritos)

**Files:**
- Modify: `data_loader.py`
- Test: `tests/test_data_loader.py`

**Interfaces:**
- Consumes: `data_store.find_csv`.
- Produces:
  - `load_horarios()` → DataFrame con columnas `NRC, MATERIA, CURSO, TITULO, SECC., <días>, RUT PROFESOR, PROFESOR` (solo filas `TIPO == "CLAS"`).
  - `load_ramos_inscritos()` → DataFrame `RUT, NRC` (crudo de UG307, para horario).
  - `load_all()` → dict con claves `postulaciones, notas, promedios, horarios, ramos_inscritos` (SIN `carga`).
  - Se elimina `load_carga`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_data_loader.py`:

```python
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
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_data_loader.py -v`
Expected: FAIL (hoy `load_all` trae `carga` y `load_horarios` no expone columnas de profesor).

- [ ] **Step 3: Reescribir `data_loader.py`**

```python
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
```

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_data_loader.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data_loader.py tests/test_data_loader.py
git commit -m "refactor: data_loader usa data_store, expone profesor y ramos inscritos, elimina carga"
```

---

### Task 3: `model.py` — eliminar `CARGA_ACTUAL` de las features

**Files:**
- Modify: `model.py`
- Test: `tests/test_model.py`

**Interfaces:**
- Produces:
  - `FEATURES == ["NOTA_CURSO", "PROMEDIO", "EXPERIENCIA", "TIPO_NUM"]` (sin `CARGA_ACTUAL`).
  - `FEATURE_LABELS` sin la clave `CARGA_ACTUAL`.
  - `build_training_data(postulaciones, notas, promedios)` (sin parámetro `carga`).
  - `train(training_data) -> (model, metrics)` y `predict_scores(model, candidates) -> pd.Series` sin cambios de firma salvo lo anterior.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_model.py`:

```python
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
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_model.py -v`
Expected: FAIL (hoy `FEATURES` incluye `CARGA_ACTUAL` y `build_training_data` pide `carga`).

- [ ] **Step 3: Editar `model.py`**

Cambiar la constante:

```python
FEATURES = ["NOTA_CURSO", "PROMEDIO", "EXPERIENCIA", "TIPO_NUM"]
FEATURE_LABELS = {
    "NOTA_CURSO": "Nota en el curso",
    "PROMEDIO": "Promedio acumulado",
    "EXPERIENCIA": "Experiencia previa",
    "TIPO_NUM": "Tipo de ayudantía",
}
```

Cambiar la firma y cuerpo de `build_training_data` para quitar `carga`:

```python
def build_training_data(
    postulaciones: pd.DataFrame,
    notas: pd.DataFrame,
    promedios: pd.DataFrame,
) -> pd.DataFrame:
    labeled = postulaciones[postulaciones["Estado"].isin(["Aceptado", "Rechazado"])].copy()
    labeled["label"] = (labeled["Estado"] == "Aceptado").astype(int)
    labeled["RUT"] = labeled["RUT"].astype(str)
    labeled["Curso"] = labeled["Curso"].astype(str).str.strip()
    labeled["Materia"] = labeled["Materia"].astype(str).str.strip()

    notas2 = notas.copy()
    notas2["RUT"] = notas2["RUT"].astype(str)
    best_nota = (
        notas2.groupby(["RUT", "MATERIA", "CURSO"])["NOTA"].max()
        .reset_index(name="NOTA_CURSO")
    )

    df = labeled.merge(
        best_nota, left_on=["RUT", "Materia", "Curso"],
        right_on=["RUT", "MATERIA", "CURSO"], how="left",
    )
    df = df.merge(
        promedios.rename(columns={"PROMEDIO  GENERAL  ACUMULADO": "PROMEDIO"}),
        on="RUT", how="left",
    )

    exp = (
        postulaciones[postulaciones["Estado"] == "Aceptado"]
        .groupby("RUT").size().reset_index(name="EXPERIENCIA")
    )
    exp["RUT"] = exp["RUT"].astype(str)
    df = df.merge(exp, on="RUT", how="left")
    df["EXPERIENCIA"] = df["EXPERIENCIA"].fillna(0)

    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    df["TIPO_NUM"] = le.fit_transform(df["Tipo de ayudante"].fillna("Desconocido"))

    return df[FEATURES + ["label"]].dropna()
```

(El resto de `model.py` —`train`, `predict_scores`— no cambia.)

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_model.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add model.py tests/test_model.py
git commit -m "refactor: elimina CARGA_ACTUAL de las features del modelo"
```

---

### Task 4: `scoring.py` — pesos + score híbrido

**Files:**
- Modify: `scoring.py`
- Test: `tests/test_scoring_score.py`

**Interfaces:**
- Produces:
  - `DEFAULT_WEIGHTS: dict[str, float]` = `{"nota":0.40,"promedio":0.15,"experiencia":0.20,"ia":0.25}`.
  - `normalize_weights(weights: dict) -> dict` — renormaliza a suma 1; si la suma es 0 reparte igual.
  - `compute_hybrid_score(df: pd.DataFrame, p_ia, weights: dict) -> pd.Series` — combina `NOTA_CURSO/7`, `PROMEDIO/7`, `EXPERIENCIA/max`, y `p_ia`. Resultado en [0,1].
  - `TYPES_REQUIRING_ATTENDANCE: set[str]`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_scoring_score.py`:

```python
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
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_scoring_score.py -v`
Expected: FAIL (`normalize_weights`/`compute_hybrid_score`/`DEFAULT_WEIGHTS`/`TYPES_REQUIRING_ATTENDANCE` no existen).

- [ ] **Step 3: Añadir a `scoring.py`**

Reemplazar la cabecera y la constante de umbral por:

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

MIN_PASSING_GRADE = 4.75
MAX_GRADE = 7.0

DEFAULT_WEIGHTS = {"nota": 0.40, "promedio": 0.15, "experiencia": 0.20, "ia": 0.25}

TYPES_REQUIRING_ATTENDANCE = {"de Catedra", "Laboratorio Tipo 1", "Laboratorio Tipo 2"}


def normalize_weights(weights: dict) -> dict:
    total = sum(weights.values())
    if total <= 0:
        n = len(weights)
        return {k: 1.0 / n for k in weights}
    return {k: v / total for k, v in weights.items()}


def compute_hybrid_score(df: pd.DataFrame, p_ia, weights: dict) -> pd.Series:
    w = normalize_weights(weights)
    norm_nota = (df["NOTA_CURSO"] / MAX_GRADE).clip(0, 1)
    norm_prom = (df["PROMEDIO"] / MAX_GRADE).clip(0, 1)
    max_exp = df["EXPERIENCIA"].max()
    if max_exp and max_exp > 0:
        norm_exp = (df["EXPERIENCIA"] / max_exp).clip(0, 1)
    else:
        norm_exp = df["EXPERIENCIA"] * 0.0
    p_ia = pd.Series(list(p_ia), index=df.index)
    score = (w["nota"] * norm_nota + w["promedio"] * norm_prom
             + w["experiencia"] * norm_exp + w["ia"] * p_ia)
    return score.clip(0, 1)
```

(Las funciones `_parse_time_block`, `_has_schedule_conflict`, `_build_schedule_map` quedan igual.)

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_scoring_score.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scoring.py tests/test_scoring_score.py
git commit -m "feat: pesos ajustables y score híbrido en scoring"
```

---

### Task 5: `scoring.py` — filtro de horario condicional al tipo + `rank_candidates`

**Files:**
- Modify: `scoring.py`
- Test: `tests/test_scoring_rank.py`

**Interfaces:**
- Consumes: `compute_hybrid_score`, `TYPES_REQUIRING_ATTENDANCE`, `model.predict_scores`, `model.FEATURES`.
- Produces:
  - `schedule_filter_passes(tipo: str, has_conflict: bool) -> bool`.
  - `rank_candidates(target_nrc, postulaciones, notas, promedios, horarios, ramos_inscritos, model, weights=DEFAULT_WEIGHTS, top_n=5) -> pd.DataFrame` — **sin** parámetro `carga`/`ug307`; ahora recibe `ramos_inscritos` y `weights`. Columnas de salida: `RUT, TIPO_AYUDANTE, NOTA_CURSO, EXPERIENCIA, PROMEDIO, SCORE, FILTRO_NOTA, FILTRO_HORARIO`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_scoring_rank.py`:

```python
import scoring


def test_schedule_filter_only_for_attendance_types():
    # tipo que exige asistencia + conflicto => NO pasa
    assert scoring.schedule_filter_passes("de Catedra", True) is False
    # tipo que exige asistencia + sin conflicto => pasa
    assert scoring.schedule_filter_passes("de Catedra", False) is True
    # tipo sin asistencia + conflicto => igual pasa
    assert scoring.schedule_filter_passes("Corrector", True) is True
    assert scoring.schedule_filter_passes("Coordinador Tipo 1", True) is True
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_scoring_rank.py -v`
Expected: FAIL (`schedule_filter_passes` no existe).

- [ ] **Step 3: Añadir `schedule_filter_passes` y reescribir `rank_candidates`**

Añadir helper:

```python
def schedule_filter_passes(tipo: str, has_conflict: bool) -> bool:
    if tipo in TYPES_REQUIRING_ATTENDANCE:
        return not has_conflict
    return True
```

Reemplazar `rank_candidates` por:

```python
def rank_candidates(
    target_nrc: str,
    postulaciones: pd.DataFrame,
    notas: pd.DataFrame,
    promedios: pd.DataFrame,
    horarios: pd.DataFrame,
    ramos_inscritos: pd.DataFrame,
    model: RandomForestClassifier,
    weights: dict = None,
    top_n: int = 5,
) -> pd.DataFrame:
    from model import predict_scores
    from sklearn.preprocessing import LabelEncoder

    weights = weights or DEFAULT_WEIGHTS
    out_cols = ["RUT", "TIPO_AYUDANTE", "NOTA_CURSO", "EXPERIENCIA",
                "PROMEDIO", "SCORE", "FILTRO_NOTA", "FILTRO_HORARIO"]

    nrc_info = horarios[horarios["NRC"] == target_nrc]
    if nrc_info.empty:
        return pd.DataFrame(columns=out_cols)

    materia = str(nrc_info.iloc[0]["MATERIA"]).strip()
    raw_curso = nrc_info.iloc[0]["CURSO"]
    try:
        curso = str(int(float(raw_curso)))
    except (ValueError, TypeError):
        curso = str(raw_curso).strip()

    cands_post = postulaciones[
        (postulaciones["NRC"] == target_nrc) &
        (postulaciones["Estado"].isin(["Pendiente", "Aceptado"]))
    ][["RUT", "Tipo de ayudante"]].drop_duplicates("RUT").rename(
        columns={"Tipo de ayudante": "TIPO_AYUDANTE"})
    if cands_post.empty:
        return pd.DataFrame(columns=out_cols)

    exp_counts = (
        postulaciones[postulaciones["Estado"] == "Aceptado"]
        .groupby("RUT").size().reset_index(name="EXPERIENCIA"))

    course_grades = (
        notas[(notas["MATERIA"] == materia) & (notas["CURSO"] == curso)]
        [["RUT", "NOTA"]].sort_values("NOTA", ascending=False)
        .drop_duplicates("RUT").rename(columns={"NOTA": "NOTA_CURSO"}))

    schedule_map = _build_schedule_map(horarios)
    target_sched = schedule_map.get(target_nrc, {})
    ri = ramos_inscritos.copy()
    ri["RUT"] = ri["RUT"].astype(str).str.strip()
    ri["NRC"] = ri["NRC"].astype(str).str.strip()
    enrolled_by_rut = ri.groupby("RUT")["NRC"].apply(list).to_dict()

    def get_cand_sched(rut):
        merged = {}
        for nrc in enrolled_by_rut.get(rut, []):
            for day, blocks in schedule_map.get(nrc, {}).items():
                merged.setdefault(day, []).extend(blocks)
        return merged

    df = cands_post.copy()
    df = df.merge(course_grades, on="RUT", how="left")
    df = df.merge(exp_counts, on="RUT", how="left")
    df = df.merge(promedios[["RUT", "PROMEDIO  GENERAL  ACUMULADO"]], on="RUT", how="left")
    df["NOTA_CURSO"] = df["NOTA_CURSO"].fillna(0)
    df["EXPERIENCIA"] = df["EXPERIENCIA"].fillna(0)
    df["PROMEDIO"] = df["PROMEDIO  GENERAL  ACUMULADO"].fillna(0)

    le = LabelEncoder()
    le.fit(["Corrector", "Coordinador Tipo 1", "Coordinador Tipo 2",
            "Laboratorio Tipo 1", "Laboratorio Tipo 2", "Proyecto", "de Catedra"])
    df["TIPO_NUM"] = df["TIPO_AYUDANTE"].apply(
        lambda x: le.transform([x])[0] if x in le.classes_ else 0)

    df["FILTRO_NOTA"] = df["NOTA_CURSO"] >= MIN_PASSING_GRADE
    df["_CONFLICT"] = df["RUT"].apply(
        lambda r: _has_schedule_conflict(get_cand_sched(r), target_sched))
    df["FILTRO_HORARIO"] = df.apply(
        lambda r: schedule_filter_passes(r["TIPO_AYUDANTE"], r["_CONFLICT"]), axis=1)

    eligible = df[df["FILTRO_NOTA"] & df["FILTRO_HORARIO"]].copy()
    if eligible.empty:
        df["SCORE"] = 0.0
        return df[out_cols].sort_values("NOTA_CURSO", ascending=False)

    p_ia = predict_scores(model, eligible)
    eligible["SCORE"] = compute_hybrid_score(eligible, p_ia, weights).round(4)
    result = eligible.sort_values("SCORE", ascending=False).head(top_n)
    return result[out_cols]
```

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_scoring_rank.py tests/test_scoring_score.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scoring.py tests/test_scoring_rank.py
git commit -m "feat: filtro de horario condicional al tipo y score híbrido en rank_candidates"
```

---

### Task 6: `justification.py` — usar pesos del profesor, quitar carga

**Files:**
- Modify: `justification.py`
- Test: `tests/test_justification.py`

**Interfaces:**
- Consumes: `scoring.normalize_weights`, `scoring.DEFAULT_WEIGHTS`, `scoring.MAX_GRADE`.
- Produces: `generate(row: dict, weights: dict = None, course_name: str = "") -> str`. Ya no lee `CARGA_ACTUAL`. Siempre menciona la nota; menciona experiencia/promedio si están entre los factores de mayor contribución según los pesos.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_justification.py`:

```python
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
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_justification.py -v`
Expected: FAIL (firma actual no acepta `weights`; aún referencia carga).

- [ ] **Step 3: Reescribir `justification.py`**

```python
"""Justificación breve en lenguaje natural por candidato."""
from scoring import normalize_weights, DEFAULT_WEIGHTS, MAX_GRADE


def _nota_label(nota: float) -> str:
    if nota >= 6.5:
        return "excelente"
    if nota >= 5.5:
        return "muy buena"
    if nota >= 5.0:
        return "buena"
    return "aprobatoria"


def generate(row: dict, weights: dict = None, course_name: str = "") -> str:
    weights = normalize_weights(weights or DEFAULT_WEIGHTS)
    nota = float(row["NOTA_CURSO"])
    exp = int(row["EXPERIENCIA"])
    prom = float(row["PROMEDIO"])

    contributions = {
        "experiencia": weights["experiencia"] * (exp / max(exp, 1)),
        "promedio": weights["promedio"] * (prom / MAX_GRADE),
    }
    top_factors = [f for f, _ in sorted(contributions.items(), key=lambda kv: kv[1], reverse=True)
                   if contributions[f] > 0][:2]

    parts = []
    course_ref = f" en {course_name}" if course_name else ""
    parts.append(
        f"Obtuvo nota {nota:.1f}{course_ref} ({_nota_label(nota)}), "
        f"cumpliendo el requisito académico mínimo.")

    if "experiencia" in top_factors:
        if exp == 0:
            parts.append("No registra experiencia previa como ayudante.")
        elif exp == 1:
            parts.append("Cuenta con 1 semestre de experiencia previa como ayudante.")
        else:
            parts.append(f"Cuenta con {exp} semestres de experiencia previa como ayudante, "
                         f"lo que reduce el tiempo de inducción.")

    if "promedio" in top_factors and prom > 0:
        parts.append(f"Su promedio académico acumulado es {prom:.2f}, "
                     f"reflejando consistencia académica general.")

    return " ".join(parts)
```

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_justification.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add justification.py tests/test_justification.py
git commit -m "refactor: justificación usa pesos del profesor y elimina carga"
```

---

### Task 7: Módulo `auth` (login por RUT del profesor)

**Files:**
- Create: `auth.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Produces:
  - `normalize_rut(rut) -> str` — deja solo dígitos y K (mayúscula).
  - `authenticate(rut, horarios: pd.DataFrame) -> dict | None` — `{"rut", "nombre", "nrcs": list[str]}` o `None` si el RUT no aparece como `RUT PROFESOR`.
  - `courses_for_professor(rut, horarios) -> list[str]` — NRCs (str) ordenados de ese profesor.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_auth.py`:

```python
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
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_auth.py -v`
Expected: FAIL (`No module named 'auth'`).

- [ ] **Step 3: Implementar `auth.py`**

```python
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
```

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_auth.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: módulo auth para login de profesor por RUT"
```

---

### Task 8: `analysis.py` — adaptar a las nuevas firmas

**Files:**
- Modify: `analysis.py`
- Test: `tests/test_analysis_smoke.py`

**Interfaces:**
- Consumes: `scoring.rank_candidates` (nueva firma con `ramos_inscritos`, `weights`, sin `carga`).
- Produces: `compute_ranking_accuracy(postulaciones, notas, promedios, horarios, ramos_inscritos, model, weights=None) -> dict` (sin `carga`/`ug307`). `compute_tca_real` sin cambios de firma.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_analysis_smoke.py`:

```python
import inspect
import analysis


def test_ranking_accuracy_signature_has_no_carga():
    params = list(inspect.signature(analysis.compute_ranking_accuracy).parameters)
    assert "carga" not in params and "ug307" not in params
    assert "ramos_inscritos" in params
```

- [ ] **Step 2: Verificar que falla**

Run: `python -m pytest tests/test_analysis_smoke.py -v`
Expected: FAIL (la firma actual tiene `carga` y `ug307`).

- [ ] **Step 3: Editar `analysis.py`**

Cambiar la firma y la llamada interna a `rank_candidates`:

```python
def compute_ranking_accuracy(
    postulaciones: pd.DataFrame,
    notas: pd.DataFrame,
    promedios: pd.DataFrame,
    horarios: pd.DataFrame,
    ramos_inscritos: pd.DataFrame,
    model: RandomForestClassifier,
    weights: dict = None,
) -> dict:
```

Dentro del bucle, reemplazar la llamada por:

```python
        result = rank_candidates(nrc, postulaciones, notas, promedios,
                                 horarios, ramos_inscritos, model,
                                 weights=weights, top_n=5)
```

(El resto del cuerpo de `analysis.py` no cambia.)

- [ ] **Step 4: Verificar que pasa**

Run: `python -m pytest tests/test_analysis_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis.py tests/test_analysis_smoke.py
git commit -m "refactor: analysis adaptado a rank_candidates con ramos_inscritos y weights"
```

---

### Task 9: App multipágina + vista de Login

**Files:**
- Create: `views/__init__.py` (vacío)
- Create: `views/login.py`
- Rewrite: `app.py`

**Interfaces:**
- Consumes: `data_loader.load_all`, `model.build_training_data`, `model.train`, `auth.authenticate`.
- Produces:
  - `views.login.render()` — formulario de login que setea `st.session_state["profesor"]`.
  - `app.py` arma `st.navigation`: si no hay sesión, solo muestra Login; si hay, muestra Ranking + Cargar datos.
  - Cache helpers en `app.py`: `get_data()`, `get_model()` (cacheados con Streamlit).

- [ ] **Step 1: Verificar versión de Streamlit**

Run: `pip install -r requirements.txt && python -c "import streamlit, sys; v=tuple(int(x) for x in streamlit.__version__.split('.')[:2]); print(streamlit.__version__); sys.exit(0 if v>=(1,36) else 1)"`
Expected: imprime versión ≥ 1.36 y sale 0.

- [ ] **Step 2: Crear `views/login.py`**

```python
import streamlit as st
from auth import authenticate


def render():
    st.title("Ingreso de profesores")
    st.caption("Acceso de demostración. La clave es su RUT.")
    horarios = st.session_state["_data"]["horarios"]

    with st.form("login"):
        nombre = st.text_input("Nombre")
        apellido = st.text_input("Apellido")
        rut = st.text_input("RUT (clave)", type="password")
        ok = st.form_submit_button("Ingresar")

    if ok:
        prof = authenticate(rut, horarios)
        if prof is None:
            st.error("RUT no encontrado como profesor en los datos del período.")
        else:
            prof["nombre_ingresado"] = f"{nombre} {apellido}".strip()
            st.session_state["profesor"] = prof
            st.rerun()
```

- [ ] **Step 3: Reescribir `app.py`**

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from data_loader import load_all
from model import build_training_data, train

st.set_page_config(page_title="Recomendación de Ayudantes", page_icon="🎓", layout="wide")


@st.cache_data(show_spinner="Cargando datos académicos…")
def get_data():
    return load_all()


@st.cache_resource(show_spinner="Entrenando modelo Random Forest…")
def get_model():
    data = get_data()
    td = build_training_data(data["postulaciones"], data["notas"], data["promedios"])
    return train(td)


# Datos siempre disponibles en sesión para las vistas
st.session_state["_data"] = get_data()

import views.login as login_view

if "profesor" not in st.session_state:
    pg = st.navigation([st.Page(login_view.render, title="Ingreso", icon="🔑")])
else:
    import views.ranking as ranking_view
    import views.upload as upload_view
    with st.sidebar:
        st.markdown(f"**Profesor:** {st.session_state['profesor']['nombre']}")
        if st.button("Cerrar sesión"):
            del st.session_state["profesor"]
            st.rerun()
    pg = st.navigation([
        st.Page(ranking_view.render, title="Mis cursos / Ranking", icon="📊"),
        st.Page(upload_view.render, title="Cargar datos", icon="📂"),
    ])

pg.run()
```

> Nota: las Tasks 10 y 11 crean `views/ranking.py` y `views/upload.py`. Hasta entonces, para verificar el login se puede comentar temporalmente el bloque `else` o crear stubs vacíos con una función `render()` que llame `st.write("pendiente")`.

- [ ] **Step 4: Verificación manual del login**

Crear stubs temporales si hace falta:
```bash
mkdir -p views && printf 'def render():\n    import streamlit as st\n    st.write("ranking pendiente")\n' > views/ranking.py
printf 'def render():\n    import streamlit as st\n    st.write("upload pendiente")\n' > views/upload.py
```
Run: `streamlit run app.py`
Verificar: aparece la pantalla de Ingreso; con un RUT inválido muestra error; con un `RUT PROFESOR` real de UG201 entra y muestra el nombre en la barra lateral y las dos páginas. Cerrar sesión vuelve al login.

- [ ] **Step 5: Commit**

```bash
git add app.py views/__init__.py views/login.py views/ranking.py views/upload.py
git commit -m "feat: app Streamlit multipágina con login de profesor"
```

---

### Task 10: Vista de Ranking (sliders de pesos, KPIs, justificación, export)

**Files:**
- Rewrite: `views/ranking.py`

**Interfaces:**
- Consumes: `app.get_data`, `app.get_model`, `data_loader` (vía `_data`), `scoring.rank_candidates`, `scoring.DEFAULT_WEIGHTS`, `justification.generate`, `model.FEATURE_LABELS`.
- Produces: `views.ranking.render()`.

- [ ] **Step 1: Implementar `views/ranking.py`**

```python
import io
import pandas as pd
import streamlit as st

from scoring import rank_candidates, DEFAULT_WEIGHTS, MIN_PASSING_GRADE
from justification import generate as generate_justification


def render():
    from app import get_data, get_model
    data = get_data()
    model, metrics = get_model()
    horarios = data["horarios"]
    postulaciones = data["postulaciones"]
    prof = st.session_state["profesor"]

    st.title("Mis cursos / Ranking de ayudantes")

    # Solo NRCs del profesor que además tienen postulaciones activas
    prof_nrcs = set(prof["nrcs"])
    activos = set(postulaciones[postulaciones["Estado"].isin(["Pendiente", "Aceptado"])]["NRC"].unique())
    valid_nrcs = sorted(prof_nrcs & activos & set(horarios["NRC"].unique()))
    if not valid_nrcs:
        st.warning("No tienes cursos con postulaciones activas en los datos cargados.")
        return

    labels = {}
    for nrc in valid_nrcs:
        row = horarios[horarios["NRC"] == nrc].iloc[0]
        labels[nrc] = f"{nrc} — {row.get('TITULO','')} ({row.get('MATERIA','')} {row.get('CURSO','')})"
    selected_label = st.selectbox("Curso (NRC)", list(labels.values()))
    selected_nrc = [k for k, v in labels.items() if v == selected_label][0]

    st.sidebar.markdown("### Importancia de variables")
    w_nota = st.sidebar.slider("Nota en el curso", 0.0, 1.0, DEFAULT_WEIGHTS["nota"], 0.05)
    w_prom = st.sidebar.slider("Promedio acumulado", 0.0, 1.0, DEFAULT_WEIGHTS["promedio"], 0.05)
    w_exp = st.sidebar.slider("Experiencia previa", 0.0, 1.0, DEFAULT_WEIGHTS["experiencia"], 0.05)
    w_ia = st.sidebar.slider("Señal del modelo (IA)", 0.0, 1.0, DEFAULT_WEIGHTS["ia"], 0.05)
    weights = {"nota": w_nota, "promedio": w_prom, "experiencia": w_exp, "ia": w_ia}
    top_n = st.sidebar.slider("Candidatos a mostrar", 1, 20, 5)

    ranking = rank_candidates(
        selected_nrc, postulaciones, data["notas"], data["promedios"],
        horarios, data["ramos_inscritos"], model, weights=weights, top_n=top_n)

    total_post = len(postulaciones[(postulaciones["NRC"] == selected_nrc) &
                                   (postulaciones["Estado"].isin(["Pendiente", "Aceptado"]))])

    if ranking.empty:
        st.warning("No se encontraron candidatos para este NRC.")
        return
    eligible = ranking[ranking["FILTRO_NOTA"] & ranking["FILTRO_HORARIO"]].copy()
    if eligible.empty:
        st.error("Ningún postulante supera los filtros. Verifica notas en RA311 para este curso.")
        st.dataframe(ranking[["RUT", "NOTA_CURSO", "FILTRO_NOTA", "FILTRO_HORARIO"]])
        return

    # KPIs
    tca = 100.0
    score_kpi = float(eligible["SCORE"].mean())
    conflictos = int((~ranking["FILTRO_HORARIO"]).sum())
    k1, k2, k3 = st.columns(3)
    k1.metric("KPI 1 · TCA", f"{tca:.0f}%", help=f"Candidatos recomendados con nota ≥ {MIN_PASSING_GRADE}")
    k2.metric("KPI 2 · Score recomendación", f"{score_kpi:.2f}", help="Promedio del score de los recomendados")
    k3.metric("KPI 3 · Descartes por horario", conflictos,
              help="Candidatos de tipo con asistencia obligatoria descartados por choque de horario")

    course_name = horarios[horarios["NRC"] == selected_nrc].iloc[0].get("TITULO", "")
    eligible = eligible.reset_index(drop=True)
    eligible.index += 1
    eligible["JUSTIFICACIÓN"] = eligible.apply(
        lambda r: generate_justification(r.to_dict(), weights, course_name), axis=1)

    display_cols = ["RUT", "TIPO_AYUDANTE", "NOTA_CURSO", "EXPERIENCIA", "PROMEDIO", "SCORE"]
    st.dataframe(eligible[display_cols].style.format(
        {"NOTA_CURSO": "{:.1f}", "PROMEDIO": "{:.2f}", "SCORE": "{:.4f}",
         "EXPERIENCIA": "{:.0f}"}).background_gradient(subset=["SCORE"], cmap="Greens"),
        use_container_width=True)

    st.subheader("Detalle por candidato")
    for rank, row in eligible.iterrows():
        with st.expander(f"#{rank} — RUT {row['RUT']} | {row['TIPO_AYUDANTE']} | Score: {row['SCORE']:.4f}"):
            st.info(row["JUSTIFICACIÓN"])

    # Export
    export_df = eligible[["RUT", "TIPO_AYUDANTE", "NOTA_CURSO", "EXPERIENCIA",
                          "PROMEDIO", "SCORE", "JUSTIFICACIÓN"]].copy()
    export_df.insert(0, "RANKING", range(1, len(export_df) + 1))
    export_df["NRC"] = selected_nrc
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Ranking")
        pd.DataFrame({"Métrica": ["NRC", "TCA (%)", "Score recomendación", "Descartes horario"],
                      "Valor": [selected_nrc, tca, round(score_kpi, 4), conflictos]}
                     ).to_excel(writer, index=False, sheet_name="KPIs")
    st.download_button("Descargar Excel", buffer.getvalue(),
                       file_name=f"ranking_NRC{selected_nrc}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
```

- [ ] **Step 2: Verificación manual**

Run: `streamlit run app.py`
Ingresar con un RUT real, seleccionar un curso, mover los sliders y verificar: el ranking se reordena, la justificación cambia el énfasis según los pesos, los 3 KPIs aparecen, y el Excel se descarga con hojas Ranking y KPIs. No debe aparecer ninguna columna de carga.

- [ ] **Step 3: Commit**

```bash
git add views/ranking.py
git commit -m "feat: vista de ranking con sliders de pesos, KPIs redefinidos y export"
```

---

### Task 11: Vista de Carga de datos (persistente + reset)

**Files:**
- Rewrite: `views/upload.py`

**Interfaces:**
- Consumes: `data_store.FILE_CODES`, `data_store.DATA_DIR`, `data_store.validate_columns`, `data_store.present_files`, `data_store.clear_all`, `app.get_data`, `app.get_model`.
- Produces: `views.upload.render()`.

- [ ] **Step 1: Implementar `views/upload.py`**

```python
import pandas as pd
import streamlit as st

import data_store
from data_store import FILE_CODES, DATA_DIR, validate_columns, present_files, clear_all


def render():
    from app import get_data, get_model

    st.title("Cargar / actualizar datos (CSV)")
    st.caption("Sube los archivos del período. Se guardan en el servidor y persisten entre sesiones.")

    st.subheader("Estado actual")
    present = present_files()
    st.table(pd.DataFrame(
        [{"Archivo": k, "Código": FILE_CODES[k], "Presente": "✅" if v else "❌"}
         for k, v in present.items()]))

    st.subheader("Limpiar datos")
    st.write("Borra los archivos actuales antes de subir un set nuevo para evitar mezclar períodos.")
    if st.button("🗑️ Limpiar todos los datos cargados"):
        deleted = clear_all()
        get_data.clear()
        get_model.clear()
        st.success(f"Eliminados {len(deleted)} archivos. Sube los nuevos a continuación.")
        st.rerun()

    st.subheader("Subir archivos")
    key_to_label = {
        "postulaciones": "Postulaciones (reportePostulaciones)",
        "notas": "Notas / malla (RA311)",
        "promedios": "Promedios (UG305)",
        "ramos_inscritos": "Ramos inscritos (UG307)",
        "horarios": "Horarios y NRC (UG201)",
    }
    skiprows = {"horarios": 4}

    for key, label in key_to_label.items():
        up = st.file_uploader(label, type="csv", key=f"up_{key}")
        if up is not None:
            df = pd.read_csv(up, skiprows=skiprows.get(key, 0))
            df.columns = df.columns.str.strip()
            missing = validate_columns(key, df.columns)
            if missing:
                st.error(f"{label}: faltan columnas {missing}. No se guardó.")
            else:
                dest = DATA_DIR / up.name
                up.seek(0)
                dest.write_bytes(up.getvalue())
                get_data.clear()
                get_model.clear()
                st.success(f"{label}: guardado como {up.name} y datos recargados.")
```

> Nota sobre validación de `horarios`: el archivo real trae 4 filas de cabecera; por eso se valida tras `skiprows=4`. Al guardar se conserva el archivo original tal cual (con sus cabeceras), porque `data_loader.load_horarios` también aplica `skiprows=4`.

- [ ] **Step 2: Verificación manual**

Run: `streamlit run app.py`
Ingresar, ir a "Cargar datos": verificar que la tabla de estado muestra los 5 archivos como presentes. Subir un CSV con columnas incorrectas → debe rechazarlo nombrando las columnas faltantes. Probar "Limpiar todos los datos" y volver a subir los 5 → la app vuelve a funcionar (ranking disponible). 

> ⚠️ Hacer una copia de respaldo de los 5 CSV antes de probar el botón Limpiar, ya que borra los archivos del disco.

- [ ] **Step 3: Commit**

```bash
git add views/upload.py
git commit -m "feat: vista de carga de CSV persistente con validación y reset"
```

---

### Task 12: Actualizar documentación y verificación final

**Files:**
- Modify: `README.md`
- Modify: `PRESENTACION.md`

**Interfaces:** —

- [ ] **Step 1: Correr toda la batería de tests**

Run: `python -m pytest -v`
Expected: PASS en todos los módulos (data_store, data_loader, model, scoring×2, justification, auth, analysis).

- [ ] **Step 2: Actualizar `README.md`**

Reemplazar las secciones desactualizadas para reflejar: features sin `carga_actual`; score híbrido con pesos ajustables (default nota>promedio); KPI 2 = score por postulante (ya no Tiempo de Cierre); KPI 3 = filtro de horario condicional al tipo; app multipágina con login por RUT y carga persistente de CSV con reset; arreglo de rutas. Añadir entrada en "Historial de cambios" con fecha 2026-06-24 describiendo estos ajustes por feedback del cliente.

- [ ] **Step 3: Actualizar `PRESENTACION.md`**

Ajustar la tabla de KPIs y los puntos de la demo para reflejar el score como KPI, el horario condicional al tipo, el login por profesor y la carga de datos. Quitar referencias a `carga_actual` y al "Tiempo de cierre" como KPI medido.

- [ ] **Step 4: Verificación manual end-to-end**

Run: `streamlit run app.py`
Recorrer: login → ranking (sliders, KPIs, export) → cargar datos (estado, validación, reset). Confirmar que no quedan referencias a carga ni a Tiempo de Cierre en la UI.

- [ ] **Step 5: Commit**

```bash
git add README.md PRESENTACION.md
git commit -m "docs: actualizar README y presentación a los ajustes del cliente"
```

---

## Notas de implementación
- Hay un riesgo de import circular: las vistas hacen `from app import get_data, get_model` dentro de `render()` (import diferido), no a nivel de módulo. Mantenerlo así.
- `analysis.py` (análisis retrospectivo) quedó adaptado pero ya no se invoca desde la nueva app; se conserva como utilidad. Si se quiere volver a exponer, añadir una vista futura.
- El RUT como "clave" es solo un filtro de demostración; no es seguridad real (documentado en el spec).
