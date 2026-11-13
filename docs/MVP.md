# LivingSeries — 90-day MVP plan

## Days 0–14: one series, one channel

- Pick the genre and the first three characters.
- Seed the canon (world facts, character voices, relationships).
- Stand up the FastAPI gateway and SQLite memory.
- Connect the LLM endpoint (Strata TP=4 on the Arc box; fall back to vLLM/MLX).
- Ship the Discord bot with `/talk`.

**Gate:** 20 real conversations, no moderation incidents, character replies coherent across 10 turns.

## Days 15–30: the clip loop

- Score interactions; generate a daily clip manifest.
- Render 3 clips/day with ffmpeg + the video pipeline.
- Post to TikTok/YouTube Shorts; track clip → Discord conversion.
- Add a landing page with the membership waitlist.

**Gate:** 100 clips posted; clip → Discord ≥ 2%; D7 Discord retention ≥ 25%.

## Days 31–60: the episode engine

- Implement the branch graph and canon checks.
- Weekly episode: planner reads the week's interactions, drafts 3 branches, the engine picks one.
- Add the paid tier (full episodes + private character).
- Add the moderation review queue.

**Gate:** 4 weekly episodes shipped; paid conversion ≥ 3% of active Discord members.

## Days 61–90: scale the loop

- Add a second series only if the first clears the gates.
- Move memory to Postgres + pgvector if rows > 250k.
- Add creator tools: a character builder and a canon editor.
- Measure: CAC, LTV, clip velocity, episode watch time.

**Gate:** 1,000 Discord members, 100 paying, LTV/CAC > 2.

## Metrics that matter

| Metric | Target |
|---|---|
| Clip → Discord conversion | ≥ 2% |
| D7 Discord retention | ≥ 25% |
| Episode completion | ≥ 40% |
| Paid conversion | ≥ 3% |
| Median reply latency | < 2 s |
| Moderation incidents | 0 unreviewed |

## What not to build yet

- A mobile app.
- A marketplace.
- Multi-series orchestration.
- Real-time video avatars.
- A custom vector database.

The MVP is a loop, not a platform. Prove the loop first.
