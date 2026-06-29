# Informe Ejecutivo — Sistema de Recomendación de Ayudantes

**Proyecto:** Optimización de la Programación Académica y Gestión Curricular
**Curso:** IA Aplicada · Universidad de los Andes · Primer Semestre 2026
**Grupo 13:** Freddy Bacigalupo · Clemente Barros · Ignacio Liberón
**Profesora:** Carla Vairetti · **Ayudante:** Samuel Aliaga

---

## 1. Problema

La asignación de ayudantes en la Facultad es un proceso **manual, lento y poco trazable**. Cada coordinador debe revisar decenas de postulaciones por curso y cruzar a mano información dispersa (notas, promedios, experiencia, disponibilidad horaria) para decidir. Esto genera alta carga operativa, decisiones poco homogéneas y conflictos de horario detectados tarde, que obligan a reasignaciones.

**Pregunta que aborda el proyecto:** ¿de qué manera se puede apoyar la asignación de ayudantes de forma más eficiente, objetiva y sistemática, usando la información académica disponible?

## 2. Objetivos

- Ordenar a los postulantes de cada curso con un **puntaje objetivo y explicable**, como **apoyo a la decisión** (no la reemplaza: el coordinador decide).
- Reducir la carga operativa y los errores (conflictos de horario, candidatos sin dominio del ramo).
- Entregar una herramienta **funcional, usable y mantenible** que el cliente pueda operar de forma autónoma cada semestre.

## 3. Solución implementada

Aplicación web (Streamlit) que, a partir de los datos del período, genera un **ranking de candidatos por curso** con justificación en lenguaje natural. El flujo es: **cargar datos → ingresar como profesor → revisar ranking y KPIs → exportar**.

Componentes principales:
- **Filtros duros (no negociables):** nota ≥ 4.75 en el ramo, y **sin conflicto de horario** para los tipos que exigen asistencia presencial (cátedra y laboratorio).
- **Score híbrido configurable:** combina una **señal de IA** (Random Forest que estima la probabilidad de ser un buen ayudante a partir de decisiones históricas) con **pesos que el profesor ajusta** (nota, promedio, experiencia, señal de IA). Por defecto la nota pesa más que el promedio.

  `Score = w_nota·(Nota/7) + w_prom·(Promedio/7) + w_exp·Exp + w_ia·P(Aceptado)`
- **Justificación automática** por candidato, según los factores de mayor peso.
- **Login por profesor** (clave = RUT, validado contra UG201): cada uno ve solo sus cursos.
- **Carga de datos persistente** y reutilizable cada semestre, con respaldo recuperable.

> **Alineación con el cliente:** el modelo y los KPIs fueron **rediseñados según el feedback del cliente** (mayor peso a la nota que al promedio, KPIs comprensibles, conflicto de horario dependiente del tipo de ayudantía). Esto corrige la observación de que indicadores previos no le hacían sentido al cliente.

## 4. Tecnologías

Python 3.12 · **Streamlit** (interfaz) · **scikit-learn** (Random Forest) · **pandas** (datos) · openpyxl/xlsxwriter (export Excel) · **pytest** (pruebas automáticas). Datos de entrada: 5 reportes institucionales en CSV (postulaciones, RA311 notas, UG305 promedios, UG307 ramos inscritos, UG201 horarios/profesor).

## 5. KPIs definidos y resultados (datos reales del período)

> Reproducibles con `python kpi_report.py` (ver `docs/kpi_evidencia.md`).

| KPI | Definición | Resultado |
|---|---|---|
| **KPI 1 — TCA** (Compatibilidad Académica) | % de ayudantes que cumplen nota ≥ 4.75 en el ramo | **87,7 %** histórico (línea base ≈67 %, objetivo 90 %); **100 % por construcción** en las recomendaciones del sistema |
| **KPI 2 — Score de recomendación** | Puntaje híbrido por candidato | Score medio **0,69** (mediana 0,70) sobre **519** candidatos recomendados en **94** cursos |
| **KPI 3 — Conflicto de horario** | Asignaciones inviables por choque de horario (tipos con asistencia) | **72** descartes automáticos detectados |

**Evidencia de utilidad del ranking** (validación retrospectiva sobre 87 cursos con un aceptado histórico): el candidato #1 del modelo coincide con el que el coordinador eligió en el **79,3 %** de los casos, y el aceptado aparece en el **Top-3 en el 94,3 %**. Es decir, el sistema reproduce con alta fidelidad las decisiones reales, evidenciando que es un apoyo útil y no aleatorio.

**Modelo (señal de IA):** 446 casos de entrenamiento (300 aceptados / 146 rechazados), validación cruzada 5-fold con Accuracy 67 % y ROC-AUC 0,75. Importancia de variables aprendida: tipo de ayudantía 42 %, promedio 24 %, nota en el curso 19 %, experiencia 15 %.

## 6. Análisis de resultados

- **Calidad académica garantizada:** al ser la nota un filtro duro, el 100 % de los recomendados domina el ramo; el TCA histórico (87,7 %) ya supera ampliamente la línea base estimada (67 %).
- **Apoyo real a la decisión:** el alto acierto Top-1/Top-3 muestra que el ranking concuerda con el criterio experto del coordinador, pero entregándolo en segundos y de forma trazable.
- **Prevención de conflictos:** los 72 descartes por horario son reasignaciones evitadas antes de publicar.
- **Hallazgo del modelo:** el **tipo de ayudantía** es la variable más predictiva de la decisión histórica (42 %), algo que un esquema de pesos fijos no capturaba; por eso se mantiene una señal de IA dentro del score híbrido.

## 7. Aprendizajes

- **Validar con el cliente cambia el diseño:** los KPIs y los pesos del modelo se reformularon tras su feedback; un indicador "correcto" técnicamente pero sin sentido para el cliente no aporta valor.
- **La nota no lo es todo:** el dato histórico mostró que el coordinador pondera múltiples factores; el modelo híbrido (IA + pesos ajustables) respeta el criterio humano en lugar de imponer una fórmula rígida.
- **Robustez operativa:** las pruebas con uso real revelaron fallos (dependencias, manejo de datos faltantes, borrado de archivos) que se corrigieron; un MVP "funciona" solo cuando soporta el uso real, no solo el camino feliz.

## 8. Limitaciones y trabajo futuro

**Limitaciones:** la señal de IA aprende de decisiones históricas y puede arrastrar sus sesgos; la nota se busca por coincidencia exacta materia+curso (no detecta cursos equivalentes); el login es de demostración (POC), no seguridad real; no hay integración directa con los sistemas de la universidad.

**Trabajo futuro:** integración directa con los sistemas académicos; detección de cursos equivalentes; reentrenamiento con datos de varios períodos; gestión de preferencias del coordinador; autenticación real y multiusuario.
