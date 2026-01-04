from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


flow = InstalledAppFlow.from_client_secrets_file(
    BASE_DIR / "client_secret.json",
    SCOPES,
)


flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",
    SCOPES,
)

creds = flow.run_local_server(
    port=0,
    access_type="offline",
    prompt="consent",
)

print("\n=== COPY THIS REFRESH TOKEN ===")
print(creds.refresh_token)
