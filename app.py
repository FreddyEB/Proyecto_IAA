"""
MVP — Sistema de Recomendación de Ayudantes
Streamlit interface powered by a Random Forest classifier.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
import io

from data_loader import load_all, _find_csv
from model import build_training_data, train, FEATURE_LABELS
from scoring import rank_candidates, MIN_PASSING_GRADE
from justification import generate as generate_justification
from analysis import compute_tca_real, compute_ranking_accuracy

st.set_page_config(
    page_title="Recomendación de Ayudantes",
    page_icon="🎓",
    layout="wide",
)

# ── Load data & train model (cached) ─────────────────────────────────────────
@st.cache_data(show_spinner="Cargando datos académicos…")
def get_data():
    return load_all()


@st.cache_resource(show_spinner="Entrenando modelo Random Forest…")
def get_model():
    data = get_data()
    training_data = build_training_data(
        data["postulaciones"], data["notas"], data["promedios"], data["carga"]
    )
    return train(training_data)


@st.cache_data(show_spinner="Calculando ranking…")
def get_ranking(nrc: str, top_n: int):
    data = get_data()
    model, _ = get_model()
    ug307 = pd.read_csv(_find_csv("UG307"))
    return rank_candidates(
        target_nrc=nrc,
        postulaciones=data["postulaciones"],
        notas=data["notas"],
        promedios=data["promedios"],
        carga=data["carga"],
        horarios=data["horarios"],
        ug307=ug307,
        model=model,
        top_n=top_n,
    )


@st.cache_data(show_spinner="Calculando análisis retrospectivo…")
def get_retrospective():
    data = get_data()
    model, _ = get_model()
    ug307 = pd.read_csv(_find_csv("UG307"))
    tca = compute_tca_real(data["postulaciones"], data["notas"])
    ranking_acc = compute_ranking_accuracy(
        data["postulaciones"], data["notas"], data["promedios"],
        data["carga"], data["horarios"], ug307, model,
    )
    return tca, ranking_acc


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Configuración")
    st.markdown("---")

    data = get_data()
    model, metrics = get_model()
    horarios = data["horarios"]
    postulaciones = data["postulaciones"]

    # NRC selector
    nrcs_with_postulations = set(
        postulaciones[postulaciones["Estado"].isin(["Pendiente", "Aceptado"])]["NRC"].unique()
    )
    valid_nrcs = sorted(nrcs_with_postulations & set(horarios["NRC"].unique()))

    if not valid_nrcs:
        st.error("No se encontraron NRCs con postulaciones activas.")
        st.stop()

    nrc_labels = {}
    for nrc in valid_nrcs:
        row = horarios[horarios["NRC"] == nrc].iloc[0]
        nrc_labels[nrc] = f"{nrc} — {row.get('TITULO','')} ({row.get('MATERIA','')} {row.get('CURSO','')})"

    selected_label = st.selectbox("Seleccionar curso (NRC)", list(nrc_labels.values()))
    selected_nrc = [k for k, v in nrc_labels.items() if v == selected_label][0]
    top_n = st.slider("Candidatos a mostrar", 1, 10, 5)

    st.markdown("---")
    st.markdown("### Modelo Random Forest")
    st.markdown(f"- **Muestras de entrenamiento:** {metrics['n_samples']}")
    st.markdown(f"- **Aceptados / Rechazados:** {metrics['n_accepted']} / {metrics['n_rejected']}")
    st.markdown(f"- **CV Accuracy:** {metrics['cv_accuracy_mean']:.1%} ± {metrics['cv_accuracy_std']:.1%}")
    st.markdown(f"- **CV ROC-AUC:** {metrics['cv_roc_auc_mean']:.3f} ± {metrics['cv_roc_auc_std']:.3f}")
    st.markdown(f"- **Nota mínima requerida:** {MIN_PASSING_GRADE}")
    st.markdown("---")
    st.caption("Grupo 13 · IA Aplicada 2026-01")


# ── Main content ──────────────────────────────────────────────────────────────
st.title("Sistema de Recomendación de Ayudantes")
st.markdown(f"**Curso seleccionado:** `{selected_label}`")

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

# ── Feature importances ───────────────────────────────────────────────────────
st.subheader("Importancia de variables (Random Forest)")
fi = metrics["feature_importances"]
fi_df = pd.DataFrame({
    "Variable": [FEATURE_LABELS[k] for k in fi],
    "Importancia": list(fi.values()),
}).sort_values("Importancia", ascending=True)
st.bar_chart(fi_df.set_index("Variable"))

st.markdown("---")

# ── KPI metrics ───────────────────────────────────────────────────────────────
st.subheader("Indicadores del proceso (KPI)")

with st.spinner("Calculando recomendaciones…"):
    ranking = get_ranking(selected_nrc, top_n)

total_postulantes = len(
    postulaciones[
        (postulaciones["NRC"] == selected_nrc) &
        (postulaciones["Estado"].isin(["Pendiente", "Aceptado"]))
    ]
)

if not ranking.empty:
    eligible = ranking[ranking["FILTRO_NOTA"] & ranking["FILTRO_HORARIO"]]
    tca = len(eligible) / total_postulantes * 100 if total_postulantes > 0 else 0
    tch = len(ranking[~ranking["FILTRO_HORARIO"]]) / total_postulantes * 100 if total_postulantes > 0 else 0
else:
    eligible = pd.DataFrame()
    tca = tch = 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("TCA — Compatibilidad Académica", f"{tca:.1f}%",
          help="% de postulantes que aprueban el filtro de nota mínima")
k2.metric("TCH — Conflicto Horario", f"{tch:.1f}%",
          help="% de postulantes con conflicto horario detectado")
k3.metric("Postulantes activos", total_postulantes)
k4.metric("Candidatos elegibles", len(eligible))

st.markdown("---")

# ── Ranking table ─────────────────────────────────────────────────────────────
st.subheader(f"Top {top_n} candidatos recomendados")

if ranking.empty:
    st.warning("No se encontraron candidatos para este NRC.")
    st.stop()

eligible_ranking = ranking[ranking["FILTRO_NOTA"] & ranking["FILTRO_HORARIO"]].copy()

if eligible_ranking.empty:
    st.error(
        f"Ningún postulante supera los filtros duros. "
        f"Verifica que existan notas en RA311 para {nrc_row.get('MATERIA','')} {nrc_row.get('CURSO','')}."
    )
    st.dataframe(ranking[["RUT", "NOTA_CURSO", "FILTRO_NOTA", "FILTRO_HORARIO"]], use_container_width=True)
    st.stop()

course_name = nrc_row.get("TITULO", f"{nrc_row.get('MATERIA','')} {nrc_row.get('CURSO','')}")
eligible_ranking = eligible_ranking.reset_index(drop=True)
eligible_ranking.index += 1
eligible_ranking["JUSTIFICACIÓN"] = eligible_ranking.apply(
    lambda r: generate_justification(r.to_dict(), course_name), axis=1
)

display_cols = ["RUT", "NOTA_CURSO", "EXPERIENCIA", "PROMEDIO", "CARGA_ACTUAL", "SCORE"]
st.dataframe(
    eligible_ranking[display_cols].style.format({
        "NOTA_CURSO": "{:.1f}", "PROMEDIO": "{:.2f}",
        "SCORE": "{:.4f}", "EXPERIENCIA": "{:.0f}", "CARGA_ACTUAL": "{:.0f}",
    }).background_gradient(subset=["SCORE"], cmap="Greens"),
    use_container_width=True,
)

# ── Candidate cards ───────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Detalle por candidato")

for rank, row in eligible_ranking.iterrows():
    with st.expander(f"#{rank} — RUT {row['RUT']}  |  Score: {row['SCORE']:.4f}  (P(Aceptado))"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nota en el curso", f"{row['NOTA_CURSO']:.1f}")
        c2.metric("Experiencia previa", f"{int(row['EXPERIENCIA'])} sem.")
        c3.metric("Promedio acumulado", f"{row['PROMEDIO']:.2f}")
        c4.metric("Carga actual", f"{int(row['CARGA_ACTUAL'])} ramos")
        st.markdown("**Justificación:**")
        st.info(row["JUSTIFICACIÓN"])

# ── Retrospective analysis ────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📈 Análisis retrospectivo (validación del modelo)")

tca_data, rank_acc = get_retrospective()

st.markdown("#### TCA — Compatibilidad Académica histórica")
r1, r2, r3 = st.columns(3)
r1.metric("TCA real (histórico)", f"{tca_data['tca_real_pct']}%",
          delta=f"{tca_data['tca_real_pct'] - tca_data['tca_baseline_pct']:+.1f}% vs línea base")
r2.metric("Línea base estimada", f"{tca_data['tca_baseline_pct']}%")
r3.metric("Objetivo MVP", f"{tca_data['tca_objetivo_pct']}%")

st.caption(
    f"Calculado sobre {tca_data['total_aceptados']} asignaciones históricas con estado Aceptado. "
    f"{tca_data['con_nota_en_ra311']} de ellas tienen nota registrada en RA311."
)

st.markdown("#### Tasa de aceptación del ranking")
a1, a2, a3 = st.columns(3)
a1.metric("NRCs evaluados", rank_acc["nrcs_evaluados"])
a2.metric("Top-1 correcto", f"{rank_acc['top1_rate_pct']}%",
          help="% de NRCs donde el candidato #1 del modelo coincide con el Aceptado real")
a3.metric("Aceptado en Top-3", f"{rank_acc['top3_rate_pct']}%",
          help="% de NRCs donde el candidato aceptado aparece entre los 3 primeros del ranking")

with st.expander("Ver detalle por NRC"):
    st.dataframe(rank_acc["details"], use_container_width=True)

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Exportar resultados")

export_df = eligible_ranking[
    ["RUT", "NOTA_CURSO", "EXPERIENCIA", "PROMEDIO", "CARGA_ACTUAL", "SCORE", "JUSTIFICACIÓN"]
].copy()
export_df.insert(0, "RANKING", range(1, len(export_df) + 1))
export_df["NRC"] = selected_nrc
export_df["ASIGNATURA"] = course_name

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    export_df.to_excel(writer, index=False, sheet_name="Ranking")
    summary = pd.DataFrame({
        "Métrica": ["NRC", "Asignatura", "Total postulantes", "Candidatos elegibles",
                    "TCA (%)", "TCH (%)", "CV Accuracy", "CV ROC-AUC"],
        "Valor": [selected_nrc, course_name, total_postulantes, len(eligible_ranking),
                  f"{tca:.1f}", f"{tch:.1f}",
                  f"{metrics['cv_accuracy_mean']:.1%}", f"{metrics['cv_roc_auc_mean']:.3f}"],
    })
    summary.to_excel(writer, index=False, sheet_name="Resumen KPI")
    fi_export = pd.DataFrame({
        "Variable": [FEATURE_LABELS[k] for k in fi],
        "Importancia": list(fi.values()),
    }).sort_values("Importancia", ascending=False)
    fi_export.to_excel(writer, index=False, sheet_name="Feature Importances")
    retro_summary = pd.DataFrame({
        "Métrica": ["TCA real (%)", "TCA línea base (%)", "TCA objetivo (%)",
                    "Top-1 match (%)", "Top-3 match (%)", "NRCs evaluados"],
        "Valor": [tca_data["tca_real_pct"], tca_data["tca_baseline_pct"], tca_data["tca_objetivo_pct"],
                  rank_acc["top1_rate_pct"], rank_acc["top3_rate_pct"], rank_acc["nrcs_evaluados"]],
    })
    retro_summary.to_excel(writer, index=False, sheet_name="Análisis Retrospectivo")
    rank_acc["details"].to_excel(writer, index=False, sheet_name="Detalle por NRC")

st.download_button(
    label="Descargar Excel",
    data=buffer.getvalue(),
    file_name=f"ranking_ayudantes_NRC{selected_nrc}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
