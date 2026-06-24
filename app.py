import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from data_loader import load_all
from model import build_training_data, train

st.set_page_config(page_title="Recomendación de Ayudantes", page_icon="🎓", layout="wide")


@st.cache_data(show_spinner="Cargando datos académicos…")
def get_data():
    return load_all()


@st.cache_resource(show_spinner="Entrenando modelo Random Forest…")
def get_model():
    data = get_data()
    td = build_training_data(data["postulaciones"], data["notas"], data["promedios"])
    return train(td)


# Datos siempre disponibles en sesión para las vistas
st.session_state["_data"] = get_data()

import views.login as login_view

if "profesor" not in st.session_state:
    pg = st.navigation([st.Page(login_view.render, title="Ingreso", icon="🔑")])
else:
    import views.ranking as ranking_view
    import views.upload as upload_view
    with st.sidebar:
        st.markdown(f"**Profesor:** {st.session_state['profesor']['nombre']}")
        if st.button("Cerrar sesión"):
            del st.session_state["profesor"]
            st.rerun()
    pg = st.navigation([
        st.Page(ranking_view.render, title="Mis cursos / Ranking", icon="📊"),
        st.Page(upload_view.render, title="Cargar datos", icon="📂"),
    ])

pg.run()
