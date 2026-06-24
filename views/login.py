import streamlit as st
from auth import authenticate


def render():
    st.title("Ingreso de profesores")
    st.caption("Acceso de demostración. La clave es su RUT.")
    horarios = st.session_state["_data"]["horarios"]

    with st.form("login"):
        nombre = st.text_input("Nombre")
        apellido = st.text_input("Apellido")
        rut = st.text_input("RUT (clave)", type="password")
        ok = st.form_submit_button("Ingresar")

    if ok:
        prof = authenticate(rut, horarios)
        if prof is None:
            st.error("RUT no encontrado como profesor en los datos del período.")
        else:
            prof["nombre_ingresado"] = f"{nombre} {apellido}".strip()
            st.session_state["profesor"] = prof
            st.rerun()
