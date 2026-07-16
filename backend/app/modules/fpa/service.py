from __future__ import annotations

import json
import re
import secrets
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ...db import fetch_all, fetch_one, open_connection, utc_now, write_task_event

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fpa.build_ai_request_package import BuildError, build_ai_request_package
from scripts.fpa.fill_fpa_workbook import FpaPayloadError, fill_workbook
from scripts.fpa.validate_ai_result import ValidationError as AiResultValidationError
from scripts.fpa.validate_ai_result import load_json as load_schema_json
from scripts.fpa.validate_ai_result import validate_result


STATUSES = {
    "draft": "草稿",
    "waiting_ai_call": "等待AI调用",
    "validating_result": "结果校验中",
    "generating_result": "生成结果中",
    "completed": "已完成",
    "failed": "失败",
    "canceled": "已取消",
}
COUNT_TIMINGS = {"估算早期": 0.8, "估算中期": 1.0, "估算晚期": 1.2}
SYSTEMS = [
    {"code": "claimcar", "name": "车险理赔核心系统", "sort_order": 10, "knowledge_dir": "claimcar"},
    {"code": "claimoth", "name": "非车险理赔核心系统", "sort_order": 20, "knowledge_dir": "claimoth"},
    {"code": "onlineclaim", "name": "在线理赔服务平台", "sort_order": 30, "knowledge_dir": "onlineclaim"},
    {"code": "clqp", "name": "零配件报价系统", "sort_order": 40, "knowledge_dir": "clqp"},
]


class FpaError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400, stage: str = "validation"):
        super().__init__(message)
        self.status_code = status_code
        self.stage = stage


@dataclass(frozen=True)
class FpaPaths:
    task_root: Path
    input_dir: Path
    ai_dir: Path
    runtime_dir: Path
    output_dir: Path


