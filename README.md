# Sistema de Recomendación de Ayudantes — MVP

**Curso:** IA Aplicada · Universidad de los Andes · 2026-01  
**Grupo 13:** Freddy Bacigalupo, Clemente Barros, Ignacio Liberón  
**Profesora:** Carla Vairetti · **Ayudante:** Samuel Aliaga

---

## Descripción

Sistema inteligente de recomendación de ayudantes para la Facultad de Ingeniería y Ciencias Aplicadas. Dado un curso (NRC), el sistema aplica filtros de elegibilidad y un **score híbrido** (modelo de Machine Learning + pesos ajustables por el profesor) para ordenar a los postulantes más adecuados, con justificaciones explicables. Actúa como apoyo a la decisión: el profesor decide.

---

## Cómo ejecutar

> **Requisito:** Python **3.11 o 3.12**. No uses Python 3.14: rompe Streamlit
> (`TypeError: Metaclasses with custom tp_new are not supported`).
> Verifica tu versión con `python3 --version`.

### Opción A — con entorno virtual (recomendado)

Aísla las dependencias del proyecto para no instalarlas globalmente.

```bash
# 1. Crear el entorno virtual (una sola vez)
python3.12 -m venv .venv

# 2. Activarlo (cada vez que abras una terminal nueva)
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows (PowerShell)

# 3. Instalar dependencias (una sola vez, dentro del venv)
pip install -r requirements.txt

# 4. Ejecutar la app
streamlit run app.py
```

Verás `(.venv)` al inicio del prompt cuando esté activo. Para salir del entorno: `deactivate`.

### Opción B — sin entorno virtual

Instala las dependencias en tu Python global (más simple, pero las mezcla con otros proyectos):

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Resultado

La app se abre en `http://localhost:8501`. La primera vez (sin datos) entra en **modo carga**: sube los 5 CSV desde la página *Cargar datos* y quedan guardados en el almacén del app (`app_data/`), que persiste entre sesiones. El app **solo** gestiona esa carpeta; nunca lee ni borra archivos fuera de ella.

### Tests

Con el venv activo (o en tu Python global, según la opción elegida):

```bash
python -m pytest -q
```

---

## Estructura del proyecto

```
ayudantes_mvp/
├── app.py            # Entrada Streamlit multipágina (st.navigation) + login
├── views/
│   ├── login.py      # Login de profesor (clave = RUT)
│   ├── ranking.py    # Ranking por curso, sliders de pesos, KPIs, export
│   └── upload.py     # Carga persistente de CSV con validación y reset
├── auth.py           # Autenticación por RUT contra UG201
├── data_store.py     # Resolución, validación y persistencia de los CSV
├── data_loader.py    # Carga y limpieza de los CSV
├── model.py          # Random Forest (señal P(Aceptado))
├── scoring.py        # Filtros + score híbrido con pesos ajustables
├── justification.py  # Texto explicativo por candidato (según pesos)
├── analysis.py       # Análisis retrospectivo (utilidad)
├── tests/            # Suite pytest
├── requirements.txt
└── README.md
```

### Archivos de datos (almacén del app: `app_data/`)

| Código | Contenido | Uso |
|---|---|---|
| `reportePostulaciones` | Postulaciones con estado (Aceptado/Rechazado/Pendiente) | Candidatos + etiquetas de entrenamiento + experiencia |
| `RA311` | Historial académico con notas por curso | Nota del postulante en el curso |
| `UG305` | Promedio acumulado por alumno | Feature: promedio general |
| `UG307` | Ramos inscritos en el período | Detección de conflictos horarios |
| `UG201` | NRCs con horarios, tipo y profesor | Horarios, tipo de bloque y relación profesor↔curso |

> Los nombres de estudiantes no están presentes por privacidad. El **RUT** es el identificador único.

---

## Login de profesores

El profesor ingresa su nombre y apellido, y su **clave es su RUT**. El RUT se valida contra `RUT PROFESOR` en UG201 y determina **qué cursos (NRC) ve**: solo los que dicta ese período. Es un mecanismo de demostración (POC), no de seguridad real.

