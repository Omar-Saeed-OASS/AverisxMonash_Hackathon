import asyncio

from workflows.general_subgraph.general_graph import general_graph


DUMMY_EMAIL = {
    "email_id": "email_001",
    "from_name": "Remy Ong",
    "from_email": "remyongjingyi1233@gmail.com",
    "received_at": "2026-09-20T04:50:19+00:00",
    "subject": "Project update and review",
    "body": (
        "Hi team, the first draft of the project report is ready for review. "
        "Please confirm the figures and send your feedback by Friday. "
        "We will discuss the final changes in next week's meeting."
    )
}


def test_general_email_graph():
    result = asyncio.run(general_graph.ainvoke(DUMMY_EMAIL))

    assert result["category"] == "GENERAL"
    assert result["summary"]
    assert result["key_points"]
    assert result["action_items"]
    assert isinstance(result["summary"], str)
    assert isinstance(result["key_points"], str)
    assert isinstance(result["action_items"], str)
    assert result["requires_response"] == "Yes"
    assert result["word_count"] > 0
    assert result["from_email"] == DUMMY_EMAIL["from_email"]


if __name__ == "__main__":
    output = asyncio.run(general_graph.ainvoke(DUMMY_EMAIL))
    print(output["display_text"])