import logging
from typing import Optional

from groq import AsyncGroq
from app.state import ConversationState
from app.config import settings

logger = logging.getLogger(__name__)


MODEL_NAME = settings.GROQ_MODEL_NAME

# Initialize Groq client
client = AsyncGroq(api_key=settings.GROQ_API_KEY)

# Main System Prompt
SYSTEM_PROMPT = """You are a helpful, professional, and friendly voice assistant for a scheduling agent. 
Your output will be spoken aloud, so it MUST be:
1. Concise (under 2 sentences).
2. Natural and conversational.
3. Polite but direct.
4. Free of any special characters or markdown (no * or #).

Your task is to generate the next response based on the "Current Goal" and "Context".
"""


async def generate_response(
    state: ConversationState, goal: str, context_note: Optional[str] = None
) -> str:
    """
    Generates a dynamic response using LLM based on conversation state and goal.

    Args:
        state: Current conversation state
        goal: What the response should achieve (e.g., "Ask for name")
        context_note: Optional extra context (e.g., "User provided invalid date")

    Returns:
        str: The generated response text
    """
    try:
        # Construct dynamic context
        user_msg = state.last_user_message or "(No message yet)"

        # Build prompt inputs
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
Current Goal: {goal}
Context Note: {context_note or "None"}

User's Name: {state.name or "Unknown"}
Meeting Title: {state.meeting_title or "Not set"}
Meeting Time: {state.meeting_datetime or "Not set"}

Last User Message: "{user_msg}"

Generate the response now:
""",
            },
        ]

        logger.info("[GENERATOR] Generating response for goal: '%s'", goal)

        # Call Groq
        chat_completion = await client.chat.completions.create(
            messages=messages,
            model=MODEL_NAME,  # Fast and cheap
            temperature=0.7,
            max_tokens=60,
        )

        response_text = chat_completion.choices[0].message.content.strip()

        # Clean up quotes if present
        if response_text.startswith('"') and response_text.endswith('"'):
            response_text = response_text[1:-1]

        logger.info("[GENERATOR] Generated: '%s'", response_text)
        return response_text

    except Exception as e:
        logger.error("[GENERATOR] Failed to generate response: %s", e)
        # Fallback to a safe static response if LLM fails
        return "I'm sorry, I process that. Could you please repeat?"
