import os
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
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

    async def list_emails(self, limit: int = 100) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_emails_sync, limit)

    def _list_emails_sync(self, limit: int) -> list[dict[str, Any]]:
        result = (
            self.client.table("emails")
            .select("*")
            .order("received_at", desc=True)
            .limit(max(1, min(limit, 500)))
            .execute()
        )
        return result.data or []

    async def get_email(self, email_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_email_sync, email_id)

    def _get_email_sync(self, email_id: str) -> dict[str, Any] | None:
        # email_id is not guaranteed unique (repeated test sends can insert
        # duplicates), so take the most recent row instead of maybe_single(),
        # which raises when more than one row matches.
        result = (
            self.client.table("emails")
            .select("*")
            .eq("email_id", email_id)
            .order("received_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        row = rows[0] if rows else None
        if not row:
            # The dashboard falls back to the row's UUID `id` when email_id is
            # blank, so accept that as a lookup key too. A non-UUID value here
            # (the common case: a real email_id with no match) raises at the
            # DB level rather than returning an empty result, so treat that
            # the same as "not found".
            try:
                by_uuid = (
                    self.client.table("emails")
                    .select("*")
                    .eq("id", email_id)
                    .limit(1)
                    .execute()
                )
                uuid_rows = by_uuid.data or []
            except Exception:
                uuid_rows = []
            row = uuid_rows[0] if uuid_rows else None
        if not row:
            return None

        attachments = (
            self.client.table("attachments")
            .select("*")
            .eq("email_id", row["id"])
            .execute()
        )
        row["attachment_records"] = attachments.data or []
        return row

    async def upload_attachments(self, email_data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._upload_attachments_sync, email_data)

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
        return (result.data if result is not None else None) or {}

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
        )
        current = (current.data if current is not None else None) or {}
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
        attachment_uuid = attachments[0].get("attachment_record_id") if attachments else None
        if attachments and not all(attachment.get("storage_path") for attachment in attachments):
            self._upload_attachments_sync(email_data)
            attachment_uuid = attachments[0]["attachment_record_id"]

        metadata = {
            "routing_reasoning": email_data.get("routing_reasoning", ""),
        }
        if email_data.get("category") == "SPAM":
            metadata.update(
                {
                    key: email_data[key]
                    for key in (
                        "spam_score", "is_spam", "spam_reasons", "risk_signals",
                        "recommended_action", "spam_reason", "confidence",
                        "spam_count", "is_blacklisted", "blacklist_status", "spam_action",
                    )
                    if key in email_data
                }
            )
        else:
            metadata.update(
                {
                    key: email_data[key]
                    for key in (
                        "summary", "key_points", "action_items", "requires_response",
                        "suggested_reply", "confidence",
                    )
                    if key in email_data
                }
            )

        self.client.table("emails").insert(
            {
                "id": email_uuid,
                "email_id": email_data["email_id"],
                "sender": email_data["from_name"],
                "received_at": email_data["received_at"],
                "raw_payload": email_data["raw_payload"],
                "attached_docs": bool(attachments),
                "category": email_data.get("category"),
                "metadata": metadata,
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

    def _upload_attachments_sync(self, email_data: dict[str, Any]) -> None:
        attachments = email_data.get("attachments", [])
        if not attachments:
            return

        attachment_uuid = attachments[0].get("attachment_record_id") or str(uuid.uuid4())
        for attachment in attachments:
            clean_filename = Path(attachment["filename"]).name
            storage_path = f"{attachment_uuid}/{clean_filename}"
            if not attachment.get("storage_path"):
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

    async def record_human_decision(
        self, email_id: str, decision: str, note: str | None
    ) -> dict[str, Any]:
        """Persist an adjuster's approve/reject call on a flagged BL_COMPARISON email."""
        return await asyncio.to_thread(
            self._record_human_decision_sync, email_id, decision, note
        )

    def _record_human_decision_sync(
        self, email_id: str, decision: str, note: str | None
    ) -> dict[str, Any]:
        # email_id is not guaranteed unique, so resolve to the most recent
        # matching row's primary key and update that exact row only.
        current = (
            self.client.table("emails")
            .select("id, metadata")
            .eq("email_id", email_id)
            .order("received_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = current.data or []
        if not rows:
            return {}
        row = rows[0]

        current_metadata = dict(row.get("metadata") or {})
        current_metadata["human_review"] = {
            "decision": decision,
            "note": note,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }

        result = (
            self.client.table("emails")
            .update(
                {
                    "status": decision,
                    "metadata": current_metadata,
                    "updated_at": "now()",
                }
            )
            .eq("id", row["id"])
            .execute()
        )
        return result.data[0] if result.data else {}

    async def update_email_results(self, email_id: str, final_state: dict[str, Any]) -> None:
        """Persist the comparison result on the existing email row."""
        await asyncio.to_thread(self.update_email_results_sync, email_id, final_state)

    def update_email_results_sync(self, email_id: str, state: dict[str, Any]) -> None:
        update_data = {
            "status": state.get("status"),
            "has_defect": state.get("has_defect"),
            "defect_fields": state.get("defect_fields"),
            "review_reason": state.get("review_reason"),
            "si_extracted": state.get("si_extracted"),
            "bl_extracted": state.get("bl_extracted"),
            "enterprise_risk_report": state.get("enterprise_risk_report"),
            "updated_at": "now()",
        }
        update_data = {
            key: value for key, value in update_data.items() if value is not None
        }

        if "discrepancy_details" in state:
            update_data["metadata"] = {
                "discrepancy_details": state.get("discrepancy_details")
            }

        try:
            self.client.table("emails").update(update_data).eq(
                "email_id", email_id
            ).execute()
        except Exception:
            logger.exception("Failed to update database for email %s", email_id)
            raise