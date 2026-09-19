Gmail FastAPI Email Listener
============================

What this does
--------------
This project runs as a FastAPI server instead of a one-time script.

When the server starts, it keeps checking Gmail in the background. When it finds a new email matching GMAIL_QUERY, it downloads attachments and automatically calls:

    handle_email(email_data)

Edit handle_email() in gmailapi.py to add your own logic.

Live-email behavior
-------------------
Every 10 seconds by default, the service checks Gmail using GMAIL_QUERY.

It only processes emails received after the FastAPI service starts running.

If no new email is found, the terminal prints:

    Checking Gmail for new emails...
    Gmail check complete: 0 new email(s)

Docker log output
-----------------
When a new email is found, the Docker output prints a JSON array using the same structure as the old gmailapi.py script:

    [
      {
        "email_id": "email_001",
        "from": "sender@example.com",
        "subject": "Example subject",
        "body": "Email body text...",
        "attachments": [
          "/app/data/BL&SI/email_001_file.xlsx"
        ]
      }
    ]

Important note about "automatic when email arrives"
---------------------------------------------------
There are two ways to do this:

1. Polling, which this project uses.
   The FastAPI app checks Gmail every POLL_SECONDS seconds. This is easiest for local development and Docker.

2. True Gmail push notifications.
   This requires Google Pub/Sub, a public HTTPS webhook URL, and Gmail API watch(). It is more production-like, but more setup.


Local setup
-----------
1. Install dependencies:

    pip install -r requirements.txt

2. Make sure credentials.json is in this folder.

3. Run once locally so Google OAuth can open your browser and create token.json:

    python -c "from gmailapi import get_service; get_service(); print('Gmail login OK')"

4. Start the FastAPI server:

    uvicorn gmailapi:app --host 0.0.0.0 --port 8000 --reload

5. Open:

    http://localhost:8000

6. To manually force a Gmail check:

    curl -X POST http://localhost:8000/check-now


Docker build
------------
Build the image:

    docker build -t gmail-fastapi-listener .


Docker run on PowerShell
------------------------
Run this from the project folder:

    docker run --rm -p 8000:8000 `
    -v "${PWD}\credentials.json:/app/secrets/credentials.json:ro" `
    -v "${PWD}\token.json:/app/secrets/token.json" `
    -v "${PWD}\docker-data:/app/data" `
    -e GMAIL_QUERY="category:primary is:unread" `
    -e POLL_SECONDS=10 `
    --name gmail-listener `
    gmail-fastapi-listener


Docker run on macOS/Linux
-------------------------
Run this from the project folder:

    docker run --rm -p 8000:8000 \
      -v "$PWD/credentials.json:/app/secrets/credentials.json:ro" \
      -v "$PWD/token.json:/app/secrets/token.json" \
      -v "$PWD/docker-data:/app/data" \
      -e GMAIL_QUERY="category:primary is:unread" \
      -e POLL_SECONDS=10 \
      --name gmail-listener \
      gmail-fastapi-listener


Environment variables
---------------------
GMAIL_CREDENTIALS_FILE
Default in Docker: /app/secrets/credentials.json

GMAIL_TOKEN_FILE
Default in Docker: /app/secrets/token.json

ATTACHMENTS_DIR
Default in Docker: /app/data/BL&SI

PROCESSED_FILE
Default in Docker: /app/data/processed_emails.json

GMAIL_QUERY
Default: category:primary is:unread

POLL_SECONDS
Default: 10

MAX_RESULTS
Default: 5


Useful endpoints
----------------
GET /
Shows service status.

GET /health
Health check endpoint for Docker or cloud hosting.

POST /check-now
Manually checks Gmail immediately.


Notes
-----
Do not commit credentials.json, token.json, .env, BL&SI, or processed_emails.json to Git.
