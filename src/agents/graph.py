from langgraph.graph import StateGraph, END

from src.models.state import AgentState
from src.agents.nodes import (
    intent_node,
    flight_tool,
    hotel_tool,
    clarify_node,
    synthesis_node,
    web_search_fallback_node,
)
from src.agents.routers import router, flight_tool_router


def create_agent():
    graph = StateGraph(AgentState)

    graph.add_node("intent", intent_node)
    graph.add_node("flight_tool", flight_tool)
    graph.add_node("hotel_tool", hotel_tool)
    graph.add_node("clarify", clarify_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("web_search_fallback", web_search_fallback_node)

    graph.set_entry_point("intent")

    graph.add_conditional_edges("intent", router)
    graph.add_conditional_edges("flight_tool", flight_tool_router)

    graph.add_edge("hotel_tool", "synthesis")
    graph.add_edge("clarify", END)
    graph.add_edge("synthesis", END)
    graph.add_edge("web_search_fallback", END)

    return graph.compile()


# Global instance
agent = create_agent()
