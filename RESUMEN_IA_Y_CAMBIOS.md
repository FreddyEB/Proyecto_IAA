# Resumen para el equipo — Qué hace la IA y qué cambió

> Documento corto para entender el estado actual del MVP de recomendación de ayudantes.
> Detalle técnico en `README.md`; diseño en `docs/superpowers/specs/` y plan en `docs/superpowers/plans/`.

---

## ¿Qué hace la IA hoy?

Dado un curso (NRC), la app **ordena a los postulantes** de mejor a peor con un **score**, y explica cada recomendación. **No asigna sola**: es apoyo a la decisión; el profesor decide.

El score es **híbrido**, combina dos cosas:

1. **Señal de IA (Random Forest):** un modelo entrenado con las decisiones históricas (quién fue Aceptado / Rechazado) que estima `P(Aceptado)` para cada postulante. Variables que usa: nota en el curso, promedio acumulado, experiencia previa como ayudante y tipo de ayudantía.
2. **Pesos ajustables por el profesor:** con sliders, el profesor decide cuánto pesa cada factor (nota, promedio, experiencia, señal de IA). Por defecto **la nota pesa más que el promedio**.

```
Score = w_nota·(Nota/7) + w_promedio·(Promedio/7) + w_experiencia·Exp + w_ia·P(Aceptado)
```

Antes de calcular el score, hay **2 filtros duros**:
- **Nota:** debe tener nota ≥ 4.75 en el curso. Si no lo cursó, queda fuera.
- **Horario (según el tipo):** el choque de horario descarta **solo** a los tipos que exigen asistencia presencial (`de Catedra`, `Laboratorio Tipo 1/2`). Para `Corrector`, `Coordinador Tipo 1/2` y `Proyecto` no aplica.

Cada candidato recomendado trae una **justificación en texto** que destaca los factores con más peso según los sliders del profesor.

---

## Cómo se usa (flujo)

1. **Cargar datos:** se suben los 5 CSV (RA311, UG201, UG305, UG307, reportePostulaciones). Quedan guardados en `app_data/` y persisten entre sesiones. **Hay que cargar los 5**; con menos, la app no deja continuar.
2. **Login:** el profesor entra con su **RUT** como clave (validado contra UG201). Solo ve **sus** cursos.
3. **Ranking:** elige un curso, ajusta los sliders, ve el ranking + KPIs + justificaciones, y exporta a Excel.

---

## KPIs

- **KPI 1 — TCA:** compatibilidad académica (recomendados con nota ≥ 4.75).
- **KPI 2 — Score de recomendación:** el score híbrido por postulante.
- **KPI 3 — Conflicto horario:** descartes por choque, solo entre tipos con asistencia obligatoria.

---

## Qué cambió respecto a la versión anterior (feedback del cliente)

| Antes | Ahora |
|---|---|
| Score = solo `P(Aceptado)` del Random Forest | **Score híbrido**: IA + **pesos ajustables** por el profesor (nota > promedio) |
| Variable "carga académica" en el modelo | **Eliminada** del modelo y de la UI (UG307 se conserva solo para horario) |
| KPI 2 = "Tiempo de Cierre" (no calculable) | **KPI 2 = el score** por postulante |
| Choque de horario descartaba a todos | Descarta **solo** según el tipo (cátedra/laboratorio) |
| Una sola página, sin usuarios | **App multipágina con login** por profesor (RUT); cada uno ve solo sus cursos |
| Datos fijos en código | **Carga de CSV** persistente (`app_data/`), reutilizable cada semestre |

### Cambios de robustez (a partir de pruebas reales)
- La app **ya no se cae** si faltan datos: entra en modo carga y pide los archivos.
- **"Limpiar" es seguro:** mueve los archivos a un respaldo recuperable (`app_data/_backup/`), **no los borra del computador** ni toca tus archivos personales.
- El app **solo gestiona la carpeta `app_data/`**; nunca lee ni borra nada fuera de ella.
- Suite de **tests automáticos** (`pytest`) para la lógica (datos, score, filtros, login).

---

## Limitaciones a tener presente

- La señal de IA aprende de decisiones históricas → puede arrastrar sesgos previos.
- El login es de demostración (POC): el RUT es llave de filtrado, no seguridad real.
- La nota se busca por coincidencia exacta de materia+curso; no detecta cursos equivalentes.
- No hay integración con los sistemas de la universidad (se trabaja con CSV).
