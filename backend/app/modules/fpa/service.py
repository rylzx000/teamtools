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
DEFAULT_COUNT_TIMING = "估算中期"
DEFAULT_INTEGRITY_LEVEL = "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式"
COUNT_TIMINGS = {
    "估算早期": 1.39,
    "估算中期": 1.21,
    "估算晚期": 1.10,
    "项目交付后及运维阶段": 1.00,
}
INTEGRITY_LEVELS = {
    "没有明确的完整性级别或等级为C/D",
    DEFAULT_INTEGRITY_LEVEL,
    "完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施",
}
INTEGRITY_FACTORS = {
    "没有明确的完整性级别或等级为C/D": 1.00,
    DEFAULT_INTEGRITY_LEVEL: 1.10,
    "完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施": 1.30,
}
COMMON_RELEVANCE_TOKENS = {
    "系统",
    "需求",
    "功能",
    "新增",
    "修改",
    "查询",
    "提交",
    "用户",
    "信息",
    "处理",
    "平台",
    "核心",
    "服务",
    "状态",
    "流程",
    "任务",
}
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


def select_option(value: str, coefficient: float) -> dict[str, Any]:
    return {"value": value, "label": f"{coefficient:.2f} {value}", "coefficient": coefficient}


def get_form_config(data_dir: Path) -> dict[str, Any]:
    systems = load_systems(data_dir)
    return {
        "systems": systems,
        "count_timings": [select_option(value, coefficient) for value, coefficient in COUNT_TIMINGS.items()],
        "integrity_levels": [
            select_option(value, INTEGRITY_FACTORS[value])
            for value in (
                "没有明确的完整性级别或等级为C/D",
                DEFAULT_INTEGRITY_LEVEL,
                "完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施",
            )
        ],
        "defaults": {
            "system_code": systems[0]["code"] if systems else None,
            "count_timing": DEFAULT_COUNT_TIMING,
            "integrity_level": DEFAULT_INTEGRITY_LEVEL,
        },
    }


def system_by_code(data_dir: Path, code: str) -> dict[str, Any]:
    ensure_resources(data_dir)
    systems_yaml = data_dir / "config" / "modules" / "fpa" / "systems.yaml"
    payload = yaml.safe_load(systems_yaml.read_text(encoding="utf-8")) or {}
    for item in payload.get("systems") or SYSTEMS:
        if item.get("code") == code:
            return dict(item)
    raise FpaError("系统编码不存在", 400, "task_create")


def system_entries(data_dir: Path) -> list[dict[str, Any]]:
    ensure_resources(data_dir)
    systems_yaml = data_dir / "config" / "modules" / "fpa" / "systems.yaml"
    payload = yaml.safe_load(systems_yaml.read_text(encoding="utf-8")) or {}
    return [dict(item) for item in (payload.get("systems") or SYSTEMS)]


def knowledge_dir_path(data_dir: Path, system: dict[str, Any]) -> Path | None:
    raw = system.get("knowledge_dir")
    if not raw:
        return None
    path = Path(str(raw))
    if path.is_absolute():
        return path
    candidate = data_dir / path
    if candidate.exists():
        return candidate
    return data_dir / "modules" / "fpa" / "knowledge" / str(raw)


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
    count_timing: str = DEFAULT_COUNT_TIMING,
    integrity_level: str = DEFAULT_INTEGRITY_LEVEL,
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
    if integrity_level not in INTEGRITY_LEVELS:
        raise FpaError("完整性级别不支持", 400, "task_create")

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
        "integrity_level": integrity_level,
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
        "system_relevance": build_system_relevance(data_dir, task_id, task),
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
    analysis_path = analysis_markdown_path(paths)
    excel_path = paths.output_dir / "FPA工作量评估.xlsx"
    summary_path = paths.ai_dir / "AI请求摘要.json"
    is_admin = user["role"] == "admin"
    process = read_json(process_path) if process_path.exists() else None
    result_summary = summarize_process(process) if isinstance(process, dict) else None
    return {
        "task": task_public,
        "artifacts": {
            "ai_request_summary": {
                "available": summary_path.exists() and is_admin,
                "content": read_json(summary_path) if summary_path.exists() and is_admin else None,
            },
            "ai_analysis_md": {
                "available": analysis_path is not None,
                "content": analysis_path.read_text(encoding="utf-8") if analysis_path else None,
            },
            "fpa_process_json": {
                "available": process_path.exists() and is_admin,
                "content": process if process_path.exists() and is_admin else None,
            },
            "result_summary": {
                "available": result_summary is not None,
                "content": result_summary,
            },
            "excel_result": {
                "available": excel_path.exists() and task["status"] == "completed",
                "download_url": f"/api/fpa/tasks/{task_id}/download/excel",
            },
        },
    }


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_task_params(paths: FpaPaths) -> dict[str, Any]:
    path = paths.input_dir / "task_params.json"
    if not path.exists():
        return {}
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def write_task_params(paths: FpaPaths, params: dict[str, Any]) -> None:
    (paths.input_dir / "task_params.json").write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")


