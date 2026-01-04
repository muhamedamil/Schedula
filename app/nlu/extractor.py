import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from groq import Groq
from pydantic import ValidationError

from app.state import ConversationState
from app.config import settings
from app.nlu.validators import (
    validate_name,
    validate_meeting_datetime,
    validate_meeting_title,
)
from app.utils.datetime_parser import parse_datetime
from app.nlu.prompts import SYSTEM_PROMPT, USER_PROMPT
from app.nlu.schemas import ExtractionFields
from app.utils.logger import setup_logging


# Logging ------------------------------------

logger = logging.getLogger(__name__)
# Groq Client ------------------------------------

GROQ_API_KEY = settings.GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

MODEL_NAME = settings.GROQ_MODEL_NAME
REQUEST_TIMEOUT = settings.LLM_REQUEST_TIMEOUT
MAX_RETRIES = settings.LLM_MAX_RETRIES
GROQ_TEMPERATURE = settings.GROQ_TEMPERATURE
GROQ_MAX_TOKENS = settings.GROQ_MAX_TOKENS
GROQ_TOP_P = settings.GROQ_TOP_P

# Helpers ---------------------------------------------


def _safe_json_parse(text: str) -> Dict[str, Any]:
    """
    Safely extract JSON from LLM output.
    Never raises; returns empty dict if parsing fails.
    """
    if not text:
        return {}

    # Direct attempt
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract first JSON object in the text
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and start < end:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse JSON from LLM output: %s", text)
    return {}


def _call_groq(user_message: str) -> Dict[str, Any]:
    """
    Blocking Groq call. Must run in executor.
    """
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT.format(user_message=user_message)},
        ],
        temperature=GROQ_TEMPERATURE,
        max_completion_tokens=GROQ_MAX_TOKENS,
        top_p=GROQ_TOP_P,
    )

    content = completion.choices[0].message.content
    return _safe_json_parse(content)


async def _run_with_retries(user_message: str) -> Dict[str, Any]:
    """
    Async wrapper with retries and timeout protection.
    """
    loop = asyncio.get_running_loop()
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, _call_groq, user_message),
                timeout=REQUEST_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("Groq timeout on attempt %s", attempt)
        except Exception as e:
            logger.exception("Groq call failed on attempt %s: %s", attempt, e)
    return {}


# Main Extraction ------------------------------------


async def extract_fields(
    state: ConversationState,
    user_message: str,
) -> ConversationState:
    """
    Extract structured fields from user input using LLM.
    Fully async, retry-protected, schema-validated.
    """
    logger.info("[EXTRACT_FIELDS] Called with user_message: %s", user_message)

    raw_output = await _run_with_retries(user_message)
    logger.info("[EXTRACT_FIELDS] LLM raw output: %s", raw_output)
    if not raw_output:
        return state

    # ---------------- Pydantic schema enforcement ---------------- #
    try:
        fields = ExtractionFields(**raw_output)
    except ValidationError as e:
        logger.warning(
            "Schema validation failed. Raw output: %s | Error: %s",
            raw_output,
            e,
        )
        return state

    # ---------------- Validators ---------------- #
    name = validate_name(fields.name)
    title = validate_meeting_title(fields.meeting_title)

    logger.info(
        name,
        title,
        fields.meeting_datetime_text,
    )

    # ---------------- Confirmation Status ---------------- #
    if fields.confirmation_status:
        val = fields.confirmation_status.lower().strip()
        if val in {"yes", "no", "uncertain"}:
            state.confirmation_status = val
            logger.info("Updated state.confirmation_status to: %s", val)

    meeting_datetime: Optional[datetime] = None

    if fields.meeting_datetime_text:

        user_tz = ZoneInfo(state.timezone or "UTC")
        now = datetime.now(user_tz)
        parsed_dt = parse_datetime(
            fields.meeting_datetime_text,
            now=now,
            tz=user_tz,
        )

        if not parsed_dt:
            logger.info(
                "Date parsing failed for text: %s",
                fields.meeting_datetime_text,
            )
        else:
            validated_dt = validate_meeting_datetime(parsed_dt, now=now)

            if validated_dt:
                meeting_datetime = validated_dt
            else:
                logger.info(
                    "Parsed datetime failed validation: %s",
                    parsed_dt,
                )

    # ---------------- Defensive state updates ---------------- #
    if name and not state.name:
        state.name = name
        logger.info("Updated state.name to: %s", name)

    if meeting_datetime and not state.meeting_datetime:
        state.meeting_datetime = meeting_datetime
        logger.info("Updated state.meeting_datetime to: %s", meeting_datetime)

    if title and not state.meeting_title:
        state.meeting_title = title
        logger.info("Updated state.meeting_title to: %s", title)

    return state
