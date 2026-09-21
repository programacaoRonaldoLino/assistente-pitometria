"""Compatibilidade para indexação dos PDFs no OpenAI Vector Store."""

from __future__ import annotations

from pathlib import Path

from access_control import DATA_DIR
from local_search import index_pdf as index_local_pdf
from rag import upload_manual

DOCS_DIR = DATA_DIR / "docs"


def index_pdf(pdf_path: Path) -> int:
    pages = index_local_pdf(pdf_path)
    upload_manual(pdf_path)
    return pages
