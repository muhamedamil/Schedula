# Voice-Activated Scheduling Assistant

An intelligent, real-time voice agent that makes scheduling meetings effortless. Using natural conversation, this assistant listens, understands, and creates calendar events directly in Google Calendar. It’s built for speed, multi-user support, and seamless real-time interaction.

---

## Why a Custom-Built Solution?

While many “Voice as a Service” platforms exist (like VAPI, Retell, or ElevenLabs Realtime), I wanted to build a solution from the ground up.

This decision was driven by a commitment to gain more in depth knowledge. By constructing the Speech-to-Text (STT) pipeline, the Text-to-Speech (TTS) engine, and the WebSocket orchestration manually, I was able to:
- Gain a deep understanding of low-latency audio processing.
- Implement a highly customized, secure OAuth 2.0 flow for Google Calendar.
- Create a lightweight, portable architecture without vendor lock-in.
- Leverage **LangGraph** for granular control over the conversational state machine.

---

## Experience the Live Agent

**Deployed URL:** [https://05c0775ce34e.ngrok-free.app/]

**Sample Workflow:** [https://drive.google.com/file/d/14cW0vytOUcGlRqboeaosNfORdlMnmJ8H/view?usp=sharing]

> [!IMPORTANT]
> To test the calendar integration, please **Sign In** with your Google account on the landing page. The agent will then be authorized to create events directly on your personal primary calendar.

---

## Key Features

- **Real-Time Voice Interaction**: It Communicates instantly using WebSockets for speech recognition (STT) and speech synthesis (TTS).
- **Natural Language Understanding**: It Uses LLMs (Groq/OpenAI) to extract dates, times, and meeting topics from casual conversation.
- **Multi-User Google Calendar Support**: Implements OAuth 2.0 and OpenID Connect to securely verify users and manage their individual calendars.
- **Robust Workflow Management**: Orchestrated by **LangGraph**, ensuring a reliable state machine for conversational flow and data validation.
- **Premium Voice Quality**: Integrated with the **Kokoro TTS** model for human-like, expressive responses.

---

## Technical Architecture & Design Philosophy

The project is structured for performance and clarity:

1. **Frontend (HTML5/Vanilla JS)**: Captures audio from the microphone, handles Google OAuth, and communicates with the backend through a persistent WebSocket for instant feedback.
2. **Backend (FastAPI)**: Asynchronous Python service that coordinates between various AI models and the Google API.
3. **Brain (LangGraph & LLM)**: The conversation logic is a directed graph. It doesn't just "chat"; it follows a logical flow (Identify User -> Extract DateTime -> Clarify Topic -> Confirm -> Execute).
### 📅 How it connects to your Google Calendar

Think of the assistant as a polite helper who only asks for a "temporary key" to your calendar's front door.

- **No Passwords Stored**: We never see or save your Google password. We use a secure, one-time "handshake" (OAuth 2.0) that you control.
- **Respecting Your Privacy**: The assistant only asks for permission to manage your events. It doesn't read your emails or access your personal files.
- **Total Privacy**: Each conversation is strictly private. The assistant uses your unique secure token to make sure it's talking to *your* calendar and no one else's.
- **You're in Control**: You can revoke access at any time through your Google Account settings.

####  Under the Hood (The Technical Bit)

For those interested in how the gears turn, here is the flow:

1.  **Identity Initiation**: The frontend uses the **Google Identity Services (GSI)** client to request an `access_token` with the `calendar.events` scope.
2.  **Secure Handshake**: This token is passed to the backend during the WebSocket connection. The server immediately validates it by calling the Google `userinfo` endpoint.
3.  **Stateless Security**: No user credentials or tokens are stored in a database. Everything is held in memory for the duration of the session, following the "security by design" principle.
4.  **API Execution**: When you confirm a meeting, the backend uses the **Google API Client Library** to securely push the event to your `primary` calendar.

---


---

## Testing the Agent

1. **Authenticate**: Click the **Sign In with Google** button.
2. **Initiate**: Click the **Microphone** icon.
3. **Converse**: Say something like: *"I want to schedule a lunch with Mark tomorrow at 1:30 PM."*
4. **Confirm**: The agent will repeat the details. Say *"Yes"* to confirm.
5. **Verify**: Check your [Google Calendar](https://calendar.google.com). A new event will appear with the specified details.

---

---
## Notes on Performance & Latency

The Voice Scheduling Assistant relies on real-time TTS (Text-to-Speech) and STT (Speech-to-Text) processing, which are computed locally on the server. Since the current EC2 instance used for hosting is not a high-end machine, you may notice slight latency when interacting with the assistant.

This delay occurs because the models (Kokoro TTS and Whisper STT) perform intensive computations using the system’s CPU/GPU resources. The latency can be significantly reduced by:
   - Hosting on a more powerful machine with better CPU/GPU specs.
   - Using cloud-based APIs for STT/TTS, which offload the computation externally.

Note: In this project, API-based STT/TTS was deliberately avoided to reduce costs and ensure full control over the voice pipeline.

---

## How to Run Locally

### Prerequisites

- Python 3.10+
- FFmpeg (for audio processing)
- Google Cloud Console Project with Calendar API enabled.

### Setup Steps

1. **Clone the project:**
   ```bash
   git clone [https://github.com/muhamedamil/Schedula]
   cd Voice_scheduling_agent
   ```

2. **Install dependencies:**
   ```bash
   python -m venv myenv
   source myenv/Scripts/activate  
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


## Assessment Submission Details

- **Developer**: [Muhammed Amil]
- **Key Challenge Overcome**: Implemented a secure, real-time WebSocket authentication flow that bridges the frontend OAuth layer with the backend service runner without storing sensitive user data. During this process, I also navigated the challenges of hosting the application on AWS, which helped me gain hands-on experience with EC2, systemd services, Nginx, and networking configurations. Additionally, I explored new capabilities in LangGraph, improving how the conversational state machine manages multi-step dialogues and real-time user interactions.

---

