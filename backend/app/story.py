"""Branching story engine.

The LLM proposes branches; this module enforces canon and pacing.  A branch that contradicts a canon
fact is rejected, not repaired.  The MVP keeps the graph in memory and persists the chosen branch in
the series canon so the next episode can build on it.
"""
from __future__ import annotations

import json
from typing import Any

from .llm import LlmClient, llm_json
from .memory import MemoryStore


def _canon_conflicts(branch: dict[str, Any], canon: dict[str, Any]) -> list[str]:
    conflicts: list[str] = []
    text = json.dumps(branch).lower()
    for key, value in canon.items():
        if key.startswith("forbid_"):
            forbidden = str(value).lower()
            if forbidden and forbidden in text:
                conflicts.append(f"branch mentions forbidden canon '{key}': {forbidden}")
    return conflicts


def plan_episode(store: MemoryStore, client: LlmClient, series_id: str, week: int,
                 candidates: list[dict[str, Any]]) -> dict[str, Any]:
    series = store.get_series(series_id)
    if series is None:
        raise ValueError("unknown series")
    canon = series["canon"]
    interactions = "\n".join(
        f"- {c['viewer']} -> {c['character']}: {c['message'][:160]} | reply: {c['reply'][:160]}"
        for c in candidates[:20]
    )
    prompt = (
        f"You are the showrunner of '{series['title']}' (series id {series_id}).\n"
        f"Canon:\n{json.dumps(canon, indent=2)}\n"
        f"This week's strongest viewer interactions:\n{interactions}\n\n"
        "Propose exactly 3 branches for episode {week}. Return JSON only:\n"
        '{"branches":[{"title":"...","summary":"...","characters":["..."],"hook":"..."}]}'
    ).replace("{week}", str(week))
    data = llm_json(client, [{"role": "user", "content": prompt}], max_tokens=1024)
    branches = data.get("branches", [])
    if not isinstance(branches, list) or not branches:
        branches = [{"title": f"Episode {week}", "summary": data.get("raw", "No branch generated"),
                     "characters": [], "hook": "The night begins."}]
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for b in branches[:3]:
        conflicts = _canon_conflicts(b, canon)
        if conflicts:
            rejected.append({"branch": b, "conflicts": conflicts})
        else:
            accepted.append(b)
    chosen = accepted[0] if accepted else None
    if chosen is not None:
        canon[f"episode_{week}_branch"] = chosen.get("title", "")
        canon[f"episode_{week}_summary"] = chosen.get("summary", "")
        store.add_series(series_id, series["title"], canon)
    return {
        "series": series_id,
        "week": week,
        "accepted": accepted,
        "rejected": rejected,
        "chosen": chosen,
        "stub": data.get("stub", False),
    }