def relevance_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text.lower()):
        if not raw or raw in COMMON_RELEVANCE_TOKENS:
            continue
        if re.fullmatch(r"[a-z0-9_]+", raw):
            tokens.add(raw)
            continue
        if 2 <= len(raw) <= 8:
            tokens.add(raw)
        for size in (2, 3, 4, 5, 6):
            if len(raw) > size:
                tokens.update(raw[index : index + size] for index in range(len(raw) - size + 1))
    return {token for token in tokens if token not in COMMON_RELEVANCE_TOKENS}


def system_relevance_text(data_dir: Path, system: dict[str, Any]) -> str:
    chunks = [str(system.get("code") or ""), str(system.get("name") or "")]
    root = knowledge_dir_path(data_dir, system)
    if root:
        for name in (str(system.get("brief_file") or "teamtools-system-brief.md"), "08-FPA场景拆分字典.md"):
            path = root / name
            if path.exists():
                chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def score_system_relevance(input_text: str, system: dict[str, Any], tokens: set[str]) -> int:
    text = input_text.lower()
    score = 0
    code = str(system.get("code") or "").lower()
    name = str(system.get("name") or "")
    if code and code in text:
        score += 8
    if name and name in input_text:
        score += 10
    for token in tokens:
        if len(token) < 2 or token in COMMON_RELEVANCE_TOKENS:
            continue
        if token in text:
            score += 2 if len(token) >= 4 else 1
    return score


def build_system_relevance(data_dir: Path, task_id: str, task: dict[str, Any]) -> dict[str, Any]:
    paths = task_paths(data_dir, task_id)
    params = read_task_params(paths)
    selected_code = str(task["system_code"])
    selected_name = str(task["system_name"])
    input_path = paths.input_dir / "merged_input.md"
    input_text = input_path.read_text(encoding="utf-8") if input_path.exists() else ""

    scored: list[dict[str, Any]] = []
    for system in system_entries(data_dir):
        tokens = relevance_tokens(system_relevance_text(data_dir, system))
        score = score_system_relevance(input_text, system, tokens)
        scored.append({"system": system, "score": score})

    selected = next((item for item in scored if item["system"].get("code") == selected_code), None)
    best = max(scored, key=lambda item: item["score"], default=selected)
    selected_score = int(selected["score"] if selected else 0)
    best_score = int(best["score"] if best else 0)
    best_system = dict(best["system"] if best else task)
    confirmed = bool(params.get("system_relevance_confirmed"))
    status = "pass"
    if best_system.get("code") != selected_code and best_score >= max(selected_score + 4, 5):
        status = "warning"
    if best_system.get("code") != selected_code and selected_score <= 1 and best_score >= 8:
        status = "blocked"
    if status == "blocked" and selected and not selected["system"].get("knowledge_dir"):
        status = "warning"
    message = "系统选择与需求文本未发现明显冲突。"
    if status in {"warning", "blocked"}:
        message = f"当前需求可能更像【{best_system.get('name')}】，你选择的是【{selected_name}】，是否仍按当前系统继续？"
    if confirmed:
        message = "用户已确认按当前选择系统继续评估。"

    return {
        "status": status,
        "confirmed": confirmed,
        "selected_system_code": selected_code,
        "selected_system_name": selected_name,
        "best_match_system_code": str(best_system.get("code") or ""),
        "best_match_system_name": str(best_system.get("name") or ""),
        "selected_score": selected_score,
        "best_match_score": best_score,
        "message": message,
    }


