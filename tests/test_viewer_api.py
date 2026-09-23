"""Contract tests for the read-only analyst viewer API."""

import csv
import json
import os
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import viewer
from app.main import app


OUTPUT = Path(__file__).resolve().parents[1] / "out"
CLIENT = TestClient(app)
DOWNLOADS = ("nodes_roles.csv", "clusters.csv", "top_nodes.csv")


def top_gid() -> str:
    with (OUTPUT / "top_nodes.csv").open(newline="") as handle:
        return next(csv.DictReader(handle))["gid"]


def hits(payload):
    if isinstance(payload, list):
        return payload
    for key in ("results", "gids", "matches"):
        if key in payload:
            return payload[key]
    raise AssertionError(f"Unknown search response shape: {payload!r}")


def test_graph_contains_official_nodes_and_exact_string_ids():
    response = CLIENT.get("/api/graph")
    assert response.status_code == 200
    graph = response.json()
    assert len(graph["nodes"]) == 2248
    assert len(graph["edges"]) == 3119
    assert all(isinstance(node["id"], str) for node in graph["nodes"])
    assert all(isinstance(edge["source"], str) and isinstance(edge["target"], str)
               for edge in graph["edges"])
    assert top_gid() in {node["id"] for node in graph["nodes"]}


def test_top_node_has_metrics_cluster_and_sorted_directed_neighbors():
    gid = top_gid()
    response = CLIENT.get(f"/api/node/{gid}")
    assert response.status_code == 200
    detail = response.json()
    node = detail["node"]
    assert node["gid"] == gid
    assert isinstance(node["gid"], str)
    assert node["role"]
    assert node["evidence"]
    assert "priority_score" in node
    assert "in_deg" in node and "out_deg" in node
    assert detail["cluster"]["cluster_id"] is not None

    graph = json.loads((OUTPUT / "graph.json").read_text())
    incoming = [edge for edge in graph["edges"] if edge["target"] == gid]
    outgoing = [edge for edge in graph["edges"] if edge["source"] == gid]
    assert incoming and outgoing
    for label, edges, peer_key in (
        ("incoming", incoming, "source"),
        ("outgoing", outgoing, "target"),
    ):
        neighbors = detail[label]
        assert len(neighbors) == len(edges)
        assert [item["sum_kzt"] for item in neighbors] == sorted(
            (edge["sum_kzt"] for edge in edges), reverse=True
        )
        assert {item["gid"] for item in neighbors} == {edge[peer_key] for edge in edges}
        assert all(isinstance(item["gid"], str) and item["role"]
                   and item["n_tx"] >= 1 for item in neighbors)


def test_unknown_node_and_partial_gid_search():
    missing = CLIENT.get("/api/node/999999999999999999")
    assert missing.status_code == 404
    assert "error" in missing.json()

    gid = top_gid()
    response = CLIENT.get("/api/search", params={"q": gid[-6:]})
    assert response.status_code == 200
    matches = hits(response.json())
    assert len(matches) <= 10
    assert matches[0] == gid
    assert gid in [match if isinstance(match, str) else match["gid"] for match in matches]


def test_top_clusters_and_whitelisted_downloads():
    top = CLIENT.get("/api/top")
    clusters = CLIENT.get("/api/clusters")
    assert top.status_code == clusters.status_code == 200
    assert len(top.json()) >= 20
    assert top.json()[0]["gid"] == top_gid()
    assert isinstance(top.json()[0]["gid"], str)
    assert clusters.json()
    for name in DOWNLOADS:
        response = CLIENT.get(f"/api/download/{name}")
        assert response.status_code == 200
        assert response.content == (OUTPUT / name).read_bytes()
    for name in ("metrics.csv", "graph.json", "../metrics.csv", "not-a-file.csv"):
        response = CLIENT.get(f"/api/download/{name}")
        assert response.status_code != 200


def test_node_explanations_are_structured_and_match_graph():
    gid = top_gid()
    node = CLIENT.get(f"/api/node/{gid}").json()["node"]
    graph_node = next(row for row in CLIENT.get("/api/graph").json()["nodes"] if row["id"] == gid)
    rules = node["role_explanation"]
    assert rules == graph_node["role_explanation"]
    assert rules[-1]["role"] == node["role"]
    assert rules[-1]["matched"] is True
    assert all(not rule["matched"] for rule in rules[:-1])
    priority = node["priority_explanation"]
    assert priority == graph_node["priority_explanation"]
    assert len(priority["components"]) == 5
    assert abs(priority["score"] - node["priority_score"]) < 1e-10


def test_missing_outputs_return_actionable_503(tmp_path, monkeypatch):
    monkeypatch.setattr(viewer, "store", viewer.OutputStore(tmp_path))
    for path in ("/api/graph", "/api/top", "/api/clusters", "/api/search?q=123",
                 "/api/node/123", "/api/download/top_nodes.csv"):
        response = CLIENT.get(path)
        assert response.status_code == 503, path
        assert response.json() == {"error": "Run `make pipeline` first"}


def test_output_store_reloads_when_file_mtime_changes(tmp_path, monkeypatch):
    for name in ("graph.json", "metrics.csv", *DOWNLOADS):
        shutil.copy2(OUTPUT / name, tmp_path / name)
    monkeypatch.setattr(viewer, "store", viewer.OutputStore(tmp_path))
    before = CLIENT.get("/api/top")
    assert before.status_code == 200
    original = before.json()[0]["why"]

    path = tmp_path / "top_nodes.csv"
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0])
    rows[0]["why"] = "Updated investigation reason."
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))

    after = CLIENT.get("/api/top")
    assert after.status_code == 200
    assert after.json()[0]["why"] == "Updated investigation reason."
    assert after.json()[0]["why"] != original
