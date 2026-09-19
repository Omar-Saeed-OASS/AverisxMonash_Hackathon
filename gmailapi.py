import asyncio
import base64
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
ATTACHMENTS_DIR = Path(os.getenv("ATTACHMENTS_DIR", "BL&SI"))
PROCESSED_FILE = Path(os.getenv("PROCESSED_FILE", "processed_emails.json"))
GMAIL_QUERY = os.getenv("GMAIL_QUERY", "category:primary")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "30"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "10"))


def get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def load_processed_ids() -> set[str]:
    if not PROCESSED_FILE.exists():
        return set()

    with PROCESSED_FILE.open("r", encoding="utf-8") as f:
        return set(json.load(f))


def save_processed_ids(processed_ids: set[str]) -> None:
    with PROCESSED_FILE.open("w", encoding="utf-8") as f:
        json.dump(sorted(processed_ids), f, indent=2)


def decode_body(data: str) -> str:
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


def get_message_body(payload: dict[str, Any]) -> str:
    """Extract the plain text body, handling multipart messages."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return decode_body(data)
            elif "parts" in part:
                result = get_message_body(part)
                if result:
                    return result
    else:
        data = payload.get("body", {}).get("data")
        if data:
            return decode_body(data)

    return ""


def extract_attachments(service, msg_id: str, payload: dict[str, Any], email_index: int) -> list[str]:
    """Download attachment parts to disk and return their paths."""
    saved_paths = []
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

    def walk_parts(parts):
        for part in parts:
            filename = part.get("filename")
            body = part.get("body", {})

            if filename and body.get("attachmentId"):
                att_id = body["attachmentId"]
                att = service.users().messages().attachments().get(
                    userId="me", messageId=msg_id, id=att_id
                ).execute()
                file_data = base64.urlsafe_b64decode(att["data"])

                safe_name = f"email_{email_index:03d}_{filename}"
                file_path = ATTACHMENTS_DIR / safe_name
                with file_path.open("wb") as f:
                    f.write(file_data)
                saved_paths.append(str(file_path))

            if "parts" in part:
                walk_parts(part["parts"])

    if "parts" in payload:
        walk_parts(payload["parts"])

    return saved_paths


def get_message(service, msg_id: str, email_index: int) -> dict[str, Any]:
    full = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}

    return {
        "gmail_message_id": msg_id,
        "email_id": f"email_{email_index:03d}",
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", ""),
        "body": get_message_body(full["payload"]),
        "attachments": extract_attachments(service, msg_id, full["payload"], email_index),
    }


def list_messages(service, query: str = "", max_results: int = 10) -> list[dict[str, str]]:
    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    return results.get("messages", [])


def handle_email(email_data: dict[str, Any]) -> None:
    """
    This function is called automatically for every new email found by the app.
    Put your processing logic here, such as reading Excel attachments or calling AI.
    """
    print(
        f"New email: {email_data['subject']} from {email_data['from']} "
        f"with {len(email_data['attachments'])} attachment(s)"
    )


async def check_for_new_emails() -> list[dict[str, Any]]:
    service = get_service()
    processed_ids = load_processed_ids()
    messages = list_messages(service, query=GMAIL_QUERY, max_results=MAX_RESULTS)
    new_emails = []

    for index, message in enumerate(messages, start=len(processed_ids) + 1):
        msg_id = message["id"]
        if msg_id in processed_ids:
            continue

        email_data = get_message(service, msg_id, index)
        handle_email(email_data)
        processed_ids.add(msg_id)
        new_emails.append(email_data)

    if new_emails:
        save_processed_ids(processed_ids)

    return new_emails


async def email_polling_loop() -> None:
    while True:
        try:
            print("Checking Gmail for new emails...", flush=True)
            new_emails = await check_for_new_emails()
            print(f"Gmail check complete: {len(new_emails)} new email(s)", flush=True)
        except Exception as exc:
            print(f"Email polling failed: {exc}", flush=True)

        await asyncio.sleep(POLL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(email_polling_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Gmail Email Listener", lifespan=lifespan)


@app.get("/")
def root():
    return {
        "status": "running",
        "gmail_query": GMAIL_QUERY,
        "poll_seconds": POLL_SECONDS,
    }


@app.post("/check-now")
async def check_now():
    new_emails = await check_for_new_emails()
    return {"new_email_count": len(new_emails), "emails": new_emails}


@app.get("/health")
def health():
    return {"status": "ok"}
