import os
import time

from dotenv import load_dotenv
from google import genai

from schemas import EmailRouterSchema

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def classify_email(subject: str, body: str) -> EmailRouterSchema:

    prompt = f"""
You are an email routing classifier for a shipping company.

Classify the email into exactly ONE category:

BL_COMPARISON
- Comparing a Bill of Lading (BL) with a Shipping Instruction (SI)
- Checking discrepancies between shipping documents

SI_REQUEST
- Requesting, creating, changing, or updating a Shipping Instruction

INVOICE_QUERY
- Questions about invoices, billing, charges, payments, or invoice status

GENERAL
- Normal business email that does not match the above

SPAM
- Unwanted, irrelevant, suspicious, or promotional email

Email subject:
{subject}

Email body:
{body}

Return the category and a one-sentence reasoning.
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": EmailRouterSchema,
                },
            )

            return response.parsed

        except Exception as exc:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                raise exc