from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class AgentLog(BaseModel):
    id: Optional[str] = Field(default=None)
    session_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    # Datos adicionales de tracing
    tools: Optional[List[Dict[str, Any]]] = None      # llamadas a herramientas
    metadata: Optional[Dict[str, Any]] = None         # p.ej., prioridades calculadas, filtros, etc.
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
