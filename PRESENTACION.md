# Guía de Presentación — MVP Recomendación de Ayudantes
**Grupo 13** · Freddy Bacigalupo, Clemente Barros, Ignacio Liberón  
**Formato:** 7 min presentación + 10 min preguntas

---

## Estructura (7 min exactos)

### [0:00 – 1:00] Problema en una frase
> *"Asignar ayudantes hoy es manual, lento y propenso a conflictos de horario. Esto lo resuelve el sistema que van a ver, ordenando candidatos con un score explicable que el profesor puede ajustar."*

Pasar directo a la demo.

---

### [1:00 – 4:30] Demo en vivo ← núcleo de la presentación

1. **Login:** ingresar como profesor (clave = RUT). Mostrar que solo aparecen *sus* cursos.
2. Seleccionar un NRC → mostrar el ranking con scores.
3. **Mover los sliders de pesos** (nota, promedio, experiencia, señal IA):
   > *"El profesor decide qué importa más. Por defecto la nota pesa más que el promedio, pero es ajustable — y la IA sigue aportando el patrón histórico."*
4. Expandir el candidato #1 → leer la justificación en voz alta (cambia con los pesos).
5. Mostrar la página **Cargar datos**:
   > *"Para el próximo semestre, el profesor sube los nuevos CSV, se guardan y el modelo se reentrena. Un botón limpia el set anterior."*

---

### [4:30 – 6:00] KPIs: qué medimos

| KPI | Qué mide |
|---|---|
| **KPI 1 — TCA** | Compatibilidad académica (nota ≥ 4.75) de los recomendados |
| **KPI 2 — Score de recomendación** | Calidad del candidato según el score híbrido |
| **KPI 3 — Conflicto horario** | Descartes por choque, solo en tipos con asistencia obligatoria (cátedra / laboratorio) |

---

### [6:00 – 7:00] Una limitación honesta + próximo paso
> *"Hoy funciona con CSVs subidos manualmente y el login es de demostración. El siguiente paso natural es conectarlo a los sistemas de la universidad."*

---

## Lo que NO prometer

- ❌ Integración con sistemas institucionales (no implementada)
- ❌ Seguridad real del login (el RUT es solo llave de filtrado)
- ❌ Detección automática de cursos equivalentes (no implementada)

## Lo que SÍ se puede prometer

- ✅ Ranking reproducible con score híbrido (IA + criterio del profesor)
- ✅ Importancia de variables ajustable por el profesor
- ✅ Justificaciones explicables por candidato
- ✅ Filtro de horario inteligente según el tipo de ayudantía
- ✅ Carga de datos persistente para reutilizar cada semestre
- ✅ Exportación a Excel lista para usar
