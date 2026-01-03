"""
workflow.py

Defines and initializes the conversation StateGraph for the Voice Scheduling Agent.
"""

from langgraph.graph import StateGraph, END
from app.graph import (
    start_node,
    ask_name_node,
    ask_datetime_node,
    ask_title_node,
    confirm_details_node,
    handle_confirmation_node,
)
from app.state import ConversationState
import logging

logger = logging.getLogger(__name__)

# ---------------- Node Mapping ---------------- #
# Maps state.step strings to corresponding async node functions
NODE_MAPPING = {
    "START": start_node,
    "ASK_NAME": ask_name_node,
    "ASK_DATETIME": ask_datetime_node,
    "ASK_TITLE": ask_title_node,
    "CONFIRM_DETAILS": confirm_details_node,
    "AWAIT_CONFIRMATION": handle_confirmation_node,
}

# ---------------- StateGraph Initialization ---------------- #
# This graph handles the full conversation workflow
conversation_graph: StateGraph[ConversationState] = StateGraph(
    initial_state="START",       # starting node
    nodes=NODE_MAPPING,          # node mapping
    end_states=[END],            # nodes considered as end of conversation
    state_type=ConversationState # type of state object
)

# ---------------- Utility Functions ---------------- #

def get_node_for_step(step: str):
    """
    Retrieve the async node function for a given step.
    """
    node_func = NODE_MAPPING.get(step)
    if not node_func:
        logger.warning("No node found for step: %s", step)
        return None
    return node_func

async def run_step(state: ConversationState):
    """
    Run the current step for a given conversation state.
    This is a convenience wrapper for LangGraph's run().
    """
    current_step = state.step or "START"
    node_func = get_node_for_step(current_step)

    if not node_func:
        logger.error("Invalid step: %s, defaulting to START", current_step)
        node_func = start_node

    try:
        new_state = await conversation_graph.run(state)
        return new_state
    except Exception as e:
        logger.exception("Error running state graph at step %s: %s", current_step, e)
        state.system_message = "Oops! Something went wrong. Let's start over."
        state.step = "START"
        return state

# ---------------- Optional: Debug / Testing ---------------- #
if __name__ == "__main__":
    import asyncio
    from app.state import ConversationState

    async def test_graph():
        state = ConversationState()
        while state.step != END:
            state = await run_step(state)
            print(f"[{state.step}] {state.system_message}")
            # simulate user input for testing
            state.last_user_message = input("User: ")

    asyncio.run(test_graph())
