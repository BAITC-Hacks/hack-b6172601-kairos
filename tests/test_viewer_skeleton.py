"""The hierarchy view uses exported retained edges, not an induced subgraph."""

import csv

from app.api import viewer
from tests.test_viewer_api import CLIENT, OUTPUT


def test_skeleton_matches_retained_export_and_preserves_identifiers():
    response = CLIENT.get("/api/skeleton")
    assert response.status_code == 200
    with (OUTPUT / "skeleton_edges.csv").open(newline="") as handle:
        expected = [{"source": row["src"], "target": row["dst"], "sum_kzt": float(row["sum_kzt"])}
                    for row in csv.DictReader(handle)]
    assert response.json() == expected
    graph = CLIENT.get("/api/graph").json()
    marked = {node["id"] for node in graph["nodes"] if node["skeleton"]}
    assert {edge[key] for edge in expected for key in ("source", "target")} == marked
    assert all(isinstance(edge["source"], str) and isinstance(edge["target"], str) for edge in expected)
    induced = [edge for edge in graph["edges"] if edge["source"] in marked and edge["target"] in marked]
    assert len(expected) < len(induced)


def test_missing_skeleton_has_actionable_error(tmp_path, monkeypatch):
    monkeypatch.setattr(viewer, "store", viewer.OutputStore(tmp_path))
    response = CLIENT.get("/api/skeleton")
    assert response.status_code == 503
    assert response.json() == {"error": "Run `make pipeline` first"}
