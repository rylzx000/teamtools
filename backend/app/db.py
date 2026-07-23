from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS app_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user', 'admin')),
        default_system_code TEXT,
        initial_password_seed TEXT,
        enabled INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_login_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        module TEXT NOT NULL,
        title TEXT NOT NULL,
        status TEXT NOT NULL,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        submitted_at TEXT,
        ai_request_created_at TEXT,
        ai_request_fetched_at TEXT,
        ai_result_received_at TEXT,
        processing_started_at TEXT,
        finished_at TEXT,
        cancel_requested INTEGER NOT NULL DEFAULT 0,
        cancelled_at TEXT,
        cancelled_by TEXT,
        failure_stage TEXT,
        error_summary TEXT,
        admin_error_detail TEXT,
        rerun_from_task_id TEXT,
        FOREIGN KEY(created_by) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fpa_task_details (
        task_id TEXT PRIMARY KEY,
        system_code TEXT NOT NULL,
        system_name TEXT NOT NULL,
        assessment_mode TEXT NOT NULL,
        count_timing TEXT NOT NULL,
        no_knowledge_mode INTEGER NOT NULL DEFAULT 0,
        target_person_days REAL,
        ai_item_count INTEGER,
        result_item_count INTEGER,
        result_median_person_days REAL,
        target_hit INTEGER,
        quality_flags TEXT,
        validation_errors TEXT,
        model_call_source TEXT,
        model_call_ticket TEXT,
        shared_quota_deducted_at TEXT,
        FOREIGN KEY(task_id) REFERENCES tasks(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS model_key_config (
        id TEXT PRIMARY KEY,
        enabled INTEGER NOT NULL DEFAULT 0,
        provider TEXT NOT NULL,
        api_base TEXT NOT NULL,
        model_name TEXT NOT NULL,
        api_key TEXT,
        default_quota INTEGER NOT NULL DEFAULT 10,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        updated_by TEXT,
        FOREIGN KEY(updated_by) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_model_quotas (
        user_id TEXT PRIMARY KEY,
        enabled INTEGER NOT NULL DEFAULT 1,
        quota_total INTEGER NOT NULL,
        used_count INTEGER NOT NULL DEFAULT 0,
        last_used_at TEXT,
        last_reset_at TEXT,
        reset_by TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(reset_by) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS model_call_events (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        source TEXT NOT NULL CHECK(source IN ('personal_key', 'shared_key')),
        provider TEXT,
        model_name TEXT,
        ticket TEXT,
        status TEXT NOT NULL CHECK(status IN ('issued', 'succeeded', 'failed')),
        deducted INTEGER NOT NULL DEFAULT 0,
        error_summary TEXT,
        created_at TEXT NOT NULL,
        completed_at TEXT,
        FOREIGN KEY(task_id) REFERENCES tasks(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_files (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        file_role TEXT NOT NULL,
        storage_path TEXT NOT NULL,
        original_name TEXT,
        display_name TEXT,
        mime_type TEXT,
        size_bytes INTEGER,
        sha256 TEXT,
        downloadable INTEGER NOT NULL DEFAULT 0,
        viewable INTEGER NOT NULL DEFAULT 0,
        admin_only INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT,
        event_type TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tasks_module_status_created ON tasks(module, status, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_created_by_module_created ON tasks(created_by, module, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_task_files_task_role ON task_files(task_id, file_role)",
    "CREATE INDEX IF NOT EXISTS idx_model_call_events_task ON model_call_events(task_id)",
    "CREATE INDEX IF NOT EXISTS idx_model_call_events_ticket ON model_call_events(ticket)",
)


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        super().__exit__(exc_type, exc, tb)
        self.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def open_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    actual = hash_password(password, salt).split("$", 2)[2]
    return secrets.compare_digest(actual, expected)


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes"}


def initialize_database(db_path: Path, *, seed_dev_users_enabled: bool | None = None) -> None:
    with open_connection(db_path) as conn:
        migrate_legacy_tables(conn)
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)
        migrate_current_schema(conn)
        conn.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)", ("schema_version", "2"))
        should_seed = env_flag("TEAMTOOLS_SEED_DEV_USERS") if seed_dev_users_enabled is None else seed_dev_users_enabled
        if should_seed:
            seed_dev_users(conn)
        conn.commit()


def migrate_legacy_tables(conn: sqlite3.Connection) -> None:
    legacy_checks = {
        "tasks": "created_by",
        "task_events": "event_type",
    }
    for table, required_column in legacy_checks.items():
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        if not exists:
            continue
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if required_column in columns:
            continue
        backup = f"{table}_legacy_v1"
        backup_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (backup,),
        ).fetchone()
        if not backup_exists:
            conn.execute(f"ALTER TABLE {table} RENAME TO {backup}")


def migrate_current_schema(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "default_system_code" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN default_system_code TEXT")
    if "initial_password_seed" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN initial_password_seed TEXT")
    fpa_columns = {row["name"] for row in conn.execute("PRAGMA table_info(fpa_task_details)").fetchall()}
    if "model_call_source" not in fpa_columns:
        conn.execute("ALTER TABLE fpa_task_details ADD COLUMN model_call_source TEXT")
    if "model_call_ticket" not in fpa_columns:
        conn.execute("ALTER TABLE fpa_task_details ADD COLUMN model_call_ticket TEXT")
    if "shared_quota_deducted_at" not in fpa_columns:
        conn.execute("ALTER TABLE fpa_task_details ADD COLUMN shared_quota_deducted_at TEXT")


def seed_dev_users(conn: sqlite3.Connection) -> None:
    # Technical fallback for local tests and compatibility; production users should come from the import script.
    users = [
        ("dev-admin", "admin", "管理员", "admin", "admin123", "admin123", None),
        ("dev-demo", "demo", "演示用户", "user", "demo123", "demo123", None),
    ]
    for user_id, username, display_name, role, password, initial_password_seed, default_system_code in users:
        exists = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
        if exists:
            conn.execute(
                """
                UPDATE users
                SET default_system_code = COALESCE(default_system_code, ?),
                    initial_password_seed = COALESCE(initial_password_seed, ?),
                    updated_at = ?
                WHERE username = ?
                """,
                (default_system_code, initial_password_seed, utc_now(), username),
            )
            continue
        now = utc_now()
        conn.execute(
            """
            INSERT INTO users(
                id, username, display_name, password_hash, role,
                default_system_code, initial_password_seed, enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                user_id,
                username,
                display_name,
                hash_password(password),
                role,
                default_system_code,
                initial_password_seed,
                now,
                now,
            ),
        )


def task_count(db_path: Path) -> int:
    with open_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM tasks").fetchone()
        return int(row["count"] if row else 0)


def fetch_one(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def fetch_all(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def write_task_event(
    db_path: Path,
    task_id: str | None,
    event_type: str,
    message: str,
    level: str = "info",
) -> None:
    with open_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO task_events(task_id, event_type, level, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, event_type, level, message, utc_now()),
        )
        conn.commit()


def next_pending_task(db_path: Path) -> sqlite3.Row | None:
    with open_connection(db_path) as conn:
        return conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE status = 'waiting_ai_call'
            ORDER BY created_at, id
            LIMIT 1
            """
        ).fetchone()


def update_task_status(db_path: Path, task_id: str, status: str, message: str | None = None) -> None:
    with open_connection(db_path) as conn:
        now = utc_now()
        conn.execute(
            """
            UPDATE tasks
            SET status = ?,
                updated_at = ?,
                finished_at = CASE WHEN ? IN ('completed', 'failed', 'canceled') THEN ? ELSE finished_at END,
                error_summary = COALESCE(?, error_summary)
            WHERE id = ?
            """,
            (status, now, status, now, message, task_id),
        )
        conn.commit()
