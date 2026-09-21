"""Persistência de permissões e cotas de consulta do portal."""

from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path


DATA_DIR = Path(os.environ.get("APP_DATA_DIR", Path(__file__).resolve().parent / "data"))
DB_PATH = DATA_DIR / "portal.db"


def _connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize() -> None:
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                daily_limit INTEGER NOT NULL DEFAULT 10,
                extra_questions INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS daily_usage (
                email TEXT NOT NULL,
                usage_date TEXT NOT NULL,
                questions INTEGER NOT NULL DEFAULT 0,
                extra_questions INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (email, usage_date),
                FOREIGN KEY (email) REFERENCES users(email) ON DELETE CASCADE
            );
            """
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(daily_usage)")}
        if "extra_questions" not in columns:
            connection.execute(
                "ALTER TABLE daily_usage ADD COLUMN extra_questions INTEGER NOT NULL DEFAULT 0"
            )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def grant_access(email: str, daily_limit: int) -> None:
    email = normalize_email(email)
    if not email or "@" not in email:
        raise ValueError("Informe um e-mail válido.")
    if not 1 <= daily_limit <= 10_000:
        raise ValueError("O limite diário deve estar entre 1 e 10.000.")
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO users (email, enabled, daily_limit)
            VALUES (?, 1, ?)
            ON CONFLICT(email) DO UPDATE SET enabled = 1, daily_limit = excluded.daily_limit
            """,
            (email, daily_limit),
        )


def revoke_access(email: str) -> None:
    with _connection() as connection:
        connection.execute("UPDATE users SET enabled = 0 WHERE email = ?", (normalize_email(email),))


def add_extra_questions(email: str, quantity: int) -> None:
    if not 1 <= quantity <= 10_000:
        raise ValueError("A liberação adicional deve estar entre 1 e 10.000 perguntas.")
    with _connection() as connection:
        user = connection.execute(
            "SELECT 1 FROM users WHERE email = ? AND enabled = 1", (normalize_email(email),)
        ).fetchone()
        if not user:
            raise ValueError("Usuário autorizado não encontrado.")
        connection.execute(
            """
            INSERT INTO daily_usage (email, usage_date, questions, extra_questions) VALUES (?, ?, 0, ?)
            ON CONFLICT(email, usage_date) DO UPDATE
            SET extra_questions = extra_questions + excluded.extra_questions
            """,
            (normalize_email(email), date.today().isoformat(), quantity),
        )


def user_status(email: str) -> dict | None:
    email = normalize_email(email)
    today = date.today().isoformat()
    with _connection() as connection:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return None
        used = connection.execute(
            "SELECT questions, extra_questions FROM daily_usage WHERE email = ? AND usage_date = ?",
            (email, today),
        ).fetchone()
    questions = used["questions"] if used else 0
    extra_questions = used["extra_questions"] if used else 0
    allowed = user["daily_limit"] + extra_questions
    return {
        "email": email,
        "enabled": bool(user["enabled"]),
        "daily_limit": user["daily_limit"],
        "extra_questions": extra_questions,
        "questions": questions,
        "remaining": max(0, allowed - questions),
    }


def consume_question(email: str) -> dict:
    """Reserva uma pergunta de forma atômica e retorna o saldo atualizado."""
    email = normalize_email(email)
    today = date.today().isoformat()
    with _connection() as connection:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not user["enabled"]:
            raise PermissionError("Seu acesso a consultas não está autorizado.")
        usage = connection.execute(
            "SELECT questions, extra_questions FROM daily_usage WHERE email = ? AND usage_date = ?",
            (email, today),
        ).fetchone()
        questions = usage["questions"] if usage else 0
        allowed = user["daily_limit"] + (usage["extra_questions"] if usage else 0)
        if questions >= allowed:
            raise PermissionError("Seu limite diário de consultas foi atingido.")
        connection.execute(
            """
            INSERT INTO daily_usage (email, usage_date, questions, extra_questions) VALUES (?, ?, 1, 0)
            ON CONFLICT(email, usage_date) DO UPDATE SET questions = questions + 1
            """,
            (email, today),
        )
    return user_status(email) or {}


def list_users() -> list[dict]:
    today = date.today().isoformat()
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT u.email, u.enabled, u.daily_limit,
                   COALESCE(d.extra_questions, 0) AS extra_questions,
                   COALESCE(d.questions, 0) AS questions
            FROM users u
            LEFT JOIN daily_usage d ON d.email = u.email AND d.usage_date = ?
            ORDER BY u.email
            """,
            (today,),
        ).fetchall()
    return [
        {
            "E-mail": row["email"],
            "Ativo": "Sim" if row["enabled"] else "Não",
            "Limite diário": row["daily_limit"],
            "Perguntas extras": row["extra_questions"],
            "Usadas hoje": row["questions"],
            "Restantes": max(0, row["daily_limit"] + row["extra_questions"] - row["questions"]),
        }
        for row in rows
    ]
