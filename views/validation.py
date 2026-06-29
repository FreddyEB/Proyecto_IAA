import pandas as pd
import streamlit as st

from services import get_data, get_model
from model import FEATURE_LABELS
from scoring import DEFAULT_WEIGHTS
from analysis import compute_tca_real, compute_ranking_accuracy


@st.cache_data(show_spinner="Calculando validación retrospectiva…")
def _retrospective():
    data = get_data()
    model, _ = get_model()
    tca = compute_tca_real(data["postulaciones"], data["notas"])
    acc = compute_ranking_accuracy(
        data["postulaciones"], data["notas"], data["promedios"],
        data["horarios"], data["ramos_inscritos"], model, weights=DEFAULT_WEIGHTS)
    return tca, acc


def render():
    model, metrics = get_model()

    st.title("Validación / KPIs del modelo")
    st.caption("Evidencia sobre los datos históricos cargados. "
               "Reproducible fuera de la app con `python kpi_report.py`.")

    # ── Modelo (señal de IA) ──────────────────────────────────────────────
    st.subheader("Modelo (señal de IA · Random Forest)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Muestras de entrenamiento", metrics["n_samples"],
              help=f"Aceptados {metrics['n_accepted']} / Rechazados {metrics['n_rejected']}")
    c2.metric("CV Accuracy", f"{metrics['cv_accuracy_mean']:.1%}")
    c3.metric("CV ROC-AUC", f"{metrics['cv_roc_auc_mean']:.3f}")
    fi = metrics["feature_importances"]
    fi_df = pd.DataFrame({
        "Variable": [FEATURE_LABELS[k] for k in fi],
        "Importancia": list(fi.values()),
    }).sort_values("Importancia")
    st.bar_chart(fi_df.set_index("Variable"))

    tca, acc = _retrospective()

    # ── KPI 1 — TCA real ──────────────────────────────────────────────────
    st.subheader("KPI 1 — TCA real (compatibilidad académica histórica)")
    t1, t2, t3 = st.columns(3)
    t1.metric("TCA real", f"{tca['tca_real_pct']}%",
              delta=f"{tca['tca_real_pct'] - tca['tca_baseline_pct']:+.1f} pts vs línea base")
    t2.metric("Línea base estimada", f"{tca['tca_baseline_pct']}%")
    t3.metric("Objetivo MVP", f"{tca['tca_objetivo_pct']}%")
    st.caption(f"Calculado sobre {tca['con_nota_en_ra311']} asignaciones aceptadas con nota "
               f"registrada en RA311 (de {tca['total_aceptados']} totales).")

    # ── KPI 2 — Acierto del ranking ───────────────────────────────────────
    st.subheader("KPI 2 — Acierto del ranking vs. decisiones del coordinador")
    a1, a2, a3 = st.columns(3)
    a1.metric("NRC evaluados", acc["nrcs_evaluados"])
    a2.metric("Top-1 correcto", f"{acc['top1_rate_pct']}%",
              help="% de NRC donde el #1 del modelo coincide con el aceptado real")
    a3.metric("Aceptado en Top-3", f"{acc['top3_rate_pct']}%",
              help="% de NRC donde el aceptado aparece entre los 3 primeros")
    st.caption("Evidencia de que el ranking reproduce las decisiones reales (no es aleatorio).")
    with st.expander("Ver detalle por NRC"):
        st.dataframe(acc["details"], use_container_width=True)