def confirm_system_relevance(db_path: Path, data_dir: Path, task_id: str, user: dict[str, Any]) -> dict[str, Any]:
    with open_connection(db_path) as conn:
        task = get_task_for_user(conn, task_id, user)
        if task["status"] != "waiting_ai_call":
            raise FpaError("当前状态不能确认系统选择", 409, "system_relevance")
    relevance = build_system_relevance(data_dir, task_id, task)
    paths = task_paths(data_dir, task_id)
    params = read_task_params(paths)
    params.update(
        {
            "system_relevance_confirmed": True,
            "system_relevance_status": relevance["status"],
            "best_match_system_code": relevance["best_match_system_code"],
            "confirmed_at": utc_now(),
        }
    )
    write_task_params(paths, params)
    write_task_event(db_path, task_id, "system_relevance_confirmed", "用户确认按当前系统继续评估")
    return {"system_relevance": build_system_relevance(data_dir, task_id, task)}


def analysis_markdown_path(paths: FpaPaths) -> Path | None:
    for name in ("AI评估.md", "AI分析.md"):
        path = paths.ai_dir / name
        if path.exists():
            return path
    return None


def summarize_process(process: dict[str, Any]) -> dict[str, Any]:
    estimates = process.get("estimates") if isinstance(process.get("estimates"), dict) else {}
    context = process.get("assessment_context") if isinstance(process.get("assessment_context"), dict) else {}
    return {
        "item_count": process.get("item_count"),
        "function_point_total": estimates.get("function_point_total"),
        "adjusted_fp_total": estimates.get("adjusted_fp_total"),
        "work_days": estimates.get("work_days") if isinstance(estimates.get("work_days"), dict) else {},
        "target_check": estimates.get("target_check") if isinstance(estimates.get("target_check"), dict) else {},
        "quality_gate": process.get("quality_gate") if isinstance(process.get("quality_gate"), dict) else {},
        "quality_warnings": process.get("quality_warnings") or [],
        "review_notes": context.get("review_notes") or context.get("quality_notes") or process.get("review_notes") or [],
        "uncounted_items": context.get("uncounted_items") or [],
        "coverage_notes": context.get("coverage_notes") or "",
    }


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
        json.dumps(safe_ai_result_payload(payload), ensure_ascii=False, indent=2),
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
        ai_assessment_md, structured = extract_ai_response(payload)
        validate_structured_json(
            structured,
            data_dir,
            expected_system_code=task["system_code"],
            expected_system_name=task["system_name"],
        )
        (paths.ai_dir / "AI结构化结果.json").write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")
        if ai_assessment_md.strip():
            (paths.ai_dir / "AI评估.md").write_text(ai_assessment_md.strip() + "\n", encoding="utf-8")
            register_file(db_path, data_dir, task_id, "ai_assessment_md", paths.ai_dir / "AI评估.md", viewable=True)
        elif structured.get("analysis_notes"):
            (paths.ai_dir / "AI分析.md").write_text(str(structured["analysis_notes"]), encoding="utf-8")
        register_file(db_path, data_dir, task_id, "ai_structured_json", paths.ai_dir / "AI结构化结果.json", admin_only=True)
        with open_connection(db_path) as conn:
            conn.execute("UPDATE tasks SET status = 'generating_result', updated_at = ? WHERE id = ?", (utc_now(), task_id))
            conn.commit()
        frozen_items = structured["frozen_items"]
        process = generate_result_files(db_path, data_dir, task_id, task, structured, ai_assessment_md)
        with open_connection(db_path) as conn:
            target_check = process["estimates"]["target_check"]
            hit_status = target_check.get("hit_status")
            quality_flags = list(process.get("quality_warnings") or [])
            quality_flags.extend(structured.get("review_notes") or structured.get("quality_notes") or [])
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
                    len(frozen_items),
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


def safe_ai_result_payload(payload: dict[str, Any]) -> Any:
    data = payload["raw_response"] if payload.get("raw_response") is not None else payload
    return redact_sensitive(data)


