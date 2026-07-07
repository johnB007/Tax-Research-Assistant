from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from tax_agent.config import get_settings


@dataclass
class RetrievedChunk:
    content: str
    citation_label: str
    source_name: str
    source_url: str


def _db_path() -> Path:
    return get_settings().law_db_path


def _to_fts_query(query: str) -> str:
    terms = re.findall(r"[A-Za-z0-9_]+", query.lower())
    if not terms:
        return ""
    return " OR ".join(dict.fromkeys(terms))


def search_law(query: str, limit: int = 8) -> list[RetrievedChunk]:
    query = query.strip()
    if not query:
        return []

    fts_query = _to_fts_query(query)
    if not fts_query:
        return []

    db_path = _db_path()
    if not db_path.exists():
        return []

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT c.content, c.citation_label, s.name, s.url
            FROM chunks_fts f
            JOIN chunks c ON c.id = f.rowid
            JOIN sources s ON s.id = c.source_id
            WHERE chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts)
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()

    return [
        RetrievedChunk(
            content=row[0],
            citation_label=row[1],
            source_name=row[2],
            source_url=row[3],
        )
        for row in rows
    ]
