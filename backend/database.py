import os
import sqlite3
import json
from datetime import datetime, timezone


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")


def get_database_path():
    """
    Convert DATABASE_URL into a path that sqlite3 can understand.

    Development:
        sqlite:///./app.db -> ./app.db

    Docker:
        sqlite:////data/app.db -> /data/app.db
    """
    if DATABASE_URL.startswith("sqlite:///"):
        return DATABASE_URL.replace("sqlite:///", "", 1)

    return DATABASE_URL


def get_connection():
    database_path = get_database_path()

    connection = sqlite3.connect(database_path)

    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_messages_session_id
        ON messages(session_id)
        """
    )

    connection.commit()
    connection.close()


def save_message(session_id, role, content, metadata=None):
    connection = get_connection()

    metadata_json = json.dumps(metadata) if metadata is not None else None

    created_at = datetime.now(timezone.utc).isoformat()

    connection.execute(
        """
        INSERT INTO messages (
            session_id,
            role,
            content,
            metadata,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session_id,
            role,
            content,
            metadata_json,
            created_at
        )
    )

    connection.commit()
    connection.close()


def get_messages(session_id):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT role, content, metadata
        FROM messages
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,)
    ).fetchall()

    connection.close()

    messages = []

    for row in rows:

        message = {
            "role": row["role"],
            "content": row["content"]
        }

        if row["metadata"]:
            message["metadata"] = json.loads(row["metadata"])

        messages.append(message)

    return messages
