# LivingSeries

AI-native interactive serials: persistent characters with memory, a branching story engine, weekly
episodes shaped by viewer interactions, and a clip factory that turns the best moments into short-form
distribution.

This repository is the MVP scaffold. It is deliberately small: one FastAPI service, SQLite memory,
an OpenAI-compatible LLM client, a story engine, a clip candidate queue, and a Discord bot stub.

## What it runs on

| Layer | Default | Notes |
|---|---|---|
| LLM | `LLM_BASE_URL` (OpenAI-compatible) | Point at Strata (`http://127.0.0.1:8080/v1`), vLLM XPU (`http://10.0.1.121:8081/v1`), or MLX (`http://10.0.4.108:11234/v1`) |
| Memory | SQLite (`data/livingseries.db`) | Swap for Postgres + pgvector when you outgrow it |
| Story | JSON branch graph per series | The LLM plans; the engine enforces canon |
| Clips | JSON manifest queue | Feed to ffmpeg / your render pipeline |
| Discord | `discord.py` bot (optional) | `/talk <character> <message>` |

## Quick start

```sh
cd LivingSeries
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env            # edit the LLM endpoint
python scripts/seed.py          # creates the demo series and characters
uvicorn backend.app.main:app --reload --port 8090
```

Then:

```sh
curl -s http://127.0.0.1:8090/v1/series
curl -s -X POST http://127.0.0.1:8090/v1/chat \
  -H 'content-type: application/json' \
  -d '{"series":"demo","character":"mara","viewer":"alex","message":"What did you dream last night?"}'
```

## The loop

1. A viewer talks to a character (Discord, web, or API).
2. The character answers with its own memory plus the viewer's history.
3. The interaction is scored; the best ones become clip candidates.
4. The weekly episode planner reads the candidates and drafts a branch.
5. Clips go out; new viewers join; their interactions feed the next episode.

## Layout

```
backend/app/
  main.py          FastAPI routes
  config.py        environment
  llm.py           OpenAI-compatible client (Strata / vLLM / MLX)
  memory.py        SQLite episodic memory + retrieval
  characters.py    character registry and prompts
  story.py         branch graph and episode planner
  clips.py         clip candidate queue and scoring
  discord_bot.py   optional Discord bridge
docs/
  PLATFORM.md      product, architecture, unit economics
  MVP.md           90-day plan and metrics
scripts/
  seed.py          demo series + characters
tests/
  test_api.py      smoke tests (no LLM required)
```

## Status

MVP scaffold. The LLM client is model-agnostic; the memory and story layers are intentionally simple
so the product loop can be measured before the infrastructure is scaled.
