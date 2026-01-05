from langgraph.graph import StateGraph, END
import logging

from app.state import ConversationState
from app.nlu.extractor import extract_fields
from app.nlu.generator import generate_response
from app.calendar.google_calendar import GoogleCalendarService, GoogleCalendarError

logger = logging.getLogger(__name__)
calendar_service = GoogleCalendarService()


# Nodes --------------------------------

async def start_node(state: ConversationState) -> dict:
    logger.info("[START_NODE] Executing")

    # Logic for authenticated users 
    if state.name:
        logger.info("User authenticated as %s. Skipping ASK_NAME.", state.name)
        response = await generate_response(
            state,
            goal=f"Greet {state.name} warmly back. Mention you are ready to schedule on their calendar. Ask for the date and time.",
        )
        state.system_message = response
        state.step = "ASK_DATETIME"
        logger.info("Set step to ASK_DATETIME")

    else:
        #Standard flow for guests
        response = await generate_response(
            state,
            goal="Greet the user warmly and ask for their name to start scheduling.",
        )
        state.system_message = response
        state.step = "ASK_NAME"
        logger.info("Set step to ASK_NAME")

    return state.dict()


async def ask_name_node(state: ConversationState) -> dict:
    logger.info("Executing with last_user_message: %s", state.last_user_message)
    state = await extract_fields(state, state.last_user_message)
    logger.info("[ASK_NAME_NODE] After extraction, state.name: %s", state.name)

    if state.name:
        response = await generate_response(
            state,
            goal="Acknowledge the user's name warmly and ask for the meeting date and time.",
        )
        state.system_message = response
        state.step = "ASK_DATETIME"
        logger.info("Name found, moving to ASK_DATETIME")
    else:
        # Dynamic Retry
        response = await generate_response(
            state,
            goal="Politely explain you didn't catch the name and ask for it again.",
            context_note="User input was unclear or didn't contain a name.",
        )
        state.system_message = response
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
        "After extraction, meeting_datetime: %s",
        state.meeting_datetime,
    )

    if state.meeting_datetime:
        response = await generate_response(
            state,
            goal="Acknowledge the date/time and ask if they want to add a meeting title (or say no to skip).",
        )
        state.system_message = response
        state.step = "ASK_TITLE"
        logger.info("[ASK_DATETIME_NODE] DateTime found, moving to ASK_TITLE")
    else:
        # Dynamic Retry
        response = await generate_response(
            state,
            goal="Politely explain the date was invalid or missing, and ask for the date and time again (e.g. tomorrow at 3pm).",
            context_note="Date parsing failed.",
        )
        state.system_message = response
        state.step = "ASK_DATETIME"
        logger.info("[ASK_DATETIME_NODE] No datetime found, staying in ASK_DATETIME")

    return state.dict()


async def ask_title_node(state: ConversationState) -> dict:
    logger.info("[ASK_TITLE_NODE] Executing")
    state = await extract_fields(state, state.last_user_message)

    msg = (state.last_user_message or "").lower().strip()

    # If title extracted OR user explicitly says no/skip
    if state.meeting_title or msg in {"no", "nope", "skip", "none", "not needed"}:
        state.step = "CONFIRM_DETAILS"
        logger.info("Moving to CONFIRM_DETAILS")
    else:
        # Dynamic Retry
        response = await generate_response(
            state,
            goal="Politely ask for the title again, or remind them they can say 'no' to skip.",
            context_note="Input was not a title or 'no'.",
        )
        state.system_message = response
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
    title_str = state.meeting_title or "Meeting"

    # We pass the formatted details to the LLM to ensure accuracy
    context_note = f"CONFIRMATION DETAILS: Title='{title_str}', Date='{date_str}'. Name='{state.name}'"

    # Dynamic Confirmation Request
    response = await generate_response(
        state,
        goal=f"Ask user to confirm these EXACT details: {title_str} on {date_str}. Ask 'Should I create it?'. Be precise.",
        context_note=context_note,
    )

    state.system_message = response
    state.step = "AWAIT_CONFIRMATION"

    return state.dict()


async def await_confirmation_node(state: ConversationState) -> dict:
    logger.info(
        "[AWAIT_CONFIRMATION_NODE] Executing with response: %s", state.last_user_message
    )

    # Ensure fresh extraction for intent
    state.confirmation_status = None
    state = await extract_fields(state, state.last_user_message)

    intent = state.confirmation_status
    logger.info("Confirmation intent extracted: %s", intent)

    if intent == "yes":
        try:
            await calendar_service.create_event(
                title=state.meeting_title or "Meeting",
                start_datetime=state.meeting_datetime,
                description=f"Meeting with {state.name}",
                duration_minutes=30,
                access_token=state.google_access_token,
            )

            # Dynamic Success Message + Ask about another event
            final_response = await generate_response(
                state,
                goal="Confirm the meeting was successfully created. Then ask if they would like to schedule ANOTHER event.",
            )
            state.system_message = final_response
            state.is_confirmed = True
            state.step = "HANDLE_NEW_LOOP" 

        except GoogleCalendarError:
            logger.exception("Calendar error")
            state.system_message = "I encountered an issue connecting to the calendar. Please try again later."
            state.is_confirmed = False
            state.step = "END"

    elif intent == "no":
        state.system_message = (
            "Okay, I've cancelled the request. Let me know if you need anything else."
        )
        state.is_confirmed = False
        state.step = "END"

    else:
        state.system_message = "I'm not sure if you want to confirm. Please say yes to confirm or no to cancel."
        state.step = "AWAIT_CONFIRMATION"

    return state.dict()


async def handle_new_loop_node(state: ConversationState) -> dict:
    logger.info("[HANDLE_NEW_LOOP_NODE] Executing")

    state.confirmation_status = None
    state = await extract_fields(state, state.last_user_message)

    intent = state.confirmation_status
    logger.info("Loop intent: %s", intent)

    if intent == "yes":
        # RESET STATE for new event
        logger.info("User wants another event. Resetting state.")
        state.name = None
        state.meeting_datetime = None
        state.meeting_title = None
        state.is_confirmed = False
        state.confirmation_status = None

        # Ask for name again
        response = await generate_response(
            state, goal="Enthusiastically accept. Ask who the new meeting is with."
        )
        state.system_message = response
        state.step = "ASK_NAME"

    elif intent == "no":
        response = await generate_response(
            state, goal="Politely say goodbye and end the session."
        )
        state.system_message = response
        state.step = "END"

    else:
        state.system_message = (
            "I didn't catch that. Do you want to schedule another event? Yes or No?"
        )
        state.step = "HANDLE_NEW_LOOP"

    return state.dict()
