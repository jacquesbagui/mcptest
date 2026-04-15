"""Realistic MCP server: read-mostly access to a notes directory.

Exposes four tools over stdio (default) or streamable HTTP:

- list_notes: list all notes with their titles
- read_note: return the full body of a note by id
- search_notes: case-insensitive substring search in titles + bodies
- create_note: append a new note to the directory (returns the new id)

Usage:
    python notes_server.py                 # stdio
    python notes_server.py http [port]     # streamable HTTP
    NOTES_DIR=/tmp/notes python notes_server.py
"""

from __future__ import annotations

import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP


def _notes_dir() -> Path:
    base = Path(os.environ.get("NOTES_DIR", "")) or Path.home() / ".mcpact-notes"
    base.mkdir(parents=True, exist_ok=True)
    return base


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    body: str


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or uuid.uuid4().hex[:8]


def _parse(path: Path) -> Note:
    text = path.read_text(encoding="utf-8")
    title, _, body = text.partition("\n")
    return Note(id=path.stem, title=title.strip() or path.stem, body=body.lstrip("\n"))


def _all_notes() -> list[Note]:
    return sorted(
        (_parse(p) for p in _notes_dir().glob("*.md")),
        key=lambda n: n.id,
    )


mcp = FastMCP("notes")


@mcp.tool()
def list_notes() -> list[dict[str, str]]:
    """List every note with its id and title."""
    return [{"id": n.id, "title": n.title} for n in _all_notes()]


@mcp.tool()
def read_note(id: str) -> dict[str, str]:
    """Return the full body of a note by id."""
    path = _notes_dir() / f"{id}.md"
    if not path.is_file():
        raise FileNotFoundError(f"note not found: {id}")
    n = _parse(path)
    return {"id": n.id, "title": n.title, "body": n.body}


@mcp.tool()
def search_notes(query: str) -> list[dict[str, str]]:
    """Case-insensitive substring search in titles and bodies."""
    q = query.lower().strip()
    if not q:
        return []
    hits: list[dict[str, str]] = []
    for n in _all_notes():
        if q in n.title.lower() or q in n.body.lower():
            hits.append({"id": n.id, "title": n.title})
    return hits


@mcp.tool()
def create_note(title: str, body: str = "") -> dict[str, str]:
    """Create a new note and return its id."""
    if not title.strip():
        raise ValueError("title must not be empty")
    note_id = _slug(title)
    path = _notes_dir() / f"{note_id}.md"
    i = 1
    while path.exists():
        i += 1
        path = _notes_dir() / f"{note_id}-{i}.md"
    path.write_text(f"{title.strip()}\n\n{body}", encoding="utf-8")
    return {"id": path.stem, "title": title.strip()}


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport == "http":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.environ.get("PORT", "3000"))
        mcp.settings.host = "127.0.0.1"
        mcp.settings.port = port
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