---

## Modelo de IA y score híbrido

### Señal de IA — Random Forest
Clasificación binaria supervisada (`1 = Aceptado`, `0 = Rechazado`) entrenada con las decisiones históricas. Features: `NOTA_CURSO`, `PROMEDIO`, `EXPERIENCIA`, `TIPO_NUM`. Produce `P_IA = P(Aceptado)`.

> La feature `CARGA_ACTUAL` fue eliminada del modelo. UG307 se conserva solo para la detección de conflictos horarios.

### Score final (KPI 2, por postulante)
```
Score = w_nota·(Nota/7) + w_prom·(Promedio/7) + w_exp·norm(Exp) + w_ia·P_IA
```
Los pesos `w_*` los ajusta el profesor con sliders (suman 1 al renormalizar). Por defecto **la nota pesa más que el promedio**: `{nota: 0.40, promedio: 0.15, experiencia: 0.20, ia: 0.25}`.

---

## Lógica de decisión

### Filtros duros
1. **Nota:** el postulante debe tener nota ≥ **4.75** en el curso exacto (RA311). Si no cursó el ramo, queda descartado.
2. **Horario (condicional al tipo):** el choque de horario descarta **solo** a los tipos que exigen asistencia presencial: `de Catedra`, `Laboratorio Tipo 1`, `Laboratorio Tipo 2`. Para `Corrector`, `Coordinador Tipo 1/2` y `Proyecto` el choque **no aplica**.

### Ranking y justificación
Los elegibles se ordenan por score híbrido (top-N configurable). Para cada uno se genera una justificación en español que destaca los factores de mayor peso según los sliders del profesor.

---

## KPIs

| KPI | Descripción |
|---|---|
| **KPI 1 — TCA** | % de candidatos recomendados que cumplen el filtro de nota (≥ 4.75) |
| **KPI 2 — Score de recomendación** | El score híbrido por postulante (reemplaza al antiguo "Tiempo de Cierre") |
| **KPI 3 — Conflicto horario** | Descartes por choque de horario, solo entre tipos con asistencia obligatoria |

---

## Carga de datos (próximos semestres)

La página **Cargar datos** permite subir los 5 CSV (reconocidos por código: RA311, UG201, UG305, UG307, reportePostulaciones), validando columnas. Los archivos se guardan en el almacén del app (`app_data/`) y persisten entre sesiones. El botón **Limpiar** (con confirmación) saca el set actual del almacén **moviéndolo a un respaldo recuperable** (`app_data/_backup/<fecha>/`) — no borra nada de tu computador ni toca tus archivos originales. Tras cargar o limpiar, el modelo se re-entrena.

---

## Dependencias

```
streamlit==1.39.0
pandas==2.2.2
openpyxl==3.1.2
xlsxwriter==3.2.0
scikit-learn==1.5.0
pytest==8.2.0
```

---

## Limitaciones conocidas

- El modelo se entrena con datos del período cargado; la señal de IA refleja criterios históricos de selección, que pueden tener sesgos.
- La nota en el curso se busca por coincidencia exacta MATERIA+CURSO; cursos equivalentes no se detectan automáticamente.
- El login es un POC: el RUT funciona como llave de filtrado, no como seguridad real.
- No hay integración directa con los sistemas académicos de la universidad.

---

## Historial de cambios

| Fecha | Cambio |
|---|---|
| 2026-05-15 | Implementación inicial y reemplazo del scoring lineal por Random Forest. |
| 2026-05-17 | Guía de presentación y análisis retrospectivo. |
| 2026-05-18 | Umbral `MIN_PASSING_GRADE` a 4.75. |
| 2026-06-24 | **Ajustes por feedback del cliente:** score híbrido con pesos ajustables (nota > promedio), eliminación de `CARGA_ACTUAL`, KPI 2 = score por postulante, KPI 3 de horario condicional al tipo, app multipágina con login por profesor (RUT) y carga persistente de CSV con reset, arreglo de rutas, suite de tests pytest. |
