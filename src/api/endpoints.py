from fastapi import APIRouter, HTTPException

from src.models.schemas import QueryRequest, QueryResponse
from src.models.state import AgentState
from src.services.session_service import session_service
from src.utils.validators import QueryValidator
from src.agents.graph import agent


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query_agent(req: QueryRequest):
    try:
        # Validate and sanitize input
        try:
            sanitized_query = QueryValidator.sanitize_query(req.query)
        except ValueError as e:
            print(f"Input validation failed: {e}")
            raise HTTPException(status_code=400, detail=str(e))

        # Validate session ID if provided
        if req.session_id and not QueryValidator.validate_session_id(req.session_id):
            raise HTTPException(status_code=400, detail="Invalid session ID format")

        # Get or create session
        session = session_service.get_or_create_session(req.session_id)

        # Add user query to history
        session.conversation_history.append(
            {
                "role": "user",
                "content": sanitized_query,
            }
        )

        # Create agent state
        initial_state = AgentState(
            query=sanitized_query,
            conversation_history=session.conversation_history,
        )

        # Run agent
        result = agent.invoke(initial_state)

        if not result.get("response"):
            raise HTTPException(status_code=500, detail="Agent execution failed")

        # Add assistant response to history
        session.conversation_history.append(
            {
                "role": "assistant",
                "content": result["response"],
            }
        )

        # Update session with last results
        session.last_intent = result.get("intent")
        session.last_flights = result.get("flights")
        session.last_hotels = result.get("hotels")

        # Save session
        session_service.update_session(session)

        return QueryResponse(
            answer=result["response"],
            session_id=session.session_id,
            intent=result.get("intent"),
            used_flight_api=bool(result.get("flights")),
            used_hotel_api=bool(result.get("hotels")),
            conversation_history=session.conversation_history,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@router.get("/session/{session_id}")
def get_session(session_id: str):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/session/{session_id}")
def clear_session(session_id: str):
    if session_service.delete_session(session_id):
        return {"message": "Session cleared"}

    raise HTTPException(status_code=404, detail="Session not found")
