# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "mcp>=2.0.0",
#     "pydantic>=2.0.0",
# ]
# ///
"""Local Discord MCP server using the Discord REST API v10.

Loads credentials from:
1. Environment variables (DISCORD_BOT_TOKEN, DISCORD_WRITE_CHANNELS)
2. ~/.config/mcp/discord.env
3. macOS Keychain ('discord-mcp-bot-token')
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, ConfigDict, Field

DISCORD_API_BASE = "https://discord.com/api/v10"
ENV_FILE_PATH = Path.home() / ".config" / "mcp" / "discord.env"

mcp = MCPServer("discord_mcp")


def _load_env_file(path: Path = ENV_FILE_PATH) -> dict[str, str]:
    """Parses a simple KEY=VALUE env file without external dependencies."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        val = val.strip().strip("'").strip('"')
        values[key] = val
    return values


def _resolve_config() -> tuple[str, set[str]]:
    """Resolves DISCORD_BOT_TOKEN and optional DISCORD_WRITE_CHANNELS allowlist."""
    env_file = _load_env_file()

    token = os.environ.get("DISCORD_BOT_TOKEN") or env_file.get("DISCORD_BOT_TOKEN", "")
    if not token and sys.platform == "darwin":
        try:
            token = subprocess.check_output(
                ["security", "find-generic-password", "-s", "discord-mcp-bot-token", "-w"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except (subprocess.SubprocessError, OSError):
            token = ""

    if not token:
        raise RuntimeError(
            f"DISCORD_BOT_TOKEN not found in environment, {ENV_FILE_PATH}, or macOS Keychain."
        )

    raw_channels = os.environ.get("DISCORD_WRITE_CHANNELS") or env_file.get(
        "DISCORD_WRITE_CHANNELS", ""
    )
    allowed_channels = {ch.strip() for ch in raw_channels.split(",") if ch.strip()}
    return token, allowed_channels


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bot {token}",
        "User-Agent": "DiscordMCP (local, 1.0)",
    }


class ListChannelsInput(BaseModel):
    """Input parameters for listing channels in a Discord server (guild)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    guild_id: str = Field(
        ...,
        pattern=r"^\d{17,20}$",
        description="Discord server (guild) ID.",
    )


class ReadMessagesInput(BaseModel):
    """Input parameters for reading messages from a Discord channel."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    channel_id: str = Field(
        ...,
        pattern=r"^\d{17,20}$",
        description="Discord channel ID to read messages from.",
    )
    limit: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Number of recent messages to fetch (1-100).",
    )


