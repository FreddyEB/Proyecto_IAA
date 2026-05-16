# Sistema de Recomendación de Ayudantes — MVP

**Curso:** IA Aplicada · Universidad de los Andes · 2026-01  
**Grupo 13:** Freddy Bacigalupo, Clemente Barros, Ignacio Liberón  
**Profesora:** Carla Vairetti · **Ayudante:** Samuel Aliaga

---

## Descripción

Sistema inteligente de recomendación de ayudantes para la Facultad de Ingeniería y Ciencias Aplicadas. Dado un curso (NRC), el sistema identifica a los postulantes más adecuados aplicando filtros de elegibilidad y un modelo de Machine Learning que predice la probabilidad de que un candidato sea aceptado, basándose en decisiones históricas reales.

---

## Cómo ejecutar

```bash
cd ayudantes_mvp
pip install -r requirements.txt
streamlit run app.py
```

La app se abre automáticamente en `http://localhost:8501`.

---

## Estructura del proyecto

```
ayudantes_mvp/
├── app.py            # Interfaz Streamlit
├── model.py          # Entrenamiento y predicción (Random Forest)
├── scoring.py        # Filtros duros + ranking con score del modelo
├── data_loader.py    # Carga y limpieza de los 5 CSVs
├── justification.py  # Generación de texto explicativo en español
├── requirements.txt
└── README.md
```

### Archivos de datos (directorio raíz del proyecto)

| Archivo | Contenido | Uso |
|---|---|---|
| `reportePostulaciones 202610.xlsx - Registros.csv` | Postulaciones con estado (Aceptado/Rechazado/Pendiente) | Candidatos + etiquetas de entrenamiento |
| `RA311 - Cumplimiento de Malla Pregrado...csv` | Historial académico completo con notas por curso | Nota del postulante en el curso |
| `UG305 - Reporte Alumnos con Promedio...csv` | Promedio acumulado por alumno | Feature: promedio general |
| `UG307 - Ramos Inscritos por Periodo...csv` | Ramos inscritos en el período actual | Feature: carga académica + detección de conflictos horarios |
| `UG201 - Listado de NRC por Periodo...csv` | NRCs con horarios por día | Horarios de cursos para filtro de conflicto |

> Los nombres de estudiantes no están presentes en los datos por privacidad. El **RUT** es el identificador único de cada postulante.

---

## Arquitectura del sistema

```
CSVs (datos reales)
      │
      ▼
data_loader.py  ──►  model.py (Random Forest)
      │                    │
      ▼                    ▼ P(Aceptado)
scoring.py  ◄─────────────┘
  │  Filtros duros (nota ≥ 4.0, sin conflicto horario)
  │  Score = predict_proba del modelo
      │
      ▼
justification.py  ──►  texto explicativo por candidato
      │
      ▼
app.py (Streamlit)
```

---

## Modelo de IA — Random Forest

### Problema de aprendizaje
Clasificación binaria supervisada:  
- **Label 1:** postulante fue `Aceptado` históricamente  
- **Label 0:** postulante fue `Rechazado`

### Features

| Feature | Descripción | Fuente |
|---|---|---|
| `NOTA_CURSO` | Mejor nota del postulante en el curso específico | RA311 |
| `PROMEDIO` | Promedio académico acumulado | UG305 |
| `CARGA_ACTUAL` | Número de ramos inscritos este período | UG307 |
| `EXPERIENCIA` | Semestres previos como ayudante aceptado | reportePostulaciones |
| `TIPO_NUM` | Tipo de ayudantía (corrector, cátedra, lab, etc.) codificado | reportePostulaciones |

### Configuración del modelo

```python
RandomForestClassifier(
    n_estimators=200,
    max_depth=6,
    min_samples_leaf=5,
    class_weight="balanced",  # compensa desbalance Aceptado/Rechazado
    random_state=42,
)
```

### Métricas (validación cruzada 5-fold)

| Métrica | Valor |
|---|---|
| CV Accuracy | 68.4% ± 3.3% |
| CV ROC-AUC | 0.754 ± 0.011 |
| Muestras de entrenamiento | 446 |
| Aceptados / Rechazados | 300 / 146 |

### Feature importances (aprendidas del modelo)

| Variable | Importancia |
|---|---|
| Tipo de ayudantía | ~40% |
| Promedio acumulado | ~21% |
| Nota en el curso | ~17% |
| Experiencia previa | ~14% |
| Carga académica | ~8% |

> El modelo descubrió que el **tipo de ayudantía** es el factor más predictivo, algo que los pesos fijos del modelo lineal original no capturaban.

---

## Lógica de decisión

### Paso 1 — Filtros duros (no negociables)
1. **Filtro de nota:** el postulante debe tener nota ≥ 4.0 en el curso exacto (MATERIA + CURSO en RA311). Si no cursó el ramo, queda descartado.
2. **Filtro de horario:** se cruzan los bloques horarios del NRC objetivo (UG201) con los ramos inscritos del postulante (UG307). Si hay superposición, queda descartado.

### Paso 2 — Scoring con Random Forest
Para los candidatos que pasan los filtros, el score es `P(Aceptado)` según el modelo entrenado. Se ordenan de mayor a menor y se presentan los top-N.

### Paso 3 — Justificación automática
Para cada candidato se genera un texto en español que menciona los 2-3 factores más relevantes de su perfil (nota, experiencia, promedio, carga).

---

## KPIs medidos en la app

| KPI | Descripción | Objetivo |
|---|---|---|
| **TCA** — Tasa de Compatibilidad Académica | % de postulantes que pasan el filtro de nota | ≥ 90% |
| **TCH** — Tasa de Conflicto Horario | % de postulantes con conflicto horario detectado | ≤ 2% |
| Postulantes activos | Total con estado Pendiente o Aceptado para el NRC | — |
| Candidatos elegibles | Postulantes que pasan ambos filtros duros | — |

---

## Funcionalidades de la interfaz

- **Selector de NRC** en sidebar (solo NRCs con postulaciones activas)
- **Slider** para elegir cuántos candidatos mostrar (1–10)
- **Métricas del modelo** en sidebar: accuracy, ROC-AUC, muestras de entrenamiento
- **Gráfico de feature importances** aprendidas por el Random Forest
- **Tabla de ranking** con gradiente de color por score
- **Cards expandibles** por candidato con métricas individuales y justificación
- **Exportación a Excel** con 3 hojas: Ranking, Resumen KPI, Feature Importances

---

## Dependencias

```
streamlit==1.35.0
pandas==2.2.2
openpyxl==3.1.2
xlsxwriter==3.2.0
scikit-learn==1.5.0
```

---

## Limitaciones conocidas

- El modelo se entrena con datos del período 202610. No hay datos de períodos anteriores para ampliar el conjunto de entrenamiento.
- La nota del postulante en el curso se busca por coincidencia exacta de MATERIA+CURSO. Cursos equivalentes o renombrados no se detectan automáticamente.
- Los pesos del modelo reflejan los criterios de selección históricos de los coordinadores, que pueden tener sesgos implícitos.
- No hay integración directa con los sistemas académicos de la universidad (Proof of Concept).

---

## Historial de cambios

| Fecha | Cambio |
|---|---|
| 2026-05-15 | Implementación inicial: `data_loader.py`, `scoring.py` (pesos lineales fijos), `justification.py`, `app.py` |
| 2026-05-15 | Reemplazo del scoring lineal por modelo Random Forest (`model.py`). Score = P(Aceptado). Métricas de CV y feature importances visibles en la app. |
| 2026-05-15 | Creación de este documento (`README.md`) |
