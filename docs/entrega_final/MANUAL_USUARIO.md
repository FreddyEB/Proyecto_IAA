# Manual de Usuario — Sistema de Recomendación de Ayudantes

**Grupo 13 · IA Aplicada · Universidad de los Andes · 2026**

---

## 1. ¿Qué es y para qué sirve?

Es una aplicación web que ayuda a **coordinadores y profesores** a elegir ayudantes para sus cursos. Dado un curso, el sistema **ordena a los postulantes** de mejor a peor con un puntaje objetivo y entrega una **explicación** de por qué se recomienda a cada uno.

**Importante:** la herramienta es un **apoyo a la decisión**. No asigna sola: usted revisa el ranking y toma la decisión final.

## 2. ¿A quién está dirigida?

A profesores y coordinadores académicos que reciben postulaciones de ayudantes. No requiere conocimientos técnicos para usarla.

## 3. Requisitos para usarla

- Un computador con la aplicación instalada y en ejecución (ver *Manual de Instalación*). Si alguien del equipo técnico ya la dejó corriendo, solo necesita el navegador.
- Un **navegador web** (Chrome, Edge, Firefox o Safari).
- Los **5 archivos de datos** del período en formato CSV (los entrega la universidad):
  1. Postulaciones (`reportePostulaciones`)
  2. Notas / malla (`RA311`)
  3. Promedios (`UG305`)
  4. Ramos inscritos (`UG307`)
  5. Horarios y NRC por período (`UG201`)
- Su **RUT**, que funciona como clave de ingreso.

## 4. Funcionalidades

- **Carga de datos** persistente (se guarda y dura entre sesiones).
- **Ingreso por profesor:** cada uno ve únicamente sus cursos.
- **Ranking de candidatos** por curso, con puntaje y justificación.
- **Sliders de importancia:** usted decide cuánto pesa cada criterio.
- **Indicadores (KPIs)** del proceso y página de **Validación** del modelo.
- **Exportación a Excel** del ranking.

## 5. Paso a paso

### Paso 1 — Abrir la aplicación
Abra el navegador en la dirección que indica el equipo técnico (por defecto `http://localhost:8501`).

### Paso 2 — Cargar los datos (solo la primera vez del período)
Si aún no hay datos, la app abre directamente la página **Cargar datos**:
1. Suba cada uno de los **5 archivos CSV** en su casilla correspondiente.
2. La app valida cada archivo; si falta una columna, lo avisa y no lo guarda.
3. Debe cargar **los 5**. Mientras falte alguno, verá un aviso ("Faltan N archivos…") y **no podrá continuar**.
4. Cuando estén los 5, aparece "✅ Ya puede iniciar sesión".

> Los datos quedan guardados; en los siguientes ingresos del semestre no hay que volver a subirlos.

### Paso 3 — Ingresar
1. Escriba su **nombre y apellido**.
2. En **clave**, escriba su **RUT** (con o sin puntos/guión, da igual).
3. Presione **Ingresar**. Verá solo **sus** cursos.

### Paso 4 — Revisar el ranking de un curso
1. Elija un curso (NRC) en el selector.
2. Vea la tabla de candidatos ordenados por **Score**, con nota, experiencia, promedio y tipo de ayudantía.
3. Lea la **justificación** de cada candidato desplegando "Detalle por candidato".

### Paso 5 — Ajustar la importancia de los criterios (opcional)
En la barra lateral mueva los **sliders** (Nota, Promedio, Experiencia, Señal de IA). El ranking y las justificaciones se recalculan al instante. Ponga en 0 los criterios que no le interesen.

### Paso 6 — Revisar los KPIs y la validación (opcional)
- En la página del ranking verá los **3 KPIs** del curso.
- En la página **Validación / KPIs** verá la evidencia del modelo (TCA real, acierto del ranking frente a decisiones históricas).

### Paso 7 — Exportar
Presione **Descargar Excel** para obtener el ranking con justificaciones y KPIs.

### Paso 8 — Cambiar de período (cuando corresponda)
En **Cargar datos**, marque la casilla de confirmación y presione **Limpiar**: el set actual se mueve a un respaldo recuperable (no se borra de su computador). Luego suba los archivos del nuevo período.

## 6. Casos de uso

- **"Necesito 2 ayudantes de cátedra para mi curso":** ingrese, abra el curso, mire el Top del ranking; suba el peso de *Nota* y *Experiencia* si quiere priorizar dominio del ramo y experiencia previa. Exporte y comunique su decisión.
- **"Quiero comparar candidatos con criterio propio":** ajuste los sliders a su criterio (p. ej. dar más peso a la señal de IA si confía en el patrón histórico) y observe cómo cambia el orden.
- **"Empieza un nuevo semestre":** limpie los datos anteriores (quedan respaldados) y cargue los CSV del período nuevo.

> **Recomendación:** valide con un par de cursos conocidos que el ranking le hace sentido antes de usarlo de forma masiva.

## 7. Limitaciones conocidas

- La nota se busca por coincidencia exacta de **materia + curso**; cursos equivalentes o renombrados no se detectan automáticamente.
- La señal de IA aprende de decisiones históricas y puede reflejar sesgos previos.
- El ingreso por RUT es un mecanismo de **demostración**, no de seguridad real.
- La herramienta trabaja con los CSV cargados; no se conecta en línea con los sistemas de la universidad.
- Si un curso no muestra candidatos, revise que existan notas en RA311 para ese ramo y que haya postulaciones activas.
