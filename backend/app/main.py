"""LivingSeries API.

Run:  uvicorn backend.app.main:app --reload --port 8090
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .characters import reply as character_reply
from .clips import collect_candidates, manifest, score_interaction
from .config import settings
from .llm import LlmClient
from .memory import MemoryStore
from .story import plan_episode

app = FastAPI(title="LivingSeries", version="0.1.0")
store = MemoryStore()
llm = LlmClient()


class ChatRequest(BaseModel):
    series: str
    character: str
    viewer: str = Field(min_length=1)
    message: str = Field(min_length=1)


class EpisodeRequest(BaseModel):
    series: str
    week: int = 1


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "llm": llm.health(), "db": str(store.db_path)}


@app.get("/v1/series")
def list_series() -> dict[str, Any]:
    return {"series": store.list_series()}


@app.get("/v1/series/{series_id}/characters")
def list_characters(series_id: str) -> dict[str, Any]:
    return {"series": series_id, "characters": store.list_characters(series_id)}


@app.post("/v1/chat")
def chat(req: ChatRequest) -> dict[str, Any]:
    try:
        result = character_reply(store, llm, req.series, req.character, req.viewer, req.message)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    series = store.get_series(req.series) or {"canon": {}}
    interaction = {
        "series": req.series, "character": req.character, "viewer": req.viewer,
        "message": req.message, "reply": result["reply"],
    }
    score = score_interaction(interaction, series["canon"])
    interaction_id = store.add_interaction(req.series, req.character, req.viewer, req.message,
                                           result["reply"], score)
    clip_candidate = score >= settings.clip_min_score
    clip_id = None
    if clip_candidate:
        clip_id = store.add_clip(interaction_id, manifest(interaction, score))
    return {
        **result,
        "interaction_id": interaction_id,
        "score": score,
        "clip_candidate": clip_candidate,
        "clip_id": clip_id,
    }


@app.get("/v1/memory/{viewer}/{character}")
def memory(viewer: str, character: str) -> dict[str, Any]:
    rows = store.all_memories(viewer, character)
    return {"viewer": viewer, "character": character,
            "memories": [{"id": m.id, "text": m.text, "kind": m.kind, "salience": m.salience} for m in rows]}


@app.post("/v1/episodes/plan")
def episodes_plan(req: EpisodeRequest) -> dict[str, Any]:
    candidates = collect_candidates(store, req.series)
    try:
        return plan_episode(store, llm, req.series, req.week, candidates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/clips")
def clips(status: Optional[str] = None) -> dict[str, Any]:
    return {"clips": store.list_clips(status)}


@app.post("/v1/clips/{clip_id}/approve")
def approve_clip(clip_id: int) -> dict[str, Any]:
    if not store.approve_clip(clip_id):
        raise HTTPException(status_code=404, detail="clip not found or not a candidate")
    return {"clip_id": clip_id, "status": "approved"}