class SendMessageInput(BaseModel):
    """Input parameters for sending a message to a Discord channel."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    channel_id: str = Field(
        ...,
        pattern=r"^\d{17,20}$",
        description="Target Discord channel ID.",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Message content to send (max 2000 characters).",
    )


@mcp.tool(
    name="discord_list_guilds",
    annotations={
        "title": "List Discord Servers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def discord_list_guilds() -> str:
    """Lists all Discord servers (guilds) that the bot is a member of."""
    token, _ = _resolve_config()
    async with httpx.AsyncClient(headers=_headers(token), timeout=10.0) as client:
        resp = await client.get(f"{DISCORD_API_BASE}/users/@me/guilds")
        resp.raise_for_status()
        guilds: list[dict[str, Any]] = resp.json()

    if not guilds:
        return "Bot is not a member of any Discord servers yet."
    return "\n".join(f"- {g['name']} (guild_id: {g['id']})" for g in guilds)


@mcp.tool(
    name="discord_list_channels",
    annotations={
        "title": "List Discord Server Channels",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def discord_list_channels(params: ListChannelsInput) -> str:
    """Lists text and announcement channels in a Discord server."""
    token, allowed_channels = _resolve_config()
    async with httpx.AsyncClient(headers=_headers(token), timeout=10.0) as client:
        resp = await client.get(f"{DISCORD_API_BASE}/guilds/{params.guild_id}/channels")
        resp.raise_for_status()
        channels: list[dict[str, Any]] = resp.json()

    # Discord channel types: 0 = GUILD_TEXT, 5 = GUILD_ANNOUNCEMENT, 15 = GUILD_FORUM
    text_channels = [c for c in channels if c.get("type") in (0, 5, 15)]
    if not text_channels:
        return "No text channels found in this server."

    lines: list[str] = []
    for ch in sorted(text_channels, key=lambda x: x.get("position", 0)):
        cid = ch["id"]
        writable_tag = ""
        if allowed_channels:
            writable_tag = " [WRITABLE]" if cid in allowed_channels else " [read-only]"
        lines.append(f"- #{ch.get('name', 'unknown')} (channel_id: {cid}){writable_tag}")
    return "\n".join(lines)


@mcp.tool(
    name="discord_read_messages",
    annotations={
        "title": "Read Discord Channel Messages",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def discord_read_messages(params: ReadMessagesInput) -> str:
    """Reads and formats recent messages from a Discord channel (oldest to newest)."""
    token, _ = _resolve_config()
    async with httpx.AsyncClient(headers=_headers(token), timeout=10.0) as client:
        resp = await client.get(
            f"{DISCORD_API_BASE}/channels/{params.channel_id}/messages",
            params={"limit": params.limit},
        )
        resp.raise_for_status()
        messages: list[dict[str, Any]] = resp.json()

    if not messages:
        return "No messages found in channel."

    lines: list[str] = []
    for msg in reversed(messages):
        author = msg.get("author", {}).get("username", "unknown")
        ts = msg.get("timestamp", "")[:16].replace("T", " ")
        content = msg.get("content", "")
        attachments = [a.get("filename", "file") for a in msg.get("attachments", [])]
        suffix = f" [attachments: {', '.join(attachments)}]" if attachments else ""
        lines.append(f"[{ts}] {author}: {content}{suffix}")
    return "\n".join(lines)


@mcp.tool(
    name="discord_send_message",
    annotations={
        "title": "Send Discord Message",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def discord_send_message(params: SendMessageInput) -> str:
    """Sends a message to a Discord channel with @everyone/@here mentions disabled."""
    token, allowed_channels = _resolve_config()
    if allowed_channels and params.channel_id not in allowed_channels:
        return (
            f"Error: Channel {params.channel_id} is not in DISCORD_WRITE_CHANNELS allowlist "
            f"({sorted(allowed_channels)})."
        )

    payload: dict[str, Any] = {
        "content": params.content,
        "allowed_mentions": {"parse": []},
    }
    async with httpx.AsyncClient(headers=_headers(token), timeout=10.0) as client:
        resp = await client.post(
            f"{DISCORD_API_BASE}/channels/{params.channel_id}/messages",
            json=payload,
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
    return f"Sent message (id: {data.get('id')}) to channel {params.channel_id}."


async def _cli_smoke_test(message: str) -> None:
    """Runs a quick smoke test: discovers the target channel and posts a test message."""
    token, allowed_channels = _resolve_config()
    async with httpx.AsyncClient(headers=_headers(token), timeout=10.0) as client:
        me_resp = await client.get(f"{DISCORD_API_BASE}/users/@me")
        me_resp.raise_for_status()
        bot_user = me_resp.json()
        print(f"Authenticated as bot: {bot_user.get('username')} (id: {bot_user.get('id')})")

        target_channel_id: str | None = None
        if allowed_channels:
            target_channel_id = min(allowed_channels)
            print(f"Using configured DISCORD_WRITE_CHANNELS target: {target_channel_id}")
        else:
            guilds_resp = await client.get(f"{DISCORD_API_BASE}/users/@me/guilds")
            guilds_resp.raise_for_status()
            guilds: list[dict[str, Any]] = guilds_resp.json()
            print(f"Found {len(guilds)} guild(s): {[g['name'] for g in guilds]}")
            for g in guilds:
                ch_resp = await client.get(f"{DISCORD_API_BASE}/guilds/{g['id']}/channels")
                if ch_resp.status_code != 200:
                    continue
                text_chs = [c for c in ch_resp.json() if c.get("type") == 0]
                if text_chs:
                    # Prefer #general or first text channel
                    chosen = next(
                        (c for c in text_chs if c.get("name") in ("general", "bot", "test")),
                        text_chs[0],
                    )
                    target_channel_id = chosen["id"]
                    print(
                        f"Selected channel #{chosen.get('name')} ({target_channel_id}) "
                        f"in server '{g['name']}'"
                    )
                    break

        if not target_channel_id:
            print("No writable text channel found. Invite the bot to a server first.")
            return

    result = await discord_send_message(
        SendMessageInput(channel_id=target_channel_id, content=message)
    )
    print(result)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke-test":
        import asyncio

        msg = (
            sys.argv[2]
            if len(sys.argv) > 2
            else "Hello from your local Discord MCP server! 🚀"
        )
        asyncio.run(_cli_smoke_test(msg))
    else:
        mcp.run()
