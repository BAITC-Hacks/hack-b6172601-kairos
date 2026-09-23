"""Regressions for defects found in the pre-hackathon audit.

Each test names the defect it locks down, so a future change that reintroduces
it fails loudly instead of quietly.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.ratelimit import WINDOW_SECONDS, check, reset
from app.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


# --- validation errors must never become a 500 -----------------------------

def test_non_json_body_returns_422_not_500():
    """Raw bytes in the validation error used to break JSON serialization."""
    response = client.post(
        "/api/ask", content=b'{"question":"hello"}', headers={"Content-Type": "text/plain"}
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


def test_non_finite_number_returns_422_not_500():
    response = client.post(
        "/api/ask", content=b'{"question": NaN}', headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422, response.text


def test_undecodable_body_is_rejected_cleanly():
    """A body that is not valid UTF-8 fails at transport parsing, before model
    validation, so the framework answers 400. What matters is that it is a clean
    JSON response and not a stack trace."""
    response = client.post(
        "/api/ask", content=b"\xff\xfe not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400, response.text
    json.dumps(response.json())  # must not raise
    assert "Traceback" not in response.text


def test_validation_detail_is_json_serializable():
    """A structurally valid body with an invalid field must serialize cleanly."""
    response = client.post("/api/ask", json={"question": {"not": "a string"}})
    assert response.status_code == 422, response.text
    body = response.json()
    json.dumps(body)  # must not raise
    assert body["error"]["code"] == "validation_error"


# --- the rate limiter must not be bypassable by a header -------------------

class _Req:
    """Minimal stand-in for a Starlette request."""

    def __init__(self, headers=None, peer="127.0.0.1"):
        self.headers = headers or {}
        self.client = type("C", (), {"host": peer})()


def test_forged_forwarded_header_cannot_reset_the_bucket(monkeypatch):
    """Live finding: Fly appends the real address to a client-supplied
    X-Forwarded-For, so the FIRST entry is attacker-controlled. Taking it made
    the limiter bypassable on the public deployment - every forged value got a
    fresh bucket. The last entry is the one the platform vouches for."""
    from app.api.routes import _client_ip
    from app.core.config import Settings, get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("CLIENT_IP_HEADER", "")
    try:
        forged = _Req({"x-forwarded-for": "1.2.3.4, 203.0.113.9"})
        assert _client_ip(forged) == "203.0.113.9", "the attacker-supplied entry won"
    finally:
        get_settings.cache_clear()


def test_platform_header_wins_over_forwarded_for(monkeypatch):
    from app.api.routes import _client_ip
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("CLIENT_IP_HEADER", "fly-client-ip")
    try:
        request = _Req({"x-forwarded-for": "1.2.3.4", "fly-client-ip": "203.0.113.9"})
        assert _client_ip(request) == "203.0.113.9"
    finally:
        get_settings.cache_clear()


def test_forwarded_header_is_ignored_when_proxy_is_not_trusted():
    """TRUST_PROXY_HEADERS defaults to false, so a forged header must not help."""
    reset()
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.trust_proxy_headers is False

    from app.api.routes import _client_ip

    class _Req:
        headers = {"x-forwarded-for": "9.9.9.9"}
        client = type("C", (), {"host": "127.0.0.1"})()

    assert _client_ip(_Req()) == "127.0.0.1"


def test_expired_buckets_are_evicted():
    reset()
    from app.core.ratelimit import _hits

    for i in range(5_100):
        check(f"10.0.{i // 256}.{i % 256}", limit=10, now=0.0)
    before = len(_hits)
    check("192.168.1.1", limit=10, now=WINDOW_SECONDS + 1_000)
    assert len(_hits) < before, "expired buckets were not evicted"


# --- the language guard must actually fail on Cyrillic ---------------------

def test_language_guard_detects_cyrillic(tmp_path):
    """The previous grep -P implementation silently passed on macOS."""
    (tmp_path / "sentinel.txt").write_text(chr(0x041F) + chr(0x0440), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_language.py")],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 1, result.stdout


def test_language_guard_passes_on_clean_tree(tmp_path):
    (tmp_path / "clean.txt").write_text("plain ascii text", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_language.py")],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout


# --- the seeder must not destroy an existing dataset -----------------------

def test_seeder_keeps_existing_data(tmp_path):
    (tmp_path / "accounts.json").write_text('[{"sentinel": "retain-me"}]', encoding="utf-8")
    (tmp_path / "transactions.json").write_text("[]", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seed_data.py"), "--out", str(tmp_path)],
        capture_output=True, text=True, check=True,
    )
    kept = json.loads((tmp_path / "accounts.json").read_text())
    assert kept[0]["sentinel"] == "retain-me"


def test_seeder_regenerates_with_force(tmp_path):
    (tmp_path / "accounts.json").write_text('[{"sentinel": "retain-me"}]', encoding="utf-8")
    (tmp_path / "transactions.json").write_text("[]", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seed_data.py"), "--out", str(tmp_path), "--force"],
        capture_output=True, text=True, check=True,
    )
    regenerated = json.loads((tmp_path / "accounts.json").read_text())
    assert "sentinel" not in regenerated[0]


# --- the Docker build context must not carry secrets -----------------------

def test_dockerignore_patterns_match_nested_paths():
    """A bare pattern in .dockerignore matches only the build-context root.

    The previous version of this test asserted that the substring ".env" was
    present, which passed while nested paths still shipped in the image.
    """
    lines = [
        line.strip()
        for line in (ROOT / ".dockerignore").read_text().splitlines()
        if line.strip() and not line.startswith("#") and not line.startswith("!")
    ]
    must_be_recursive = {".env", ".venv/", ".traces/", "__pycache__/", "._*", "*.log"}
    for needle in must_be_recursive:
        matching = [line for line in lines if line.endswith(needle)]
        assert matching, f"no pattern covers {needle}"
        assert all(line.startswith("**/") for line in matching), (
            f"{needle} is not anchored with **/, so it only matches the context root: {matching}"
        )
