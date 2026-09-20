import os
import asyncio
import uuid
from typing import Any
from supabase import create_client
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class DBManager:
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY in environment.")

        self.client = create_client(url, key)
        self.bucket = os.getenv("SUPABASE_ATTACHMENTS_BUCKET")

    def download_sync(self, bucket: str, filepath: str) -> bytes:
        """Synchronous call to Supabase storage."""
        return self.client.storage.from_(bucket).download(filepath)

    async def download_file_bytes(self, bucket: str, filepath: str) -> bytes:
        """
        Asynchronously downloads a file from Supabase storage into memory.
        """
        try:
            # Offloads the blocking network call to a background thread
            file_bytes = await asyncio.to_thread(self.download_sync, bucket, filepath)
            return file_bytes

        except Exception as e:
            logging.error(f"Failed to download {filepath} from {bucket}: {e}")
            raise

    async def save_email(self, email_data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_email_sync, email_data)

    async def is_sender_blacklisted(self, sender_email: str) -> bool:
        reputation = await self.get_sender_reputation(sender_email)
        return bool(reputation.get("is_blacklisted"))

    async def get_sender_reputation(self, sender_email: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_sender_reputation_sync, sender_email)

    def _get_sender_reputation_sync(self, sender_email: str) -> dict[str, Any]:
        result = (
            self.client.table("sender_reputation")
            .select("spam_count, is_blacklisted, blacklist_reason")
            .eq("sender_email", sender_email.lower())
            .maybe_single()
            .execute()
        )
        return result.data or {}

    async def record_spam_decision(self, spam_data: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._record_spam_decision_sync, spam_data)

    def _record_spam_decision_sync(self, spam_data: dict[str, Any]) -> dict[str, Any]:
        sender_email = spam_data["from_email"].lower()
        current = (
            self.client.table("sender_reputation")
            .select("spam_count, is_blacklisted")
            .eq("sender_email", sender_email)
            .maybe_single()
            .execute()
        ).data or {}
        spam_count = int(current.get("spam_count") or 0) + 1
        threshold = int(spam_data.get("blacklist_threshold") or 3)
        is_blacklisted = bool(current.get("is_blacklisted")) or spam_count >= threshold
        row = {
            "sender_email": sender_email,
            "sender_name": spam_data.get("from_name") or None,
            "spam_count": spam_count,
            "is_blacklisted": is_blacklisted,
            "last_spam_at": spam_data.get("received_at"),
            "last_spam_reason": spam_data.get("spam_reason"),
            "last_spam_score": spam_data.get("spam_score"),
            "blacklist_reason": (
                f"Automatically blacklisted after {spam_count} spam messages"
                if is_blacklisted else None
            ),
        }
        self.client.table("sender_reputation").upsert(row, on_conflict="sender_email").execute()
        return {"spam_count": spam_count, "is_blacklisted": is_blacklisted}

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