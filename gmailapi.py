import asyncio
import base64
import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from db_manager import DBManager


load_dotenv()


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
ATTACHMENTS_DIR = Path(os.getenv("ATTACHMENTS_DIR", "BL&SI"))
PROCESSED_FILE = Path(os.getenv("PROCESSED_FILE", "processed_emails.json"))
GMAIL_QUERY = os.getenv("GMAIL_QUERY", "category:primary is:unread")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "10"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))
APP_STARTED_AT_MS = int(time.time() * 1000)
EMAIL_SEQUENCE = 0
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "documents")


DB_MANAGER: DBManager | None = None


def get_db_manager() -> DBManager:
    global DB_MANAGER

    if DB_MANAGER is None:
        DB_MANAGER = DBManager(SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET)

    return DB_MANAGER


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
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PROCESSED_FILE.open("w", encoding="utf-8") as f:
        json.dump(sorted(processed_ids), f, indent=2)


async def load_processed_ids_async() -> set[str]:
    return await asyncio.to_thread(load_processed_ids)


async def save_processed_ids_async(processed_ids: set[str]) -> None:
    await asyncio.to_thread(save_processed_ids, processed_ids)


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


def guess_doc_type(filename: str) -> str | None:
    name = filename.lower()
    if "si" in name:
        return "SI"
    if "bl" in name or "b/l" in name:
        return "BL"
    return "Unknown"


def extract_attachments(service, msg_id: str, payload: dict[str, Any], email_index: int) -> list[dict[str, Any]]:
    """Download attachment parts to disk and return metadata plus file bytes."""
    attachments = []
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
                attachments.append(
                    {
                        "filename": filename,
                        "local_path": str(file_path),
                        "content": file_data,
                        "content_type": part.get("mimeType") or "application/octet-stream",
                        "file_format": Path(filename).suffix.lstrip(".").lower() or None,
                        "doc_type": guess_doc_type(filename),
                    }
                )

            if "parts" in part:
                walk_parts(part["parts"])

    if "parts" in payload:
        walk_parts(payload["parts"])

    return attachments


def get_message(service, msg_id: str, email_index: int) -> dict[str, Any]:
    full = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
    from_name, from_email = parseaddr(headers.get("From", ""))
    received_at = datetime.fromtimestamp(
        int(full.get("internalDate", "0")) / 1000,
        tz=timezone.utc,
    ).isoformat()

    return {
        "email_id": f"email_{email_index:03d}",
        "from_name": from_name,
        "from_email": from_email,
        "received_at": received_at,
        "subject": headers.get("Subject", ""),
        "body": get_message_body(full["payload"]),
        "raw_payload": full,
        "attachments": extract_attachments(service, msg_id, full["payload"], email_index),
    }


async def get_message_async(service, msg_id: str, email_index: int) -> dict[str, Any]:
    return await asyncio.to_thread(get_message, service, msg_id, email_index)


def serialize_email_for_output(email_data: dict[str, Any]) -> dict[str, Any]:
    output = {
        key: value
        for key, value in email_data.items()
        if key not in {"raw_payload", "attachments"}
    }
    if not email_data["attachments"]:
        output["attachment_record"] = None
        return output

    output["attachment_record"] = {
        "id": email_data["attachments"][0].get("attachment_record_id"),
        "doc_type": [attachment["doc_type"] for attachment in email_data["attachments"]],
        "storage_path": [attachment.get("storage_path") for attachment in email_data["attachments"]],
        "file_format": [attachment.get("file_format") for attachment in email_data["attachments"]],
        "files": [
            {
                "filename": attachment["filename"],
                "local_path": attachment["local_path"],
            }
            for attachment in email_data["attachments"]
        ],
    }
    return output


def list_messages(service, query: str = "", max_results: int = 5) -> list[dict[str, str]]:
    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    return results.get("messages", [])


async def list_messages_async(service, query: str = "", max_results: int = 5) -> list[dict[str, str]]:
    return await asyncio.to_thread(list_messages, service, query, max_results)


def get_message_internal_date(service, msg_id: str) -> int:
    metadata = service.users().messages().get(
        userId="me",
        id=msg_id,
        format="metadata",
        metadataHeaders=[],
    ).execute()
    return int(metadata.get("internalDate", "0"))


async def get_message_internal_date_async(service, msg_id: str) -> int:
    return await asyncio.to_thread(get_message_internal_date, service, msg_id)


async def handle_email(email_data: dict[str, Any]) -> None:
    """
    This function is called automatically for every new email found by the app.
    Put your processing logic here, such as reading Excel attachments or calling AI.
    """
    # Add your workflow here. The structured Docker log is printed after polling.
    pass


async def check_for_new_emails() -> list[dict[str, Any]]:
    global EMAIL_SEQUENCE

    service = await asyncio.to_thread(get_service)
    processed_ids = await load_processed_ids_async()
    messages = await list_messages_async(service, query=GMAIL_QUERY, max_results=MAX_RESULTS)
    new_emails = []
    processed_ids_changed = False

    for message in messages:
        msg_id = message["id"]
        if msg_id in processed_ids:
            continue

        if await get_message_internal_date_async(service, msg_id) <= APP_STARTED_AT_MS:
            processed_ids.add(msg_id)
            processed_ids_changed = True
            continue

        EMAIL_SEQUENCE += 1
        email_data = await get_message_async(service, msg_id, EMAIL_SEQUENCE)
        await handle_email(email_data)
        await get_db_manager().save_email(email_data)
        processed_ids.add(msg_id)
        processed_ids_changed = True
        new_emails.append(serialize_email_for_output(email_data))

    if processed_ids_changed:
        await save_processed_ids_async(processed_ids)

    return new_emails


async def email_polling_loop() -> None:
    while True:
        try:
            print("Checking Gmail for new emails...", flush=True)
            new_emails = await check_for_new_emails()
            if new_emails:
                print(json.dumps(new_emails, indent=2, ensure_ascii=False), flush=True)
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
