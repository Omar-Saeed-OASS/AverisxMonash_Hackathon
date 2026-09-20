import asyncio

from workflows.spam_subgraph.spam_graph import spam_graph


DUMMY_SPAM_EMAIL = {
    "email_id": "email_spam_001",
    "from_name": "Account Security Team",
    "from_email": "security@example.test",
    "received_at": "2026-09-20T05:00:00+00:00",
    "subject": "URGENT: Verify your account now",
    "body": (
        "Your account will be suspended today. Click here to verify your password "
        "and send an urgent payment to keep access."
    ),
    "attachments": [],
    "spam_count": 1,
    "blacklist_threshold": 3,
}


def test_spam_graph():
    result = asyncio.run(spam_graph.ainvoke(DUMMY_SPAM_EMAIL))

    assert 0 <= result["spam_score"] <= 1
    assert isinstance(result["spam_reasons"], str)
    assert isinstance(result["risk_signals"], str)
    assert result["recommended_action"] in {"allow", "review", "reject"}
    assert result["is_spam"] is True
    assert result["spam_count"] == 2
    assert result["is_blacklisted"] is False
    assert "2/3" in result["blacklist_status"]


if __name__ == "__main__":
    result = asyncio.run(spam_graph.ainvoke(DUMMY_SPAM_EMAIL))
    print(result["display_text"])