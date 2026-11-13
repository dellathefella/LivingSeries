"""SQLite episodic memory.

The MVP stores memories as rows and retrieves them by cosine similarity over a deterministic
bag-of-words embedding.  That is intentionally weak: it proves the loop without a vector database.
Swap `embed()` for a real embedding endpoint and `search()` for pgvector/Qdrant when the row count
crosses ~250k.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import settings

_WORD = re.compile(r"[a-z0-9']+")


def embed(text: str, dim: int | None = None) -> list[float]:
    """A deterministic bag-of-words embedding: stable, dependency-free, and good enough for the MVP."""
    dim = dim or settings.embedding_dim
    vec = [0.0] * dim
    for word in _WORD.findall(text.lower()):
        h = 0
        for ch in word:
            h = (h * 131 + ord(ch)) & 0xFFFFFFFF
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class Memory:
    id: int
    viewer: str
    character: str
    series: str
    text: str
    kind: str
    salience: float
    created_at: float


class MemoryStore:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS series (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, canon_json TEXT NOT NULL, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY, series_id TEXT NOT NULL, name TEXT NOT NULL, voice TEXT NOT NULL,
                prompt TEXT NOT NULL, state_json TEXT NOT NULL, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, viewer TEXT NOT NULL, character TEXT NOT NULL,
                series TEXT NOT NULL, text TEXT NOT NULL, kind TEXT NOT NULL, salience REAL NOT NULL,
                embedding_json TEXT NOT NULL, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, series TEXT NOT NULL, character TEXT NOT NULL,
                viewer TEXT NOT NULL, message TEXT NOT NULL, reply TEXT NOT NULL, score REAL NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS clips (
                id INTEGER PRIMARY KEY AUTOINCREMENT, interaction_id INTEGER NOT NULL, status TEXT NOT NULL,
                manifest_json TEXT NOT NULL, created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memories_viewer ON memories(viewer, character);
            CREATE INDEX IF NOT EXISTS idx_interactions_series ON interactions(series, created_at);
            """
        )
        self._conn.commit()

    # ---- series / characters ---------------------------------------------------------------
    def add_series(self, series_id: str, title: str, canon: dict) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO series(id, title, canon_json, created_at) VALUES (?,?,?,?)",
            (series_id, title, json.dumps(canon), time.time()),
        )
        self._conn.commit()

    def add_character(self, char_id: str, series_id: str, name: str, voice: str, prompt: str,
                      state: dict | None = None) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO characters(id, series_id, name, voice, prompt, state_json, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (char_id, series_id, name, voice, prompt, json.dumps(state or {}), time.time()),
        )
        self._conn.commit()

    def list_series(self) -> list[dict]:
        rows = self._conn.execute("SELECT id, title, canon_json FROM series ORDER BY id").fetchall()
        return [{"id": r["id"], "title": r["title"], "canon": json.loads(r["canon_json"])} for r in rows]

    def get_series(self, series_id: str) -> dict | None:
        r = self._conn.execute("SELECT id, title, canon_json FROM series WHERE id=?", (series_id,)).fetchone()
        return None if r is None else {"id": r["id"], "title": r["title"], "canon": json.loads(r["canon_json"])}

    def list_characters(self, series_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, name, voice, prompt, state_json FROM characters WHERE series_id=? ORDER BY id",
            (series_id,),
        ).fetchall()
        return [
            {"id": r["id"], "name": r["name"], "voice": r["voice"], "prompt": r["prompt"],
             "state": json.loads(r["state_json"])}
            for r in rows
        ]

    def get_character(self, char_id: str) -> dict | None:
        r = self._conn.execute(
            "SELECT id, series_id, name, voice, prompt, state_json FROM characters WHERE id=?", (char_id,)
        ).fetchone()
        if r is None:
            return None
        return {"id": r["id"], "series_id": r["series_id"], "name": r["name"], "voice": r["voice"],
                "prompt": r["prompt"], "state": json.loads(r["state_json"])}

    # ---- memory ----------------------------------------------------------------------------
    def add_memory(self, viewer: str, character: str, series: str, text: str, kind: str = "episodic",
                   salience: float = 1.0) -> int:
        cur = self._conn.execute(
            "INSERT INTO memories(viewer, character, series, text, kind, salience, embedding_json, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (viewer, character, series, text, kind, salience, json.dumps(embed(text)), time.time()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def search(self, viewer: str, character: str, query: str, top_k: int | None = None) -> list[Memory]:
        top_k = top_k or settings.memory_top_k
        q = embed(query)
        rows = self._conn.execute(
            "SELECT id, viewer, character, series, text, kind, salience, embedding_json, created_at"
            " FROM memories WHERE viewer=? AND character=? ORDER BY id DESC LIMIT 500",
            (viewer, character),
        ).fetchall()
        scored = []
        for r in rows:
            sim = cosine(q, json.loads(r["embedding_json"]))
            scored.append((sim * float(r["salience"]), r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            Memory(r["id"], r["viewer"], r["character"], r["series"], r["text"], r["kind"],
                   float(r["salience"]), float(r["created_at"]))
            for _, r in scored[:top_k]
        ]

    def all_memories(self, viewer: str, character: str) -> list[Memory]:
        rows = self._conn.execute(
            "SELECT id, viewer, character, series, text, kind, salience, created_at"
            " FROM memories WHERE viewer=? AND character=? ORDER BY id",
            (viewer, character),
        ).fetchall()
        return [Memory(r["id"], r["viewer"], r["character"], r["series"], r["text"], r["kind"],
                       float(r["salience"]), float(r["created_at"])) for r in rows]

    # ---- interactions / clips --------------------------------------------------------------
    def add_interaction(self, series: str, character: str, viewer: str, message: str, reply: str,
                        score: float) -> int:
        cur = self._conn.execute(
            "INSERT INTO interactions(series, character, viewer, message, reply, score, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (series, character, viewer, message, reply, score, time.time()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def recent_interactions(self, series: str, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, series, character, viewer, message, reply, score, created_at"
            " FROM interactions WHERE series=? ORDER BY score DESC, created_at DESC LIMIT ?",
            (series, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def add_clip(self, interaction_id: int, manifest: dict, status: str = "candidate") -> int:
        cur = self._conn.execute(
            "INSERT INTO clips(interaction_id, status, manifest_json, created_at) VALUES (?,?,?,?)",
            (interaction_id, status, json.dumps(manifest), time.time()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_clips(self, status: str | None = None) -> list[dict]:
        if status:
            rows = self._conn.execute(
                "SELECT id, interaction_id, status, manifest_json, created_at FROM clips WHERE status=? ORDER BY id DESC",
                (status,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, interaction_id, status, manifest_json, created_at FROM clips ORDER BY id DESC"
            ).fetchall()
        return [
            {"id": r["id"], "interaction_id": r["interaction_id"], "status": r["status"],
             "manifest": json.loads(r["manifest_json"]), "created_at": r["created_at"]}
            for r in rows
        ]

    def approve_clip(self, clip_id: int) -> bool:
        cur = self._conn.execute("UPDATE clips SET status='approved' WHERE id=? AND status='candidate'", (clip_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        self._conn.close()


def memories_as_context(memories: Iterable[Memory]) -> str:
    lines = [f"- ({m.kind}) {m.text}" for m in memories]
    return "\n".join(lines) if lines else "(no memories yet)"
