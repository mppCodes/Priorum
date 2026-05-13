"""
Configuración de logging para Priorum.

Comportamiento:
  - Consola : gestionada íntegramente por uvicorn (no se modifica)
  - Fichero : INFO+  (todo lo que uvicorn muestra en consola + logs detallados de la app)

Nombre del fichero: logs/YYYY-MM-DD_HH-MM-SS.log  (fecha/hora de arranque del servidor)
"""
import logging
from datetime import datetime
from pathlib import Path

# ── Directorio y fichero ──────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")

# ── Handler de fichero ────────────────────────────────────────────────────────
_FMT     = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATEFMT))
_file_handler.setLevel(logging.INFO)


def setup_logging() -> None:
    """
    Añade el handler de fichero al root logger sin tocar los handlers
    de uvicorn ni la consola. Uvicorn gestiona su propia salida por consola.
    Se llama al importar el módulo y de nuevo en el lifespan de FastAPI
    para garantizar que el handler de fichero sigue activo tras el arranque.
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Añadir el file handler solo si no está ya registrado (evitar duplicados)
    if _file_handler not in root.handlers:
        root.addHandler(_file_handler)

    # Asegurar que uvicorn y fastapi propagan al root para que lleguen al fichero
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        lg = logging.getLogger(name)
        lg.propagate = True


# Aplicar al importar el módulo
setup_logging()
