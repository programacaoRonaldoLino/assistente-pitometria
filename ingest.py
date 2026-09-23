"""Indexação de manuais exclusivamente no OpenAI Vector Store."""

from __future__ import annotations

from pathlib import Path

from access_control import DATA_DIR
from rag import remove_manual as remove_remote_manual, upload_manual

DOCS_DIR = DATA_DIR / "docs"


def index_pdf(pdf_path: Path) -> None:
    """Envia o PDF para a OpenAI; não extrai conteúdo no servidor."""
    upload_manual(pdf_path)


def delete_manual(name: str) -> str | None:
    """Remove o manual da OpenAI e do diretório persistente."""
    if not name or Path(name).name != name or Path(name).suffix.lower() != ".pdf":
        raise ValueError("Nome de manual inválido.")

    warning = remove_remote_manual(name)
    path = DOCS_DIR / name
    if path.exists():
        path.unlink()
    return warning
