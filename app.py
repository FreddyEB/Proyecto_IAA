import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from services import get_data, get_model

if not st.session_state.get("_page_config_set"):
    st.set_page_config(page_title="Recomendación de Ayudantes", page_icon="🎓", layout="wide")
    st.session_state["_page_config_set"] = True


# Datos disponibles en sesión para las vistas. Si faltan archivos (p. ej. tras
# limpiar para recargar), no se crashea: se entra en modo bootstrap de carga.
try:
    st.session_state["_data"] = get_data()
    _data_ok = True
except FileNotFoundError:
    st.session_state["_data"] = None
    _data_ok = False

import views.login as login_view
import views.upload as upload_view

if not _data_ok:
    st.warning("No hay datos cargados. Sube los archivos CSV para comenzar.")
    pg = st.navigation([st.Page(upload_view.render, title="Cargar datos", icon="📂", url_path="upload")])
elif "profesor" not in st.session_state:
    pg = st.navigation([st.Page(login_view.render, title="Ingreso", icon="🔑", url_path="login")])
else:
    import views.ranking as ranking_view
    with st.sidebar:
        st.markdown(f"**Profesor:** {st.session_state['profesor']['nombre']}")
        if st.button("Cerrar sesión"):
            del st.session_state["profesor"]
            st.rerun()
    pg = st.navigation([
        st.Page(ranking_view.render, title="Mis cursos / Ranking", icon="📊", url_path="ranking"),
        st.Page(upload_view.render, title="Cargar datos", icon="📂", url_path="upload"),
    ])

pg.run()