def ensure_resources(data_dir: Path) -> None:
    profile = data_dir / "modules" / "fpa" / "profile"
    skill_dir = profile / "skill"
    schema_dir = profile / "schema"
    config_dir = data_dir / "config" / "modules" / "fpa"
    for directory in (skill_dir, schema_dir, config_dir, data_dir / "tasks" / "fpa"):
        directory.mkdir(parents=True, exist_ok=True)

    systems_yaml = config_dir / "systems.yaml"
    if not systems_yaml.exists():
        systems_yaml.write_text(
            yaml.safe_dump({"systems": SYSTEMS}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    prompt_template = skill_dir / "prompt_template.md"
    if not prompt_template.exists():
        prompt_template.write_text(
            """你是 FPA 工作量评估助手。请只输出满足 JSON 契约的对象，不要输出 Markdown 代码块。

需求名称：{{ requirement_title }}
系统编码：{{ system_code }}
系统名称：{{ system_name }}
规模计数时机：{{ project_features }}
target_person_days：{{ target_person_days }}

系统资料摘要：
{{ knowledge_summary }}

用户需求：
{{ input_text }}

输出契约：
{{ schema_text }}

限制：
{{ output_rules }}
""",
            encoding="utf-8",
        )

    schema_file = schema_dir / "result.schema.json"
    if not schema_file.exists():
        schema_file.write_text(
            json.dumps(
                {
                    "type": "object",
                    "required": ["items"],
                    "properties": {
                        "requirement_name": {"type": "string"},
                        "assessment_context": {"type": "object"},
                        "project_features": {"type": "object"},
                        "analysis_notes": {"type": "string"},
                        "uncertainties": {"type": "array"},
                        "items": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "object"},
                        },
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def load_systems(data_dir: Path) -> list[dict[str, Any]]:
    ensure_resources(data_dir)
    systems_yaml = data_dir / "config" / "modules" / "fpa" / "systems.yaml"
    payload = yaml.safe_load(systems_yaml.read_text(encoding="utf-8")) or {}
    systems = payload.get("systems") or SYSTEMS
    return sorted(
        [
            {
                "code": str(item["code"]),
                "name": str(item["name"]),
                "sort_order": int(item.get("sort_order", 999)),
                "no_knowledge_mode": not bool(item.get("knowledge_dir")),
            }
            for item in systems
        ],
        key=lambda item: item["sort_order"],
    )


def system_by_code(data_dir: Path, code: str) -> dict[str, Any]:
    ensure_resources(data_dir)
    systems_yaml = data_dir / "config" / "modules" / "fpa" / "systems.yaml"
    payload = yaml.safe_load(systems_yaml.read_text(encoding="utf-8")) or {}
    for item in payload.get("systems") or SYSTEMS:
        if item.get("code") == code:
            return dict(item)
    raise FpaError("系统编码不存在", 400, "task_create")


def task_paths(data_dir: Path, task_id: str) -> FpaPaths:
    root = data_dir / "tasks" / "fpa" / task_id
    paths = FpaPaths(root, root / "input", root / "ai", root / "runtime", root / "output")
    for path in (paths.input_dir, paths.ai_dir, paths.runtime_dir, paths.output_dir):
        path.mkdir(parents=True, exist_ok=True)
    return paths


def public_task(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["status_label"] = STATUSES.get(str(row["status"]), str(row["status"]))
    result["target_hit"] = None if row.get("target_hit") is None else bool(row["target_hit"])
    result["can_cancel"] = row["status"] in {"waiting_ai_call", "validating_result", "generating_result"}
    result["can_rerun"] = row["status"] in {"completed", "failed", "canceled"}
    result["can_download_excel"] = row["status"] == "completed"
    result["can_fetch_ai_request"] = row["status"] == "waiting_ai_call"
    result["can_submit_ai_result"] = row["status"] == "waiting_ai_call"
    return result


def get_task_for_user(conn: sqlite3.Connection, task_id: str, user: dict[str, Any]) -> dict[str, Any]:
    where = "t.id = ? AND t.module = 'fpa'"
    params: list[Any] = [task_id]
    if user["role"] != "admin":
        where += " AND t.created_by = ?"
        params.append(user["id"])
    row = fetch_one(
        conn,
        f"""
        SELECT t.*, d.system_code, d.system_name, d.count_timing, d.no_knowledge_mode,
               d.target_person_days, d.ai_item_count, d.result_item_count,
               d.result_median_person_days, d.target_hit, d.quality_flags
        FROM tasks t
        JOIN fpa_task_details d ON d.task_id = t.id
        WHERE {where}
        """,
        tuple(params),
    )
    if not row:
        raise FpaError("任务不存在", 404, "permission")
    return row


def create_task(
    db_path: Path,
    data_dir: Path,
    user: dict[str, Any],
    *,
    system_code: str,
    title: str | None,
    input_text: str | None,
    uploaded_text: str | None = None,
    uploaded_name: str | None = None,
    target_person_days: float | None = None,
    count_timing: str = "估算早期",
    rerun_from_task_id: str | None = None,
) -> dict[str, Any]:
    ensure_resources(data_dir)
    input_text = (input_text or "").strip()
    uploaded_text = (uploaded_text or "").strip()
    if not input_text and not uploaded_text:
        raise FpaError("请粘贴需求文本或上传 Markdown 文件", 400, "task_create")
    if len(input_text) > 20_000 or len(uploaded_text) > 20_000:
        raise FpaError("输入内容不能超过 2 万字符", 400, "task_create")
    if target_person_days is not None and target_person_days <= 0:
        raise FpaError("目标人天必须大于 0", 400, "task_create")
    if count_timing not in COUNT_TIMINGS:
        raise FpaError("规模计数时机不支持", 400, "task_create")

    system = system_by_code(data_dir, system_code)
    requirement_title = (title or "").strip() or "FPA工作量评估"
    task_id = "fpa-" + utc_now().replace("-", "").replace(":", "").replace("+", "z") + "-" + secrets.token_hex(3)
    paths = task_paths(data_dir, task_id)
    if input_text:
        (paths.input_dir / "pasted_input.md").write_text(input_text, encoding="utf-8")
        register_file(db_path, data_dir, task_id, "input_pasted", paths.input_dir / "pasted_input.md", viewable=True)
    if uploaded_text:
        (paths.input_dir / "uploaded_input.md").write_text(uploaded_text, encoding="utf-8")
        register_file(
            db_path,
            data_dir,
            task_id,
            "input_uploaded",
            paths.input_dir / "uploaded_input.md",
            original_name=uploaded_name,
            viewable=True,
        )
    merged = "\n\n".join(part for part in [input_text, uploaded_text] if part)
    (paths.input_dir / "merged_input.md").write_text(merged, encoding="utf-8")
    params = {
        "task_id": task_id,
        "system_code": system_code,
        "system_name": system["name"],
        "requirement_title": requirement_title,
        "title": requirement_title,
        "target_person_days": target_person_days,
        "count_timing": count_timing,
        "created_by": user["id"],
    }
    (paths.input_dir / "task_params.json").write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")

    build_ai_request(data_dir, task_id, system_code)

    now = utc_now()
    with open_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO tasks(id, module, title, status, created_by, created_at, updated_at,
                              submitted_at, ai_request_created_at, rerun_from_task_id)
            VALUES (?, 'fpa', ?, 'waiting_ai_call', ?, ?, ?, ?, ?, ?)
            """,
            (task_id, requirement_title, user["id"], now, now, now, now, rerun_from_task_id),
        )
        conn.execute(
            """
            INSERT INTO fpa_task_details(task_id, system_code, system_name, assessment_mode,
                                         count_timing, no_knowledge_mode, target_person_days)
            VALUES (?, ?, ?, 'system_function', ?, ?, ?)
            """,
            (task_id, system_code, system["name"], count_timing, 0 if system.get("knowledge_dir") else 1, target_person_days),
        )
        conn.commit()
    register_file(db_path, data_dir, task_id, "task_params", paths.input_dir / "task_params.json", viewable=True)
    register_file(db_path, data_dir, task_id, "ai_request_package", paths.ai_dir / "AI请求包.json", admin_only=True)
    register_file(db_path, data_dir, task_id, "ai_request_summary", paths.ai_dir / "AI请求摘要.json", admin_only=True)
    write_task_event(db_path, task_id, "ai_request_created", "AI 请求包已生成")
    return task_response(task_id, "waiting_ai_call", requirement_title)


def register_file(
    db_path: Path,
    data_dir: Path,
    task_id: str,
    role: str,
    path: Path,
    *,
    original_name: str | None = None,
    downloadable: bool = False,
    viewable: bool = False,
    admin_only: bool = False,
) -> None:
    try:
        rel = path.relative_to(data_dir)
    except ValueError as exc:
        raise FpaError("文件路径越界", 500, "file") from exc
    with open_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO task_files(id, task_id, file_role, storage_path, original_name,
                                              display_name, mime_type, size_bytes, downloadable,
                                              viewable, admin_only, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{task_id}:{role}",
                task_id,
                role,
                str(rel).replace("\\", "/"),
                original_name,
                path.name,
                "application/octet-stream",
                path.stat().st_size if path.exists() else 0,
                1 if downloadable else 0,
                1 if viewable else 0,
                1 if admin_only else 0,
                utc_now(),
            ),
        )
        conn.commit()


def build_ai_request(
    data_dir: Path,
    task_id: str,
    system_code: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = task_paths(data_dir, task_id)
    try:
        return build_ai_request_package(
            task_dir=paths.task_root,
            data_dir=data_dir,
            profile_dir=data_dir / "modules" / "fpa" / "profile",
            systems_config=data_dir / "config" / "modules" / "fpa" / "systems.yaml",
            system_code=system_code,
            output_dir=paths.ai_dir,
        )
    except BuildError as exc:
        raise FpaError(str(exc), 500, "resource") from exc


def task_response(task_id: str, status: str, title: str, rerun_from_task_id: str | None = None) -> dict[str, Any]:
    task = {
        "id": task_id,
        "module": "fpa",
        "status": status,
        "status_label": STATUSES[status],
        "title": title,
        "detail_url": f"/fpa/tasks/{task_id}",
        "ai_request_url": f"/api/fpa/tasks/{task_id}/ai-request",
    }
    if rerun_from_task_id:
        task["rerun_from_task_id"] = rerun_from_task_id
    return {"task": task}


def sanitize_ai_request(package: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in package.items() if key != "metadata"}


def fetch_ai_request(db_path: Path, data_dir: Path, task_id: str, user: dict[str, Any]) -> dict[str, Any]:
    with open_connection(db_path) as conn:
        task = get_task_for_user(conn, task_id, user)
        if task["status"] != "waiting_ai_call":
            raise FpaError("当前状态不能获取 AI 请求包", 409, "ai_request")
        paths = task_paths(data_dir, task_id)
        package_path = paths.ai_dir / "AI请求包.json"
        if not package_path.exists():
            raise FpaError("AI 请求包不存在", 404, "ai_request")
        conn.execute(
            "UPDATE tasks SET ai_request_fetched_at = ?, updated_at = ? WHERE id = ?",
            (utc_now(), utc_now(), task_id),
        )
        conn.commit()
    write_task_event(db_path, task_id, "ai_request_fetched", "前端获取 AI 请求包")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    return {
        "task": {"id": task_id, "status": task["status"], "status_label": STATUSES[task["status"]]},
        "ai_request": sanitize_ai_request(package),
    }


def list_tasks(db_path: Path, user: dict[str, Any], status: str | None = None) -> dict[str, Any]:
    params: list[Any] = []
    where = "t.module = 'fpa'"
    if user["role"] != "admin":
        where += " AND t.created_by = ?"
        params.append(user["id"])
    if status:
        where += " AND t.status = ?"
        params.append(status)
    with open_connection(db_path) as conn:
        rows = fetch_all(
            conn,
            f"""
            SELECT t.id, t.title, d.system_name, t.status, t.created_at, t.finished_at,
                   d.target_person_days, d.count_timing, d.result_median_person_days,
                   d.target_hit, u.display_name AS created_by, t.failure_stage
            FROM tasks t
            JOIN fpa_task_details d ON d.task_id = t.id
            JOIN users u ON u.id = t.created_by
            WHERE {where}
            ORDER BY t.created_at DESC
            """,
            tuple(params),
        )
    items = [public_task(row) for row in rows]
    return {"items": items, "page": 1, "page_size": len(items), "total": len(items)}


def task_detail(db_path: Path, data_dir: Path, task_id: str, user: dict[str, Any]) -> dict[str, Any]:
    with open_connection(db_path) as conn:
        task = get_task_for_user(conn, task_id, user)
    paths = task_paths(data_dir, task_id)
    task_public = public_task(task)
    task_public["quality_flags"] = json.loads(task.get("quality_flags") or "[]")
    process_path = paths.runtime_dir / "FPA生成过程.json"
    analysis_path = paths.ai_dir / "AI分析.md"
    excel_path = paths.output_dir / "FPA工作量评估.xlsx"
    summary_path = paths.ai_dir / "AI请求摘要.json"
    return {
        "task": task_public,
        "artifacts": {
            "ai_request_summary": {
                "available": summary_path.exists() and user["role"] == "admin",
                "content": read_json(summary_path) if summary_path.exists() and user["role"] == "admin" else None,
            },
            "ai_analysis_md": {
                "available": analysis_path.exists(),
                "content": analysis_path.read_text(encoding="utf-8") if analysis_path.exists() else None,
            },
            "fpa_process_json": {
                "available": process_path.exists(),
                "content": read_json(process_path) if process_path.exists() else None,
            },
            "excel_result": {
                "available": excel_path.exists() and task["status"] == "completed",
                "download_url": f"/api/fpa/tasks/{task_id}/download/excel",
            },
        },
    }


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def handle_ai_result(db_path: Path, data_dir: Path, task_id: str, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    with open_connection(db_path) as conn:
        task = get_task_for_user(conn, task_id, user)
        if task["status"] != "waiting_ai_call":
            raise FpaError("当前状态不能回传 AI 结果", 409, "ai_result")
    paths = task_paths(data_dir, task_id)
    now = utc_now()
    if not payload.get("success"):
        safe_error = sanitize_error(payload.get("error") or {})
        (paths.ai_dir / "AI调用错误.json").write_text(json.dumps(safe_error, ensure_ascii=False, indent=2), encoding="utf-8")
        fail_task(db_path, task_id, "ai_call", safe_error.get("message", "模型调用失败"), json.dumps(safe_error, ensure_ascii=False))
        register_file(db_path, data_dir, task_id, "ai_call_error", paths.ai_dir / "AI调用错误.json", admin_only=True)
        return {"task": {"id": task_id, "status": "failed", "status_label": STATUSES["failed"]}}

    (paths.ai_dir / "AI原始响应.json").write_text(
        json.dumps(payload.get("raw_response") or payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    register_file(db_path, data_dir, task_id, "ai_raw_response", paths.ai_dir / "AI原始响应.json", admin_only=True)
    with open_connection(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET status = 'validating_result', updated_at = ?, ai_result_received_at = ?, processing_started_at = ? WHERE id = ?",
            (now, now, now, task_id),
        )
        conn.commit()
    try:
        structured = payload.get("structured_json") or extract_json(payload.get("raw_response"))
        validate_structured_json(structured, data_dir)
        (paths.ai_dir / "AI结构化结果.json").write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
        if structured.get("analysis_notes"):
            (paths.ai_dir / "AI分析.md").write_text(str(structured["analysis_notes"]), encoding="utf-8")
        register_file(db_path, data_dir, task_id, "ai_structured_json", paths.ai_dir / "AI结构化结果.json", admin_only=True)
        with open_connection(db_path) as conn:
            conn.execute("UPDATE tasks SET status = 'generating_result', updated_at = ? WHERE id = ?", (utc_now(), task_id))
            conn.commit()
        process = generate_result_files(db_path, data_dir, task_id, task, structured)
        with open_connection(db_path) as conn:
            target_check = process["estimates"]["target_check"]
            hit_status = target_check.get("hit_status")
            quality_flags = list(process.get("quality_warnings") or [])
            quality_flags.extend(structured.get("quality_notes") or [])
            conn.execute(
                """
                UPDATE tasks
                SET status = 'completed', updated_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (utc_now(), utc_now(), task_id),
            )
            conn.execute(
                """
                UPDATE fpa_task_details
                SET ai_item_count = ?, result_item_count = ?, result_median_person_days = ?,
                    target_hit = ?, quality_flags = ?
                WHERE task_id = ?
                """,
                (
                    len(structured["items"]),
                    process["item_count"],
                    process["estimates"]["work_days"]["middle"],
                    None if hit_status == "not_provided" else int(hit_status == "hit"),
                    json.dumps(quality_flags, ensure_ascii=False),
                    task_id,
                ),
            )
            conn.commit()
        return {"task": {"id": task_id, "status": "completed", "status_label": STATUSES["completed"]}}
    except Exception as exc:
        fail_task(db_path, task_id, getattr(exc, "stage", "ai_result"), str(exc), repr(exc))
        return {"task": {"id": task_id, "status": "failed", "status_label": STATUSES["failed"]}}


def sanitize_error(error: dict[str, Any]) -> dict[str, str]:
    message = str(error.get("message") or "模型调用失败")
    message = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-***", message)
    return {"code": str(error.get("code") or "model_call_error")[:80], "message": message[:500]}


def extract_json(raw_response: Any) -> dict[str, Any]:
    if isinstance(raw_response, dict):
        content = raw_response.get("structured_json")
        if isinstance(content, dict):
            return content
        choices = raw_response.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = message.get("content")
        else:
            content = raw_response
    else:
        content = raw_response
    if isinstance(content, dict):
        return content
    text = str(content or "")
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise FpaError("模型响应中未找到 JSON 对象", 400, "json_validation")
    return json.loads(match.group(0))


def validate_structured_json(data: Any, data_dir: Path) -> None:
    schema_file = data_dir / "modules" / "fpa" / "profile" / "schema" / "result.schema.json"
    try:
        schema = load_schema_json(schema_file, "result.schema.json")
        validate_result(data, schema)
    except AiResultValidationError as exc:
        raise FpaError(str(exc), 400, "json_validation") from exc


def generate_result_files(
    db_path: Path,
    data_dir: Path,
    task_id: str,
    task: dict[str, Any],
    structured: dict[str, Any],
) -> dict[str, Any]:
    paths = task_paths(data_dir, task_id)
    target_days = task.get("target_person_days")
    payload = {
        "requirement_name": task["title"],
        "assessor": "TeamTools",
        "assessment_date": utc_now()[:10],
        "count_mode": "估算功能点",
        "target_work_days": None if target_days is None else float(target_days),
        "project_features": {"count_timing": task["count_timing"]},
        "assessment_context": {
            "system_code": task["system_code"],
            "system_name": task["system_name"],
            "task_id": task_id,
            "no_knowledge_mode": bool(task.get("no_knowledge_mode")),
            "ai_analysis_notes": structured.get("analysis_notes", ""),
            "uncounted_items": structured.get("uncounted_items", []),
            "quality_notes": structured.get("quality_notes", []),
            "coverage_notes": structured.get("coverage_notes", ""),
            "uncertainties": structured.get("uncertainties", []),
        },
        "items": structured["items"],
    }
    payload_path = paths.runtime_dir / "Excel脚本输入payload.json"
    process_path = paths.runtime_dir / "FPA生成过程.json"
    excel_path = paths.output_dir / "FPA工作量评估.xlsx"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        process = fill_workbook(
            payload_path=payload_path,
            output_path_override=excel_path,
            template_path_override=data_dir / "modules" / "fpa" / "profile" / "templates" / "fpa_template.xlsx",
            mapping_path=data_dir / "modules" / "fpa" / "profile" / "mapping" / "excel_mapping.yaml",
            process_output_override=process_path,
        )
    except FpaPayloadError as exc:
        raise FpaError(str(exc), 500, "excel_generation") from exc
    register_file(db_path, data_dir, task_id, "generation_summary", paths.runtime_dir / "FPA生成过程.json", admin_only=True)
    register_file(db_path, data_dir, task_id, "result_excel", paths.output_dir / "FPA工作量评估.xlsx", downloadable=True)
    return process


def fail_task(db_path: Path, task_id: str, stage: str, summary: str, detail: str) -> None:
    with open_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'failed', updated_at = ?, finished_at = ?, failure_stage = ?,
                error_summary = ?, admin_error_detail = ?
            WHERE id = ?
            """,
            (utc_now(), utc_now(), stage, summary[:500], detail[:2000], task_id),
        )
        conn.commit()
    write_task_event(db_path, task_id, "task_failed", summary, "error")


def cancel_task(db_path: Path, task_id: str, user: dict[str, Any]) -> dict[str, Any]:
    with open_connection(db_path) as conn:
        task = get_task_for_user(conn, task_id, user)
        if task["status"] not in {"waiting_ai_call", "validating_result", "generating_result"}:
            raise FpaError("当前状态不允许取消", 409, "cancel")
        conn.execute(
            """
            UPDATE tasks
            SET status = 'canceled', cancel_requested = 1, cancelled_at = ?, cancelled_by = ?,
                updated_at = ?, finished_at = ?
            WHERE id = ?
            """,
            (utc_now(), user["id"], utc_now(), utc_now(), task_id),
        )
        conn.commit()
    return {"task": {"id": task_id, "status": "canceled", "status_label": STATUSES["canceled"], "cancel_requested": True}}


def rerun_task(db_path: Path, data_dir: Path, task_id: str, user: dict[str, Any]) -> dict[str, Any]:
    with open_connection(db_path) as conn:
        task = get_task_for_user(conn, task_id, user)
    paths = task_paths(data_dir, task_id)
    merged = paths.input_dir / "merged_input.md"
    if not merged.exists():
        raise FpaError("原任务输入文件不存在", 404, "rerun")
    return {
        "source_task_id": task_id,
        **create_task(
            db_path,
            data_dir,
            user,
            system_code=task["system_code"],
            title=task["title"],
            input_text=merged.read_text(encoding="utf-8"),
            target_person_days=task.get("target_person_days"),
            count_timing=task["count_timing"],
            rerun_from_task_id=task_id,
        ),
    }


def download_excel_path(db_path: Path, data_dir: Path, task_id: str, user: dict[str, Any]) -> Path:
    with open_connection(db_path) as conn:
        task = get_task_for_user(conn, task_id, user)
    if task["status"] != "completed":
        raise FpaError("任务未完成，不能下载 Excel", 409, "download")
    path = task_paths(data_dir, task_id).output_dir / "FPA工作量评估.xlsx"
    if not path.exists():
        raise FpaError("Excel 文件不存在", 404, "download")
    return path
