from __future__ import annotations

import secrets
import sqlite3
from pathlib import Path
from typing import Any

from ...db import fetch_all, fetch_one, open_connection, utc_now


CONFIG_ID = "shared_default"
DEFAULT_PROVIDER = "deepseek"
DEFAULT_API_BASE = "https://api.deepseek.com"
DEFAULT_MODEL_NAME = "deepseek-v4-flash"
DEFAULT_QUOTA = 10
SOURCE_PERSONAL = "personal_key"
SOURCE_SHARED = "shared_key"
QUOTA_EXHAUSTED_MESSAGE = "公用apikey个人用量已用完，请输入可用的apikey"


class ModelKeyError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400, stage: str = "model_key"):
        super().__init__(message)
        self.status_code = status_code
        self.stage = stage


def get_public_config(db_path: Path) -> dict[str, Any]:
    with open_connection(db_path) as conn:
        row = get_config_row(conn)
    return public_config(row)


def save_admin_config(db_path: Path, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    default_quota = parse_non_negative_int(payload.get("default_quota"), DEFAULT_QUOTA, "默认个人额度")
    provider = str(payload.get("provider") or DEFAULT_PROVIDER).strip() or DEFAULT_PROVIDER
    api_base = str(payload.get("api_base") or DEFAULT_API_BASE).strip() or DEFAULT_API_BASE
    model_name = str(payload.get("model_name") or DEFAULT_MODEL_NAME).strip() or DEFAULT_MODEL_NAME
    enabled = bool(payload.get("enabled"))
    incoming_key = str(payload.get("api_key") or "")
    now = utc_now()
    with open_connection(db_path) as conn:
        existing = get_config_row(conn, include_default=False)
        api_key = incoming_key if incoming_key else (existing.get("api_key") if existing else None)
        if existing:
            conn.execute(
                """
                UPDATE model_key_config
                SET enabled = ?, provider = ?, api_base = ?, model_name = ?, api_key = ?,
                    default_quota = ?, updated_at = ?, updated_by = ?
                WHERE id = ?
                """,
                (int(enabled), provider, api_base, model_name, api_key, default_quota, now, user["id"], CONFIG_ID),
            )
        else:
            conn.execute(
                """
                INSERT INTO model_key_config(id, enabled, provider, api_base, model_name, api_key,
                                             default_quota, created_at, updated_at, updated_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (CONFIG_ID, int(enabled), provider, api_base, model_name, api_key, default_quota, now, now, user["id"]),
            )
        conn.commit()
        row = get_config_row(conn)
    return public_config(row)


def list_admin_quotas(db_path: Path) -> list[dict[str, Any]]:
    with open_connection(db_path) as conn:
        users = fetch_all(
            conn,
            """
            SELECT id, username, display_name, role
            FROM users
            WHERE enabled = 1
            ORDER BY username
            """,
        )
        items = []
        for user in users:
            quota = get_or_create_quota(conn, user["id"])
            items.append(public_quota(quota, user))
        conn.commit()
    return items


def save_user_quota(db_path: Path, target_user_id: str, admin_user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    quota_total = parse_non_negative_int(payload.get("quota_total"), DEFAULT_QUOTA, "个人额度")
    enabled = bool(payload.get("enabled", True))
    now = utc_now()
    with open_connection(db_path) as conn:
        ensure_user_exists(conn, target_user_id)
        get_or_create_quota(conn, target_user_id)
        conn.execute(
            """
            UPDATE user_model_quotas
            SET enabled = ?, quota_total = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (int(enabled), quota_total, now, target_user_id),
        )
        conn.commit()
        quota = quota_with_user(conn, target_user_id)
    return quota


def reset_user_quota(db_path: Path, target_user_id: str, admin_user: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    with open_connection(db_path) as conn:
        ensure_user_exists(conn, target_user_id)
        get_or_create_quota(conn, target_user_id)
        conn.execute(
            """
            UPDATE user_model_quotas
            SET used_count = 0, last_reset_at = ?, reset_by = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (now, admin_user["id"], now, target_user_id),
        )
        conn.commit()
        quota = quota_with_user(conn, target_user_id)
    return quota


def bulk_set_quotas(db_path: Path, admin_user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    quota_total = parse_non_negative_int(payload.get("quota_total"), DEFAULT_QUOTA, "统一额度")
    now = utc_now()
    with open_connection(db_path) as conn:
        user_ids = [row["id"] for row in conn.execute("SELECT id FROM users WHERE enabled = 1").fetchall()]
        for user_id in user_ids:
            get_or_create_quota(conn, user_id)
            conn.execute(
                "UPDATE user_model_quotas SET quota_total = ?, updated_at = ? WHERE user_id = ?",
                (quota_total, now, user_id),
            )
        conn.commit()
    return {"updated": len(user_ids), "quota_total": quota_total}


def bulk_reset_quotas(db_path: Path, admin_user: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    with open_connection(db_path) as conn:
        user_ids = [row["id"] for row in conn.execute("SELECT id FROM users WHERE enabled = 1").fetchall()]
        for user_id in user_ids:
            get_or_create_quota(conn, user_id)
        conn.execute(
            """
            UPDATE user_model_quotas
            SET used_count = 0, last_reset_at = ?, reset_by = ?, updated_at = ?
            WHERE user_id IN (SELECT id FROM users WHERE enabled = 1)
            """,
            (now, admin_user["id"], now),
        )
        conn.commit()
    return {"updated": len(user_ids)}


def issue_shared_key(db_path: Path, task: dict[str, Any]) -> dict[str, Any]:
    if task["status"] != "waiting_ai_call":
        raise ModelKeyError("当前状态不能领取公用 Key", 409, "shared_model_key")
    with open_connection(db_path) as conn:
        config = get_config_row(conn)
        if not config["enabled"]:
            raise ModelKeyError("团队公用 Key 未启用，请输入可用的apikey", 409, "shared_model_key")
        if not config.get("api_key"):
            raise ModelKeyError("团队公用 Key 未配置，请输入可用的apikey", 409, "shared_model_key")
        quota = get_or_create_quota(conn, task["created_by"])
        if not quota["enabled"] or remaining(quota) <= 0:
            raise ModelKeyError(QUOTA_EXHAUSTED_MESSAGE, 409, "shared_model_key")

        ticket = "mk-" + secrets.token_urlsafe(24)
        now = utc_now()
        conn.execute(
            """
            UPDATE fpa_task_details
            SET model_call_source = ?, model_call_ticket = ?
            WHERE task_id = ?
            """,
            (SOURCE_SHARED, ticket, task["id"]),
        )
        conn.execute(
            """
            INSERT INTO model_call_events(id, task_id, user_id, source, provider, model_name,
                                          ticket, status, deducted, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'issued', 0, ?)
            """,
            (
                "event-" + secrets.token_hex(12),
                task["id"],
                task["created_by"],
                SOURCE_SHARED,
                config["provider"],
                config["model_name"],
                ticket,
                now,
            ),
        )
        conn.commit()
        quota = get_or_create_quota(conn, task["created_by"])
    return {
        "provider": config["provider"],
        "api_base": config["api_base"],
        "model": config["model_name"],
        "api_key": config["api_key"],
        "ticket": ticket,
        "quota": quota_summary(quota),
    }


def record_personal_call(
    db_path: Path,
    task_id: str,
    user_id: str,
    *,
    provider: str | None = None,
    model_name: str | None = None,
    status: str = "succeeded",
    error_summary: str | None = None,
) -> None:
    now = utc_now()
    with open_connection(db_path) as conn:
        conn.execute(
            "UPDATE fpa_task_details SET model_call_source = ?, model_call_ticket = NULL WHERE task_id = ?",
            (SOURCE_PERSONAL, task_id),
        )
        conn.execute(
            """
            INSERT INTO model_call_events(id, task_id, user_id, source, provider, model_name,
                                          status, deducted, error_summary, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                "event-" + secrets.token_hex(12),
                task_id,
                user_id,
                SOURCE_PERSONAL,
                provider,
                model_name,
                status,
                truncate(error_summary),
                now,
                now,
            ),
        )
        conn.commit()


def record_call_failure(
    db_path: Path,
    task_id: str,
    *,
    source: str | None,
    ticket: str | None,
    user_id: str,
    error_summary: str,
    provider: str | None = None,
    model_name: str | None = None,
) -> None:
    source = normalize_source(source)
    if source == SOURCE_SHARED and ticket:
        with open_connection(db_path) as conn:
            conn.execute(
                """
                UPDATE model_call_events
                SET status = 'failed', error_summary = ?, completed_at = ?
                WHERE task_id = ? AND ticket = ? AND source = ?
                """,
                (truncate(error_summary), utc_now(), task_id, ticket, SOURCE_SHARED),
            )
            conn.commit()
        return
    if source == SOURCE_PERSONAL:
        record_personal_call(
            db_path,
            task_id,
            user_id,
            provider=provider,
            model_name=model_name,
            status="failed",
            error_summary=error_summary,
        )


def deduct_shared_quota_once(db_path: Path, task_id: str, *, excel_exists: bool) -> dict[str, Any]:
    if not excel_exists:
        return {"deducted": False, "reason": "excel_missing"}
    now = utc_now()
    with open_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT t.id, t.created_by, d.model_call_source, d.model_call_ticket, d.shared_quota_deducted_at
            FROM tasks t
            JOIN fpa_task_details d ON d.task_id = t.id
            WHERE t.id = ?
            """,
            (task_id,),
        ).fetchone()
        if not row:
            return {"deducted": False, "reason": "task_missing"}
        if row["model_call_source"] != SOURCE_SHARED:
            return {"deducted": False, "reason": "not_shared_key"}
        if row["shared_quota_deducted_at"]:
            return {"deducted": False, "reason": "already_deducted"}
        quota = get_or_create_quota(conn, row["created_by"])
        conn.execute(
            """
            UPDATE user_model_quotas
            SET used_count = used_count + 1, last_used_at = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (now, now, row["created_by"]),
        )
        conn.execute(
            "UPDATE fpa_task_details SET shared_quota_deducted_at = ? WHERE task_id = ?",
            (now, task_id),
        )
        if row["model_call_ticket"]:
            conn.execute(
                """
                UPDATE model_call_events
                SET status = 'succeeded', deducted = 1, completed_at = ?
                WHERE task_id = ? AND ticket = ? AND source = ?
                """,
                (now, task_id, row["model_call_ticket"], SOURCE_SHARED),
            )
        conn.commit()
    return {"deducted": True}


def quota_summary_for_user(db_path: Path, user_id: str) -> dict[str, Any]:
    with open_connection(db_path) as conn:
        quota = get_or_create_quota(conn, user_id)
        conn.commit()
    return quota_summary(quota)


def normalize_source(value: Any) -> str | None:
    raw = str(value or "").strip()
    if raw in {SOURCE_PERSONAL, SOURCE_SHARED}:
        return raw
    return None


def get_config_row(conn: sqlite3.Connection, *, include_default: bool = True) -> dict[str, Any] | None:
    row = fetch_one(conn, "SELECT * FROM model_key_config WHERE id = ?", (CONFIG_ID,))
    if row or not include_default:
        return row
    return {
        "id": CONFIG_ID,
        "enabled": 0,
        "provider": DEFAULT_PROVIDER,
        "api_base": DEFAULT_API_BASE,
        "model_name": DEFAULT_MODEL_NAME,
        "api_key": None,
        "default_quota": DEFAULT_QUOTA,
        "created_at": None,
        "updated_at": None,
        "updated_by": None,
    }


def get_or_create_quota(conn: sqlite3.Connection, user_id: str) -> dict[str, Any]:
    row = fetch_one(conn, "SELECT * FROM user_model_quotas WHERE user_id = ?", (user_id,))
    if row:
        return row
    config = get_config_row(conn)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO user_model_quotas(user_id, enabled, quota_total, used_count, created_at, updated_at)
        VALUES (?, 1, ?, 0, ?, ?)
        """,
        (user_id, int(config["default_quota"]), now, now),
    )
    return fetch_one(conn, "SELECT * FROM user_model_quotas WHERE user_id = ?", (user_id,))


def quota_with_user(conn: sqlite3.Connection, user_id: str) -> dict[str, Any]:
    row = fetch_one(
        conn,
        """
        SELECT q.*, u.username, u.display_name, u.role
        FROM user_model_quotas q
        JOIN users u ON u.id = q.user_id
        WHERE q.user_id = ?
        """,
        (user_id,),
    )
    if not row:
        raise ModelKeyError("用户额度不存在", 404, "model_quota")
    user = {"id": user_id, "username": row["username"], "display_name": row["display_name"], "role": row["role"]}
    return public_quota(row, user)


def ensure_user_exists(conn: sqlite3.Connection, user_id: str) -> None:
    if not fetch_one(conn, "SELECT id FROM users WHERE id = ? AND enabled = 1", (user_id,)):
        raise ModelKeyError("用户不存在", 404, "model_quota")


def public_config(row: dict[str, Any]) -> dict[str, Any]:
    key = row.get("api_key") or ""
    return {
        "enabled": bool(row["enabled"]),
        "provider": row["provider"],
        "api_base": row["api_base"],
        "model_name": row["model_name"],
        "default_quota": int(row["default_quota"]),
        "has_api_key": bool(key),
        "masked_key": mask_key(key),
    }


def public_quota(quota: dict[str, Any], user: dict[str, Any] | None = None) -> dict[str, Any]:
    data = {
        "user_id": quota["user_id"],
        "enabled": bool(quota["enabled"]),
        "quota_total": int(quota["quota_total"]),
        "used_count": int(quota["used_count"]),
        "remaining": remaining(quota),
        "last_used_at": quota.get("last_used_at"),
        "last_reset_at": quota.get("last_reset_at"),
    }
    if user:
        data.update(
            {
                "username": user["username"],
                "display_name": user["display_name"],
                "role": user["role"],
            }
        )
    return data


def quota_summary(quota: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": bool(quota["enabled"]),
        "quota_total": int(quota["quota_total"]),
        "used_count": int(quota["used_count"]),
        "remaining": remaining(quota),
    }


def remaining(quota: dict[str, Any]) -> int:
    return max(0, int(quota["quota_total"]) - int(quota["used_count"]))


def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}***{key[-4:]}"


def parse_non_negative_int(value: Any, default: int, label: str) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ModelKeyError(f"{label}必须是非负整数", 400, "model_quota") from exc
    if parsed < 0:
        raise ModelKeyError(f"{label}必须是非负整数", 400, "model_quota")
    return parsed


def truncate(value: str | None, limit: int = 500) -> str | None:
    if value is None:
        return None
    return str(value)[:limit]
