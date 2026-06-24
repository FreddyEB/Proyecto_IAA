import pandas as pd
import streamlit as st

import data_store
from data_store import FILE_CODES, DATA_DIR, validate_columns, present_files, clear_all


def render():
    from app import get_data, get_model

    st.title("Cargar / actualizar datos (CSV)")
    st.caption("Sube los archivos del período. Se guardan en el servidor y persisten entre sesiones.")

    st.subheader("Estado actual")
    present = present_files()
    st.table(pd.DataFrame(
        [{"Archivo": k, "Código": FILE_CODES[k], "Presente": "✅" if v else "❌"}
         for k, v in present.items()]))

    st.subheader("Limpiar datos")
    st.write("Borra los archivos actuales antes de subir un set nuevo para evitar mezclar períodos.")
    if st.button("🗑️ Limpiar todos los datos cargados"):
        deleted = clear_all()
        get_data.clear()
        get_model.clear()
        st.success(f"Eliminados {len(deleted)} archivos. Sube los nuevos a continuación.")
        st.rerun()

    st.subheader("Subir archivos")
    key_to_label = {
        "postulaciones": "Postulaciones (reportePostulaciones)",
        "notas": "Notas / malla (RA311)",
        "promedios": "Promedios (UG305)",
        "ramos_inscritos": "Ramos inscritos (UG307)",
        "horarios": "Horarios y NRC (UG201)",
    }
    skiprows = {"horarios": 4}

    for key, label in key_to_label.items():
        up = st.file_uploader(label, type="csv", key=f"up_{key}")
        if up is not None:
            df = pd.read_csv(up, skiprows=skiprows.get(key, 0))
            df.columns = df.columns.str.strip()
            missing = validate_columns(key, df.columns)
            if missing:
                st.error(f"{label}: faltan columnas {missing}. No se guardó.")
            else:
                dest = DATA_DIR / up.name
                up.seek(0)
                dest.write_bytes(up.getvalue())
                get_data.clear()
                get_model.clear()
                st.success(f"{label}: guardado como {up.name} y datos recargados.")
