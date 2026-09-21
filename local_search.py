"""Busca textual local para responder consultas simples sem chamar a IA."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pdfplumber

from access_control import DATA_DIR


DB_PATH = DATA_DIR / "portal.db"
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]{3,}")


def _connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def initialize() -> None:
    with _connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS local_pages (
                source TEXT NOT NULL,
                page INTEGER NOT NULL,
                content TEXT NOT NULL,
                PRIMARY KEY (source, page)
            )
            """
        )


def index_pdf(path: Path) -> int:
    """Extrai e persiste o texto de cada página do PDF."""
    pages: list[tuple[str, int, str]] = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append((path.name, number, text))
    with _connection() as connection:
        connection.execute("DELETE FROM local_pages WHERE source = ?", (path.name,))
        connection.executemany(
            "INSERT INTO local_pages (source, page, content) VALUES (?, ?, ?)", pages
        )
    return len(pages)


def search(question: str, selected_sources: list[str] | None = None, limit: int = 5) -> list[dict]:
    words = list(dict.fromkeys(word.lower() for word in WORD_RE.findall(question)))
    if not words:
        return []
    with _connection() as connection:
        rows = connection.execute("SELECT source, page, content FROM local_pages").fetchall()
    results = []
    selected = set(selected_sources or [])
    for source, page, content in rows:
        if selected and source not in selected:
            continue
        normalized = content.lower()
        score = sum(normalized.count(word) for word in words)
        if score:
            results.append(
                {
                    "score": score,
                    "text": content[:1_200],
                    "metadata": {"source": source, "page": page},
                }
            )
    return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]
