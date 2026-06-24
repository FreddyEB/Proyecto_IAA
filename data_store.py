"""Resolución, validación y persistencia de los CSV de entrada."""
from pathlib import Path

DATA_DIR = Path(__file__).parent

FILE_CODES = {
    "postulaciones": "reportePostulaciones",
    "notas": "RA311",
    "promedios": "UG305",
    "ramos_inscritos": "UG307",
    "horarios": "UG201",
}

EXPECTED_COLUMNS = {
    "postulaciones": ["RUT", "NRC", "Materia", "Curso", "Estado", "Tipo de ayudante", "Profesor"],
    "notas": ["RUT", "MATERIA", "CURSO", "NOTA"],
    "promedios": ["RUT", "PROMEDIO  GENERAL  ACUMULADO"],
    "ramos_inscritos": ["RUT", "NRC"],
    "horarios": ["NRC", "MATERIA", "CURSO", "TIPO", "RUT PROFESOR", "PROFESOR"],
}


def find_csv(code: str, base_dir: Path = DATA_DIR) -> Path:
    matches = sorted(Path(base_dir).glob(f"*{code}*.csv"))
    if not matches:
        raise FileNotFoundError(f"No CSV found matching '*{code}*' en {base_dir}")
    return matches[0]


def validate_columns(code: str, columns) -> list[str]:
    expected = EXPECTED_COLUMNS[code]
    present = {str(c).strip() for c in columns}
    return [c for c in expected if c not in present]


def present_files(base_dir: Path = DATA_DIR) -> dict[str, bool]:
    result = {}
    for key, code in FILE_CODES.items():
        try:
            find_csv(code, base_dir)
            result[key] = True
        except FileNotFoundError:
            result[key] = False
    return result


def clear_all(base_dir: Path = DATA_DIR) -> list[str]:
    deleted = []
    for code in FILE_CODES.values():
        for path in Path(base_dir).glob(f"*{code}*.csv"):
            path.unlink()
            deleted.append(path.name)
    return deleted
