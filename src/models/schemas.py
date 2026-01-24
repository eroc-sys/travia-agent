from typing import Optional, Literal, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class TravelIntent(BaseModel):
    intent: Literal["flight_search", "hotel_search", "both", "clarify", "follow_up"]
    origin: Optional[str]
    destination: Optional[str]
    check_in: Optional[str]
    check_out: Optional[str]
    travelers: int = Field(default=1)
    reasoning: str


class Session(BaseModel):
    session_id: str
    conversation_history: List[Dict[str, str]] = []
    last_intent: Optional[Dict[str, Any]] = None
    last_flights: Optional[List[Dict[str, Any]]] = None
    last_hotels: Optional[List[Dict[str, Any]]] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    session_id: str
    intent: Optional[Dict[str, Any]]
    used_flight_api: bool
    used_hotel_api: bool
    conversation_history: List[Dict[str, str]]