# Guía de Presentación — MVP Recomendación de Ayudantes
**Grupo 13** · Freddy Bacigalupo, Clemente Barros, Ignacio Liberón

---

## 1. Contexto y problema *(2 min)*

- El proceso actual de asignación de ayudantes es **manual, lento y sin criterios sistemáticos**
- El coordinador revisa perfiles uno a uno con información dispersa
- Consecuencias: conflictos de horario no detectados, asignaciones subóptimas, alta carga operativa

---

## 2. Solución propuesta *(2 min)*

- Sistema de recomendación que **automatiza la evaluación** de postulantes para cada curso
- Genera un ranking ordenado con justificación para cada candidato
- **La decisión final siempre es del coordinador** — el sistema lo apoya, no lo reemplaza

---

## 3. Demostración en vivo *(5–7 min)*

1. Abrir la app y seleccionar un NRC con varios postulantes
2. Mostrar los KPIs (TCA, TCH) y explicar qué miden
3. Mostrar el gráfico de **feature importances** → explicar el componente de IA
4. Expandir 2–3 cards de candidatos y leer las justificaciones
5. Descargar el Excel y mostrar las hojas brevemente

---

## 4. El modelo de IA *(3 min)*

- **Random Forest** entrenado con decisiones históricas reales (Aceptado/Rechazado)
- Aprende qué características predicen una buena asignación — sin pesos fijos arbitrarios

**Feature importances aprendidas:**

| Variable | Importancia |
|---|---|
| Tipo de ayudantía | ~40% |
| Promedio acumulado | ~21% |
| Nota en el curso | ~17% |
| Experiencia previa | ~14% |
| Carga académica | ~8% |

> El modelo descubrió que el **tipo de ayudantía** es el factor más predictivo — algo que no habría surgido con pesos fijos.

**Métricas (validación cruzada 5-fold):**
- CV Accuracy: **68.4%** · CV ROC-AUC: **0.754**
- Entrenado con 446 muestras (300 aceptados / 146 rechazados)

---

## 5. KPIs y medición de impacto *(2 min)*

| KPI | Línea base | Objetivo MVP |
|---|---|---|
| TCA — Compatibilidad Académica | ~67% | ≥ 90% |
| TCP — Tiempo de Cierre del Proceso | ~12 días hábiles | ≤ 5 días hábiles |
| TCH — Conflicto Horario | ~12% | ≤ 2% |

- **TCA:** el filtro de nota mínima garantiza que solo candidatos con dominio del curso aparezcan en el ranking
- **TCP:** el coordinador pasa de revisar perfiles individuales a validar un ranking ya estructurado
- **TCH:** la verificación automática de horarios elimina conflictos antes de la asignación

---

## 6. Limitaciones y trabajo futuro *(2 min)*

| Limitación | Impacto |
|---|---|
| Solo un período de datos (202610) | Modelo entrenado con ~446 muestras; mejorará con más períodos históricos |
| No detecta cursos equivalentes | Postulantes que aprobaron el ramo con otro código quedan descartados |
| Sin integración con sistemas de la universidad | Los datos se cargan manualmente desde CSVs exportados (PoC) |
| Sin seguimiento post-asignación | No se mide si el ayudante recomendado tuvo buen desempeño real |

**Próximos pasos:**
- Incorporar datos históricos de períodos anteriores para robustecer el modelo
- Definir tabla de equivalencias de cursos con el coordinador
- Evaluar integración con sistemas académicos institucionales
