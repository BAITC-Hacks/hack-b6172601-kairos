"""Assistant graph tools are deterministic and need no API key."""
from app.agent.registry import REGISTRY
from app.tools import graph


def test_tools_registered():
    for name in ("get_account", "top_accounts", "who_collects_from", "money_paths", "cluster_summary"):
        assert REGISTRY.get(name) is not None


def test_get_account_by_suffix_and_unknown():
    top = graph.top_accounts(limit=1)["accounts"][0]["gid"]
    card = graph.get_account(top[-6:])
    assert card["gid"] == top and card["incoming_count"] >= 1
    assert "error" in graph.get_account("000000000000")


def test_who_collects_from_and_paths():
    top = graph.top_accounts(limit=1)["accounts"][0]["gid"]
    payers = [row["gid"] for row in graph.get_account(top)["incoming_top"][:3]]
    result = graph.who_collects_from(payers, 1)
    assert any(item["gid"] == top for item in result["collectors"])
    paths = graph.money_paths(payers[0], top)["paths"]
    assert paths and paths[0]["steps"][-1]["to"] == top
