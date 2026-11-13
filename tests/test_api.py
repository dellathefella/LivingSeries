"""API smoke tests.  They run without a model: the LLM client falls back to its stub."""
from __future__ import annotations

import os
import tempfile

os.environ["LS_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:1/v1"  # unreachable: the stub is used
os.environ["LS_LLM_REQUIRED"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app, store  # noqa: E402
from scripts.seed import CHARACTERS, MEMORIES, SERIES  # noqa: E402

client = TestClient(app)


def seed() -> None:
    store.add_series(SERIES["id"], SERIES["title"], SERIES["canon"])
    for c in CHARACTERS:
        store.add_character(c["id"], SERIES["id"], c["name"], c["voice"], c["prompt"], c["state"])
    for viewer, character, text in MEMORIES:
        store.add_memory(viewer, character, SERIES["id"], text, kind="episodic", salience=1.5)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_series_and_characters() -> None:
    seed()
    r = client.get("/v1/series")
    assert r.status_code == 200
    assert any(s["id"] == "demo" for s in r.json()["series"])
    r = client.get("/v1/series/demo/characters")
    assert r.status_code == 200
    assert {c["id"] for c in r.json()["characters"]} == {"mara", "ivo", "sable"}


def test_chat_uses_memory_and_scores() -> None:
    seed()
    r = client.post("/v1/chat", json={
        "series": "demo", "character": "mara", "viewer": "alex",
        "message": "Do you remember the blue plate?",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["reply"]
    assert body["stub"] is True
    assert body["memories_used"]
    assert 0.0 <= body["score"] <= 1.0
    assert body["interaction_id"] > 0


def test_clip_candidate_and_approval() -> None:
    seed()
    r = client.post("/v1/chat", json={
        "series": "demo", "character": "sable", "viewer": "alex",
        "message": "I dreamed the clock moved and everyone forgot their names.",
    })
    body = r.json()
    if body["clip_candidate"]:
        clip_id = body["clip_id"]
        assert clip_id is not None
        r = client.post(f"/v1/clips/{clip_id}/approve")
        assert r.status_code == 200
        assert r.json()["status"] == "approved"
    r = client.get("/v1/clips")
    assert r.status_code == 200


def test_episode_plan() -> None:
    seed()
    client.post("/v1/chat", json={
        "series": "demo", "character": "ivo", "viewer": "alex",
        "message": "Read me the ending of your novel.",
    })
    r = client.post("/v1/episodes/plan", json={"series": "demo", "week": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["week"] == 1
    assert isinstance(body["accepted"], list)