def redact_sensitive(value: Any) -> Any:
    blocked = {"apikey", "api_key", "authorization", "token"}
    if isinstance(value, dict):
        return {
            key: "***"
            if str(key).lower() in blocked
            else redact_sensitive(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def extract_ai_response(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    structured = payload.get("structured_json")
    if structured is not None:
        if not isinstance(structured, dict):
            raise FpaError("structured_json 必须是对象", 400, "json_validation")
        assessment_md = payload.get("ai_assessment_md") or payload.get("analysis_md") or payload.get("AI评估.md") or ""
        return str(assessment_md), structured

    text = extract_raw_response_text(payload.get("raw_response"))
    assessment_md = extract_tagged_block(text, "AI评估.md")
    structured_text = extract_tagged_block(text, "AI结构化结果.json")
    try:
        parsed = json.loads(structured_text)
    except json.JSONDecodeError as exc:
        raise FpaError(f"AI结构化结果.json 解析失败: {exc.msg}", 400, "json_validation") from exc
    if not isinstance(parsed, dict):
        raise FpaError("AI结构化结果.json 必须是对象", 400, "json_validation")
    return assessment_md, parsed


def extract_tagged_block(text: str, tag: str) -> str:
    pattern = rf"<{re.escape(tag)}>\s*(.*?)\s*</{re.escape(tag)}>"
    match = re.search(pattern, text, flags=re.S)
    if not match:
        raise FpaError(f"模型响应中未找到 {tag} 区块", 400, "json_validation")
    return match.group(1).strip()


def extract_raw_response_text(raw_response: Any) -> str:
    if isinstance(raw_response, dict):
        content = raw_response.get("structured_json")
        if isinstance(content, str):
            return content
        choices = raw_response.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = message.get("content")
        else:
            content = raw_response
    else:
        content = raw_response
    if not isinstance(content, str) or not content.strip():
        raise FpaError("模型响应正文为空", 400, "json_validation")
    return content


def validate_structured_json(
    data: Any,
    data_dir: Path,
    *,
    expected_system_code: str | None = None,
    expected_system_name: str | None = None,
) -> None:
    schema_file = data_dir / "modules" / "fpa" / "profile" / "schema" / "result.schema.json"
    try:
        schema = load_schema_json(schema_file, "result.schema.json")
        validate_result(
            data,
            schema,
            expected_system_code=expected_system_code,
            expected_system_name=expected_system_name,
        )
    except AiResultValidationError as exc:
        raise FpaError(str(exc), 400, "json_validation") from exc


def generate_result_files(
    db_path: Path,
    data_dir: Path,
    task_id: str,
    task: dict[str, Any],
    structured: dict[str, Any],
    ai_assessment_md: str,
) -> dict[str, Any]:
    paths = task_paths(data_dir, task_id)
    target_days = task.get("target_person_days")
    task_params = read_task_params(paths)
    integrity_level = str(task_params.get("integrity_level") or DEFAULT_INTEGRITY_LEVEL)
    frozen_items = structured["frozen_items"]
    payload = {
        "requirement_name": task["title"],
        "assessor": "TeamTools",
        "assessment_date": utc_now()[:10],
        "count_mode": "估算功能点",
        "target_work_days": None if target_days is None else float(target_days),
        "project_features": {"count_timing": task["count_timing"], "integrity_level": integrity_level},
        "assessment_context": {
            "system_code": task["system_code"],
            "system_name": task["system_name"],
            "task_id": task_id,
            "no_knowledge_mode": bool(task.get("no_knowledge_mode")),
            "ai_assessment_md": ai_assessment_md,
            "ai_assessment_context": structured.get("assessment_context", {}),
            "ai_project_features": structured.get("project_features", {}),
            "review_notes": structured.get("review_notes", []),
            "ai_analysis_notes": structured.get("analysis_notes", ""),
            "uncounted_items": structured.get("uncounted_items", []),
            "quality_notes": structured.get("quality_notes", []),
            "coverage_notes": structured.get("coverage_notes", ""),
            "uncertainties": structured.get("uncertainties", []),
        },
        "items": frozen_items,
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
    task_params = read_task_params(paths)
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
            integrity_level=str(task_params.get("integrity_level") or DEFAULT_INTEGRITY_LEVEL),
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
