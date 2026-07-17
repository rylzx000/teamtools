import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "fpa" / "build_ai_request_package.py"
SCHEMA = ROOT / "data" / "modules" / "fpa" / "profile" / "schema" / "result.schema.json"
SAMPLE = ROOT / "data" / "modules" / "fpa" / "examples" / "expected" / "AI结构化结果.sample.json"
INVALID_SAMPLE = ROOT / "data" / "modules" / "fpa" / "examples" / "expected" / "AI结构化结果.invalid.sample.json"
VALIDATOR = ROOT / "scripts" / "fpa" / "validate_ai_result.py"


def run_command(args, **kwargs):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    options = {
        "cwd": ROOT,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "env": env,
    }
    options.update(kwargs)
    return subprocess.run(args, **options)


def load_sample():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


class AiRequestPackageTests(unittest.TestCase):
    def run_builder(self, *args):
        return run_command([sys.executable, str(SCRIPT), *args])

    def run_validator(self, result_file, *extra_args):
        return run_command(
            [
                sys.executable,
                str(VALIDATOR),
                "--result-file",
                str(result_file),
                "--schema-file",
                str(SCHEMA),
                *extra_args,
            ]
        )

    def assert_validation_fails(self, data, expected_text, *extra_args):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            result = self.run_validator(path, *extra_args)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text, result.stderr)

    def test_demo_task_generates_dual_section_prompt_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "ai"
            result = self.run_builder(
                "--task-dir",
                "data/modules/fpa/examples/demo-task",
                "--data-dir",
                "data",
                "--profile-dir",
                "data/modules/fpa/profile",
                "--systems-config",
                "data/config/modules/fpa/systems.yaml",
                "--system-code",
                "onlineclaim",
                "--output-dir",
                str(output_dir),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            package = json.loads((output_dir / "AI请求包.json").read_text(encoding="utf-8"))
            summary = json.loads((output_dir / "AI请求摘要.json").read_text(encoding="utf-8"))

            prompt = package["plain_prompt"]
            self.assertEqual(package["provider"], "deepseek")
            self.assertEqual(package["request_format"], "messages")
            self.assertEqual(package["messages"][0]["role"], "system")
            self.assertEqual(package["messages"][1]["role"], "user")
            self.assertIn("<AI评估.md>", prompt)
            self.assertIn("<AI结构化结果.json>", prompt)
            self.assertIn("change_facts", prompt)
            self.assertIn("routing_decisions", prompt)
            self.assertIn("split_merge_decisions", prompt)
            self.assertIn("frozen_items", prompt)
            self.assertIn("target_person_days: 10.0", prompt)
            self.assertIn("目标人天只能作为校准参考", prompt)
            self.assertIn("不得改变功能点数量、拆分/合并边界", prompt)
            self.assertIn("优先使用 08-FPA场景拆分字典.md", prompt)
            self.assertIn("无系统字典模式", prompt)
            self.assertIn("规模计数时机: 估算早期", prompt)
            self.assertIn(
                "完整性级别: 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
                prompt,
            )
            package_text = json.dumps(package, ensure_ascii=False)
            self.assertNotIn("sk-", package_text)
            self.assertNotIn("OPENAI_API_KEY", package_text)
            self.assertFalse(Path(package["metadata"]["template_file"]).is_absolute())
            self.assertFalse(Path(package["metadata"]["schema_file"]).is_absolute())
            self.assertFalse(Path(package["metadata"]["knowledge_file"]).is_absolute())
            self.assertEqual(package["metadata"]["project_features"]["规模计数时机"], "估算早期")
            self.assertEqual(
                package["metadata"]["project_features"]["完整性级别"],
                "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
            )
            self.assertFalse(package["metadata"]["has_system_scene_dictionary"])
            self.assertTrue(package["metadata"]["no_system_dictionary_mode"])
            self.assertEqual(package["metadata"]["scene_dictionary_file"], "")
            self.assertNotIn("查勘采集页面新增事故地点", json.dumps(summary, ensure_ascii=False))
            self.assertEqual(summary["system_code"], "onlineclaim")
            self.assertFalse(summary["has_system_scene_dictionary"])
            self.assertTrue(summary["no_system_dictionary_mode"])
            self.assertEqual(summary["scene_dictionary_file"], "")
            self.assertEqual(summary["dictionary_chars"], 0)
            self.assertGreater(summary["brief_chars"], 0)
            self.assertGreater(summary["prompt_chars"], 0)

    def test_unknown_system_code_fails_without_partial_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "ai"
            result = self.run_builder(
                "--task-dir",
                "data/modules/fpa/examples/demo-task",
                "--data-dir",
                "data",
                "--profile-dir",
                "data/modules/fpa/profile",
                "--systems-config",
                "data/config/modules/fpa/systems.yaml",
                "--system-code",
                "missing",
                "--output-dir",
                str(output_dir),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("system_code 不存在", result.stderr)
            self.assertFalse((output_dir / "AI请求包.json").exists())

    def test_validate_ai_result_accepts_valid_sample(self):
        result = self.run_validator(SAMPLE)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("校验通过", result.stdout)

    def test_validate_ai_result_rejects_invalid_sample(self):
        result = self.run_validator(INVALID_SAMPLE)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(
            any(
                text in result.stderr
                for text in ("禁止字段", "未允许字段", "系统中文名", "枚举值非法", "悬空引用")
            ),
            result.stderr,
        )

    def test_validate_ai_result_rejects_duplicate_fact_id(self):
        data = load_sample()
        data["change_facts"][1]["fact_id"] = data["change_facts"][0]["fact_id"]

        self.assert_validation_fails(data, "change_facts.fact_id 重复")

    def test_validate_ai_result_rejects_duplicate_route_id(self):
        data = load_sample()
        data["routing_decisions"][1]["route_id"] = data["routing_decisions"][0]["route_id"]

        self.assert_validation_fails(data, "routing_decisions.route_id 重复")

    def test_validate_ai_result_rejects_duplicate_stable_id(self):
        data = load_sample()
        data["frozen_items"][1]["stable_id"] = data["frozen_items"][0]["stable_id"]

        self.assert_validation_fails(data, "frozen_items.stable_id 重复")

    def test_validate_ai_result_rejects_dangling_fact_reference(self):
        data = load_sample()
        data["frozen_items"][0]["fact_ids"] = ["F-999"]

        self.assert_validation_fails(data, "frozen_items[1].fact_ids 存在悬空引用")

    def test_validate_ai_result_rejects_dangling_route_reference(self):
        data = load_sample()
        data["split_merge_decisions"][0]["route_ids"] = ["R-999"]

        self.assert_validation_fails(data, "split_merge_decisions[1].route_ids 存在悬空引用")

    def test_validate_ai_result_requires_traceability_on_frozen_items(self):
        data = load_sample()
        data["frozen_items"][0]["route_ids"] = []

        self.assert_validation_fails(data, "frozen_items[1].route_ids 必须是非空数组")

    def test_validate_ai_result_requires_scene_ids_when_dictionary_hit(self):
        data = load_sample()
        data["assessment_context"]["has_system_scene_dictionary"] = True
        data["assessment_context"]["no_system_dictionary_mode"] = False
        for item in data["frozen_items"]:
            item["system_scene_ids"] = []

        self.assert_validation_fails(data, "system_scene_ids 缺失")

    def test_validate_ai_result_rejects_invalid_category(self):
        data = load_sample()
        data["frozen_items"][0]["category"] = "INPUT"

        self.assert_validation_fails(data, "category 枚举值非法")

    def test_validate_ai_result_rejects_extra_field(self):
        data = load_sample()
        data["unexpected"] = "not allowed"

        self.assert_validation_fails(data, "未允许字段")

    def test_validate_ai_result_rejects_forbidden_workday_fields(self):
        data = load_sample()
        data["adjusted_work_days_middle"] = 8.5

        self.assert_validation_fails(data, "禁止字段")

    def test_validate_ai_result_rejects_nested_forbidden_fields(self):
        data = load_sample()
        data["frozen_items"][0]["ufp"] = 3

        self.assert_validation_fails(data, "禁止字段")

    def test_validate_ai_result_rejects_system_code(self):
        data = load_sample()
        data["frozen_items"][0]["system"] = "onlineclaim"

        self.assert_validation_fails(data, "系统中文名")

    def test_validate_ai_result_checks_review_note_structures(self):
        data = load_sample()
        data["review_notes"][0]["severity"] = "critical"

        self.assert_validation_fails(data, "severity 枚举值非法")

    def test_validate_ai_result_rejects_invalid_project_feature_values(self):
        data = load_sample()
        data["project_features"] = copy.deepcopy(data["project_features"])
        data["project_features"]["规模计数时机"] = "估算随意"

        self.assert_validation_fails(data, "project_features.规模计数时机 枚举值非法")

    def test_validate_ai_result_rejects_wrong_expected_system(self):
        data = load_sample()

        self.assert_validation_fails(
            data,
            "assessment_context.system_code 与当前任务系统不一致",
            "--expected-system-code",
            "claimcar",
            "--expected-system-name",
            "车险理赔核心系统",
        )

    def test_validate_ai_result_rejects_invalid_id_format_with_consistent_refs(self):
        data = load_sample()
        fact_map = {fact["fact_id"]: fact["fact_id"].replace("F-", "FACT-") for fact in data["change_facts"]}
        route_map = {route["route_id"]: route["route_id"].replace("R-", "ROUTE-") for route in data["routing_decisions"]}
        decision_map = {
            decision["decision_id"]: decision["decision_id"].replace("D-", "DECISION-")
            for decision in data["split_merge_decisions"]
        }
        stable_map = {item["stable_id"]: item["stable_id"].replace("FP-", "ITEM-") for item in data["frozen_items"]}
        for fact in data["change_facts"]:
            fact["fact_id"] = fact_map[fact["fact_id"]]
        for route in data["routing_decisions"]:
            route["route_id"] = route_map[route["route_id"]]
            route["fact_ids"] = [fact_map[value] for value in route["fact_ids"]]
        for decision in data["split_merge_decisions"]:
            decision["decision_id"] = decision_map[decision["decision_id"]]
            decision["route_ids"] = [route_map[value] for value in decision["route_ids"]]
            decision["result_stable_ids"] = [stable_map[value] for value in decision.get("result_stable_ids", [])]
        for item in data["frozen_items"]:
            item["stable_id"] = stable_map[item["stable_id"]]
            item["fact_ids"] = [fact_map[value] for value in item["fact_ids"]]
            item["route_ids"] = [route_map[value] for value in item["route_ids"]]

        self.assert_validation_fails(data, "编号格式非法")


if __name__ == "__main__":
    unittest.main()
