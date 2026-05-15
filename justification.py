"""
Rule-based natural language justification generator.
Produces a short Spanish text explaining why a candidate is recommended,
highlighting the 2-3 most influential factors in their score.
"""

from scoring import W_NOTA, W_EXP, W_PROM, W_CARGA, MAX_GRADE, MIN_PASSING_GRADE


def _nota_label(nota: float) -> str:
    if nota >= 6.5:
        return "excelente"
    if nota >= 5.5:
        return "muy buena"
    if nota >= 5.0:
        return "buena"
    return "aprobatoria"


def _carga_label(carga: int) -> str:
    if carga <= 3:
        return "baja"
    if carga <= 5:
        return "moderada"
    return "alta"


def generate(row: dict, course_name: str = "") -> str:
    """
    row: dict with keys RUT, NOTA_CURSO, EXPERIENCIA, PROMEDIO, CARGA_ACTUAL, SCORE
    Returns a 2-3 sentence justification in Spanish.
    """
    rut = row["RUT"]
    nota = float(row["NOTA_CURSO"])
    exp = int(row["EXPERIENCIA"])
    prom = float(row["PROMEDIO"])
    carga = int(row["CARGA_ACTUAL"])
    score = float(row["SCORE"])

    # Compute normalized contributions to rank factors
    contributions = {
        "nota": W_NOTA * (nota / MAX_GRADE),
        "experiencia": W_EXP * (exp / max(exp, 1)),  # relative, not absolute
        "promedio": W_PROM * (prom / MAX_GRADE),
        "carga": W_CARGA * (1 - carga / 10),
    }
    top_factors = sorted(contributions, key=contributions.get, reverse=True)[:3]

    parts = []

    # Always mention the course grade (most critical factor)
    course_ref = f" en {course_name}" if course_name else ""
    parts.append(
        f"Obtuvo nota {nota:.1f}{course_ref} ({_nota_label(nota)}), "
        f"cumpliendo el requisito académico mínimo."
    )

    # Experience
    if "experiencia" in top_factors:
        if exp == 0:
            parts.append("No registra experiencia previa como ayudante.")
        elif exp == 1:
            parts.append("Cuenta con 1 semestre de experiencia previa como ayudante.")
        else:
            parts.append(f"Cuenta con {exp} semestres de experiencia previa como ayudante, lo que reduce el tiempo de inducción.")

    # GPA
    if "promedio" in top_factors and prom > 0:
        parts.append(f"Su promedio académico acumulado es {prom:.2f}, reflejando consistencia académica general.")

    # Load
    if "carga" in top_factors:
        label = _carga_label(carga)
        if carga == 0:
            parts.append("No registra ramos inscritos este período.")
        else:
            parts.append(
                f"Su carga académica actual es {label} ({carga} ramo{'s' if carga != 1 else ''}), "
                f"{'lo que favorece su disponibilidad.' if carga <= 5 else 'lo que podría limitar su disponibilidad.'}"
            )

    return " ".join(parts)
