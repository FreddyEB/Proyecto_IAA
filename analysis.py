"""
Retrospective analysis: compares model recommendations against historical decisions.

Metrics computed:
- TCA real: % of historical Aceptado assignments where the candidate had nota >= 4.0
- Top-1 match rate: % of NRCs where the model's #1 candidate was the one actually accepted
- Top-3 match rate: % of NRCs where the accepted candidate appears in the model's top-3
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from scoring import rank_candidates, MIN_PASSING_GRADE


def compute_tca_real(postulaciones: pd.DataFrame, notas: pd.DataFrame) -> dict:
    """
    TCA over historical Aceptado assignments.
    Compares against the 67% baseline from Entregable 2.
    """
    accepted = postulaciones[postulaciones["Estado"] == "Aceptado"].copy()
    accepted["RUT"] = accepted["RUT"].astype(str)
    accepted["Curso"] = accepted["Curso"].astype(str).str.strip()
    accepted["Materia"] = accepted["Materia"].astype(str).str.strip()

    best_nota = (
        notas.groupby(["RUT", "MATERIA", "CURSO"])["NOTA"]
        .max()
        .reset_index(name="NOTA_CURSO")
    )

    merged = accepted.merge(
        best_nota,
        left_on=["RUT", "Materia", "Curso"],
        right_on=["RUT", "MATERIA", "CURSO"],
        how="left",
    )

    total = len(merged)
    with_nota = merged["NOTA_CURSO"].notna().sum()
    compatible = (merged["NOTA_CURSO"] >= MIN_PASSING_GRADE).sum()

    return {
        "total_aceptados": total,
        "con_nota_en_ra311": int(with_nota),
        # TCA calculated only over assignments with a grade in RA311
        "tca_real_pct": round(compatible / with_nota * 100, 1) if with_nota > 0 else 0.0,
        "tca_baseline_pct": 67.0,
        "tca_objetivo_pct": 90.0,
    }


def compute_ranking_accuracy(
    postulaciones: pd.DataFrame,
    notas: pd.DataFrame,
    promedios: pd.DataFrame,
    horarios: pd.DataFrame,
    ramos_inscritos: pd.DataFrame,
    model: RandomForestClassifier,
    weights: dict = None,
) -> dict:
    """
    For each NRC with at least one Aceptado, runs the model ranking and checks
    whether the accepted candidate appears in top-1 and top-3.
    """
    nrcs_with_accepted = postulaciones[postulaciones["Estado"] == "Aceptado"]["NRC"].unique()
    valid_nrcs = set(horarios["NRC"].unique())

    top1_correct = 0
    top3_correct = 0
    evaluated = 0
    details = []

    for nrc in nrcs_with_accepted:
        if nrc not in valid_nrcs:
            continue
        accepted_ruts = set(
            postulaciones[(postulaciones["NRC"] == nrc) & (postulaciones["Estado"] == "Aceptado")]
            ["RUT"].astype(str)
        )
        result = rank_candidates(nrc, postulaciones, notas, promedios,
                                 horarios, ramos_inscritos, model,
                                 weights=weights, top_n=5)
        if result.empty:
            continue
        eligible = result[result["FILTRO_NOTA"] & result["FILTRO_HORARIO"]]
        if eligible.empty:
            continue

        evaluated += 1
        ranked = eligible["RUT"].astype(str).tolist()
        is_top1 = bool(ranked and ranked[0] in accepted_ruts)
        is_top3 = any(r in accepted_ruts for r in ranked[:3])

        if is_top1:
            top1_correct += 1
        if is_top3:
            top3_correct += 1

        nrc_info = horarios[horarios["NRC"] == nrc].iloc[0]
        details.append({
            "NRC": nrc,
            "Asignatura": nrc_info.get("TITULO", ""),
            "Top-1 correcto": "✅" if is_top1 else "❌",
            "Aceptado en Top-3": "✅" if is_top3 else "❌",
            "Score #1": round(eligible.iloc[0]["SCORE"], 4) if not eligible.empty else None,
        })

    return {
        "nrcs_evaluados": evaluated,
        "top1_match": top1_correct,
        "top3_match": top3_correct,
        "top1_rate_pct": round(top1_correct / evaluated * 100, 1) if evaluated else 0,
        "top3_rate_pct": round(top3_correct / evaluated * 100, 1) if evaluated else 0,
        "details": pd.DataFrame(details),
    }
