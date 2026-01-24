from src.models.state import AgentState


def router(state: AgentState):
    if state.intent is None:
        return "clarify"

    intent = state.intent["intent"]

    if intent == "flight_search":
        return "flight_tool"
    if intent == "hotel_search":
        return "hotel_tool"
    if intent == "both":
        return "flight_tool"
    if intent == "follow_up":
        return "synthesis"

    return "clarify"


def flight_tool_router(state: AgentState):
    # Check if we need to use web search fallback
    if state.use_web_search:
        return "web_search_fallback"

    if state.intent is None:
        return "synthesis"

    intent = state.intent["intent"]

    if intent == "both":
        return "hotel_tool"

    return "synthesis"
