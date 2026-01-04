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
    handle_new_loop_node,
)
from app.state import ConversationState

logger = logging.getLogger(__name__)


# Router ---------------------------------------------------------------------------


def next_step_router(state: ConversationState) -> str:
    """
    Determines the NEXT node to execute.
    This router is executed AFTER a node runs.
    """
    logger.info("[NEXT_STEP_ROUTER] Called with state.step: %s", state.step)
    return state.step


def route_start(state: ConversationState) -> str:
    """
    Determines the entry point based on the current step.
    This allows the graph to resume from the correct state.
    """
    logger.info("[ROUTE_START] Called with state.step: %s", state.step)
    if state.step and state.step in {
        "ASK_NAME",
        "ASK_DATETIME",
        "ASK_TITLE",
        "CONFIRM_DETAILS",
        "AWAIT_CONFIRMATION",
        "HANDLE_NEW_LOOP",
    }:
        logger.info("[ROUTE_START] Routing directly to existing step: %s", state.step)
        return state.step
    logger.info("[ROUTE_START] No valid step found. Routing to: START")
    return "START"


# Graph Builder ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    graph = StateGraph(ConversationState)

    # Nodes
    graph.add_node("START", start_node)
    graph.add_node("ASK_NAME", ask_name_node)
    graph.add_node("ASK_DATETIME", ask_datetime_node)
    graph.add_node("ASK_TITLE", ask_title_node)
    graph.add_node("CONFIRM_DETAILS", confirm_details_node)
    graph.add_node("AWAIT_CONFIRMATION", await_confirmation_node)
    graph.add_node("HANDLE_NEW_LOOP", handle_new_loop_node)

    # Dynamic Entry Point
    graph.set_conditional_entry_point(
        route_start,
        {
            "START": "START",
            "ASK_NAME": "ASK_NAME",
            "ASK_DATETIME": "ASK_DATETIME",
            "ASK_TITLE": "ASK_TITLE",
            "CONFIRM_DETAILS": "CONFIRM_DETAILS",
            "AWAIT_CONFIRMATION": "AWAIT_CONFIRMATION",
            "HANDLE_NEW_LOOP": "HANDLE_NEW_LOOP",
        },
    )

    graph.add_edge("START", END)
    graph.add_edge("ASK_NAME", END)
    graph.add_edge("ASK_DATETIME", END)

    graph.add_conditional_edges(
        "ASK_TITLE",
        next_step_router,
        {
            "CONFIRM_DETAILS": "CONFIRM_DETAILS",
            "ASK_TITLE": END,
        },
    )

    graph.add_edge("CONFIRM_DETAILS", END)
    graph.add_edge("AWAIT_CONFIRMATION", END)
    graph.add_edge("HANDLE_NEW_LOOP", END)

    return graph.compile()


# Compiled Graph ---------------------------------------------------------------------------

conversation_graph = build_graph()

# Public Runner ---------------------------------------------------------------------------


async def run_step(state: ConversationState) -> dict:
    """
    Executes exactly ONE node per websocket turn.
    """
    logger.info("Starting with state.step: %s", state.step)
    logger.info("state.last_user_message: %s", state.last_user_message)
    try:
        result = await conversation_graph.ainvoke(
            state.dict(),
            config={"recursion_limit": 3},
        )
        logger.info(
            "[RUN_STEP] Edge traversal complete. Output Step: %s", result.get("step")
        )
        return result

    except Exception:
        logger.exception("Graph execution failed")
        return state.dict()
