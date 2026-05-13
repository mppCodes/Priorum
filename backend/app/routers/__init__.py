# routers package

from .tasks import router as tasks
# Mantén tus otros routers si existen:
# from .calendar import router as calendar
# from .agent import router as agent

__all__ = ["tasks"]
# Evita importar routers aquí para no provocar efectos colaterales
# (por ejemplo: from .tasks import router as tasks)
# Importa los routers directamente desde main.py
__all__ = []
