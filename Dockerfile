FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gmailapi.py .

ENV GMAIL_CREDENTIALS_FILE=/app/secrets/credentials.json
ENV GMAIL_TOKEN_FILE=/app/secrets/token.json
ENV ATTACHMENTS_DIR=/app/data/BL&SI
ENV PROCESSED_FILE=/app/data/processed_emails.json
ENV GMAIL_QUERY="category:primary is:unread"
ENV POLL_SECONDS=10
ENV MAX_RESULTS=5

EXPOSE 8000

CMD ["uvicorn", "gmailapi:app", "--host", "0.0.0.0", "--port", "8000"]
