# Evidencia de KPIs (datos reales)

> Generado por `kpi_report.py`. Período cargado en `app_data/`.
> Pesos del score (por defecto): {'nota': 0.4, 'promedio': 0.15, 'experiencia': 0.2, 'ia': 0.25}.

## Resumen del modelo (señal de IA)

- Muestras de entrenamiento: **446** (aceptados 300 / rechazados 146)
- Validación cruzada 5-fold — Accuracy: **67.0% ± 3.5%**, ROC-AUC: **0.750 ± 0.015**, F1: **0.716**

Importancia de variables aprendida por el Random Forest:

| Variable | Importancia |
|---|---|
| Tipo de ayudantía | 42.1% |
| Promedio acumulado | 23.8% |
| Nota en el curso | 18.9% |
| Experiencia previa | 15.1% |

## KPI 1 — TCA real (compatibilidad académica histórica)

- Asignaciones aceptadas analizadas (con nota en RA311): **300** de 486 totales.
- **TCA real = 87.7%** (línea base estimada 67.0%, objetivo 90.0%).
- Interpretación: porcentaje de ayudantes aceptados que cumplían el umbral de nota ≥ 4.75 en el ramo. El sistema **garantiza por construcción** este filtro en sus recomendaciones (TCA = 100% sobre los recomendados).

## KPI 2 — Score de recomendación

- Candidatos recomendados evaluados: **519** (en 94 NRC con recomendación)
- Score promedio: **0.694** · mediana: **0.702** · mín–máx: 0.393–0.990

### Acierto del ranking vs. decisiones históricas del coordinador
- NRC evaluados (con un aceptado histórico): **87**
- **Top-1**: en **79.3%** de los NRC, el candidato #1 del modelo coincide con el que el coordinador eligió.
- **Top-3**: en **94.3%** de los NRC, el aceptado aparece entre los 3 primeros.
- Interpretación: el ranking reproduce con alta fidelidad las decisiones reales, evidencia de que es un apoyo útil (no aleatorio).

## KPI 3 — Conflicto de horario

- Descartes por choque de horario (solo tipos con asistencia obligatoria: Laboratorio Tipo 1, Laboratorio Tipo 2, de Catedra): **72**.
- Interpretación: el sistema detecta y descarta automáticamente asignaciones inviables por horario en los tipos que exigen asistencia, evitando reasignaciones posteriores.
