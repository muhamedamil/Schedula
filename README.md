# Voice-Activated Scheduling Assistant

An intelligent, real-time voice agent designed to streamline meeting scheduling via natural conversation. Built with a modern AI stack, the assistant handles speech recognition, intent extraction, and direct Google Calendar integration with a focus on speed and seamless multi-user authentication.

---

## Why a Custom-Built Solution?

While modern "Voice-as-a-Service" platforms (like VAPI, Retell, or ElevenLabs Realtime) offer excellent high-level abstractions, I chose to build this agent **entirely from scratch**.

This decision was driven by a commitment to technical mastery. By constructing the Speech-to-Text (STT) pipeline, the Text-to-Speech (TTS) engine, and the WebSocket orchestration manually, I was able to:
- Gain a deep understanding of low-latency audio processing.
- Implement a highly customized, secure OAuth 2.0 flow for Google Calendar.
- Create a lightweight, portable architecture without vendor lock-in.
- Leverage **LangGraph** for granular control over the conversational state machine.

---

## Experience the Live Agent

**Deployed URL:** []

> [!IMPORTANT]
> To test the calendar integration, please **Sign In** with your Google account on the landing page. The agent will then be authorized to create events directly on your personal primary calendar.

---

## Key Features

- **Real-Time Voice Interaction**: Powered by WebSockets for instantaneous Speech-to-Text (STT) and Text-to-Speech (TTS) feedback.
- **Natural Language Understanding**: Uses LLMs (Groq/OpenAI) to extract dates, times, and meeting topics from casual conversation.
- **Multi-User Google Calendar Support**: Implements OAuth 2.0 and OpenID Connect to securely verify users and manage their individual calendars.
- **Robust Workflow Management**: Orchestrated by **LangGraph**, ensuring a reliable state machine for conversational flow and data validation.
- **Premium Voice Quality**: Integrated with the **Kokoro TTS** model for human-like, expressive responses.

---

## Technical Architecture & Design Philosophy

The project is architected as a high-performance voice-first application:

1. **Frontend (HTML5/Vanilla JS)**: Captures audio via MediaRecorder API and manages the Google Identity Services (GIS) flow. It communicates with the backend via a persistent WebSocket for low-latency feedback.
2. **Backend (FastAPI)**: Asynchronous Python service that coordinates between various AI models and the Google API.
3. **Brain (LangGraph & LLM)**: The conversation logic is a directed graph. It doesn't just "chat"; it follows a logical flow (Identify User -> Extract DateTime -> Clarify Topic -> Confirm -> Execute).
4. **Calendar Integration**:
   - **Secure Token Exchange**: Instead of storing sensitive user credentials, the app uses a temporary access token provided by the frontend during the OAuth handshake.
   - **Permission Scoping**: Operates on a "least privilege" principle, requesting only `calendar.events` scope.
   - **Multi-Tenant Ready**: The backend identifies the user via their token in the WebSocket connection, allowing unique sessions for every logged-in user simultaneously.

---

## How to Run Locally

### Prerequisites

- Python 3.10+
- FFmpeg (for audio processing)
- Google Cloud Console Project with Calendar API enabled.

### Setup Steps

1. **Clone the project:**
   ```bash
   git clone [repository-url]
   cd Voice_scheduling_agent
   ```

2. **Install dependencies:**
   ```bash
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory (refer to `.env.example`):
   ```env
   GROQ_API_KEY=your_key
   GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
   # Optional fallback credentials
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REFRESH_TOKEN=...
   ```

4. **Start the server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8888
   ```

5. **Launch the UI:** Open `http://localhost:8888` in Chrome.

### Running with Docker

For a consistent environment:

```bash
docker-compose up --build
```

---

## Testing the Agent

1. **Authenticate**: Click the **Sign In with Google** button.
2. **Initiate**: Click the **Microphone** icon.
3. **Converse**: Say something like: *"I want to schedule a lunch with Mark tomorrow at 1:30 PM."*
4. **Confirm**: The agent will repeat the details. Say *"Yes"* to confirm.
5. **Verify**: Check your [Google Calendar](https://calendar.google.com). A new event will appear with the specified details.

---

## Sample Logs & Verification

Below is a trace of a successful event creation from the server logs:

```text
2026-01-04 22:55 | INFO | Authenticated as: Mohamed
2026-01-04 22:56 | INFO | Extracted Intent: Create Event
2026-01-04 22:56 | INFO | Details: Title='Lunch', Date='2026-01-05', Time='13:30'
2026-01-04 22:57 | INFO | Creating calendar event: title=Lunch start=2026-01-05T13:30:00
2026-01-04 22:57 | INFO | Calendar event created successfully (event_id=xyz123)
```

---

## Assessment Submission Details

- **Developer**: [Muhammed Amil]
- **Key Challenge Overcome**: Implementing a secure, real-time WebSocket authentication flow that bridges the frontend OAuth layer with a backend service runner without persisting sensitive user data.

---

*Developed for Assessment Purpose*
