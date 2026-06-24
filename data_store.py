"""Resolución, validación y persistencia de los CSV de entrada."""
import shutil
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent
BACKUP_DIRNAME = "_data_backup"

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


def clear_all(base_dir: Path = DATA_DIR) -> dict:
    """Mueve los CSV reconocidos a una carpeta de respaldo con timestamp (reversible),
    en vez de borrarlos. Devuelve {"moved": [nombres], "backup_dir": ruta|None}."""
    base_dir = Path(base_dir)
    backup_dir = base_dir / BACKUP_DIRNAME / datetime.now().strftime("%Y%m%d_%H%M%S")
    moved = []
    for code in FILE_CODES.values():
        for path in base_dir.glob(f"*{code}*.csv"):
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(backup_dir / path.name))
            moved.append(path.name)
    return {"moved": moved, "backup_dir": str(backup_dir) if moved else None}
