from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExtractionFields(BaseModel):
    name : Optional[str] = Field(
        default= None,
        description= "Person's full name if mentioned"
    )
    meeting_datetime : Optional[datetime] = Field(
        default= None,
        description= "Meeting date and time in ISO format"
    )
    meeting_title : Optional[str] = Field(
        default= None,
        description= "Optional meeting title"
    )

