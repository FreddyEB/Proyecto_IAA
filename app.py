"""
MVP — Sistema de Recomendación de Ayudantes
Streamlit interface for the teaching assistant recommendation engine.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
import io

from data_loader import load_all
from scoring import rank_candidates, W_NOTA, W_EXP, W_PROM, W_CARGA, MIN_PASSING_GRADE
from justification import generate as generate_justification

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Recomendación de Ayudantes",
    page_icon="🎓",
    layout="wide",
)

# ── Load data (cached) ────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Cargando datos académicos…")
def get_data():
    return load_all()


@st.cache_data(show_spinner="Calculando ranking…")
def get_ranking(nrc: str, top_n: int):
    data = get_data()
    return rank_candidates(
        target_nrc=nrc,
        postulaciones=data["postulaciones"],
        notas=data["notas"],
        promedios=data["promedios"],
        carga=data["carga"],
        horarios=data["horarios"],
        ug307=pd.read_csv(next(Path(__file__).parent.parent.glob("*UG307*.csv"))),
        top_n=top_n,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuración")
    st.markdown("---")

    data = get_data()
    horarios = data["horarios"]
    postulaciones = data["postulaciones"]

    # Build NRC options: only NRCs that have at least one postulation
    nrcs_with_postulations = set(
        postulaciones[postulaciones["Estado"].isin(["Pendiente", "Aceptado"])]["NRC"].unique()
    )
    nrcs_in_horarios = set(horarios["NRC"].unique())
    valid_nrcs = sorted(nrcs_with_postulations & nrcs_in_horarios)

    if not valid_nrcs:
        st.error("No se encontraron NRCs con postulaciones activas.")
        st.stop()

    # Build display labels: NRC — TITULO (MATERIA CURSO)
    nrc_labels = {}
    for nrc in valid_nrcs:
        row = horarios[horarios["NRC"] == nrc].iloc[0]
        titulo = row.get("TITULO", "")
        materia = row.get("MATERIA", "")
        curso = row.get("CURSO", "")
        nrc_labels[nrc] = f"{nrc} — {titulo} ({materia} {curso})"

    selected_label = st.selectbox(
        "Seleccionar curso (NRC)",
        options=list(nrc_labels.values()),
        help="Solo se muestran NRCs con postulaciones activas.",
    )
    selected_nrc = [k for k, v in nrc_labels.items() if v == selected_label][0]

    top_n = st.slider("Número de candidatos a mostrar", min_value=1, max_value=10, value=5)

    st.markdown("---")
    st.markdown("**Pesos del modelo**")
    st.markdown(f"- Nota en el curso: **{W_NOTA*100:.0f}%**")
    st.markdown(f"- Experiencia previa: **{W_EXP*100:.0f}%**")
    st.markdown(f"- Promedio académico: **{W_PROM*100:.0f}%**")
    st.markdown(f"- Carga académica: **{W_CARGA*100:.0f}%**")
    st.markdown(f"- Nota mínima requerida: **{MIN_PASSING_GRADE}**")
    st.markdown("---")
    st.caption("Grupo 13 · IA Aplicada 2026-01")


# ── Main content ──────────────────────────────────────────────────────────────
st.title("🎓 Sistema de Recomendación de Ayudantes")
st.markdown(f"**Curso seleccionado:** `{selected_label}`")

# Course info
nrc_row = horarios[horarios["NRC"] == selected_nrc].iloc[0]
day_cols = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"]
schedule_parts = [
    f"{day}: {nrc_row[day]}"
    for day in day_cols
    if day in nrc_row and str(nrc_row[day]).strip() not in ("", "nan")
]

col1, col2, col3 = st.columns(3)
col1.metric("NRC", selected_nrc)
col2.metric("Asignatura", f"{nrc_row.get('MATERIA','')} {nrc_row.get('CURSO','')}")
col3.metric("Horario", " | ".join(schedule_parts) if schedule_parts else "Sin horario registrado")

st.markdown("---")

# ── Compute ranking ───────────────────────────────────────────────────────────
with st.spinner("Calculando recomendaciones…"):
    ranking = get_ranking(selected_nrc, top_n)

# ── KPI metrics ───────────────────────────────────────────────────────────────
st.subheader("📊 Indicadores del proceso (KPI)")

total_postulantes = len(
    postulaciones[
        (postulaciones["NRC"] == selected_nrc) &
        (postulaciones["Estado"].isin(["Pendiente", "Aceptado"]))
    ]
)

if not ranking.empty:
    elegibles = ranking[ranking["FILTRO_NOTA"] & ranking["FILTRO_HORARIO"]]
    tca = (len(elegibles) / total_postulantes * 100) if total_postulantes > 0 else 0
    tch = (
        len(ranking[~ranking["FILTRO_HORARIO"]]) / total_postulantes * 100
        if total_postulantes > 0 else 0
    )
else:
    elegibles = pd.DataFrame()
    tca = 0
    tch = 0

k1, k2, k3 = st.columns(3)
k1.metric(
    "TCA — Compatibilidad Académica",
    f"{tca:.1f}%",
    help="% de postulantes que aprueban el filtro de nota mínima",
)
k2.metric(
    "Postulantes activos",
    total_postulantes,
    help="Postulaciones en estado Pendiente o Aceptado para este NRC",
)
k3.metric(
    "TCH — Conflicto Horario",
    f"{tch:.1f}%",
    help="% de postulantes con conflicto horario detectado",
)

st.markdown("---")

# ── Ranking table ─────────────────────────────────────────────────────────────
st.subheader(f"🏆 Top {top_n} candidatos recomendados")

if ranking.empty:
    st.warning("No se encontraron candidatos para este NRC.")
    st.stop()

eligible_ranking = ranking[ranking["FILTRO_NOTA"] & ranking["FILTRO_HORARIO"]].copy()

if eligible_ranking.empty:
    st.error(
        f"Ningún postulante supera los filtros duros para este curso. "
        f"Verifica que existan notas en RA311 para {nrc_row.get('MATERIA','')} {nrc_row.get('CURSO','')}."
    )
    st.markdown("**Postulantes descartados:**")
    st.dataframe(
        ranking[["RUT", "NOTA_CURSO", "FILTRO_NOTA", "FILTRO_HORARIO"]],
        use_container_width=True,
    )
    st.stop()

course_name = nrc_row.get("TITULO", f"{nrc_row.get('MATERIA','')} {nrc_row.get('CURSO','')}")

# Add rank and justification
eligible_ranking = eligible_ranking.reset_index(drop=True)
eligible_ranking.index += 1
eligible_ranking["JUSTIFICACIÓN"] = eligible_ranking.apply(
    lambda r: generate_justification(r.to_dict(), course_name), axis=1
)

# Display table
display_cols = ["RUT", "NOTA_CURSO", "EXPERIENCIA", "PROMEDIO", "CARGA_ACTUAL", "SCORE"]
st.dataframe(
    eligible_ranking[display_cols].style.format({
        "NOTA_CURSO": "{:.1f}",
        "PROMEDIO": "{:.2f}",
        "SCORE": "{:.4f}",
        "EXPERIENCIA": "{:.0f}",
        "CARGA_ACTUAL": "{:.0f}",
    }).background_gradient(subset=["SCORE"], cmap="Greens"),
    use_container_width=True,
)

# ── Candidate cards ───────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 Detalle por candidato")

for rank, row in eligible_ranking.iterrows():
    with st.expander(f"#{rank} — RUT {row['RUT']}  |  Score: {row['SCORE']:.4f}"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nota en el curso", f"{row['NOTA_CURSO']:.1f}")
        c2.metric("Experiencia previa", f"{int(row['EXPERIENCIA'])} sem.")
        c3.metric("Promedio acumulado", f"{row['PROMEDIO']:.2f}")
        c4.metric("Carga actual", f"{int(row['CARGA_ACTUAL'])} ramos")

        st.markdown("**Justificación:**")
        st.info(row["JUSTIFICACIÓN"])

        # Score breakdown bar
        st.markdown("**Contribución al score:**")
        breakdown = pd.DataFrame({
            "Factor": ["Nota (35%)", "Experiencia (20%)", "Promedio (10%)", "Carga (5%)"],
            "Contribución": [
                round(0.35 * row["NOTA_CURSO"] / 7, 4),
                round(0.20 * (row["EXPERIENCIA"] / max(eligible_ranking["EXPERIENCIA"].max(), 1)), 4),
                round(0.10 * row["PROMEDIO"] / 7, 4),
                round(0.05 * (1 - row["CARGA_ACTUAL"] / max(eligible_ranking["CARGA_ACTUAL"].max() + 1, 1)), 4),
            ],
        })
        st.bar_chart(breakdown.set_index("Factor"))

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📥 Exportar resultados")

export_df = eligible_ranking[["RUT", "NOTA_CURSO", "EXPERIENCIA", "PROMEDIO", "CARGA_ACTUAL", "SCORE", "JUSTIFICACIÓN"]].copy()
export_df.insert(0, "RANKING", range(1, len(export_df) + 1))
export_df["NRC"] = selected_nrc
export_df["ASIGNATURA"] = course_name

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    export_df.to_excel(writer, index=False, sheet_name="Ranking")
    # Summary sheet
    summary = pd.DataFrame({
        "Métrica": ["NRC", "Asignatura", "Total postulantes", "Candidatos elegibles", "TCA (%)", "TCH (%)"],
        "Valor": [selected_nrc, course_name, total_postulantes, len(eligible_ranking), f"{tca:.1f}", f"{tch:.1f}"],
    })
    summary.to_excel(writer, index=False, sheet_name="Resumen KPI")

st.download_button(
    label="⬇️ Descargar Excel",
    data=buffer.getvalue(),
    file_name=f"ranking_ayudantes_NRC{selected_nrc}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
