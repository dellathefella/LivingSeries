"""TP=4 benchmark: decode and prefill on the Arc box.

Usage:
    python bench_tp.py --base http://127.0.0.1:8081/v1 --model strata --lengths 1024,4096,16384

It streams a chat completion and reports time-to-first-token (prefill proxy) and decode tokens/s.
The prompt is a repeated code-agent style paragraph; the token count is approximate.
"""
from __future__ import annotations

import argparse
import json
import time

import httpx

PARAGRAPH = (
    "You are maintaining a small C++ inference engine. The scheduler reads a prompt in chunks, "
    "the expert cache holds the hottest experts in VRAM, and the CPU pool computes the rest. "
    "A request must not stall the other slots. Explain the trade-offs and propose a fix.\n"
)


def prompt_of(length: int) -> str:
    # ~4 characters per token; repeat the paragraph until the target is reached.
    target = length * 4
    return (PARAGRAPH * (target // len(PARAGRAPH) + 1))[:target]


def run_one(base: str, model: str, length: int, max_tokens: int) -> dict:
    url = f"{base}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_of(length)}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": True,
    }
    t0 = time.perf_counter()
    ttft = None
    chunks = 0
    text = []
    with httpx.Client(timeout=600) as client:
        with client.stream("POST", url, json=payload) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                obj = json.loads(data)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                piece = delta.get("content")
                if piece:
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    chunks += 1
                    text.append(piece)
    total = time.perf_counter() - t0
    decode_s = max(total - (ttft or 0.0), 1e-6)
    return {
        "prompt_tokens_approx": length,
        "generated_chunks": chunks,
        "ttft_s": round(ttft or 0.0, 3),
        "total_s": round(total, 3),
        "decode_tok_s": round(chunks / decode_s, 2),
        "text_head": "".join(text)[:120],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8081/v1")
    ap.add_argument("--model", default="strata")
    ap.add_argument("--lengths", default="1024,4096,16384")
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--reps", type=int, default=2)
    args = ap.parse_args()
    results = []
    for length in [int(x) for x in args.lengths.split(",")]:
        for rep in range(args.reps):
            r = run_one(args.base, args.model, length, args.max_tokens)
            r["rep"] = rep
            results.append(r)
            print(json.dumps(r), flush=True)
    print(json.dumps({"summary": results}, indent=2))


if __name__ == "__main__":
    main()
