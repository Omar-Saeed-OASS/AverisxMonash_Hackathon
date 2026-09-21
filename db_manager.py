import asyncio
import uuid
from typing import Any

from supabase import create_client


class DBManager:
    def __init__(self, url: str | None, key: str | None, bucket: str) -> None:
        if not url or not key:
            raise RuntimeError(
                "Missing SUPABASE_URL or SUPABASE_SECRET_KEY in environment."
            )

        self.client = create_client(url, key)
        self.bucket = bucket

    async def save_email(self, email_data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_email_sync, email_data)

    def _save_email_sync(self, email_data: dict[str, Any]) -> None:
        email_uuid = str(uuid.uuid4())
        attachment_uuid = (
            str(uuid.uuid4()) if email_data["attachments"] else None
        )

        # Upload attachments
        for attachment in email_data["attachments"]:
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

        # Save email
        self.client.table("emails").insert(
            {
                "id": email_uuid,
                "email_id": email_data["email_id"],
                "sender": email_data["from_name"],
                "received_at": email_data["received_at"],
                "raw_payload": email_data["raw_payload"],
                "attached_docs": len(email_data["attachments"]) > 0,

                # AI routing
                "category": email_data.get("category"),

                # Existing metadata column
                "metadata": {
                    "routing_reasoning": email_data.get("reasoning")
                },
            }
        ).execute()

        # No attachments → stop here
        if not email_data["attachments"]:
            return

        # Save attachment metadata
        self.client.table("emails").insert(
    {
        "id": email_uuid,
        "email_id": email_data["from_email"],
        "sender": email_data["from_name"],
        "received_at": email_data["received_at"],
        "raw_payload": email_data["raw_payload"],
        "attached_docs": len(email_data["attachments"]) > 0,
        "category": email_data.get("category"),
        "metadata": {
            "routing_reasoning": email_data.get("reasoning")
        },
    }
).execute()