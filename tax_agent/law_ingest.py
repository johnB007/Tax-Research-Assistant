from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Iterable

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from tax_agent.config import get_settings
from tax_agent import law_sources
from tax_agent.states_config import CrawlRoot

USER_AGENT = "TaxResearchAgent/1.0"


def _configure_sqlite(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA busy_timeout=90000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        # If another reader temporarily holds lock, continue with default mode.
        pass


def _init_db(db_path: Path) -> None:
    with sqlite3.connect(db_path, timeout=90) as conn:
        _configure_sqlite(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                citation_label TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES sources (id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                source_url TEXT NOT NULL,
                old_hash TEXT,
                new_hash TEXT NOT NULL,
                changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                change_type TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES sources (id)
            )
            """
        )
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(content, citation_label)")


def _extract_pdf_text(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text)
    return "\n".join(pages)


def _extract_html_text(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _download_source(url: str, cache_dir: Path) -> str:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=90)
    response.raise_for_status()

    if url.lower().endswith(".pdf"):
        cache_name = hashlib.sha256(url.encode("utf-8")).hexdigest() + ".pdf"
        cache_path = cache_dir / cache_name
        cache_path.write_bytes(response.content)
        return _extract_pdf_text(cache_path)

    return _extract_html_text(response.text)


def _normalize_url(candidate: str) -> str:
    parsed = urlparse(candidate)
    clean = parsed._replace(fragment="")
    return clean.geturl().rstrip("/")


def _is_allowed(url: str, allowed_prefixes: tuple[str, ...]) -> bool:
    return any(url.startswith(prefix.rstrip("/")) for prefix in allowed_prefixes)


def _looks_like_document(url: str) -> bool:
    lower = url.lower()
    blocked_ext = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".zip",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".mp4",
        ".mp3",
    )
    return not lower.endswith(blocked_ext)


def _extract_links(page_url: str, html_text: str) -> list[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        joined = urljoin(page_url, anchor["href"])
        if not joined.startswith("http"):
            continue
        normalized = _normalize_url(joined)
        if _looks_like_document(normalized):
            links.append(normalized)
    return links


def _safe_filename(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return f"{digest}.html"


def _fetch_html(url: str, cache_dir: Path) -> str:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=90)
    response.raise_for_status()
    html_text = response.text
    (cache_dir / _safe_filename(url)).write_text(html_text, encoding="utf-8")
    return html_text


def _discover_urls(root: CrawlRoot, cache_dir: Path) -> list[str]:
    max_pages_override = os.getenv("LAW_MAX_PAGES", "").strip()
    root_page_limit = root.max_pages
    if max_pages_override.isdigit():
        root_page_limit = min(root.max_pages, int(max_pages_override))

    seeds = [root.seed_url, *root.additional_seed_urls]
    queue: deque[tuple[str, int]] = deque([(_normalize_url(seed), 0) for seed in seeds])
    visited: set[str] = set()
    discovered: list[str] = []

    while queue and len(discovered) < root_page_limit:
        current_url, depth = queue.popleft()
        current_url = _normalize_url(current_url)

        if current_url in visited:
            continue
        if not _is_allowed(current_url, root.allowed_prefixes):
            continue

        visited.add(current_url)
        discovered.append(current_url)

        if depth >= root.max_depth:
            continue

        if current_url.lower().endswith(".pdf"):
            continue

        try:
            html_text = _fetch_html(current_url, cache_dir)
            for link in _extract_links(current_url, html_text):
                if link not in visited and _is_allowed(link, root.allowed_prefixes):
                    queue.append((link, depth + 1))
        except requests.RequestException:
            continue

    return discovered


def _chunk_text(text: str, max_words: int = 260, overlap_words: int = 40) -> Iterable[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end == len(words):
            break
        start = max(0, end - overlap_words)

    return chunks


def _source_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()


def _upsert_source(
    conn: sqlite3.Connection,
    source_name: str,
    jurisdiction: str,
    source_url: str,
    content_hash: str,
) -> tuple[int, str]:
    row = conn.execute("SELECT id, content_hash FROM sources WHERE url = ?", (source_url,)).fetchone()
    if row:
        source_id, existing_hash = row
        if existing_hash != content_hash:
            conn.execute(
                "DELETE FROM chunks_fts WHERE rowid IN (SELECT id FROM chunks WHERE source_id = ?)",
                (source_id,),
            )
            conn.execute("UPDATE sources SET content_hash = ? WHERE id = ?", (content_hash, source_id))
            conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
            conn.execute(
                "INSERT INTO source_change_log(source_id, source_url, old_hash, new_hash, change_type) VALUES (?, ?, ?, ?, ?)",
                (source_id, source_url, existing_hash, content_hash, "updated"),
            )
            return int(source_id), "updated"
        return int(source_id), "unchanged"

    cursor = conn.execute(
        "INSERT INTO sources(name, jurisdiction, url, content_hash) VALUES (?, ?, ?, ?)",
        (source_name, jurisdiction, source_url, content_hash),
    )
    source_id = int(cursor.lastrowid)
    conn.execute(
        "INSERT INTO source_change_log(source_id, source_url, old_hash, new_hash, change_type) VALUES (?, ?, ?, ?, ?)",
        (source_id, source_url, None, content_hash, "new"),
    )
    return source_id, "new"


def _insert_chunks(conn: sqlite3.Connection, source_id: int, source_name: str, chunks: Iterable[str]) -> int:
    count = 0
    for idx, content in enumerate(chunks):
        citation_label = f"{source_name} section {idx + 1}"
        cursor = conn.execute(
            "INSERT INTO chunks(source_id, chunk_index, content, citation_label) VALUES (?, ?, ?, ?)",
            (source_id, idx, content, citation_label),
        )
        row_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO chunks_fts(rowid, content, citation_label) VALUES (?, ?, ?)",
            (row_id, content, citation_label),
        )
        count += 1
    return count


def build_law_index() -> dict[str, object]:
    settings = get_settings()
    _init_db(settings.law_db_path)

    indexed_sources = 0
    indexed_chunks = 0
    failed_sources = 0
    changed_sources: list[str] = []
    new_sources = 0
    updated_sources = 0

    with sqlite3.connect(settings.law_db_path, timeout=90) as conn:
        _configure_sqlite(conn)
        for root in law_sources.LAW_CRAWL_ROOTS:
            print(f"[index] discovering urls for root: {root.name}")
            urls = _discover_urls(root, settings.cache_dir)
            print(f"[index] discovered {len(urls)} urls for root: {root.name}")

            for i, source_url in enumerate(urls, start=1):
                try:
                    text = _download_source(source_url, settings.cache_dir)
                except requests.RequestException:
                    failed_sources += 1
                    continue
                except Exception:
                    failed_sources += 1
                    continue

                if not text.strip():
                    continue

                source_name = f"{root.name} | {source_url}"
                content_hash = _source_hash(text)
                source_id, change_type = _upsert_source(
                    conn,
                    source_name=source_name,
                    jurisdiction=root.jurisdiction,
                    source_url=source_url,
                    content_hash=content_hash,
                )

                if change_type == "new":
                    new_sources += 1
                    changed_sources.append(source_url)
                elif change_type == "updated":
                    updated_sources += 1
                    changed_sources.append(source_url)

                existing_chunk_count = conn.execute(
                    "SELECT COUNT(*) FROM chunks WHERE source_id = ?", (source_id,)
                ).fetchone()[0]

                if existing_chunk_count == 0:
                    indexed_chunks += _insert_chunks(conn, source_id, root.name, _chunk_text(text))
                indexed_sources += 1

                if i % 20 == 0:
                    print(
                        f"[index] root={root.name} processed={i}/{len(urls)} total_sources={indexed_sources} total_chunks={indexed_chunks}"
                    )

    return {
        "sources": indexed_sources,
        "chunks": indexed_chunks,
        "failed_sources": failed_sources,
        "roots": len(law_sources.LAW_CRAWL_ROOTS),
        "new_sources": new_sources,
        "updated_sources": updated_sources,
        "changed_sources": changed_sources[:40],
    }


def get_recent_source_changes(limit: int = 30) -> list[dict[str, str]]:
    settings = get_settings()
    if not settings.law_db_path.exists():
        return []

    with sqlite3.connect(settings.law_db_path) as conn:
        rows = conn.execute(
            """
            SELECT source_url, old_hash, new_hash, changed_at, change_type
            FROM source_change_log
            ORDER BY changed_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results: list[dict[str, str]] = []
    for row in rows:
        results.append(
            {
                "source_url": row[0],
                "old_hash": row[1] or "",
                "new_hash": row[2] or "",
                "changed_at": row[3] or "",
                "change_type": row[4] or "",
            }
        )
    return results


def get_index_status() -> dict[str, str | int]:
    settings = get_settings()
    if not settings.law_db_path.exists():
        return {
            "db_path": str(settings.law_db_path),
            "source_count": 0,
            "chunk_count": 0,
            "last_crawled_at": "",
        }

    with sqlite3.connect(settings.law_db_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        source_count = 0
        chunk_count = 0
        last_crawled_at = ""

        if "sources" in table_names:
            source_count = int(conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
            max_created = conn.execute("SELECT MAX(created_at) FROM sources").fetchone()[0]
            if max_created:
                last_crawled_at = str(max_created)

        if "chunks" in table_names:
            chunk_count = int(conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])

        if "source_change_log" in table_names:
            max_changed = conn.execute("SELECT MAX(changed_at) FROM source_change_log").fetchone()[0]
            if max_changed:
                last_crawled_at = str(max_changed)

    return {
        "db_path": str(settings.law_db_path),
        "source_count": source_count,
        "chunk_count": chunk_count,
        "last_crawled_at": last_crawled_at,
    }
