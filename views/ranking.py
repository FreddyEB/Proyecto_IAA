import io
import pandas as pd
import streamlit as st

from scoring import rank_candidates, DEFAULT_WEIGHTS, MIN_PASSING_GRADE
from justification import generate as generate_justification


def render():
    from app import get_data, get_model
    data = get_data()
    model, metrics = get_model()
    horarios = data["horarios"]
    postulaciones = data["postulaciones"]
    prof = st.session_state["profesor"]

    st.title("Mis cursos / Ranking de ayudantes")

    # Solo NRCs del profesor que además tienen postulaciones activas
    prof_nrcs = set(prof["nrcs"])
    activos = set(postulaciones[postulaciones["Estado"].isin(["Pendiente", "Aceptado"])]["NRC"].unique())
    valid_nrcs = sorted(prof_nrcs & activos & set(horarios["NRC"].unique()))
    if not valid_nrcs:
        st.warning("No tienes cursos con postulaciones activas en los datos cargados.")
        return

    labels = {}
    for nrc in valid_nrcs:
        row = horarios[horarios["NRC"] == nrc].iloc[0]
        labels[nrc] = f"{nrc} — {row.get('TITULO','')} ({row.get('MATERIA','')} {row.get('CURSO','')})"
    selected_label = st.selectbox("Curso (NRC)", list(labels.values()))
    selected_nrc = [k for k, v in labels.items() if v == selected_label][0]

    st.sidebar.markdown("### Importancia de variables")
    w_nota = st.sidebar.slider("Nota en el curso", 0.0, 1.0, DEFAULT_WEIGHTS["nota"], 0.05)
    w_prom = st.sidebar.slider("Promedio acumulado", 0.0, 1.0, DEFAULT_WEIGHTS["promedio"], 0.05)
    w_exp = st.sidebar.slider("Experiencia previa", 0.0, 1.0, DEFAULT_WEIGHTS["experiencia"], 0.05)
    w_ia = st.sidebar.slider("Señal del modelo (IA)", 0.0, 1.0, DEFAULT_WEIGHTS["ia"], 0.05)
    weights = {"nota": w_nota, "promedio": w_prom, "experiencia": w_exp, "ia": w_ia}
    top_n = st.sidebar.slider("Candidatos a mostrar", 1, 20, 5)

    ranking = rank_candidates(
        selected_nrc, postulaciones, data["notas"], data["promedios"],
        horarios, data["ramos_inscritos"], model, weights=weights, top_n=top_n)

    total_post = len(postulaciones[(postulaciones["NRC"] == selected_nrc) &
                                   (postulaciones["Estado"].isin(["Pendiente", "Aceptado"]))])

    if ranking.empty:
        st.warning("No se encontraron candidatos para este NRC.")
        return
    eligible = ranking[ranking["FILTRO_NOTA"] & ranking["FILTRO_HORARIO"]].copy()
    if eligible.empty:
        st.error("Ningún postulante supera los filtros. Verifica notas en RA311 para este curso.")
        st.dataframe(ranking[["RUT", "NOTA_CURSO", "FILTRO_NOTA", "FILTRO_HORARIO"]])
        return

    # KPIs
    tca = 100.0
    score_kpi = float(eligible["SCORE"].mean())
    conflictos = int((~ranking["FILTRO_HORARIO"]).sum())
    k1, k2, k3 = st.columns(3)
    k1.metric("KPI 1 · TCA", f"{tca:.0f}%", help=f"Candidatos recomendados con nota ≥ {MIN_PASSING_GRADE}")
    k2.metric("KPI 2 · Score recomendación", f"{score_kpi:.2f}", help="Promedio del score de los recomendados")
    k3.metric("KPI 3 · Descartes por horario", conflictos,
              help="Candidatos de tipo con asistencia obligatoria descartados por choque de horario")

    course_name = horarios[horarios["NRC"] == selected_nrc].iloc[0].get("TITULO", "")
    eligible = eligible.reset_index(drop=True)
    eligible.index += 1
    eligible["JUSTIFICACIÓN"] = eligible.apply(
        lambda r: generate_justification(r.to_dict(), weights, course_name), axis=1)

    display_cols = ["RUT", "TIPO_AYUDANTE", "NOTA_CURSO", "EXPERIENCIA", "PROMEDIO", "SCORE"]
    st.dataframe(eligible[display_cols].style.format(
        {"NOTA_CURSO": "{:.1f}", "PROMEDIO": "{:.2f}", "SCORE": "{:.4f}",
         "EXPERIENCIA": "{:.0f}"}).background_gradient(subset=["SCORE"], cmap="Greens"),
        use_container_width=True)

    st.subheader("Detalle por candidato")
    for rank, row in eligible.iterrows():
        with st.expander(f"#{rank} — RUT {row['RUT']} | {row['TIPO_AYUDANTE']} | Score: {row['SCORE']:.4f}"):
            st.info(row["JUSTIFICACIÓN"])

    # Export
    export_df = eligible[["RUT", "TIPO_AYUDANTE", "NOTA_CURSO", "EXPERIENCIA",
                          "PROMEDIO", "SCORE", "JUSTIFICACIÓN"]].copy()
    export_df.insert(0, "RANKING", range(1, len(export_df) + 1))
    export_df["NRC"] = selected_nrc
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Ranking")
        pd.DataFrame({"Métrica": ["NRC", "TCA (%)", "Score recomendación", "Descartes horario"],
                      "Valor": [selected_nrc, tca, round(score_kpi, 4), conflictos]}
                     ).to_excel(writer, index=False, sheet_name="KPIs")
    st.download_button("Descargar Excel", buffer.getvalue(),
                       file_name=f"ranking_NRC{selected_nrc}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
