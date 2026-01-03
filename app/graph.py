from langgraph.graph import END
from app.state import ConversationState
from app.nlu.extractor import extract_fields
import logging

# Optional: import your Google Calendar helper
# from app.calendar.google_calendar import create_google_calendar_event

logger = logging.getLogger(__name__)

# ---------------- Node Definitions ---------------- #

async def start_node(state: ConversationState) -> ConversationState:
    """
    Entry point of the conversation.
    """
    state.system_message = (
        "Hi! I can help you schedule a meeting. Let's start with your name."
    )
    state.step = "ASK_NAME"
    return state


async def ask_name_node(state: ConversationState) -> ConversationState:
    """
    Ask for user's name if not already known.
    """
    # Extract any fields from last user message
    state = await extract_fields(state, state.last_user_message)

    if state.name:
        state.system_message = (
            f"Nice to meet you, {state.name}. When would you like to schedule the meeting?"
        )
        state.step = "ASK_DATETIME"
    else:
        state.system_message = "Could you please tell me your name?"
        state.step = "ASK_NAME"

    return state


async def ask_datetime_node(state: ConversationState) -> ConversationState:
    """
    Ask for meeting date & time if not already known.
    """
    # Extract any fields from last user message
    state = await extract_fields(state, state.last_user_message)

    if state.meeting_datetime:
        state.system_message = (
            "Got it. Would you like to add a title for the meeting? "
            "You can say 'no' to skip."
        )
        state.step = "ASK_TITLE"
    else:
        state.system_message = (
            "Please tell me the preferred date and time for the meeting "
            "(e.g., 12/31/2026 03:00 PM)."
        )
        state.step = "ASK_DATETIME"

    return state


async def ask_title_node(state: ConversationState) -> ConversationState:
    """
    Ask for optional meeting title.
    """
    # Extract any fields from last user message
    state = await extract_fields(state, state.last_user_message)

    if not state.meeting_title:
        state.system_message = "Do you want to add a title for the meeting? You can say 'no'."
        state.step = "ASK_TITLE"
    else:
        state.system_message = "Alright. Let me confirm the details with you."
        state.step = "CONFIRM_DETAILS"

    return state


async def confirm_details_node(state: ConversationState) -> ConversationState:
    """
    Confirm collected meeting details.
    """
    # Defensive defaults
    name = state.name or "<name missing>"
    title_part = f" titled '{state.meeting_title}'" if state.meeting_title else ""
    date_part = (
        state.meeting_datetime.strftime("%A, %d %B %Y at %I:%M %p")
        if state.meeting_datetime
        else "an unspecified time"
    )

    state.system_message = (
        f"Please confirm: A meeting for {name} on {date_part}{title_part}. "
        "Should I go ahead and create it?"
    )
    state.step = "AWAIT_CONFIRMATION"
    return state


async def handle_confirmation_node(state: ConversationState) -> ConversationState:
    """
    Handle user's confirmation input and create calendar event if confirmed.
    """
    response = state.last_user_message.strip().lower()

    if response in ["yes", "sure", "go ahead", "yep"]:
        # Create calendar event (replace with your actual implementation)
        try:
            # await create_google_calendar_event(
            #     name=state.name,
            #     datetime=state.meeting_datetime,
            #     title=state.meeting_title
            # )
            state.system_message = "Meeting has been successfully created!"
        except Exception as e:
            logger.exception("Failed to create calendar event: %s", e)
            state.system_message = "Sorry, I failed to create the meeting. Please try again."
        state.step = END
    elif response in ["no", "nah", "cancel"]:
        state.system_message = "Okay, the meeting was not created. You can start over if you like."
        state.step = END
    else:
        state.system_message = "I didn't understand that. Please reply with 'yes' or 'no'."
        state.step = "AWAIT_CONFIRMATION"

    return state
