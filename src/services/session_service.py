import uuid
from typing import Dict, Any, Optional
from src.models.schemas import Session


class SessionService:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        if session_id and session_id in self.sessions:
            return Session(**self.sessions[session_id])
        
        new_session_id = session_id or str(uuid.uuid4())
        session = Session(session_id=new_session_id)
        self.sessions[new_session_id] = session.model_dump()
        return session
    
    def update_session(self, session: Session):
        self.sessions[session.session_id] = session.model_dump()
    
    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)


# Global instance
session_service = SessionService()