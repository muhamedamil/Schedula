from langgraph.graph import StateGraph, END
from app.state import ConversationState
from typing import Literal


# ---------------- Node Definitions ---------------- #

async def start_node(state: ConversationState) -> ConversationState:
    """
    Entry point of the conversation.
    """
    state.system_message = (
        "Hi! I can help you schedule a meeting. Let's start with your name."
    )
    return state


async def ask_name_node(state: ConversationState) -> ConversationState:
    """
    Ask for user's name if not already known.
    """
    if state.name:
        state.system_message = (
            f"Nice to meet you, {state.name}. "
            "When would you like to schedule the meeting?"
        )
    else:
        state.system_message = "Could you please tell me your name?"

    return state


async def ask_datetime_node(state: ConversationState) -> ConversationState:
    """
    Ask for meeting date & time if not already known.
    """
    if state.meeting_datetime:
        state.system_message = (
            "Got it. Would you like to add a title for the meeting? "
            "You can say 'no' if you want to skip."
        )
    else:
        state.system_message = (
            "Please tell me the preferred date and time for the meeting."
        )

    return state


async def ask_title_node(state: ConversationState) -> ConversationState:
    """
    Ask for optional meeting title.
    """
    state.system_message = (
        "Alright. Let me confirm the details with you."
    )
    return state


async def confirm_details_node(state: ConversationState) -> ConversationState:
    """
    Confirm collected meeting details.
    """
    title_part = f" titled '{state.meeting_title}'" if state.meeting_title else ""
    date_part = (
        state.meeting_datetime.strftime("%A, %d %B %Y at %I:%M %p")
        if state.meeting_datetime
        else "an unspecified time"
    )

    state.system_message = (
        f"Please confirm: A meeting for {state.name} on {date_part}{title_part}. "
        "Should I go ahead and create it?"
    )

    return state
