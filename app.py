import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from services import get_data, get_model
from data_store import present_files

if not st.session_state.get("_page_config_set"):
    st.set_page_config(page_title="Recomendación de Ayudantes", page_icon="🎓", layout="wide")
    st.session_state["_page_config_set"] = True


# Solo se sale del modo carga cuando están los 5 archivos y cargan sin error.
# Con un set incompleto NO se avanza al login (evita usar datos parciales/mezclados).
st.session_state["_data"] = None
_data_ok = False
if all(present_files().values()):
    try:
        st.session_state["_data"] = get_data()
        _data_ok = True
    except Exception as e:  # archivo presente pero ilegible/corrupto
        st.session_state["_data"] = None
        st.session_state["_data_error"] = str(e)

import views.login as login_view
import views.upload as upload_view

if not _data_ok:
    st.warning("No hay datos cargados. Sube los archivos CSV para comenzar.")
    pg = st.navigation([st.Page(upload_view.render, title="Cargar datos", icon="📂", url_path="upload")])
elif "profesor" not in st.session_state:
    pg = st.navigation([st.Page(login_view.render, title="Ingreso", icon="🔑", url_path="login")])
else:
    import views.ranking as ranking_view
    import views.validation as validation_view
    with st.sidebar:
        st.markdown(f"**Profesor:** {st.session_state['profesor']['nombre']}")
        if st.button("Cerrar sesión"):
            del st.session_state["profesor"]
            st.rerun()
    pg = st.navigation([
        st.Page(ranking_view.render, title="Mis cursos / Ranking", icon="📊", url_path="ranking"),
        st.Page(validation_view.render, title="Validación / KPIs", icon="📈", url_path="validation"),
        st.Page(upload_view.render, title="Cargar datos", icon="📂", url_path="upload"),
    ])

pg.run()
