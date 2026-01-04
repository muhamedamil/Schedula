# workflow.py
import logging
from langgraph.graph import StateGraph, END

from app.graph import (
    start_node,
    ask_name_node,
    ask_datetime_node,
    ask_title_node,
    confirm_details_node,
    await_confirmation_node,
)
from app.state import ConversationState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def next_step_router(state: ConversationState) -> str:
    """
    Determines the NEXT node to execute.
    This router is executed AFTER a node runs.
    """
    return state.step


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    graph = StateGraph(ConversationState)

    # Nodes
    graph.add_node("START", start_node)
    graph.add_node("ASK_NAME", ask_name_node)
    graph.add_node("ASK_DATETIME", ask_datetime_node)
    graph.add_node("ASK_TITLE", ask_title_node)
    graph.add_node("CONFIRM_DETAILS", confirm_details_node)
    graph.add_node("AWAIT_CONFIRMATION", await_confirmation_node)

    # Entry
    graph.set_entry_point("START")

    # START always executes once, then exits
    graph.add_edge("START", END)

    # Routing AFTER each node
    for node in [
        "ASK_NAME",
        "ASK_DATETIME",
        "ASK_TITLE",
        "CONFIRM_DETAILS",
        "AWAIT_CONFIRMATION",
    ]:
        graph.add_conditional_edges(
            node,
            next_step_router,
            {
                "ASK_NAME": "ASK_NAME",
                "ASK_DATETIME": "ASK_DATETIME",
                "ASK_TITLE": "ASK_TITLE",
                "CONFIRM_DETAILS": "CONFIRM_DETAILS",
                "AWAIT_CONFIRMATION": "AWAIT_CONFIRMATION",
                None: END,
                END: END,
            },
        )

    return graph.compile()


# ---------------------------------------------------------------------------
# Compiled Graph
# ---------------------------------------------------------------------------

conversation_graph = build_graph()


# ---------------------------------------------------------------------------
# Public Runner
# ---------------------------------------------------------------------------

async def run_step(state: ConversationState) -> dict:
    """
    Executes exactly ONE node per websocket turn.
    """
    try:
        result = await conversation_graph.ainvoke(
            state.dict(),
            config={"recursion_limit": 3},
        )
        return result

    except Exception:
        logger.exception("Graph execution failed")
        return state.dict()
