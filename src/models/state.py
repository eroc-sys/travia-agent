from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class AgentState(BaseModel):
    query: str
    conversation_history: List[Dict[str, str]] = []
    intent: Optional[Dict[str, Any]] = None
    flights: Optional[List[Dict[str, Any]]] = None
    hotels: Optional[List[Dict[str, Any]]] = None
    response: Optional[str] = None
    use_web_search: bool = False
    search_query: Optional[str] = None