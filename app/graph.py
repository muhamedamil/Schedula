from langgraph.graph import StateGraph, END
import logging

from app.state import ConversationState
from app.nlu.extractor import extract_fields
from app.calendar.google_calendar import GoogleCalendarService, GoogleCalendarError

logger = logging.getLogger(__name__)
calendar_service = GoogleCalendarService()

# ---------------- Nodes ---------------- #


async def start_node(state: ConversationState) -> dict:
    logger.info("[START_NODE] Executing")
    state.system_message = "Hi! I can help you schedule a new event. Before that I would like to know What's your name?"
    state.step = "ASK_NAME"
    logger.info("Set step to ASK_NAME")
    return state.dict()


async def ask_name_node(state: ConversationState) -> dict:
    logger.info(
        "Executing with last_user_message: %s", state.last_user_message
    )
    state = await extract_fields(state, state.last_user_message)
    logger.info("[ASK_NAME_NODE] After extraction, state.name: %s", state.name)

    if state.name:
        state.system_message = (
            f"Nice to meet you, {state.name}. When should we schedule the meeting?"
        )
        state.step = "ASK_DATETIME"
        logger.info("Name found, moving to ASK_DATETIME")
    else:
        state.system_message = (
            "I didn't catch your name. If you don't mind could you please tell me your name?"
        )
        state.step = "ASK_NAME"
        logger.info("No name found, staying in ASK_NAME")

    return state.dict()


async def ask_datetime_node(state: ConversationState) -> dict:
    logger.info(
        "Executing with last_user_message: %s",
        state.last_user_message,
    )
    state = await extract_fields(state, state.last_user_message)
    logger.info(
        "After extraction, meeting_datetime: %s",state.meeting_datetime,
    )

    if state.meeting_datetime:
        state.system_message = (
            "Got it. Would you like to add a title for the meeting? You can say no."
        )
        state.step = "ASK_TITLE"
        logger.info("[ASK_DATETIME_NODE] DateTime found, moving to ASK_TITLE")
    else:
        state.system_message = (
            "Please tell me the preferred date and time "
            "(for example, 12 Jan at 3 PM)."
        )
        state.step = "ASK_DATETIME"
        logger.info("[ASK_DATETIME_NODE] No datetime found, staying in ASK_DATETIME")

    return state.dict()


async def ask_title_node(state: ConversationState) -> dict:
    logger.info("[ASK_TITLE_NODE] Executing")
    state = await extract_fields(state, state.last_user_message)

    msg = (state.last_user_message or "").lower().strip()

    # If title extracted OR user explicitly says no/skip
    if state.meeting_title or msg in {"no", "nope", "skip", "none","not needed"}:
        state.system_message = "Let me confirm the details with you."
        state.step = "CONFIRM_DETAILS"
        logger.info("Moving to CONFIRM_DETAILS")
    else:
        state.system_message = (
            "I didn't catch a title. Please say the title or say 'no' to skip."
        )
        state.step = "ASK_TITLE"
        logger.info("Staying in ASK_TITLE")

    return state.dict()


async def confirm_details_node(state: ConversationState) -> dict:
    logger.info("[CONFIRM_DETAILS_NODE] Executing")
    date_str = (
        state.meeting_datetime.strftime("%A, %d %B at %I:%M %p")
        if state.meeting_datetime
        else "an unspecified time"
    )

    title_part = f" titled '{state.meeting_title}'" if state.meeting_title else ""

    state.system_message = (
        f"Please confirm: A meeting for {state.name} on {date_str}{title_part}. "
        "Should I go ahead and create it?"
    )
    state.step = "AWAIT_CONFIRMATION"

    return state.dict()


async def await_confirmation_node(state: ConversationState) -> dict:
    logger.info(
        "[AWAIT_CONFIRMATION_NODE] Executing with response: %s", state.last_user_message
    )
    response = (state.last_user_message or "").lower().strip()

    if response in {"yes", "yep", "sure", "go ahead","yeah sure","yeah","okay go ahead"}:
        try:
            await calendar_service.create_event(
                title=state.meeting_title or "Meeting",
                start_datetime=state.meeting_datetime,
                description=f"Meeting with {state.name}",
                duration_minutes=30,
            )
            state.system_message = "Your meeting has been created successfully."
            state.is_confirmed = True
            state.step = "END"

        except GoogleCalendarError:
            logger.exception("Calendar error")
            state.system_message = (
                "I couldn't create the meeting due to a calendar error."
            )
            state.is_confirmed = False
            state.step = "END"

    elif response in {"no", "cancel", "stop"}:
        state.system_message = "Okay, I won't create the meeting."
        state.is_confirmed = False
        state.step = "END"

    else:
        state.system_message = "Please reply with yes or no."
        state.step = "AWAIT_CONFIRMATION"

    return state.dict()
