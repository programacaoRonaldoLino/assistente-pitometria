"""Indexação de manuais exclusivamente no OpenAI Vector Store."""

from __future__ import annotations

from pathlib import Path

from access_control import DATA_DIR
from rag import upload_manual

DOCS_DIR = DATA_DIR / "docs"


def index_pdf(pdf_path: Path) -> None:
    """Envia o PDF para a OpenAI; não extrai conteúdo no servidor."""
    upload_manual(pdf_path)
