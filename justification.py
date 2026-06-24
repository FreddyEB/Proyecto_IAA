"""Justificación breve en lenguaje natural por candidato."""
from scoring import normalize_weights, DEFAULT_WEIGHTS, MAX_GRADE


def _nota_label(nota: float) -> str:
    if nota >= 6.5:
        return "excelente"
    if nota >= 5.5:
        return "muy buena"
    if nota >= 5.0:
        return "buena"
    return "aprobatoria"


def generate(row: dict, weights: dict = None, course_name: str = "") -> str:
    weights = normalize_weights(weights or DEFAULT_WEIGHTS)
    nota = float(row["NOTA_CURSO"])
    exp = int(row["EXPERIENCIA"])
    prom = float(row["PROMEDIO"])

    contributions = {
        "experiencia": weights["experiencia"] * (exp / max(exp, 1)),
        "promedio": weights["promedio"] * (prom / MAX_GRADE),
    }
    top_factors = [f for f, _ in sorted(contributions.items(), key=lambda kv: kv[1], reverse=True)
                   if contributions[f] > 0][:2]

    parts = []
    course_ref = f" en {course_name}" if course_name else ""
    parts.append(
        f"Obtuvo nota {nota:.1f}{course_ref} ({_nota_label(nota)}), "
        f"cumpliendo el requisito académico mínimo.")

    if "experiencia" in top_factors:
        if exp == 0:
            parts.append("No registra experiencia previa como ayudante.")
        elif exp == 1:
            parts.append("Cuenta con 1 semestre de experiencia previa como ayudante.")
        else:
            parts.append(f"Cuenta con {exp} semestres de experiencia previa como ayudante, "
                         f"lo que reduce el tiempo de inducción.")

    if "promedio" in top_factors and prom > 0:
        parts.append(f"Su promedio académico acumulado es {prom:.2f}, "
                     f"reflejando consistencia académica general.")

    return " ".join(parts)
