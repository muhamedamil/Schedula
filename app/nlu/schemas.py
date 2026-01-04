from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExtractionFields(BaseModel):
    name: Optional[str] = Field(
        default=None, description="Person's full name if mentioned"
    )
    meeting_datetime_text: Optional[str] = None

    meeting_title: Optional[str] = Field(
        default=None, description="Optional meeting title"
    )

    confirmation_status: Optional[str] = Field(
        default=None,
        description="User confirmation intent: 'yes', 'no', 'uncertain' or null",
    )
