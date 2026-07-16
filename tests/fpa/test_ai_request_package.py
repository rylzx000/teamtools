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


class AiRequestPackageTests(unittest.TestCase):
    def run_builder(self, *args):
        return run_command([sys.executable, str(SCRIPT), *args])

    def test_demo_task_generates_messages_plain_prompt_and_summary(self):
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

            self.assertEqual(package["provider"], "deepseek")
            self.assertEqual(package["request_format"], "messages")
            self.assertEqual(package["messages"][0]["role"], "system")
            self.assertEqual(package["messages"][1]["role"], "user")
            self.assertIn("plain_prompt", package)
            self.assertIn("target_person_days: 10.0", package["plain_prompt"])
            self.assertIn("只输出结构化 JSON", package["plain_prompt"])
            self.assertIn("items[].system 必须输出系统中文名", package["plain_prompt"])
            self.assertIn("不要输出系统编码", package["plain_prompt"])
            self.assertIn("多个独立业务动作不能合并成一条功能点", package["plain_prompt"])
            self.assertIn("不计数的候选必须写入 uncounted_items", package["plain_prompt"])
            self.assertNotIn("API Key", json.dumps(package, ensure_ascii=False))
            self.assertFalse(Path(package["metadata"]["template_file"]).is_absolute())
            self.assertFalse(Path(package["metadata"]["schema_file"]).is_absolute())
            self.assertFalse(Path(package["metadata"]["knowledge_file"]).is_absolute())
            self.assertNotIn("查勘采集页面新增事故地点", json.dumps(summary, ensure_ascii=False))
            self.assertEqual(summary["system_code"], "onlineclaim")
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
        result = run_command(
            [
                sys.executable,
                str(VALIDATOR),
                "--result-file",
                "data/modules/fpa/examples/expected/AI结构化结果.sample.json",
                "--schema-file",
                str(SCHEMA),
            ]
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("校验通过", result.stdout)

    def test_validate_ai_result_rejects_invalid_enum_sample(self):
        result = run_command(
            [
                sys.executable,
                str(VALIDATOR),
                "--result-file",
                "data/modules/fpa/examples/expected/AI结构化结果.invalid.sample.json",
                "--schema-file",
                str(SCHEMA),
            ]
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(
            any(
                text in result.stderr
                for text in ("禁止字段", "未允许字段", "系统编码", "枚举值非法")
            ),
            result.stderr,
        )

    def test_validate_ai_result_rejects_invalid_category(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid-category.json"
            data = json.loads(
                (ROOT / "data/modules/fpa/examples/expected/AI结构化结果.sample.json").read_text(
                    encoding="utf-8"
                )
            )
            data["items"][0]["category"] = "INPUT"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = run_command(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--result-file",
                    str(path),
                    "--schema-file",
                    str(SCHEMA),
                ]
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("category 枚举值非法", result.stderr)

    def test_validate_ai_result_rejects_extra_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "extra.json"
            data = json.loads(
                (ROOT / "data/modules/fpa/examples/expected/AI结构化结果.sample.json").read_text(
                    encoding="utf-8"
                )
            )
            data["unexpected"] = "not allowed"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = run_command(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--result-file",
                    str(path),
                    "--schema-file",
                    str(SCHEMA),
                ]
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("未允许字段", result.stderr)

    def test_validate_ai_result_rejects_forbidden_workday_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "forbidden.json"
            data = json.loads(
                (ROOT / "data/modules/fpa/examples/expected/AI结构化结果.sample.json").read_text(
                    encoding="utf-8"
                )
            )
            data["adjusted_work_days_middle"] = 8.5
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = run_command(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--result-file",
                    str(path),
                    "--schema-file",
                    str(SCHEMA),
                ]
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("禁止字段", result.stderr)

    def test_validate_ai_result_rejects_system_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "system-code.json"
            data = json.loads(
                (ROOT / "data/modules/fpa/examples/expected/AI结构化结果.sample.json").read_text(
                    encoding="utf-8"
                )
            )
            data["items"][0]["system"] = "onlineclaim"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = run_command(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--result-file",
                    str(path),
                    "--schema-file",
                    str(SCHEMA),
                ]
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("系统中文名", result.stderr)

    def test_validate_ai_result_checks_review_note_structures(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad-note.json"
            data = json.loads(
                (ROOT / "data/modules/fpa/examples/expected/AI结构化结果.sample.json").read_text(
                    encoding="utf-8"
                )
            )
            data["quality_notes"][0]["severity"] = "critical"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = run_command(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--result-file",
                    str(path),
                    "--schema-file",
                    str(SCHEMA),
                ]
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("severity 枚举值非法", result.stderr)


if __name__ == "__main__":
    unittest.main()
