"""Seed the demo series.

Run:  python scripts/seed.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.memory import MemoryStore  # noqa: E402

SERIES = {
    "id": "demo",
    "title": "The Night Shift",
    "canon": {
        "setting": "A 24-hour diner at the edge of a city that never quite sleeps.",
        "rule_1": "The diner's clock is always 3:17 a.m.",
        "rule_2": "No character can leave the diner during an episode.",
        "rule_3": "Mara remembers every customer who has ever ordered the blue plate.",
        "forbid_real_people": "Do not name or impersonate any real person.",
    },
}

CHARACTERS = [
    {
        "id": "mara",
        "name": "Mara",
        "voice": "warm, dry, notices everything, speaks in short sentences",
        "prompt": "The night cook. She has worked the same shift for eleven years and remembers every regular.",
        "state": {"role": "cook", "mood": "steady"},
    },
    {
        "id": "ivo",
        "name": "Ivo",
        "voice": "nervous, precise, apologizes before he speaks",
        "prompt": "The dishwasher. He is writing a novel about the diner and is afraid someone will read it.",
        "state": {"role": "dishwasher", "mood": "anxious"},
    },
    {
        "id": "sable",
        "name": "Sable",
        "voice": "cool, amused, never answers a question directly",
        "prompt": "The late-shift waitress. She knows what everyone ordered before they order it.",
        "state": {"role": "waitress", "mood": "curious"},
    },
]

MEMORIES = [
    ("alex", "mara", "Alex ordered the blue plate at 3:17 and said it tasted like a memory."),
    ("alex", "mara", "Alex asked whether the clock ever moves. Mara said it does not, and that is the point."),
    ("alex", "ivo", "Alex read three pages of Ivo's novel and said the dishwasher character was too kind."),
    ("alex", "sable", "Sable predicted Alex would order coffee, then pie, then coffee again."),
]


def main() -> None:
    store = MemoryStore()
    store.add_series(SERIES["id"], SERIES["title"], SERIES["canon"])
    for c in CHARACTERS:
        store.add_character(c["id"], SERIES["id"], c["name"], c["voice"], c["prompt"], c["state"])
    for viewer, character, text in MEMORIES:
        store.add_memory(viewer, character, SERIES["id"], text, kind="episodic", salience=1.5)
    print(f"seeded series '{SERIES['id']}' with {len(CHARACTERS)} characters and {len(MEMORIES)} memories")
    store.close()


if __name__ == "__main__":
    main()
