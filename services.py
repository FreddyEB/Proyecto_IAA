"""Carga de datos y entrenamiento del modelo, cacheados (compartido por app y vistas)."""
import streamlit as st
from data_loader import load_all
from model import build_training_data, train


@st.cache_data(show_spinner="Cargando datos académicos…")
def get_data():
    return load_all()


@st.cache_resource(show_spinner="Entrenando modelo Random Forest…")
def get_model():
    data = get_data()
    td = build_training_data(data["postulaciones"], data["notas"], data["promedios"])
    return train(td)
