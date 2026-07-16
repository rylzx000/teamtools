#!/usr/bin/env python3
"""Validate an FPA AI structured JSON result without external dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CATEGORIES = {"ILF", "EIF", "EI", "EO", "EQ"}
REUSE_VALUES = {"高", "中", "低"}
CHANGE_TYPES = {"新增", "修改", "删除"}
KNOWN_SYSTEM_NAMES = {"车险理赔核心系统", "非车险理赔核心系统", "在线理赔服务平台", "零配件报价系统"}
KNOWN_SYSTEM_CODES = {"claimcar", "claimoth", "onlineclaim", "clqp"}
FORBIDDEN_ROOT_FIELDS = {
    "target_work_days",
    "target_hit",
    "adjusted_work_days_middle",
    "ufp",
    "us",
    "adjusted_fp",
    "final_work_days",
}
ROOT_ALLOWED = {
    "requirement_name",
    "assessment_context",
    "project_features",
    "items",
    "analysis_notes",
    "uncounted_items",
    "quality_notes",
    "coverage_notes",
    "uncertainties",
}
ITEM_ALLOWED = {
    "system",
    "level1_module",
    "level2_module",
    "level3_module",
    "level4_module",
    "function_description",
    "count_item_name",
    "category",
    "reuse",
    "change_type",
    "remark",
}
ITEM_REQUIRED = {
    "system",
    "level1_module",
    "function_description",
    "count_item_name",
    "category",
    "reuse",
    "change_type",
    "remark",
}


class ValidationError(Exception):
    """Validation error safe to show to developers."""


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"{label} 缺失: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{label} JSON 解析失败: {exc.msg}") from exc


def ensure_nonempty_string(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} 必须是非空字符串")


def ensure_string(value: Any, field: str) -> None:
    if not isinstance(value, str):
        raise ValidationError(f"{field} 必须是字符串")


def validate_uncounted_items(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise ValidationError("uncounted_items 必须是数组")
    allowed = {"description", "reason", "related_requirement_section"}
    required = allowed
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"uncounted_items[{index}] 必须是对象")
        extra = set(item) - allowed
        if extra:
            raise ValidationError(f"uncounted_items[{index}] 存在未允许字段: " + ", ".join(sorted(extra)))
        missing = required - set(item)
        if missing:
            raise ValidationError(f"uncounted_items[{index}] 缺少字段: " + ", ".join(sorted(missing)))
        for field in required:
            ensure_nonempty_string(item.get(field), f"uncounted_items[{index}].{field}")


def validate_quality_notes(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise ValidationError("quality_notes 必须是数组")
    allowed = {"code", "message", "severity"}
    required = allowed
    severities = {"low", "medium", "high"}
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"quality_notes[{index}] 必须是对象")
        extra = set(item) - allowed
        if extra:
            raise ValidationError(f"quality_notes[{index}] 存在未允许字段: " + ", ".join(sorted(extra)))
        missing = required - set(item)
        if missing:
            raise ValidationError(f"quality_notes[{index}] 缺少字段: " + ", ".join(sorted(missing)))
        ensure_nonempty_string(item.get("code"), f"quality_notes[{index}].code")
        ensure_nonempty_string(item.get("message"), f"quality_notes[{index}].message")
        if item.get("severity") not in severities:
            raise ValidationError(f"quality_notes[{index}].severity 枚举值非法: {item.get('severity')}")


def validate_result(result: Any, schema: Any) -> None:
    if not isinstance(schema, dict):
        raise ValidationError("result.schema.json 必须是 JSON 对象")
    if not isinstance(result, dict):
        raise ValidationError("AI 结果必须是 JSON 对象")

    forbidden = FORBIDDEN_ROOT_FIELDS & set(result)
    if forbidden:
        raise ValidationError("顶层存在禁止字段: " + ", ".join(sorted(forbidden)))
    extra_root = set(result) - ROOT_ALLOWED
    if extra_root:
        raise ValidationError("顶层存在未允许字段: " + ", ".join(sorted(extra_root)))
    if "requirement_name" not in result:
        raise ValidationError("缺少顶层字段: requirement_name")
    ensure_nonempty_string(result["requirement_name"], "requirement_name")
    items = result.get("items")
    if not isinstance(items, list) or not items:
        raise ValidationError("items 必须是非空数组")

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"items[{index}] 必须是对象")
        extra_item = set(item) - ITEM_ALLOWED
        if extra_item:
            raise ValidationError(f"items[{index}] 存在未允许字段: " + ", ".join(sorted(extra_item)))
        missing = ITEM_REQUIRED - set(item)
        if missing:
            raise ValidationError(f"items[{index}] 缺少字段: " + ", ".join(sorted(missing)))

        for field in ITEM_REQUIRED:
            ensure_nonempty_string(item.get(field), f"items[{index}].{field}")
        for optional_field in ("level2_module", "level3_module", "level4_module"):
            ensure_string(item.get(optional_field, ""), f"items[{index}].{optional_field}")

        if item["system"] in KNOWN_SYSTEM_CODES:
            raise ValidationError(f"items[{index}].system 必须使用系统中文名，不能使用系统编码: {item['system']}")
        if item["system"] not in KNOWN_SYSTEM_NAMES:
            raise ValidationError(f"items[{index}].system 不在已知系统中文名范围内: {item['system']}")
        if item["category"] not in CATEGORIES:
            raise ValidationError(f"items[{index}].category 枚举值非法: {item['category']}")
        if item["reuse"] not in REUSE_VALUES:
            raise ValidationError(f"items[{index}].reuse 枚举值非法: {item['reuse']}")
        if item["change_type"] not in CHANGE_TYPES:
            raise ValidationError(f"items[{index}].change_type 枚举值非法: {item['change_type']}")

    if "coverage_notes" in result:
        ensure_string(result["coverage_notes"], "coverage_notes")
    validate_uncounted_items(result.get("uncounted_items"))
    validate_quality_notes(result.get("quality_notes"))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 FPA AI结构化结果.json")
    parser.add_argument("--result-file", required=True)
    parser.add_argument("--schema-file", default="data/modules/fpa/profile/schema/result.schema.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = load_json(Path(args.result_file), "AI结构化结果")
        schema = load_json(Path(args.schema_file), "result.schema.json")
        validate_result(result, schema)
    except ValidationError as exc:
        print(f"校验失败: {exc}", file=sys.stderr)
        return 1

    print(f"校验通过: {args.result_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
