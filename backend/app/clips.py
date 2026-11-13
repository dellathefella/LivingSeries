"""Clip candidate scoring and manifest generation.

An interaction becomes a clip candidate when it is novel, emotionally charged, viewer-specific, and
canon-relevant.  The manifest is what the render pipeline consumes; the MVP writes JSON, not video.
"""
from __future__ import annotations

import re
from typing import Any

from .config import settings

_EMOTION = {
    "love", "hate", "afraid", "scared", "angry", "furious", "cry", "cried", "laugh", "laughed",
    "shock", "shocked", "surprise", "dream", "nightmare", "secret", "betray", "promise", "never",
    "always", "die", "died", "kiss", "lost", "found", "remember", "forget",
}
_WORD = re.compile(r"[a-z0-9']+")


def score_interaction(interaction: dict[str, Any], canon: dict[str, Any]) -> float:
    message = interaction.get("message", "")
    reply = interaction.get("reply", "")
    viewer = interaction.get("viewer", "")
    words = set(_WORD.findall((message + " " + reply).lower()))
    novelty = min(len(words) / 60.0, 1.0)
    emotion = min(len(words & _EMOTION) / 3.0, 1.0)
    specificity = 1.0 if viewer and viewer.lower() in reply.lower() else 0.0
    canon_hits = sum(1 for v in canon.values() if isinstance(v, str) and v.lower() in reply.lower())
    canon_value = min(canon_hits / 2.0, 1.0)
    return round(0.30 * novelty + 0.30 * emotion + 0.25 * specificity + 0.15 * canon_value, 3)


def manifest(interaction: dict[str, Any], score: float) -> dict[str, Any]:
    return {
        "type": "clip",
        "series": interaction.get("series"),
        "character": interaction.get("character"),
        "viewer": interaction.get("viewer"),
        "transcript": [
            {"speaker": "viewer", "text": interaction.get("message", "")},
            {"speaker": interaction.get("character", "character"), "text": interaction.get("reply", "")},
        ],
        "score": score,
        "caption": f"{interaction.get('character', 'character')} remembers {interaction.get('viewer', 'you')}.",
        "render": {"duration_s": 20, "aspect": "9:16", "subtitles": True},
    }


def collect_candidates(store, series_id: str) -> list[dict[str, Any]]:
    series = store.get_series(series_id)
    canon = series["canon"] if series else {}
    out: list[dict[str, Any]] = []
    for interaction in store.recent_interactions(series_id, limit=100):
        score = score_interaction(interaction, canon)
        if score >= settings.clip_min_score:
            out.append({"interaction": interaction, "score": score, "manifest": manifest(interaction, score)})
    out.sort(key=lambda c: c["score"], reverse=True)
    return out
