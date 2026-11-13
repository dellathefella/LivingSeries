"""Character registry and prompt assembly."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .llm import LlmClient
from .memory import MemoryStore, memories_as_context


@dataclass
class Character:
    id: str
    series_id: str
    name: str
    voice: str
    prompt: str
    state: dict[str, Any]


def load_character(store: MemoryStore, char_id: str) -> Character | None:
    row = store.get_character(char_id)
    if row is None:
        return None
    return Character(row["id"], row["series_id"], row["name"], row["voice"], row["prompt"], row["state"])


def build_system_prompt(character: Character, canon: dict[str, Any], memories: list) -> str:
    canon_lines = "\n".join(f"- {k}: {v}" for k, v in canon.items())
    return (
        f"You are {character.name}, a character in the series '{character.series_id}'.\n"
        f"Voice: {character.voice}\n"
        f"Character brief: {character.prompt}\n"
        f"Canon facts:\n{canon_lines}\n"
        f"What you remember about this viewer:\n{memories_as_context(memories)}\n"
        "Rules:\n"
        "- Stay in character. Never mention that you are an AI or a model.\n"
        "- Use the memories naturally; do not list them.\n"
        "- Keep replies under 120 words unless the viewer asks for a story.\n"
        "- If a memory is uncertain, say so in character rather than inventing canon.\n"
    )


def reply(store: MemoryStore, client: LlmClient, series_id: str, char_id: str, viewer: str,
          message: str) -> dict[str, Any]:
    series = store.get_series(series_id)
    character = load_character(store, char_id)
    if series is None or character is None:
        raise ValueError("unknown series or character")
    memories = store.search(viewer, char_id, message)
    system = build_system_prompt(character, series["canon"], memories)
    llm = client.chat([
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ])
    # The interaction itself becomes a memory; salience rises when the viewer is named or the reply is long.
    salience = 1.0 + (0.5 if viewer.lower() in llm.text.lower() else 0.0) + min(len(llm.text) / 500.0, 0.5)
    store.add_memory(viewer, char_id, series_id, f"Viewer said: {message}\nI replied: {llm.text}",
                     kind="episodic", salience=salience)
    return {
        "reply": llm.text,
        "model": llm.model,
        "stub": llm.stub,
        "memories_used": [m.text for m in memories],
        "salience": salience,
    }
