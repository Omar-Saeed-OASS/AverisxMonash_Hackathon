import asyncio
import uuid
from typing import Any

from supabase import create_client


class DBManager:
    def __init__(self, url: str | None, key: str | None, bucket: str) -> None:
        if not url or not key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY in environment.")

        self.client = create_client(url, key)
        self.bucket = bucket

    async def save_email(self, email_data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_email_sync, email_data)

    def _save_email_sync(self, email_data: dict[str, Any]) -> None:
        email_uuid = str(uuid.uuid4())
        attachments = email_data["attachments"]
        attachment_uuid = str(uuid.uuid4()) if attachments else None

        for attachment in attachments:
            storage_path = f"{attachment_uuid}/{attachment['filename']}"
            self.client.storage.from_(self.bucket).upload(
                storage_path,
                attachment["content"],
                {
                    "content-type": attachment["content_type"],
                    "x-upsert": "true",
                },
            )
            attachment["attachment_record_id"] = attachment_uuid
            attachment["storage_path"] = storage_path

        self.client.table("emails").insert(
            {
                "id": email_uuid,
                "email_id": email_data["from_email"],
                "sender": email_data["from_name"],
                "received_at": email_data["received_at"],
                "raw_payload": email_data["raw_payload"],
                "attached_docs": bool(attachments),
            }
        ).execute()

        if not attachments:
            return

        self.client.table("attachments").insert(
            {
                "id": attachment_uuid,
                "email_id": email_uuid,
                "doc_type": [attachment["doc_type"] for attachment in attachments],
                "storage_path": [attachment["storage_path"] for attachment in attachments],
                "file_format": [attachment["file_format"] for attachment in attachments],
                "is_corrupted": any(
                    attachment.get("validation_status") != "valid"
                    for attachment in attachments
                ),
            }
        ).execute()