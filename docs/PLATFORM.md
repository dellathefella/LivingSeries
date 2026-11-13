# LivingSeries — platform spec

## Thesis

Short-form video trained audiences to remix. Persistent AI characters give them something to remix
*with*. The viral unit is a 15–30 second clip of a character reacting to a specific viewer by name;
the conversion path is clip → Discord → conversation → next week's clip. The audience becomes cast.

## Product

- **Series**: a world with 3–6 characters, a canon, and a weekly episode.
- **Characters**: persistent memory per viewer and per character; relationships evolve.
- **Episodes**: a branch graph planned by the LLM, enforced by the story engine. Viewers' interactions
  are inputs to the planner, not free-form improv.
- **Clips**: automatic selection and captioning of the strongest interactions; 3 posts/day.
- **Membership**: free clips + Discord; paid tier for full episodes and a private character.

## Architecture

```
viewer ── Discord / web / API
              │
        FastAPI gateway
              │
   ┌──────────┼───────────┐
   │          │           │
 memory     story       clip queue
 (SQLite)   engine      (JSON → ffmpeg)
   │          │           │
   └──────────┼───────────┘
              │
      OpenAI-compatible LLM
   Strata TP=4 (4× Arc B60) / vLLM XPU / MLX
```

- **LLM**: one endpoint per deployment; the gateway is model-agnostic. Strata TP=4 on the Arc box is the
  always-on inference tier; MLX on the Mac Studio handles heavier reasoning and batch generation.
- **Memory**: SQLite for the MVP; Postgres + pgvector when per-viewer memory exceeds a few hundred
  thousand rows. Retrieval is cosine similarity over recent + salient memories.
- **Story**: a JSON branch graph. The LLM proposes branches; the engine checks canon facts, character
  state, and episode pacing. A branch that contradicts canon is rejected, not repaired.
- **Clips**: interactions are scored by (novelty, emotional charge, viewer specificity, canon value).
  The top N become a manifest for the render pipeline.
- **Moderation**: a classifier plus a human review queue. Characters cannot impersonate real people;
  viewer-supplied text is never rendered as a character's voice without review.

## Unit economics (MVP)

| Item | Assumption |
|---|---|
| Inference | local B60s; marginal cost ≈ electricity |
| Video render | cloud burst, ~$0.10–0.40 per clip |
| Storage / DB | < $50/mo at MVP |
| Distribution | organic; paid boosts only after retention is proven |
| Price | $9/mo membership; $29/mo creator tier |

The local inference tier is the reason the model works at small scale: per-interaction cost is near
zero, so the free tier can be generous without a cloud bill.

## Defensibility

1. **Memory**: a character that remembers you is hard to clone.
2. **Canon engine**: coherent branching is an engineering problem, not a prompt.
3. **Cost structure**: local inference keeps the marginal cost low while the audience grows.

## Risks

- **IP**: characters must be original or licensed; no real-person likeness.
- **Moderation**: viewer input can steer a character into unsafe territory; the review queue is not optional.
- **Retention**: the clip loop must convert; measure clip → Discord and D7 before scaling spend.
- **Compute**: video rendering is bursty; keep it off the always-on box.

## First series

Pick a genre the founder already has an audience for. The demo in this repo is a small mystery series
("The Night Shift") with three characters; replace it with the real first series before launch.
