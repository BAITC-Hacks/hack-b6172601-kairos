"""The method endpoint exposes configured rules without requiring artifacts."""

from dataclasses import replace

from app.api import viewer
from pipeline.config import CONFIG, method_description
from tests.test_viewer_api import CLIENT


def test_method_uses_config_and_is_available_without_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(viewer, "store", viewer.OutputStore(tmp_path))
    response = CLIENT.get("/api/method")
    assert response.status_code == 200
    assert response.json() == method_description()
    assert len(response.json()["steps"]) == 6
    changed = method_description(replace(CONFIG, coordinator_min_consolidators=7))
    assert ">= 7 consolidator candidates" in changed["rules"][0]["rule"]
    assert changed["rules"][1:] == response.json()["rules"][1:]
