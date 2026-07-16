#!/usr/bin/env python3
"""Build a sanitized FPA AI request package from task files and profile resources."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE_FILE = "AI请求包.json"
SUMMARY_FILE = "AI请求摘要.json"


class BuildError(Exception):
    """Clear, developer-facing error that is safe to print."""


def read_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise BuildError(f"{label} 缺失: {safe_display_path(path)}") from exc
    except UnicodeDecodeError as exc:
        raise BuildError(f"{label} 不是有效 UTF-8 文本: {safe_display_path(path)}") from exc


def read_json(path: Path, label: str) -> Any:
    text = read_text(path, label)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise BuildError(f"{label} JSON 解析失败: {safe_display_path(path)} ({exc.msg})") from exc


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in {"null", "none", "~"}:
        return ""
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("\"'")


def parse_simple_yaml(path: Path, label: str) -> dict[str, Any]:
    text = read_text(path, label)
    root: dict[str, Any] = {}
    current_list_key: str | None = None
    current_item: dict[str, Any] | None = None
    current_map_key: str | None = None

    try:
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" "))
            stripped = line.strip()

            if indent == 0:
                key, sep, value = stripped.partition(":")
                if not sep:
                    raise ValueError(f"非法 YAML 行: {raw_line}")
                if value.strip():
                    root[key] = parse_scalar(value)
                    current_list_key = None
                    current_map_key = None
                else:
                    root[key] = []
                    current_list_key = key
                    current_map_key = key
                current_item = None
                continue

            if current_list_key and stripped.startswith("- "):
                item_text = stripped[2:]
                current_item = {}
                root[current_list_key].append(current_item)
                if item_text:
                    key, sep, value = item_text.partition(":")
                    if not sep:
                        raise ValueError(f"非法 YAML 列表项: {raw_line}")
                    current_item[key] = parse_scalar(value)
                continue

            if current_item is not None and indent >= 4:
                key, sep, value = stripped.partition(":")
                if not sep:
                    raise ValueError(f"非法 YAML 列表字段: {raw_line}")
                current_item[key] = parse_scalar(value)
                continue

            if current_map_key and isinstance(root.get(current_map_key), list) and not root[current_map_key]:
                root[current_map_key] = {}

            if current_map_key and isinstance(root.get(current_map_key), dict) and indent >= 2:
                key, sep, value = stripped.partition(":")
                if not sep:
                    raise ValueError(f"非法 YAML 映射字段: {raw_line}")
                root[current_map_key][key] = parse_scalar(value)
                continue

            raise ValueError(f"无法解析 YAML 行: {raw_line}")
    except ValueError as exc:
        raise BuildError(f"{label} YAML 解析失败: {safe_display_path(path)} ({exc})") from exc

    return root


def safe_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def resolve_path(base: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def rel_to_base(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.name


def get_required_str(data: dict[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if value is None:
        raise BuildError(f"{label} 缺少字段: {key}")
    return str(value)


def find_system(systems: dict[str, Any], system_code: str) -> dict[str, Any]:
    entries = systems.get("systems")
    if not isinstance(entries, list):
        raise BuildError("systems.yaml 缺少 systems 列表")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("code") == system_code:
            return entry
    raise BuildError(f"system_code 不存在: {system_code}")


def load_profile(profile_dir: Path) -> dict[str, Any]:
    profile_file = profile_dir / "profile.yaml"
    profile = parse_simple_yaml(profile_file, "profile.yaml")
    resources = profile.get("resource_paths")
    if not isinstance(resources, dict):
        raise BuildError("profile.yaml 缺少 resource_paths")
    return profile


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    leftover = sorted(set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", rendered)))
    if leftover:
        raise BuildError("prompt_template.md 存在未替换变量: " + ", ".join(leftover))
    return rendered


def extract_section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end <= start:
        raise BuildError(f"prompt_template.md 缺少模板区段: {start_marker} / {end_marker}")
    return text[start + len(start_marker) : end].strip()


def ensure_nonempty_text(text: str, label: str) -> str:
    stripped = text.strip()
    if not stripped:
        raise BuildError(f"{label} 为空")
    return stripped


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(path)
    except OSError as exc:
        raise BuildError(f"输出目录不可写: {safe_display_path(path.parent)} ({exc.strerror})") from exc


def build_ai_request_package(
    task_dir: Path,
    data_dir: Path,
    profile_dir: Path,
    systems_config: Path,
    system_code: str | None,
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cwd = Path.cwd().resolve()
    task_dir = resolve_path(cwd, task_dir)
    data_dir = resolve_path(cwd, data_dir)
    profile_dir = resolve_path(cwd, profile_dir)
    systems_config = resolve_path(cwd, systems_config)
    output_dir = resolve_path(cwd, output_dir)

    if not task_dir.exists():
        raise BuildError(f"task_dir 不存在: {safe_display_path(task_dir)}")
    if not systems_config.exists():
        raise BuildError(f"systems.yaml 缺失: {safe_display_path(systems_config)}")

    input_dir = task_dir / "input"
    merged_input_file = input_dir / "merged_input.md"
    task_params_file = input_dir / "task_params.json"
    if not merged_input_file.exists():
        raise BuildError("merged_input.md 缺失: input/merged_input.md")
    if not task_params_file.exists():
        raise BuildError("task_params.json 缺失: input/task_params.json")

    profile = load_profile(profile_dir)
    resources = profile["resource_paths"]
    template_file = profile_dir / str(resources.get("prompt_template", "skill/prompt_template.md"))
    schema_file = profile_dir / str(resources.get("result_schema", "schema/result.schema.json"))
    if not template_file.exists():
        raise BuildError(f"prompt_template.md 缺失: {rel_to_base(template_file, cwd)}")
    if not schema_file.exists():
        raise BuildError(f"result.schema.json 缺失: {rel_to_base(schema_file, cwd)}")

    template_text = read_text(template_file, "prompt_template.md")
    schema_obj = read_json(schema_file, "result.schema.json")
    schema_text = json.dumps(schema_obj, ensure_ascii=False, indent=2)
    systems = parse_simple_yaml(systems_config, "systems.yaml")
    task_params = read_json(task_params_file, "task_params.json")
    merged_input = ensure_nonempty_text(read_text(merged_input_file, "merged_input.md"), "输入正文")

    effective_system_code = system_code or get_required_str(task_params, "system_code", "task_params.json")
    system = find_system(systems, effective_system_code)
    system_name = get_required_str(system, "name", "systems.yaml")
    system_type = str(system.get("system_type", ""))
    task_id = str(task_params.get("task_id") or task_dir.name)
    requirement_title = str(task_params.get("requirement_title") or task_id)
    count_timing = str(task_params.get("count_timing") or "估算早期")
    target_person_days = task_params.get("target_person_days", "")
    if target_person_days is None:
        target_person_days = ""

    max_input_chars = int(profile.get("max_input_chars", 30000))
    max_knowledge_chars = int(profile.get("max_knowledge_chars", 30000))
    max_prompt_chars = int(profile.get("max_prompt_chars", 60000))

    if len(merged_input) > max_input_chars:
        raise BuildError(f"输入正文过长: {len(merged_input)} > {max_input_chars}，请拆分需求")

    knowledge_dir_value = str(system.get("knowledge_dir") or "").strip()
    brief_file_name = str(system.get("brief_file") or "teamtools-system-brief.md").strip()
    no_knowledge_mode = knowledge_dir_value == ""
    knowledge_file: Path | None = None
    knowledge_text = ""
    if no_knowledge_mode:
        knowledge_mode = "无资料模式：systems.yaml 中 knowledge_dir 为空，本次仅基于需求正文和 FPA 通用规则评估。"
    else:
        knowledge_file = data_dir / knowledge_dir_value / brief_file_name
        if not knowledge_file.exists():
            raise BuildError(f"系统资料配置错误: knowledge_dir 非空但 brief_file 缺失 ({knowledge_dir_value}/{brief_file_name})")
        knowledge_text = read_text(knowledge_file, "teamtools-system-brief.md").strip()
        if len(knowledge_text) > max_knowledge_chars:
            raise BuildError(f"系统知识包过长: {len(knowledge_text)} > {max_knowledge_chars}，请检查系统资料配置")
        knowledge_mode = "资料模式：仅使用当前系统的 teamtools-system-brief.md，不读取 source/ 全量资料。"

    rendered = render_template(
        template_text,
        {
            "task_id": task_id,
            "requirement_title": requirement_title,
            "system_code": effective_system_code,
            "system_name": system_name,
            "system_type": system_type,
            "count_timing": count_timing,
            "target_person_days": str(target_person_days),
            "knowledge_mode": knowledge_mode,
            "system_knowledge": knowledge_text or "无系统资料。",
            "merged_input": merged_input,
            "result_schema": schema_text,
        },
    )
    system_prompt = extract_section(rendered, "<!-- SYSTEM_PROMPT_START -->", "<!-- SYSTEM_PROMPT_END -->")
    user_prompt = extract_section(rendered, "<!-- USER_PROMPT_START -->", "<!-- USER_PROMPT_END -->")
    plain_prompt = system_prompt + "\n\n" + user_prompt

    if len(plain_prompt) > max_prompt_chars:
        raise BuildError(f"总提示词过长: {len(plain_prompt)} > {max_prompt_chars}")

    template_rel = rel_to_base(template_file, cwd)
    schema_rel = rel_to_base(schema_file, cwd)
    knowledge_rel = rel_to_base(knowledge_file, data_dir) if knowledge_file else ""
    package = {
        "provider": str(profile.get("provider", "deepseek")),
        "model": str(profile.get("model", "deepseek-v4-flash")),
        "request_format": str(profile.get("request_format", "messages")),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "plain_prompt": plain_prompt,
        "generation_config": {
            "temperature": float(profile.get("temperature", 0.1)),
            "top_p": float(profile.get("top_p", 0.9)),
        },
        "metadata": {
            "task_id": task_id,
            "module": str(profile.get("module", "fpa")),
            "system_code": effective_system_code,
            "system_name": system_name,
            "no_knowledge_mode": no_knowledge_mode,
            "target_person_days": target_person_days,
            "template_file": template_rel,
            "schema_file": schema_rel,
            "knowledge_file": knowledge_rel,
        },
    }
    summary = {
        "task_id": task_id,
        "module": "fpa",
        "system_code": effective_system_code,
        "system_name": system_name,
        "no_knowledge_mode": no_knowledge_mode,
        "input_chars": len(merged_input),
        "knowledge_chars": len(knowledge_text),
        "schema_chars": len(schema_text),
        "prompt_chars": len(plain_prompt),
        "template_file": template_rel,
        "schema_file": schema_rel,
        "knowledge_file": knowledge_rel,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json_atomic(output_dir / PACKAGE_FILE, package)
    write_json_atomic(output_dir / SUMMARY_FILE, summary)
    return package, summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 FPA AI请求包.json 和 AI请求摘要.json")
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--profile-dir", default="data/modules/fpa/profile")
    parser.add_argument("--systems-config", default="data/config/modules/fpa/systems.yaml")
    parser.add_argument("--system-code")
    parser.add_argument("--output-dir")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    output_dir = Path(args.output_dir) if args.output_dir else Path(args.task_dir) / "ai"
    try:
        package, summary = build_ai_request_package(
            task_dir=Path(args.task_dir),
            data_dir=Path(args.data_dir),
            profile_dir=Path(args.profile_dir),
            systems_config=Path(args.systems_config),
            system_code=args.system_code,
            output_dir=output_dir,
        )
    except BuildError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    print(f"已生成 {PACKAGE_FILE}: {safe_display_path(resolve_path(Path.cwd(), output_dir) / PACKAGE_FILE)}")
    print(f"已生成 {SUMMARY_FILE}: {safe_display_path(resolve_path(Path.cwd(), output_dir) / SUMMARY_FILE)}")
    print(f"system_code={summary['system_code']} request_format={package['request_format']} prompt_chars={summary['prompt_chars']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
