# Diseño — Ajustes del MVP según feedback del cliente

**Proyecto:** Sistema de Recomendación de Ayudantes · Grupo 13 · IA Aplicada 2026-01
**Fecha:** 2026-06-24
**Estado:** Aprobado para escribir plan de implementación

---

## 1. Contexto

El MVP actual (Streamlit + Random Forest) ordena postulantes por curso (NRC) y entrega
un ranking explicado como apoyo a la decisión del coordinador. Tras una reunión con el
cliente, se solicitan ajustes al modelo de score, a los KPIs y a la aplicación. Este
documento define el diseño acordado para esos ajustes.

Decisiones previas fijadas por el usuario (no se discuten aquí):
- **Umbral de nota = 4.75** (`MIN_PASSING_GRADE`), fijado manualmente. Se mantiene.
- Inconsistencias doc-vs-código que NO entran en este alcance: se dejan registradas para
  después, salvo las que se corrigen como efecto natural de estos cambios.

---

## 2. Modelo y score (híbrido)

### 2.1 Features
- Se **elimina** `CARGA_ACTUAL` del modelo y de la app.
- Se **mantienen**: `NOTA_CURSO`, `PROMEDIO`, `EXPERIENCIA`, `TIPO_NUM`.
- El Random Forest se sigue entrenando con los datos históricos (label = Aceptado/Rechazado)
  y produce la señal `P_IA = P(Aceptado)`.

### 2.2 Score final (este es el KPI 2, por postulante)
```
Score = w_nota·norm(Nota) + w_prom·norm(Promedio) + w_exp·norm(Exp) + w_ia·P_IA
```
- Cada variable se normaliza a [0,1] (nota y promedio dividido por 7.0; experiencia sobre el
  máximo observado).
- Los pesos `w_*` los ajusta el profesor con sliders (ver §4.2) y suman 1 (se renormalizan).
- **Por defecto `w_nota > w_prom`** (la nota en el curso pesa más que el promedio acumulado).
- La señal de IA (`P_IA`) entra como un término ponderado más: aporta el patrón histórico
  ("a quién aceptaban"), mientras los sliders aportan el criterio explícito del profesor.
- Nota: nota y promedio entran tanto en el RF como en el término lineal. Es intencional en un
  modelo híbrido y queda documentado.

### 2.3 Reconciliación con el feedback
- "Mantener un modelo de IA" → el Random Forest sigue presente como señal `P_IA`.
- "Importancia de variables seleccionable por el profesor" → sliders de pesos `w_*`.
- "Nota más importante que promedio" → default `w_nota > w_prom`.

---

## 3. KPIs

| KPI | Antes | Después |
|---|---|---|
| **KPI 1 — TCA** (Compatibilidad Académica) | % de postulantes que pasan el filtro de nota | **Se mantiene tal cual.** |
| **KPI 2 — Tiempo de Cierre (TCP)** | Días hábiles del proceso (nunca calculable con los datos) | **Reemplazado por el Score de recomendación**: el score por postulante (fórmula híbrida §2.2) que ya se muestra en el ranking. Se eliminan las referencias a TCP en app y documentación. |
| **KPI 3 — Conflicto Horario (TCH)** | Filtro duro universal: cualquier choque descarta al candidato | **Filtro duro condicional al tipo de ayudantía** (ver §3.1). |

### 3.1 KPI 3 — Mapeo tipo → asistencia (confirmado por el usuario)
- **Exigen asistencia (choque de horario → descarta):**
  `de Catedra`, `Laboratorio Tipo 1`, `Laboratorio Tipo 2`
- **No exigen asistencia (choque de horario → NO aplica filtro):**
  `Corrector`, `Coordinador Tipo 1`, `Coordinador Tipo 2`, `Proyecto`

El KPI/indicador TCH se calcula solo sobre los candidatos de tipos que exigen asistencia.

---

## 4. App Streamlit multipágina

Se reestructura la app de una sola página a multipágina (Streamlit multipage), 100% Python.

### 4.1 Página: Login
- El profesor ingresa **nombre + apellido** y su **clave es su RUT**.
- Se valida contra UG201 (`RUT PROFESOR` + `PROFESOR`). El match real es por **RUT**;
  el nombre/apellido es para la UX.
- Sin RUT válido en UG201 → no entra.
- Es un POC: el RUT funciona como llave de filtrado, no como mecanismo de seguridad real.
- Al autenticar, se guarda el RUT del profesor en el estado de sesión.

### 4.2 Página: Mis cursos / Ranking
- Muestra **solo los NRC donde ese RUT es el profesor** (según UG201).
- Por curso seleccionado:
  - Ranking de candidatos con score híbrido.
  - KPIs: TCA, Score (KPI 2), Conflicto horario (KPI 3 condicional al tipo).
  - **Sliders de pesos** del score (`w_nota`, `w_prom`, `w_exp`, `w_ia`), con default `w_nota > w_prom`.
  - Justificación por candidato (usa los pesos del profesor para elegir factores a destacar).
  - Exportar a Excel.
- Se quita `carga_actual` de toda la UI.

### 4.3 Página: Cargar datos (CSV)
- Subir los 5 archivos; se reconocen por código en el nombre: `RA311`, `UG201`, `UG305`,
  `UG307`, `reportePostulaciones`.
- Validar que cada archivo tenga las columnas esperadas; avisar si falta algo crítico.
- **Persistencia en disco**: los archivos subidos se guardan en la carpeta de datos del
  proyecto para que persistan entre sesiones (el profesor no resube cada vez).
- **Limpiar/resetear**: opción para borrar los datos actuales antes de subir un set nuevo,
  evitando que la información de distintos períodos choque.
- Tras cargar/limpiar, se invalida la caché y se re-entrena el modelo.

---

## 5. Correcciones técnicas incluidas
- Arreglar **rutas** en `data_loader.py` (los CSV viven en la carpeta del proyecto, no en
  `parent.parent`).
- La **justificación** pasa a usar los pesos del profesor (corrige de paso la inconsistencia
  actual con los pesos lineales viejos).

## 6. Fuera de alcance
- Migración a backend + frontend separado (FastAPI/React) o a Reflex/Dash. Se mantiene Streamlit.
- Resto de inconsistencias doc-vs-código no mencionadas arriba.
- Seguridad real de autenticación (es POC).
- Detección automática de cursos equivalentes.

---

## 7. Componentes y responsabilidades (resumen)

| Módulo | Cambio principal |
|---|---|
| `data_loader.py` | Arreglar rutas; soportar recarga tras subir CSV. |
| `model.py` | Quitar `CARGA_ACTUAL` de FEATURES; el RF entrega `P_IA`. |
| `scoring.py` | Score híbrido con pesos del profesor; filtro de horario condicional al tipo. |
| `justification.py` | Usar pesos del profesor para elegir factores. |
| `app.py` → multipágina | Login, Mis cursos/Ranking (con sliders), Cargar datos (persistente + reset). |
| Datos (UG201) | Fuente de la relación profesor↔NRC vía `RUT PROFESOR`. |

---

## 8. Supuestos a validar en implementación
- Formato del RUT consistente entre UG201 (`RUT PROFESOR`) y lo que tipea el profesor /
  el RUT incrustado en `reportePostulaciones.Profesor` (`"APELLIDO/APELLIDO NOMBRE,RUT"`).
- Estrategia exacta de normalización de pesos (renormalizar a suma 1) y defaults numéricos
  concretos de los sliders.
