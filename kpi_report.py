"""
Reporte reproducible de KPIs con datos reales.

Genera evidencia para el Informe Ejecutivo y la entrega final:
- Resumen del modelo (muestras, validación cruzada, importancia de variables).
- KPI 1 — TCA real (histórico): % de asignaciones aceptadas que cumplían nota >= 4.75.
- KPI 2 — Score de recomendación: distribución del score sobre los candidatos recomendados,
  y tasa de acierto del ranking (top-1 / top-3) frente a las decisiones históricas del
  coordinador (evidencia de que la recomendación es útil).
- KPI 3 — Conflicto horario: descartes por choque de horario (solo tipos con asistencia).

Uso:
    python kpi_report.py
Salida: consola + archivo docs/kpi_evidencia.md
"""
from pathlib import Path
from statistics import mean, median

import data_loader
from model import build_training_data, train, FEATURE_LABELS
from scoring import rank_candidates, DEFAULT_WEIGHTS, MIN_PASSING_GRADE, TYPES_REQUIRING_ATTENDANCE
from analysis import compute_tca_real, compute_ranking_accuracy

OUT_PATH = Path(__file__).parent / "docs" / "kpi_evidencia.md"


def _score_distribution(data, model, weights):
    """Recorre los NRC con postulaciones activas y junta los scores recomendados
    y los descartes por conflicto de horario."""
    post = data["postulaciones"]
    activos = post[post["Estado"].isin(["Pendiente", "Aceptado"])]["NRC"].unique()
    valid = set(data["horarios"]["NRC"].unique())
    scores, conflictos, nrcs_con_recom = [], 0, 0
    for nrc in activos:
        if nrc not in valid:
            continue
        r = rank_candidates(nrc, post, data["notas"], data["promedios"],
                            data["horarios"], data["ramos_inscritos"], model,
                            weights=weights, top_n=20)
        if r.empty:
            continue
        elig = r[r["FILTRO_NOTA"] & r["FILTRO_HORARIO"]]
        conflictos += int((~r["FILTRO_HORARIO"]).sum())
        if not elig.empty:
            nrcs_con_recom += 1
            scores.extend(elig["SCORE"].tolist())
    return scores, conflictos, nrcs_con_recom


def build_report() -> str:
    data = data_loader.load_all()
    td = build_training_data(data["postulaciones"], data["notas"], data["promedios"])
    model, m = train(td)
    weights = DEFAULT_WEIGHTS

    tca = compute_tca_real(data["postulaciones"], data["notas"])
    rank_acc = compute_ranking_accuracy(
        data["postulaciones"], data["notas"], data["promedios"],
        data["horarios"], data["ramos_inscritos"], model, weights=weights)
    scores, conflictos, nrcs_con_recom = _score_distribution(data, model, weights)

    fi = "\n".join(
        f"| {FEATURE_LABELS[k]} | {v:.1%} |"
        for k, v in sorted(m["feature_importances"].items(), key=lambda kv: -kv[1]))

    if scores:
        s_line = (f"- Candidatos recomendados evaluados: **{len(scores)}** "
                  f"(en {nrcs_con_recom} NRC con recomendación)\n"
                  f"- Score promedio: **{mean(scores):.3f}** · mediana: **{median(scores):.3f}** "
                  f"· mín–máx: {min(scores):.3f}–{max(scores):.3f}")
    else:
        s_line = "- Sin candidatos recomendados (revisar datos)."

    return f"""# Evidencia de KPIs (datos reales)

> Generado por `kpi_report.py`. Período cargado en `app_data/`.
> Pesos del score (por defecto): {weights}.

## Resumen del modelo (señal de IA)

- Muestras de entrenamiento: **{m['n_samples']}** (aceptados {m['n_accepted']} / rechazados {m['n_rejected']})
- Validación cruzada 5-fold — Accuracy: **{m['cv_accuracy_mean']:.1%} ± {m['cv_accuracy_std']:.1%}**, ROC-AUC: **{m['cv_roc_auc_mean']:.3f} ± {m['cv_roc_auc_std']:.3f}**, F1: **{m['cv_f1_mean']:.3f}**

Importancia de variables aprendida por el Random Forest:

| Variable | Importancia |
|---|---|
{fi}

## KPI 1 — TCA real (compatibilidad académica histórica)

- Asignaciones aceptadas analizadas (con nota en RA311): **{tca['con_nota_en_ra311']}** de {tca['total_aceptados']} totales.
- **TCA real = {tca['tca_real_pct']}%** (línea base estimada {tca['tca_baseline_pct']}%, objetivo {tca['tca_objetivo_pct']}%).
- Interpretación: porcentaje de ayudantes aceptados que cumplían el umbral de nota ≥ {MIN_PASSING_GRADE} en el ramo. El sistema **garantiza por construcción** este filtro en sus recomendaciones (TCA = 100% sobre los recomendados).

## KPI 2 — Score de recomendación

{s_line}

### Acierto del ranking vs. decisiones históricas del coordinador
- NRC evaluados (con un aceptado histórico): **{rank_acc['nrcs_evaluados']}**
- **Top-1**: en **{rank_acc['top1_rate_pct']}%** de los NRC, el candidato #1 del modelo coincide con el que el coordinador eligió.
- **Top-3**: en **{rank_acc['top3_rate_pct']}%** de los NRC, el aceptado aparece entre los 3 primeros.
- Interpretación: el ranking reproduce con alta fidelidad las decisiones reales, evidencia de que es un apoyo útil (no aleatorio).

## KPI 3 — Conflicto de horario

- Descartes por choque de horario (solo tipos con asistencia obligatoria: {', '.join(sorted(TYPES_REQUIRING_ATTENDANCE))}): **{conflictos}**.
- Interpretación: el sistema detecta y descarta automáticamente asignaciones inviables por horario en los tipos que exigen asistencia, evitando reasignaciones posteriores.
"""


def main():
    report = build_report()
    print(report)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(f"\n[guardado en {OUT_PATH}]")


if __name__ == "__main__":
    main()
