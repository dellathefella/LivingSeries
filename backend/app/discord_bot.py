"""Optional Discord bridge.

Set DISCORD_TOKEN to enable.  The bot calls the LivingSeries API, so the gateway is the only place
that talks to the model.

    python -m backend.app.discord_bot
"""
from __future__ import annotations

import os

import httpx

from .config import settings

try:
    import discord
    from discord.ext import commands
except Exception:  # noqa: BLE001 - discord.py is optional
    discord = None
    commands = None


def _api_chat(series: str, character: str, viewer: str, message: str) -> str:
    r = httpx.post(
        f"{settings.api_base}/v1/chat",
        json={"series": series, "character": character, "viewer": viewer, "message": message},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["reply"]


def main() -> None:
    if discord is None or commands is None:
        raise SystemExit("discord.py is not installed; pip install discord.py")
    token = settings.discord_token or os.environ.get("DISCORD_TOKEN", "")
    if not token:
        raise SystemExit("DISCORD_TOKEN is not set")

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready() -> None:
        print(f"LivingSeries bot connected as {bot.user}")

    @bot.command(name="talk")
    async def talk(ctx, character: str, *, message: str) -> None:
        viewer = str(ctx.author.display_name)
        try:
            text = _api_chat("demo", character, viewer, message)
        except Exception as exc:  # noqa: BLE001
            await ctx.reply(f"The character is offline: {exc}")
            return
        await ctx.reply(text)

    bot.run(token)


if __name__ == "__main__":
    main()
