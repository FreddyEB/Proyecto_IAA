# Manual de Instalación y Despliegue

**Sistema de Recomendación de Ayudantes — Grupo 13 · IA Aplicada · 2026**

Este documento permite instalar, ejecutar y mantener la solución de forma reproducible por terceros.

---

## 1. Requisitos de hardware y software

**Hardware (mínimo):** cualquier computador con 4 GB de RAM y ~500 MB de disco libre. El entrenamiento del modelo es liviano (segundos).

**Software:**
- **Sistema operativo:** macOS, Linux o Windows.
- **Python 3.11 o 3.12.** ⚠️ **No usar Python 3.14** (rompe Streamlit con `TypeError: Metaclasses with custom tp_new are not supported`). Verifique con `python3 --version`.
- **pip** (incluido con Python).
- Navegador web moderno (Chrome, Edge, Firefox, Safari).

## 2. Dependencias

Definidas en `requirements.txt`:

```
streamlit==1.39.0      # interfaz web
pandas==2.2.2          # manejo de datos
scikit-learn==1.5.0    # modelo Random Forest
openpyxl==3.1.2        # lectura de Excel
xlsxwriter==3.2.0      # exportación a Excel
pytest==8.2.0          # pruebas automáticas
```

> `numpy` y `scipy` se instalan como dependencias transitivas. Con Python 3.11/3.12 y las versiones anteriores se resuelven solas. Si comparte el entorno con otros proyectos (p. ej. que usen `langchain`), ver *Problemas frecuentes*.

## 3. Procedimiento de instalación

### Opción A — con entorno virtual (recomendado)

Aísla las dependencias para no afectar otros proyectos.

```bash
# 1. Ubicarse en la carpeta del proyecto
cd ayudantes_mvp

# 2. Crear el entorno virtual (una sola vez)
python3.12 -m venv .venv

# 3. Activarlo (cada vez que se abra una terminal nueva)
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows (PowerShell)

# 4. Instalar dependencias (una sola vez)
pip install -r requirements.txt
```

Verá `(.venv)` al inicio del prompt cuando esté activo. Para salir: `deactivate`.

### Opción B — sin entorno virtual

```bash
cd ayudantes_mvp
pip install -r requirements.txt
```

## 4. Configuración de variables de entorno

La aplicación **no requiere variables de entorno** para funcionar: no usa claves de API ni servicios externos. Toda la configuración relevante está en el código:

- **Umbral de aprobación:** `MIN_PASSING_GRADE = 4.75` en `scoring.py`.
- **Pesos por defecto del score:** `DEFAULT_WEIGHTS` en `scoring.py`.
- **Carpeta de datos del app:** `DATA_DIR = .../app_data` en `data_store.py`.

Opcionalmente, el puerto y modo de Streamlit se pueden ajustar al ejecutar (ver sección 5) o en un archivo `.streamlit/config.toml`.

## 5. Ejecución del sistema

Con el entorno preparado:

```bash
streamlit run app.py
```

La aplicación queda disponible en `http://localhost:8501` y se abre sola en el navegador. Para detenerla: `Ctrl + C` en la terminal.

Ejecución en otro puerto o sin abrir navegador (útil en servidores):

```bash
streamlit run app.py --server.port 8080 --server.headless true
```

**Primer arranque:** si la carpeta `app_data/` está vacía, la app entra en **modo carga** y pide subir los 5 CSV antes de continuar (ver *Manual de Usuario*).

**Pruebas automáticas** (opcional, para verificar la instalación):

```bash
python -m pytest -q      # debe reportar todos los tests en verde
```

**Reporte de KPIs reproducible** (genera evidencia con los datos cargados):

```bash
python kpi_report.py     # imprime y guarda docs/kpi_evidencia.md
```

## 6. Estructura general del proyecto

```
ayudantes_mvp/
├── app.py              # Entrada Streamlit multipágina (login + navegación)
├── services.py         # Carga de datos y entrenamiento del modelo (cacheado)
├── views/
│   ├── login.py        # Ingreso por RUT
│   ├── ranking.py      # Ranking por curso + sliders + KPIs + export
│   ├── validation.py   # Validación / KPIs del modelo
│   └── upload.py       # Carga persistente de CSV + limpiar (con respaldo)
├── auth.py             # Autenticación por RUT (contra UG201)
├── data_store.py       # Almacén de datos (app_data/): rutas, validación, persistencia
├── data_loader.py      # Carga y limpieza de los CSV
├── model.py            # Modelo Random Forest (señal P(Aceptado))
├── scoring.py          # Filtros duros + score híbrido con pesos ajustables
├── justification.py    # Texto explicativo por candidato
├── analysis.py         # Validación retrospectiva (TCA real, acierto del ranking)
├── kpi_report.py       # Script de evidencia de KPIs
├── tests/              # Suite pytest
├── app_data/           # Datos del período (generado; ignorado por git)
├── docs/               # Documentación, specs, planes y entrega final
├── requirements.txt
└── README.md
```

## 7. Consideraciones de mantenimiento

- **Actualizar datos cada período:** desde la página *Cargar datos* (no requiere tocar código). Los archivos viejos quedan en `app_data/_backup/<fecha>/`.
- **Reentrenamiento:** el modelo se entrena automáticamente al cargar/limpiar datos; no hay un paso manual.
- **Cambiar criterios del modelo:** ajustar `MIN_PASSING_GRADE` o `DEFAULT_WEIGHTS` en `scoring.py`.
- **Datos sensibles:** `app_data/` contiene datos académicos reales y está **excluido de git** (`.gitignore`). No subir esa carpeta a repositorios públicos.
- **Tras cambios en el código:** correr `python -m pytest -q` antes de desplegar.
- **Dependencias:** mantener las versiones de `requirements.txt`; subir Python a 3.14 rompe Streamlit.

## 8. Problemas frecuentes y soluciones

| Síntoma | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'sklearn'` (u otra dependencia) | Dependencias no instaladas en el entorno desde el que se ejecuta | Activar el entorno correcto y `pip install -r requirements.txt` |
| `TypeError: Metaclasses with custom tp_new are not supported` | Python 3.14 | Usar Python 3.11 o 3.12 |
| `background_gradient requires matplotlib` | (resuelto en la versión actual) versión antigua que usaba matplotlib | Actualizar a la versión actual (usa barras CSS, sin matplotlib) |
| Conflicto `numpy<2` con `langchain` u otros, o `scipy requires numpy>=2` | Entorno compartido con otros proyectos | Usar un entorno virtual dedicado (Opción A). Si debe compartirse: `pip install "numpy<2" "scipy<1.14"` (compatibles con scikit-learn 1.5) |
| La app muestra "No hay datos cargados" | `app_data/` vacío o set incompleto | Subir los **5** CSV en *Cargar datos* |
| Un curso no muestra candidatos | Sin notas en RA311 para ese ramo, o sin postulaciones activas | Verificar los datos de entrada de ese curso |
| El RUT no es aceptado al ingresar | El RUT no figura como profesor en UG201 del período cargado | Confirmar que UG201 corresponde al período y contiene a ese profesor |
| Streamlit no abre el navegador | Ejecución headless o entorno remoto | Abrir manualmente `http://localhost:8501` (o el puerto configurado) |
