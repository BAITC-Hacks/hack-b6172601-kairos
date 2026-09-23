"""Read-only account browsing uses the generated analysis artifacts."""

import csv
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import viewer
from app.main import app
from pipeline.config import CONFIG, ROLE_WEIGHTS


OUTPUT = Path(__file__).resolve().parents[1] / "out"
CLIENT = TestClient(app)
FLAGS = ("common_counterparty", "synchronous_inflow", "scatter_gather",
         "likely_legit_payouts", "extension_requests")


def metric_rows():
    with (OUTPUT / "metrics.csv").open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def expected(rows, *, role=None, flag=None):
    if role is not None:
        selected = [row for row in rows if row["role"] == role]
    elif flag == "extension_requests":
        selected = [row for row in rows if row["truncated"] == "True" and row["p_continues"]
                    and float(row["p_continues"]) >= CONFIG.extension_min_probability]
    else:
        selected = [row for row in rows if row[flag] == "True"]
    return sorted(selected, key=lambda row: (-float(row["priority_score"]), row["gid"]))


def test_role_account_lists_match_artifact_and_sort_ties_by_gid():
    rows = metric_rows()
    for role in ROLE_WEIGHTS:
        response = CLIENT.get("/api/accounts", params={"role": role})
        assert response.status_code == 200
        listed = response.json()
        source = expected(rows, role=role)
        assert len(listed) == len(source)
        assert [item["gid"] for item in listed] == [row["gid"] for row in source]
        assert all(set(item) == {"gid", "role", "priority_score", "findings"} for item in listed)
        assert all(isinstance(item["gid"], str) and item["role"] == role for item in listed)
        assert [item["findings"] for item in listed] == [row["findings"] for row in source]


def test_flag_account_lists_match_artifact():
    rows = metric_rows()
    for flag in FLAGS:
        response = CLIENT.get("/api/accounts", params={"flag": flag})
        assert response.status_code == 200
        listed = response.json()
        source = expected(rows, flag=flag)
        assert [item["gid"] for item in listed] == [row["gid"] for row in source]
        assert all(item["role"] == row["role"] for item, row in zip(listed, source))
    assert len(CLIENT.get("/api/accounts", params={"flag": "extension_requests"}).json()) == 10


def test_extension_filter_rejects_missing_and_unknown_probabilities(monkeypatch):
    monkeypatch.setattr(viewer, "snapshot", lambda: {"nodes": {
        "1": {"gid": "1", "role": "peripheral", "priority_score": 0.5,
              "truncated": True, "findings": "", "p_continues": None},
        "2": {"gid": "2", "role": "peripheral", "priority_score": 0.4,
              "truncated": True, "findings": ""},
        "3": {"gid": "3", "role": "peripheral", "priority_score": 0.3,
              "truncated": True, "findings": "", "p_continues": CONFIG.extension_min_probability},
        "4": {"gid": "4", "role": "peripheral", "priority_score": 0.2,
              "truncated": False, "findings": "", "p_continues": 1.0},
    }})
    response = CLIENT.get("/api/accounts", params={"flag": "extension_requests"})
    assert response.status_code == 200
    assert [row["gid"] for row in response.json()] == ["3"]


def test_account_filter_requires_exactly_one_known_choice():
    for params in ({}, {"role": ""}, {"flag": ""}, {"role": "unknown"},
                   {"flag": "unknown"}, {"role": "coordinator", "flag": "scatter_gather"}):
        response = CLIENT.get("/api/accounts", params=params)
        assert response.status_code == 400
        assert "error" in response.json()
