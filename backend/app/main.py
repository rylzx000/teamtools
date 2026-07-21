from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import get_config
from .db import fetch_one, initialize_database, open_connection, task_count, utc_now, verify_password
from .modules.fpa.service import (
    FpaError,
    cancel_task,
    confirm_system_relevance,
    create_task,
    download_excel_path,
    ensure_resources,
    fetch_ai_request,
    get_form_config,
    handle_ai_result,
    issue_shared_model_key,
    list_tasks,
    load_systems,
    rerun_task,
    task_detail,
)
from .modules.model_keys.service import (
    ModelKeyError,
    bulk_reset_quotas,
    bulk_set_quotas,
    get_public_config as get_model_key_config,
    list_admin_quotas,
    reset_user_quota,
    save_admin_config as save_model_key_config,
    save_user_quota,
)


SESSION_COOKIE = "teamtools_session"


def create_app(
    data_dir: Path | None = None,
    frontend_dist_dir: Path | None = None,
    db_path: Path | None = None,
) -> FastAPI:
    config = get_config()
    app_data_dir = Path(data_dir or config.data_dir)
    app_db_path = Path(db_path or app_data_dir / "teamtools.db")
    app_frontend_dist = Path(frontend_dist_dir or config.frontend_dist_dir)
    initialize_database(app_db_path, seed_dev_users_enabled=config.seed_dev_users)
    ensure_resources(app_data_dir)

    app = FastAPI(title="TeamTools", version="0.1.0")
    app.state.data_dir = app_data_dir
    app.state.db_path = app_db_path
    app.state.frontend_dist_dir = app_frontend_dist

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(FpaError)
    async def fpa_error_handler(_request: Request, exc: FpaError) -> JSONResponse:
        return JSONResponse({"detail": str(exc), "stage": exc.stage}, status_code=exc.status_code)

    @app.exception_handler(ModelKeyError)
    async def model_key_error_handler(_request: Request, exc: ModelKeyError) -> JSONResponse:
        return JSONResponse({"detail": str(exc), "stage": exc.stage}, status_code=exc.status_code)

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "teamtools-backend",
            "data_dir": str(app_data_dir),
            "db_path": str(app_db_path),
            "frontend_dist_exists": app_frontend_dist.exists(),
        }

    @app.get("/api/runtime")
    def runtime() -> dict[str, object]:
        return {
            "project_root": str(config.project_root),
            "data_dir": str(app_data_dir),
            "db_path": str(app_db_path),
            "frontend_dist_dir": str(app_frontend_dist),
            "task_count": task_count(app_db_path),
        }

    @app.post("/api/auth/login")
    async def login(request: Request) -> Response:
        payload = await read_payload(request)
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        with open_connection(app_db_path) as conn:
            user = fetch_one(conn, "SELECT * FROM users WHERE username = ? AND enabled = 1", (username,))
            if not user or not verify_password(password, user["password_hash"]):
                return JSONResponse({"detail": "账号或密码错误"}, status_code=401)
            token = secrets.token_urlsafe(32)
            now = datetime.now(timezone.utc)
            expires = now + timedelta(days=7)
            conn.execute(
                """
                INSERT INTO sessions(token, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (token, user["id"], now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")),
            )
            conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (utc_now(), utc_now(), user["id"]))
            conn.commit()
        response = JSONResponse({"user": public_user(user)})
        response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=7 * 24 * 3600)
        return response

    @app.post("/api/auth/logout")
    async def logout(request: Request) -> Response:
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            with open_connection(app_db_path) as conn:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
        response = JSONResponse({"ok": True})
        response.delete_cookie(SESSION_COOKIE)
        return response

    @app.get("/api/auth/me")
    async def me(request: Request) -> dict[str, Any]:
        return {"user": public_user(require_user(request))}

    @app.get("/api/admin/model-key/config")
    async def admin_model_key_config(request: Request) -> dict[str, Any]:
        require_admin(request)
        return {"config": get_model_key_config(app_db_path)}

    @app.post("/api/admin/model-key/config")
    async def admin_save_model_key_config(request: Request) -> dict[str, Any]:
        user = require_admin(request)
        payload = await read_payload(request)
        return {"config": save_model_key_config(app_db_path, user, payload)}

    @app.get("/api/admin/model-key/quotas")
    async def admin_model_key_quotas(request: Request) -> dict[str, Any]:
        require_admin(request)
        items = list_admin_quotas(app_db_path)
        return {"items": items, "total": len(items)}

    @app.post("/api/admin/model-key/quotas/bulk-set")
    async def admin_model_key_quotas_bulk_set(request: Request) -> dict[str, Any]:
        user = require_admin(request)
        return bulk_set_quotas(app_db_path, user, await read_payload(request))

    @app.post("/api/admin/model-key/quotas/bulk-reset")
    async def admin_model_key_quotas_bulk_reset(request: Request) -> dict[str, Any]:
        user = require_admin(request)
        return bulk_reset_quotas(app_db_path, user)

    @app.post("/api/admin/model-key/quotas/{user_id}")
    async def admin_save_model_key_quota(request: Request, user_id: str) -> dict[str, Any]:
        user = require_admin(request)
        return {"quota": save_user_quota(app_db_path, user_id, user, await read_payload(request))}

    @app.post("/api/admin/model-key/quotas/{user_id}/reset")
    async def admin_reset_model_key_quota(request: Request, user_id: str) -> dict[str, Any]:
        user = require_admin(request)
        return {"quota": reset_user_quota(app_db_path, user_id, user)}

    @app.get("/api/fpa/systems")
    async def fpa_systems(request: Request) -> dict[str, Any]:
        require_user(request)
        return {"items": load_systems(app_data_dir)}

    @app.get("/api/fpa/form-config")
    async def fpa_form_config(request: Request) -> dict[str, Any]:
        require_user(request)
        return get_form_config(app_data_dir)

    @app.post("/api/fpa/tasks")
    async def fpa_create_task(request: Request) -> dict[str, Any]:
        user = require_user(request)
        payload = await read_submission_payload(request)
        target = parse_optional_float(payload.get("target_person_days"))
        return create_task(
            app_db_path,
            app_data_dir,
            user,
            system_code=str(payload.get("system_code") or ""),
            title=str(payload.get("title") or ""),
            input_text=str(payload.get("input_text") or ""),
            uploaded_text=str(payload.get("uploaded_text") or ""),
            uploaded_name=str(payload.get("uploaded_name") or ""),
            target_person_days=target,
            count_timing=str(payload.get("count_timing") or "估算中期"),
            integrity_level=str(
                payload.get("integrity_level")
                or "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式"
            ),
        )

    @app.get("/api/fpa/tasks")
    async def fpa_list_tasks(request: Request, status: str | None = None) -> dict[str, Any]:
        return list_tasks(app_db_path, require_user(request), status)

    @app.get("/api/fpa/tasks/{task_id}")
    async def fpa_get_task(request: Request, task_id: str) -> dict[str, Any]:
        return task_detail(app_db_path, app_data_dir, task_id, require_user(request))

    @app.get("/api/fpa/tasks/{task_id}/ai-request")
    async def fpa_get_ai_request(request: Request, task_id: str) -> dict[str, Any]:
        return fetch_ai_request(app_db_path, app_data_dir, task_id, require_user(request))

    @app.post("/api/fpa/tasks/{task_id}/system-relevance/confirm")
    async def fpa_confirm_system_relevance(request: Request, task_id: str) -> dict[str, Any]:
        return confirm_system_relevance(app_db_path, app_data_dir, task_id, require_user(request))

    @app.post("/api/fpa/tasks/{task_id}/shared-model-key")
    async def fpa_shared_model_key(request: Request, task_id: str) -> dict[str, Any]:
        return issue_shared_model_key(app_db_path, task_id, require_user(request))

    @app.post("/api/fpa/tasks/{task_id}/ai-result")
    async def fpa_post_ai_result(request: Request, task_id: str) -> dict[str, Any]:
        payload = await read_payload(request)
        return handle_ai_result(app_db_path, app_data_dir, task_id, require_user(request), payload)

    @app.post("/api/fpa/tasks/{task_id}/cancel")
    async def fpa_cancel(request: Request, task_id: str) -> dict[str, Any]:
        return cancel_task(app_db_path, task_id, require_user(request))

    @app.post("/api/fpa/tasks/{task_id}/rerun")
    async def fpa_rerun(request: Request, task_id: str) -> dict[str, Any]:
        return rerun_task(app_db_path, app_data_dir, task_id, require_user(request))

    @app.get("/api/fpa/tasks/{task_id}/download/excel")
    async def fpa_download_excel(request: Request, task_id: str) -> FileResponse:
        path = download_excel_path(app_db_path, app_data_dir, task_id, require_user(request))
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="FPA工作量评估.xlsx",
        )

    if app_frontend_dist.exists() and (app_frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=app_frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def frontend(full_path: str = "") -> Response:
        index_html = app_frontend_dist / "index.html"
        if index_html.exists():
            return FileResponse(index_html)
        return HTMLResponse(
            """
            <!doctype html>
            <html lang="zh-CN">
              <head><meta charset="UTF-8" /><title>TeamTools</title></head>
              <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>TeamTools</h1>
                <p>前端静态文件尚未构建。请先运行 scripts/build-frontend.ps1。</p>
              </body>
            </html>
            """.strip()
        )

    return app


def require_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise FpaError("请先登录", 401, "auth")
    with open_connection(request.app.state.db_path) as conn:
        row = fetch_one(
            conn,
            """
            SELECT u.*
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ? AND u.enabled = 1 AND s.expires_at > ?
            """,
            (token, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
    if not row:
        raise FpaError("登录已失效", 401, "auth")
    return row


def require_admin(request: Request) -> dict[str, Any]:
    user = require_user(request)
    if user["role"] != "admin":
        raise FpaError("需要管理员权限", 403, "permission")
    return user


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "default_system_code": user.get("default_system_code"),
    }


async def read_submission_payload(request: Request) -> dict[str, Any]:
    payload = await read_payload(request)
    if "input_file" in payload and not payload.get("uploaded_text"):
        payload["uploaded_text"] = str(payload.get("input_file") or "")
    return payload


async def read_payload(request: Request) -> dict[str, Any]:
    body = await request.body()
    if not body:
        return {}
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return json.loads(body.decode("utf-8"))
    if "application/x-www-form-urlencoded" in content_type:
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        return {key: values[-1] if values else "" for key, values in parsed.items()}
    if "multipart/form-data" in content_type:
        return parse_simple_multipart(body, content_type)
    return {}


def parse_simple_multipart(body: bytes, content_type: str) -> dict[str, Any]:
    marker = "boundary="
    if marker not in content_type:
        return {}
    boundary = content_type.split(marker, 1)[1].split(";", 1)[0].strip().strip('"')
    delimiter = ("--" + boundary).encode("utf-8")
    payload: dict[str, Any] = {}
    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--" or b"\r\n\r\n" not in part:
            continue
        raw_headers, value = part.split(b"\r\n\r\n", 1)
        value = value.rstrip(b"\r\n-")
        headers_text = raw_headers.decode("utf-8", errors="ignore")
        name = None
        filename = None
        for segment in headers_text.split(";"):
            segment = segment.strip()
            if segment.startswith("name="):
                name = segment.split("=", 1)[1].strip('"')
            if segment.startswith("filename="):
                filename = segment.split("=", 1)[1].strip('"')
        if not name:
            continue
        if filename:
            if not filename.lower().endswith(".md"):
                raise FpaError("上传文件只支持 Markdown", 400, "task_create")
            if len(value) > 256 * 1024:
                raise FpaError("上传文件不能超过 256KB", 400, "task_create")
            payload["uploaded_text"] = value.decode("utf-8", errors="replace")
            payload["uploaded_name"] = filename
        else:
            payload[name] = value.decode("utf-8", errors="replace")
    return payload


def parse_optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise FpaError("目标人天格式不正确", 400, "task_create") from exc
    if round(parsed, 1) != parsed:
        raise FpaError("目标人天最多 1 位小数", 400, "task_create")
    return parsed


app = create_app()
