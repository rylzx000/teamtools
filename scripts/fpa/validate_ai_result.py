#!/usr/bin/env python3
"""Validate an FPA AI structured JSON result without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CATEGORIES = {"ILF", "EIF", "EI", "EO", "EQ"}
REUSE_VALUES = {"高", "中", "低"}
CHANGE_TYPES = {"新增", "修改", "删除"}
KNOWN_SYSTEM_NAMES = {"车险理赔核心系统", "非车险理赔核心系统", "在线理赔服务平台", "零配件报价系统"}
KNOWN_SYSTEM_CODES = {"claimcar", "claimoth", "onlineclaim", "clqp"}
ROUTE_CODES = {f"R{index:02d}" for index in range(16)}
FORBIDDEN_FIELDS = {
    "template_path",
    "output_path",
    "target_work_days",
    "target_hit",
    "adjusted_work_days_middle",
    "ufp",
    "us",
    "adjusted_fp",
    "final_work_days",
    "work_days",
    "function_point_total",
}
ROOT_ALLOWED = {
    "schema_version",
    "requirement_name",
    "assessment_context",
    "project_features",
    "change_facts",
    "routing_decisions",
    "split_merge_decisions",
    "frozen_items",
    "review_notes",
}
ID_PATTERNS = {
    "fact_id": r"^F-[0-9]{3}$",
    "route_id": r"^R-[0-9]{3}$",
    "decision_id": r"^D-[0-9]{3}$",
    "stable_id": r"^FP-[0-9]{3}$",
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


def ensure_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field} 必须是对象")
    return value


def ensure_list(value: Any, field: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{field} 必须是数组")
    if nonempty and not value:
        raise ValidationError(f"{field} 必须是非空数组")
    return value


def ensure_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} 必须是非空字符串")
    return value


def ensure_string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} 必须是字符串")
    return value


def reject_forbidden_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_FIELDS & set(value)
        if forbidden:
            raise ValidationError(f"{path} 存在禁止字段: " + ", ".join(sorted(forbidden)))
        for key, child in value.items():
            reject_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value, start=1):
            reject_forbidden_fields(child, f"{path}[{index}]")


def reject_extra_fields(item: dict[str, Any], allowed: set[str], field: str) -> None:
    extra = set(item) - allowed
    if extra:
        raise ValidationError(f"{field} 存在未允许字段: " + ", ".join(sorted(extra)))


def require_fields(item: dict[str, Any], required: set[str], field: str) -> None:
    missing = required - set(item)
    if missing:
        raise ValidationError(f"{field} 缺少字段: " + ", ".join(sorted(missing)))


def ensure_unique(items: list[dict[str, Any]], key: str, field: str) -> set[str]:
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        value = ensure_nonempty_string(item.get(key), f"{field}[{index}].{key}")
        if value in seen:
            raise ValidationError(f"{field}.{key} 重复: {value}")
        seen.add(value)
    return seen


def ensure_id_format(value: str, key: str, field: str) -> None:
    if not re.fullmatch(ID_PATTERNS[key], value):
        raise ValidationError(f"{field} 编号格式非法: {value}")


def ensure_refs(values: Any, existing: set[str], field: str, id_key: str) -> list[str]:
    refs = ensure_list(values, field, nonempty=True)
    normalized: list[str] = []
    for index, value in enumerate(refs, start=1):
        ref = ensure_nonempty_string(value, f"{field}[{index}]")
        ensure_id_format(ref, id_key, f"{field}[{index}]")
        if ref not in existing:
            raise ValidationError(f"{field} 存在悬空引用: {ref}")
        normalized.append(ref)
    return normalized


def validate_assessment_context(value: Any) -> dict[str, Any]:
    context = ensure_dict(value, "assessment_context")
    required = {
        "system_code",
        "system_name",
        "system_type",
        "has_system_knowledge",
        "has_system_scene_dictionary",
        "no_system_dictionary_mode",
        "target_person_days_provided",
        "target_calibration_policy",
    }
    allowed = required | {"source_level", "requirement_level", "estimation_mode", "dictionary_gap_note"}
    reject_extra_fields(context, allowed, "assessment_context")
    require_fields(context, required, "assessment_context")
    if context["system_code"] not in KNOWN_SYSTEM_CODES:
        raise ValidationError(f"assessment_context.system_code 非法: {context['system_code']}")
    if context["system_name"] not in KNOWN_SYSTEM_NAMES:
        raise ValidationError(f"assessment_context.system_name 非法: {context['system_name']}")
    ensure_nonempty_string(context.get("system_type"), "assessment_context.system_type")
    for key in ("has_system_knowledge", "has_system_scene_dictionary", "no_system_dictionary_mode", "target_person_days_provided"):
        if not isinstance(context.get(key), bool):
            raise ValidationError(f"assessment_context.{key} 必须是布尔值")
    ensure_nonempty_string(context.get("target_calibration_policy"), "assessment_context.target_calibration_policy")
    for key in ("source_level", "requirement_level", "estimation_mode", "dictionary_gap_note"):
        if key in context:
            ensure_string(context[key], f"assessment_context.{key}")
    if context["has_system_scene_dictionary"] and context["no_system_dictionary_mode"]:
        raise ValidationError("assessment_context 字典状态冲突: 已有系统字典但标记为无系统字典模式")
    if not context["has_system_scene_dictionary"] and not context.get("dictionary_gap_note", "").strip():
        raise ValidationError("assessment_context.dictionary_gap_note 缺失: 无系统字典模式必须说明资料缺口")
    return context


def validate_project_features(value: Any) -> None:
    if value is None:
        return
    features = ensure_dict(value, "project_features")
    reject_extra_fields(features, {"规模计数时机", "完整性级别"}, "project_features")
    if "规模计数时机" in features and features["规模计数时机"] not in {
        "估算早期",
        "估算中期",
        "估算晚期",
        "项目交付后及运维阶段",
    }:
        raise ValidationError(f"project_features.规模计数时机 枚举值非法: {features['规模计数时机']}")
    if "完整性级别" in features and features["完整性级别"] not in {
        "没有明确的完整性级别或等级为C/D",
        "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
        "完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施",
    }:
        raise ValidationError(f"project_features.完整性级别 枚举值非法: {features['完整性级别']}")


def validate_change_facts(value: Any) -> tuple[list[dict[str, Any]], set[str]]:
    facts = [ensure_dict(item, f"change_facts[{index}]") for index, item in enumerate(ensure_list(value, "change_facts", nonempty=True), start=1)]
    allowed = {
        "fact_id",
        "business_purpose",
        "trigger",
        "input",
        "processing",
        "output",
        "maintained_data",
        "referenced_data",
        "evidence",
        "in_scope",
        "exclusion_reason",
    }
    required = allowed - {"exclusion_reason"}
    for index, fact in enumerate(facts, start=1):
        field = f"change_facts[{index}]"
        reject_extra_fields(fact, allowed, field)
        require_fields(fact, required, field)
        ensure_id_format(ensure_nonempty_string(fact.get("fact_id"), f"{field}.fact_id"), "fact_id", f"{field}.fact_id")
        for key in ("business_purpose", "trigger", "processing", "evidence"):
            ensure_nonempty_string(fact.get(key), f"{field}.{key}")
        for key in ("input", "output", "maintained_data", "referenced_data", "exclusion_reason"):
            if key in fact:
                ensure_string(fact[key], f"{field}.{key}")
        if not isinstance(fact.get("in_scope"), bool):
            raise ValidationError(f"{field}.in_scope 必须是布尔值")
    return facts, ensure_unique(facts, "fact_id", "change_facts")


def validate_routing_decisions(value: Any, fact_ids: set[str]) -> tuple[list[dict[str, Any]], set[str]]:
    routes = [ensure_dict(item, f"routing_decisions[{index}]") for index, item in enumerate(ensure_list(value, "routing_decisions", nonempty=True), start=1)]
    allowed = {"route_id", "fact_ids", "route_code", "route_name", "candidate_category", "decision", "system_scene_ids", "rationale"}
    required = {"route_id", "fact_ids", "route_code", "route_name", "decision", "rationale"}
    for index, route in enumerate(routes, start=1):
        field = f"routing_decisions[{index}]"
        reject_extra_fields(route, allowed, field)
        require_fields(route, required, field)
        ensure_id_format(ensure_nonempty_string(route.get("route_id"), f"{field}.route_id"), "route_id", f"{field}.route_id")
        ensure_refs(route.get("fact_ids"), fact_ids, f"{field}.fact_ids", "fact_id")
        if route.get("route_code") not in ROUTE_CODES:
            raise ValidationError(f"{field}.route_code 枚举值非法: {route.get('route_code')}")
        ensure_nonempty_string(route.get("route_name"), f"{field}.route_name")
        if route.get("candidate_category", "待复核") not in CATEGORIES | {"不计数", "待复核"}:
            raise ValidationError(f"{field}.candidate_category 枚举值非法: {route.get('candidate_category')}")
        if route.get("decision") not in {"计数", "合并", "不计数", "待复核"}:
            raise ValidationError(f"{field}.decision 枚举值非法: {route.get('decision')}")
        ensure_nonempty_string(route.get("rationale"), f"{field}.rationale")
        if "system_scene_ids" in route:
            for scene_index, scene_id in enumerate(ensure_list(route["system_scene_ids"], f"{field}.system_scene_ids"), start=1):
                ensure_nonempty_string(scene_id, f"{field}.system_scene_ids[{scene_index}]")
    return routes, ensure_unique(routes, "route_id", "routing_decisions")


def validate_split_merge_decisions(value: Any, route_ids: set[str]) -> tuple[list[dict[str, Any]], set[str]]:
    decisions = [ensure_dict(item, f"split_merge_decisions[{index}]") for index, item in enumerate(ensure_list(value, "split_merge_decisions", nonempty=True), start=1)]
    allowed = {"decision_id", "route_ids", "decision", "result_stable_ids", "rationale"}
    required = {"decision_id", "route_ids", "decision", "rationale"}
    result_stable_ids: set[str] = set()
    for index, decision in enumerate(decisions, start=1):
        field = f"split_merge_decisions[{index}]"
        reject_extra_fields(decision, allowed, field)
        require_fields(decision, required, field)
        ensure_id_format(
            ensure_nonempty_string(decision.get("decision_id"), f"{field}.decision_id"),
            "decision_id",
            f"{field}.decision_id",
        )
        ensure_refs(decision.get("route_ids"), route_ids, f"{field}.route_ids", "route_id")
        if decision.get("decision") not in {"拆分", "合并", "不计数", "待复核"}:
            raise ValidationError(f"{field}.decision 枚举值非法: {decision.get('decision')}")
        ensure_nonempty_string(decision.get("rationale"), f"{field}.rationale")
        if "result_stable_ids" in decision:
            for stable_index, stable_id in enumerate(ensure_list(decision["result_stable_ids"], f"{field}.result_stable_ids"), start=1):
                ref = ensure_nonempty_string(stable_id, f"{field}.result_stable_ids[{stable_index}]")
                ensure_id_format(ref, "stable_id", f"{field}.result_stable_ids[{stable_index}]")
                result_stable_ids.add(ref)
    ensure_unique(decisions, "decision_id", "split_merge_decisions")
    return decisions, result_stable_ids


def validate_frozen_items(
    value: Any,
    fact_ids: set[str],
    route_ids: set[str],
    context: dict[str, Any],
    result_stable_ids: set[str],
    expected_system_name: str | None = None,
) -> list[dict[str, Any]]:
    items = [ensure_dict(item, f"frozen_items[{index}]") for index, item in enumerate(ensure_list(value, "frozen_items", nonempty=True), start=1)]
    allowed = {
        "stable_id",
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
        "fact_ids",
        "route_ids",
        "system_scene_ids",
    }
    required = allowed - {"system_scene_ids"}
    for index, item in enumerate(items, start=1):
        field = f"frozen_items[{index}]"
        reject_extra_fields(item, allowed, field)
        require_fields(item, required, field)
        stable_id = ensure_nonempty_string(item.get("stable_id"), f"{field}.stable_id")
        ensure_id_format(stable_id, "stable_id", f"{field}.stable_id")
        if result_stable_ids and stable_id not in result_stable_ids:
            raise ValidationError(f"{field}.stable_id 未被 split_merge_decisions.result_stable_ids 引用: {stable_id}")
        if item.get("system") in KNOWN_SYSTEM_CODES:
            raise ValidationError(f"{field}.system 必须使用系统中文名，不能使用系统编码: {item.get('system')}")
        if item.get("system") not in KNOWN_SYSTEM_NAMES:
            raise ValidationError(f"{field}.system 不在已知系统中文名范围内: {item.get('system')}")
        if expected_system_name and item.get("system") != expected_system_name:
            raise ValidationError(f"{field}.system 与当前任务系统不一致: {item.get('system')} != {expected_system_name}")
        for key in ("level1_module", "function_description", "count_item_name", "remark"):
            ensure_nonempty_string(item.get(key), f"{field}.{key}")
        for key in ("level2_module", "level3_module", "level4_module"):
            ensure_string(item.get(key), f"{field}.{key}")
        if item.get("category") not in CATEGORIES:
            raise ValidationError(f"{field}.category 枚举值非法: {item.get('category')}")
        if item.get("reuse") not in REUSE_VALUES:
            raise ValidationError(f"{field}.reuse 枚举值非法: {item.get('reuse')}")
        if item.get("change_type") not in CHANGE_TYPES:
            raise ValidationError(f"{field}.change_type 枚举值非法: {item.get('change_type')}")
        ensure_refs(item.get("fact_ids"), fact_ids, f"{field}.fact_ids", "fact_id")
        ensure_refs(item.get("route_ids"), route_ids, f"{field}.route_ids", "route_id")
        scene_ids = ensure_list(item.get("system_scene_ids", []), f"{field}.system_scene_ids")
        if context["has_system_scene_dictionary"] and not scene_ids:
            raise ValidationError(f"{field}.system_scene_ids 缺失: 命中系统 08 字典时冻结条目必须包含系统场景编号")
        for scene_index, scene_id in enumerate(scene_ids, start=1):
            ensure_nonempty_string(scene_id, f"{field}.system_scene_ids[{scene_index}]")
    ensure_unique(items, "stable_id", "frozen_items")
    return items


def validate_review_notes(value: Any) -> None:
    if value is None:
        return
    notes = ensure_list(value, "review_notes")
    allowed = {"code", "message", "severity"}
    for index, note_value in enumerate(notes, start=1):
        note = ensure_dict(note_value, f"review_notes[{index}]")
        reject_extra_fields(note, allowed, f"review_notes[{index}]")
        require_fields(note, allowed, f"review_notes[{index}]")
        ensure_nonempty_string(note.get("code"), f"review_notes[{index}].code")
        ensure_nonempty_string(note.get("message"), f"review_notes[{index}].message")
        if note.get("severity") not in {"low", "medium", "high"}:
            raise ValidationError(f"review_notes[{index}].severity 枚举值非法: {note.get('severity')}")


def validate_result(
    result: Any,
    schema: Any,
    *,
    expected_system_code: str | None = None,
    expected_system_name: str | None = None,
) -> None:
    if not isinstance(schema, dict):
        raise ValidationError("result.schema.json 必须是 JSON 对象")
    if not isinstance(result, dict):
        raise ValidationError("AI 结果必须是 JSON 对象")

    reject_forbidden_fields(result)
    reject_extra_fields(result, ROOT_ALLOWED, "顶层")
    require_fields(
        result,
        {
            "schema_version",
            "requirement_name",
            "assessment_context",
            "change_facts",
            "routing_decisions",
            "split_merge_decisions",
            "frozen_items",
        },
        "顶层",
    )
    if result.get("schema_version") != "fpa.ai_contract.v2":
        raise ValidationError(f"schema_version 非法: {result.get('schema_version')}")
    ensure_nonempty_string(result.get("requirement_name"), "requirement_name")
    context = validate_assessment_context(result.get("assessment_context"))
    if expected_system_code and context.get("system_code") != expected_system_code:
        raise ValidationError(
            f"assessment_context.system_code 与当前任务系统不一致: {context.get('system_code')} != {expected_system_code}"
        )
    if expected_system_name and context.get("system_name") != expected_system_name:
        raise ValidationError(
            f"assessment_context.system_name 与当前任务系统不一致: {context.get('system_name')} != {expected_system_name}"
        )
    validate_project_features(result.get("project_features", {}))
    _, fact_ids = validate_change_facts(result.get("change_facts"))
    _, route_ids = validate_routing_decisions(result.get("routing_decisions"), fact_ids)
    _, result_stable_ids = validate_split_merge_decisions(result.get("split_merge_decisions"), route_ids)
    validate_frozen_items(result.get("frozen_items"), fact_ids, route_ids, context, result_stable_ids, expected_system_name)
    validate_review_notes(result.get("review_notes"))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 FPA AI结构化结果.json")
    parser.add_argument("--result-file", required=True)
    parser.add_argument("--schema-file", default="data/modules/fpa/profile/schema/result.schema.json")
    parser.add_argument("--expected-system-code")
    parser.add_argument("--expected-system-name")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = load_json(Path(args.result_file), "AI结构化结果")
        schema = load_json(Path(args.schema_file), "result.schema.json")
        validate_result(
            result,
            schema,
            expected_system_code=args.expected_system_code,
            expected_system_name=args.expected_system_name,
        )
    except ValidationError as exc:
        print(f"校验失败: {exc}", file=sys.stderr)
        return 1

    print(f"校验通过: {args.result_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
