from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

ConversationStep = Literal[
    "START",
    "ASK_NAME",
    "ASK_DATETIME",
    "ASK_TITLE",
    "CONFIRM_DETAILS",
    "AWAIT_CONFIRMATION",
    "ASK_ANOTHER",
    "HANDLE_NEW_LOOP",
    "END",
]


class ConversationState(BaseModel):
    """
    Authoritative source of truth for the conversation.
    This is what drives the workflow not the LLM.
    """

    step: str = "START"
    timezone: Optional[str] = "Asia/Kolkata"

    # Collected slots
    name: Optional[str] = None
    meeting_datetime: Optional[datetime] = None
    meeting_title: Optional[str] = None

    # IO fields
    last_user_message: Optional[str] = Field(
        default=None, description="Raw user input from the last turn"
    )

    system_message: Optional[str] = Field(
        default=None, description="What the system wants to say next"
    )

    is_confirmed: Optional[bool] = False
    confirmation_status: Optional[Literal["yes", "no", "uncertain"]] = None
