from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import urlencode

from openpyxl import load_workbook

from app.config import get_config
from app.db import initialize_database, open_connection
from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALID_SYSTEM_NAME = "车险理赔核心系统"
VALID_ITEM = {
    "stable_id": "FP-001",
    "system": VALID_SYSTEM_NAME,
    "level1_module": "理赔",
    "level2_module": "影像",
    "level3_module": "",
    "level4_module": "",
    "function_description": "提交理赔影像补传材料",
    "count_item_name": "影像补传提交",
    "category": "EI",
    "reuse": "中",
    "change_type": "新增",
    "remark": "EI 输入；中复用；新增提交能力",
}


class AsgiClient:
    def __init__(self, app):
        self.app = app
        self.cookies: dict[str, str] = {}

    def get(self, path: str):
        return self.request("GET", path)

    def post(self, path: str, *, json=None, data=None):
        return self.request("POST", path, json=json, data=data)

    def request(self, method: str, path: str, *, json=None, data=None):
        import asyncio

        return asyncio.run(self._request(method, path, json=json, data=data))

    async def _request(self, method: str, path: str, *, json=None, data=None):
        import json as json_module

        headers: list[tuple[bytes, bytes]] = []
        body = b""
        if json is not None:
            body = json_module.dumps(json, ensure_ascii=False).encode("utf-8")
            headers.append((b"content-type", b"application/json"))
        elif data is not None:
            body = urlencode(data).encode("utf-8")
            headers.append((b"content-type", b"application/x-www-form-urlencoded"))
        if self.cookies:
            cookie_value = "; ".join(f"{key}={value}" for key, value in self.cookies.items())
            headers.append((b"cookie", cookie_value.encode("utf-8")))
        headers.append((b"content-length", str(len(body)).encode("ascii")))

        status = 500
        response_headers: list[tuple[bytes, bytes]] = []
        chunks: list[bytes] = []
        sent = False

        async def receive():
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            nonlocal status, response_headers
            if message["type"] == "http.response.start":
                status = message["status"]
                response_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "method": method,
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "scheme": "http",
        }
        await self.app(scope, receive, send)
        response = AsgiResponse(status, response_headers, b"".join(chunks))
        for raw_header, raw_value in response_headers:
            if raw_header.lower() == b"set-cookie":
                cookie = SimpleCookie(raw_value.decode("latin1"))
                for key, morsel in cookie.items():
                    if morsel.value:
                        self.cookies[key] = morsel.value
                    else:
                        self.cookies.pop(key, None)
        return response


class AsgiResponse:
    def __init__(self, status_code: int, headers: list[tuple[bytes, bytes]], content: bytes):
        self.status_code = status_code
        self.headers = {key.decode("latin1").lower(): value.decode("latin1") for key, value in headers}
        self.content = content
        self.text = content.decode("utf-8", errors="replace")

    def json(self):
        import json

        return json.loads(self.text)


class FpaMvpTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["TEAMTOOLS_SEED_DEV_USERS"] = "true"
        get_config.cache_clear()

    def tearDown(self) -> None:
        os.environ.pop("TEAMTOOLS_SEED_DEV_USERS", None)
        os.environ.pop("TEAMTOOLS_DB_PATH", None)
        os.environ.pop("TEAMTOOLS_DATA_DIR", None)
        os.environ.pop("TEAMTOOLS_WORKER_ONCE", None)
        get_config.cache_clear()

    def make_data_dir(self, tmp_path: Path) -> Path:
        data_dir = tmp_path / "data"
        shutil.copytree(PROJECT_ROOT / "data" / "modules", data_dir / "modules")
        shutil.copytree(PROJECT_ROOT / "data" / "config", data_dir / "config")
        return data_dir

    def make_client(self, tmp_path: Path) -> AsgiClient:
        data_dir = self.make_data_dir(tmp_path)
        return AsgiClient(
            create_app(
                data_dir=data_dir,
                db_path=tmp_path / "teamtools-test.db",
                frontend_dist_dir=tmp_path / "frontend" / "dist",
            )
        )

    def login(self, client: AsgiClient, username: str = "admin", password: str = "admin123") -> None:
        response = client.post("/api/auth/login", json={"username": username, "password": password})
        self.assertEqual(response.status_code, 200, response.text)

    def create_waiting_task(
        self,
        client: AsgiClient,
        *,
        title: str = "理赔影像补传",
        target_days: str = "3.0",
        system_code: str = "claimcar",
        count_timing: str = "估算早期",
        integrity_level: str | None = None,
    ) -> str:
        data = {
            "system_code": system_code,
            "title": title,
            "input_text": "新增理赔影像补传、查询和审核结果通知。",
            "target_person_days": target_days,
            "count_timing": count_timing,
        }
        if integrity_level:
            data["integrity_level"] = integrity_level
        created = client.post(
            "/api/fpa/tasks",
            data=data,
        )
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["task"]["status"], "waiting_ai_call")
        return created.json()["task"]["id"]

    def test_create_task_accepts_new_project_feature_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self.make_client(Path(temp_dir))
            self.login(client)

            created = client.post(
                "/api/fpa/tasks",
                data={
                    "system_code": "claimcar",
                    "title": "新参数任务",
                    "input_text": "新增理赔影像补传。",
                    "count_timing": "项目交付后及运维阶段",
                    "integrity_level": "没有明确的完整性级别或等级为C/D",
                },
            )
            self.assertEqual(created.status_code, 200, created.text)
            task_id = created.json()["task"]["id"]
            params_path = Path(temp_dir) / "data" / "tasks" / "fpa" / task_id / "input" / "task_params.json"
            params = json.loads(params_path.read_text(encoding="utf-8"))
            self.assertEqual(params["count_timing"], "项目交付后及运维阶段")
            self.assertEqual(params["integrity_level"], "没有明确的完整性级别或等级为C/D")

    def test_rerun_preserves_project_feature_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            client = self.make_client(tmp_path)
            self.login(client)
            task_id = self.create_waiting_task(
                client,
                count_timing="项目交付后及运维阶段",
                integrity_level="完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施",
            )

            rerun = client.post(f"/api/fpa/tasks/{task_id}/rerun")
            self.assertEqual(rerun.status_code, 200, rerun.text)
            new_task_id = rerun.json()["task"]["id"]
            params_path = tmp_path / "data" / "tasks" / "fpa" / new_task_id / "input" / "task_params.json"
            params = json.loads(params_path.read_text(encoding="utf-8"))
            self.assertEqual(params["count_timing"], "项目交付后及运维阶段")
            self.assertEqual(
                params["integrity_level"],
                "完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施",
            )

    def test_form_config_returns_safe_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            client = self.make_client(tmp_path)
            self.login(client)

            response = client.get("/api/fpa/form-config")

            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertIn("systems", payload)
            self.assertIn("count_timings", payload)
            self.assertIn("integrity_levels", payload)
            self.assertIn("defaults", payload)
            self.assertEqual(payload["defaults"]["count_timing"], "估算中期")
            self.assertEqual(
                payload["defaults"]["integrity_level"],
                "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
            )
            self.assertIn("1.21 估算中期", [item["label"] for item in payload["count_timings"]])
            self.assertIn(
                "1.10 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
                [item["label"] for item in payload["integrity_levels"]],
            )
            dumped = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn("knowledge_dir", dumped)
            self.assertNotIn(str(tmp_path / "data"), dumped)

    def valid_structured_json(self) -> dict:
        sample = PROJECT_ROOT / "data" / "modules" / "fpa" / "examples" / "expected" / "AI结构化结果.sample.json"
        return json.loads(sample.read_text(encoding="utf-8"))

    def structured_for_system(
        self,
        system_code: str = "claimcar",
        system_name: str = VALID_SYSTEM_NAME,
        *,
        has_dictionary: bool = False,
    ) -> dict:
        structured = deepcopy(self.valid_structured_json())
        structured["assessment_context"]["system_code"] = system_code
        structured["assessment_context"]["system_name"] = system_name
        if has_dictionary:
            structured["assessment_context"]["has_system_scene_dictionary"] = True
            structured["assessment_context"]["no_system_dictionary_mode"] = False
            structured["assessment_context"]["dictionary_gap_note"] = ""
            for route in structured["routing_decisions"]:
                route["system_scene_ids"] = ["SC-001"]
            for item in structured["frozen_items"]:
                item["system_scene_ids"] = ["SC-001"]
            structured["review_notes"] = []
        for item in structured["frozen_items"]:
            item["system"] = system_name
        return structured

    def valid_raw_response(self) -> dict:
        sample = PROJECT_ROOT / "data" / "modules" / "fpa" / "examples" / "expected" / "AI响应.sample.md"
        return {"choices": [{"message": {"content": sample.read_text(encoding="utf-8")}}]}

    def test_fpa_happy_path_creates_task_generates_request_and_excel(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            client = self.make_client(tmp_path)
            self.login(client, "demo", "demo123")

            systems = client.get("/api/fpa/systems")
            self.assertEqual(systems.status_code, 200)
            self.assertEqual(
                [item["code"] for item in systems.json()["items"]],
                ["claimcar", "claimoth", "onlineclaim", "clqp"],
            )

            task_id = self.create_waiting_task(
                client,
                system_code="onlineclaim",
                count_timing="估算中期",
                integrity_level="完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
            )

            detail_before_ai = client.get(f"/api/fpa/tasks/{task_id}")
            self.assertEqual(detail_before_ai.status_code, 200, detail_before_ai.text)
            self.assertEqual(detail_before_ai.json()["task"]["status"], "waiting_ai_call")

            ai_request = client.get(f"/api/fpa/tasks/{task_id}/ai-request")
            self.assertEqual(ai_request.status_code, 200, ai_request.text)
            payload = ai_request.json()["ai_request"]
            self.assertEqual(payload["provider"], "deepseek")
            self.assertEqual(payload["request_format"], "messages")
            self.assertNotIn("metadata", payload)
            self.assertIn("target_person_days", payload["plain_prompt"])

            ai_package_file = Path(temp_dir) / "data" / "tasks" / "fpa" / task_id / "ai" / "AI请求包.json"
            ai_package = json.loads(ai_package_file.read_text(encoding="utf-8"))
            self.assertIn("metadata", ai_package)
            self.assertEqual(ai_package["metadata"]["schema_file"], "result.schema.json")
            self.assertEqual(ai_package["metadata"]["template_file"], "prompt_template.md")
            self.assertIn("target_person_days", ai_package["plain_prompt"])

            raw_response = self.valid_raw_response()
            raw_response["apiKey"] = "sk-test-secret"
            result = client.post(
                f"/api/fpa/tasks/{task_id}/ai-result",
                json={
                    "success": True,
                    "provider": "deepseek",
                    "model": "deepseek-v4-flash",
                    "raw_response": raw_response,
                },
            )
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["task"]["status"], "completed")

            detail = client.get(f"/api/fpa/tasks/{task_id}")
            self.assertEqual(detail.status_code, 200)
            body = detail.json()
            self.assertEqual(body["task"]["status_label"], "已完成")
            self.assertIsNotNone(body["task"]["result_median_person_days"])
            self.assertTrue(body["artifacts"]["excel_result"]["available"])
            self.assertFalse(body["artifacts"]["fpa_process_json"]["available"])
            self.assertIsNone(body["artifacts"]["fpa_process_json"]["content"])
            self.assertFalse(body["artifacts"]["ai_analysis_md"]["available"])
            self.assertIsNone(body["artifacts"]["ai_analysis_md"]["content"])
            self.assertTrue(body["artifacts"]["result_summary"]["available"])
            self.assertEqual(body["artifacts"]["result_summary"]["content"]["item_count"], 4)

            process_path = tmp_path / "data" / "tasks" / "fpa" / task_id / "runtime" / "FPA生成过程.json"
            process = json.loads(process_path.read_text(encoding="utf-8"))
            self.assertEqual(process["schema_version"], "fpa.excel_process.v1")
            self.assertIn("estimates", process)
            self.assertIsInstance(process["quality_gate"], dict)
            self.assertEqual(process["items"][0]["stable_id"], "FP-001")
            self.assertEqual(process["project_features"]["规模计数时机"], "估算中期")
            self.assertEqual(
                process["project_features"]["完整性级别"],
                "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
            )
            self.assertEqual(process["project_feature_factors"]["规模计数时机"], 1.21)
            self.assertEqual(process["project_feature_factors"]["完整性级别"], 1.1)
            self.assertEqual(process["assessment_context"]["review_notes"][0]["code"], "NO_SYSTEM_SCENE_DICTIONARY")
            self.assertEqual(body["task"]["result_median_person_days"], process["estimates"]["work_days"]["middle"])

            downloaded = client.get(f"/api/fpa/tasks/{task_id}/download/excel")
            self.assertEqual(downloaded.status_code, 200)
            self.assertTrue(downloaded.content.startswith(b"PK"))
            self.assertGreater(len(downloaded.content), 10_000)
            excel_path = Path(temp_dir) / "data" / "tasks" / "fpa" / task_id / "output" / "FPA工作量评估.xlsx"
            with zipfile.ZipFile(excel_path) as workbook:
                names = set(workbook.namelist())
            self.assertIn("xl/styles.xml", names)
            self.assertGreaterEqual(len([name for name in names if name.startswith("xl/worksheets/sheet")]), 2)

            payload_path = tmp_path / "data" / "tasks" / "fpa" / task_id / "runtime" / "Excel脚本输入payload.json"
            raw_response_path = tmp_path / "data" / "tasks" / "fpa" / task_id / "ai" / "AI原始响应.json"
            self.assertNotIn("sk-test-secret", raw_response_path.read_text(encoding="utf-8"))
            self.assertTrue(payload_path.exists())
            self.assertTrue(process_path.exists())
            excel_payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(excel_payload["target_work_days"], 3.0)
            self.assertEqual(excel_payload["assessment_context"]["task_id"], task_id)
            self.assertEqual(len(excel_payload["items"]), 4)
            self.assertEqual(excel_payload["items"][0]["stable_id"], "FP-001")
            self.assertEqual(excel_payload["assessment_context"]["review_notes"][0]["code"], "NO_SYSTEM_SCENE_DICTIONARY")
            self.assertEqual(
                excel_payload["project_features"]["integrity_level"],
                "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
            )
            with open_connection(tmp_path / "teamtools-test.db") as conn:
                counts = conn.execute(
                    "SELECT ai_item_count, result_item_count FROM fpa_task_details WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
            self.assertEqual(counts["ai_item_count"], 4)
            self.assertEqual(counts["result_item_count"], 4)

    def test_dictionary_mapping_fields_are_preserved_to_excel_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            client = self.make_client(tmp_path)
            self.login(client)
            task_id = self.create_waiting_task(client, system_code="claimcar", title="字典字段保留")
            structured = self.structured_for_system(has_dictionary=True)
            for index, item in enumerate(structured["frozen_items"], start=1):
                item["level1_module"] = "理赔服务"
                item["level2_module"] = f"字典二级模块{index}"
                item["count_item_name"] = f"字典计数项{index}"

            result = client.post(
                f"/api/fpa/tasks/{task_id}/ai-result",
                json={
                    "success": True,
                    "provider": "deepseek",
                    "model": "deepseek-v4-flash",
                    "structured_json": structured,
                },
            )
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["task"]["status"], "completed")

            task_root = tmp_path / "data" / "tasks" / "fpa" / task_id
            excel_payload = json.loads((task_root / "runtime" / "Excel脚本输入payload.json").read_text(encoding="utf-8"))
            process = json.loads((task_root / "runtime" / "FPA生成过程.json").read_text(encoding="utf-8"))
            workbook = load_workbook(task_root / "output" / "FPA工作量评估.xlsx", data_only=False)
            size = workbook["规模估算"]

            for index, expected in enumerate(structured["frozen_items"], start=1):
                row = 5 + index
                payload_item = excel_payload["items"][index - 1]
                process_item = process["items"][index - 1]
                for field in ("level1_module", "level2_module", "count_item_name", "system_scene_ids"):
                    self.assertEqual(payload_item[field], expected[field])
                    self.assertEqual(process_item[field], expected[field])
                self.assertEqual(size[f"C{row}"].value, expected["level1_module"])
                self.assertEqual(size[f"D{row}"].value, expected["level2_module"])
                self.assertEqual(size[f"H{row}"].value, expected["count_item_name"])

    def test_target_person_days_does_not_change_frozen_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            client = self.make_client(tmp_path)
            self.login(client)
            base_structured = self.structured_for_system()
            expected_items = [
                (
                    item["stable_id"],
                    item["function_description"],
                    item["count_item_name"],
                    item["category"],
                    item["route_ids"],
                )
                for item in base_structured["frozen_items"]
            ]

            for target_days in ("1.0", "20.0"):
                with self.subTest(target_days=target_days):
                    task_id = self.create_waiting_task(
                        client,
                        title=f"目标人天{target_days}",
                        target_days=target_days,
                        system_code="claimcar",
                    )
                    result = client.post(
                        f"/api/fpa/tasks/{task_id}/ai-result",
                        json={
                            "success": True,
                            "provider": "deepseek",
                            "model": "deepseek-v4-flash",
                            "structured_json": deepcopy(base_structured),
                        },
                    )
                    self.assertEqual(result.status_code, 200, result.text)
                    self.assertEqual(result.json()["task"]["status"], "completed")

                    task_root = tmp_path / "data" / "tasks" / "fpa" / task_id
                    excel_payload = json.loads(
                        (task_root / "runtime" / "Excel脚本输入payload.json").read_text(encoding="utf-8")
                    )
                    process = json.loads((task_root / "runtime" / "FPA生成过程.json").read_text(encoding="utf-8"))
                    actual_payload_items = [
                        (
                            item["stable_id"],
                            item["function_description"],
                            item["count_item_name"],
                            item["category"],
                            item["route_ids"],
                        )
                        for item in excel_payload["items"]
                    ]
                    actual_process_items = [
                        (
                            item["stable_id"],
                            item["function_description"],
                            item["count_item_name"],
                            item["category"],
                            item["route_ids"],
                        )
                        for item in process["items"]
                    ]
                    self.assertEqual(excel_payload["target_work_days"], float(target_days))
                    self.assertEqual(actual_payload_items, expected_items)
                    self.assertEqual(actual_process_items, expected_items)

    def test_regular_user_sees_summary_not_internal_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            client = self.make_client(tmp_path)
            self.login(client, "demo", "demo123")

            created = client.post(
                "/api/fpa/tasks",
                data={
                    "system_code": "claimcar",
                    "title": "普通用户任务",
                    "input_text": "新增理赔影像补传、查询和审核结果通知。",
                },
            )
            self.assertEqual(created.status_code, 200, created.text)
            task_id = created.json()["task"]["id"]
            params_path = tmp_path / "data" / "tasks" / "fpa" / task_id / "input" / "task_params.json"
            params = json.loads(params_path.read_text(encoding="utf-8"))
            self.assertEqual(params["count_timing"], "估算中期")
            self.assertEqual(
                params["integrity_level"],
                "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
            )

            task_root = tmp_path / "data" / "tasks" / "fpa" / task_id
            process = {
                "schema_version": "fpa.excel_process.v1",
                "item_count": 3,
                "estimates": {
                    "function_point_total": 18.0,
                    "adjusted_fp_total": 21.78,
                    "work_days": {"low": 2.3, "middle": 2.8, "high": 3.3},
                    "target_check": {"hit_status": "hit", "difference_days": -0.2},
                },
                "quality_gate": {"status": "passed", "failed": False, "deliverable_valid": True},
                "quality_warnings": [],
                "assessment_context": {
                    "quality_notes": [{"code": "REVIEW_IMAGE_FLOW", "message": "建议复核影像补传流程边界。", "severity": "medium"}],
                    "uncounted_items": [{"description": "历史影像批量迁移", "reason": "存量数据处理"}],
                    "coverage_notes": "已覆盖提交、查询和记录维护。",
                },
            }
            (task_root / "runtime" / "FPA生成过程.json").write_text(json.dumps(process, ensure_ascii=False), encoding="utf-8")
            (task_root / "ai" / "AI分析.md").write_text("已按 FPA 类别拆分。", encoding="utf-8")
            (task_root / "output" / "FPA工作量评估.xlsx").write_bytes(b"PK-test-workbook")
            with open_connection(tmp_path / "teamtools-test.db") as conn:
                conn.execute("UPDATE tasks SET status = 'completed', finished_at = updated_at WHERE id = ?", (task_id,))
                conn.execute(
                    """
                    UPDATE fpa_task_details
                    SET result_median_person_days = ?, target_hit = ?, quality_flags = ?
                    WHERE task_id = ?
                    """,
                    (2.8, 1, "[]", task_id),
                )
                conn.commit()

            detail = client.get(f"/api/fpa/tasks/{task_id}")
            self.assertEqual(detail.status_code, 200, detail.text)
            body = detail.json()
            self.assertFalse(body["artifacts"]["ai_request_summary"]["available"])
            self.assertIsNone(body["artifacts"]["ai_request_summary"]["content"])
            self.assertFalse(body["artifacts"]["fpa_process_json"]["available"])
            self.assertIsNone(body["artifacts"]["fpa_process_json"]["content"])
            self.assertTrue(body["artifacts"]["result_summary"]["available"])
            self.assertIn("work_days", body["artifacts"]["result_summary"]["content"])
            self.assertFalse(body["artifacts"]["ai_analysis_md"]["available"])
            self.assertIsNone(body["artifacts"]["ai_analysis_md"]["content"])

            downloaded = client.get(f"/api/fpa/tasks/{task_id}/download/excel")
            self.assertEqual(downloaded.status_code, 200)
            self.assertEqual(downloaded.content, b"PK-test-workbook")

            client.post("/api/auth/logout")
            self.login(client, "admin", "admin123")
            admin_detail = client.get(f"/api/fpa/tasks/{task_id}")
            self.assertEqual(admin_detail.status_code, 200, admin_detail.text)
            admin_body = admin_detail.json()
            self.assertTrue(admin_body["artifacts"]["ai_analysis_md"]["available"])
            self.assertIn("已按 FPA 类别拆分", admin_body["artifacts"]["ai_analysis_md"]["content"])
            self.assertTrue(admin_body["artifacts"]["fpa_process_json"]["available"])
            self.assertIsNotNone(admin_body["artifacts"]["fpa_process_json"]["content"])

    def test_user_cannot_access_other_users_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self.make_client(Path(temp_dir))
            self.login(client, "admin", "admin123")
            created = client.post(
                "/api/fpa/tasks",
                data={
                    "system_code": "claimcar",
                    "title": "管理员任务",
                    "input_text": "新增任务。",
                },
            )
            self.assertEqual(created.status_code, 200, created.text)
            task_id = created.json()["task"]["id"]

            client.post("/api/auth/logout")
            self.login(client, "demo", "demo123")

            detail = client.get(f"/api/fpa/tasks/{task_id}")
            self.assertEqual(detail.status_code, 404)
            request = client.get(f"/api/fpa/tasks/{task_id}/ai-request")
            self.assertEqual(request.status_code, 404)

    def test_worker_once_does_not_claim_waiting_ai_call_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            db_path = tmp_path / "teamtools-test.db"
            client = self.make_client(tmp_path)
            self.login(client)
            created = client.post(
                "/api/fpa/tasks",
                data={
                    "system_code": "claimcar",
                    "title": "worker 不领取任务",
                    "input_text": "新增一个等待浏览器调用 DeepSeek 的任务。",
                },
            )
            self.assertEqual(created.status_code, 200, created.text)
            task_id = created.json()["task"]["id"]

            os.environ["TEAMTOOLS_DATA_DIR"] = str(tmp_path / "data")
            os.environ["TEAMTOOLS_DB_PATH"] = str(db_path)
            os.environ["TEAMTOOLS_WORKER_ONCE"] = "true"
            get_config.cache_clear()
            from app.worker import run_worker

            run_worker()
            get_config.cache_clear()

            detail = client.get(f"/api/fpa/tasks/{task_id}")
            self.assertEqual(detail.status_code, 200, detail.text)
            self.assertEqual(detail.json()["task"]["status"], "waiting_ai_call")

    def test_ai_result_schema_rejects_extra_field_and_invalid_enum(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self.make_client(Path(temp_dir))
            self.login(client)
            created = client.post(
                "/api/fpa/tasks",
                data={
                    "system_code": "claimcar",
                    "title": "非法 AI 结果",
                    "input_text": "新增非法结果校验任务。",
                },
            )
            self.assertEqual(created.status_code, 200, created.text)
            task_id = created.json()["task"]["id"]

            result = client.post(
                f"/api/fpa/tasks/{task_id}/ai-result",
                json={
                    "success": True,
                    "provider": "deepseek",
                    "model": "deepseek-v4-flash",
                    "structured_json": {
                        "requirement_name": "非法 AI 结果",
                        "unexpected": "schema should reject this",
                        "items": [
                            {
                                "system": "车险理赔核心系统",
                                "level1_module": "理赔",
                                "function_description": "非法分类",
                                "count_item_name": "非法分类",
                                "category": "BAD",
                                "reuse": "中",
                                "change_type": "新增",
                                "remark": "应被 schema 校验拒绝",
                            }
                        ],
                    },
                },
            )
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["task"]["status"], "failed")

            detail = client.get(f"/api/fpa/tasks/{task_id}")
            self.assertEqual(detail.status_code, 200, detail.text)
            self.assertEqual(detail.json()["task"]["status"], "failed")
            self.assertEqual(detail.json()["task"]["failure_stage"], "json_validation")

    def test_ai_result_rejects_raw_response_without_required_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            client = self.make_client(tmp_path)
            self.login(client)
            task_id = self.create_waiting_task(client, title="缺少双区块")

            result = client.post(
                f"/api/fpa/tasks/{task_id}/ai-result",
                json={
                    "success": True,
                    "provider": "deepseek",
                    "model": "deepseek-v4-flash",
                    "raw_response": {"choices": [{"message": {"content": "{}"}}]},
                },
            )
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["task"]["status"], "failed")
            self.assertFalse((tmp_path / "data" / "tasks" / "fpa" / task_id / "output" / "FPA工作量评估.xlsx").exists())
            detail = client.get(f"/api/fpa/tasks/{task_id}")
            self.assertEqual(detail.json()["task"]["failure_stage"], "json_validation")

    def test_ai_result_rejects_system_code_and_backend_output_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self.make_client(Path(temp_dir))
            self.login(client)

            for structured in [
                {
                    **self.valid_structured_json(),
                    "frozen_items": [
                        {**item, "system": "onlineclaim"} for item in self.valid_structured_json()["frozen_items"]
                    ],
                },
                {**self.valid_structured_json(), "target_work_days": 8},
                {**self.valid_structured_json(), "adjusted_work_days_middle": 8},
            ]:
                task_id = self.create_waiting_task(client, title="非法字段校验")
                result = client.post(
                    f"/api/fpa/tasks/{task_id}/ai-result",
                    json={
                        "success": True,
                        "provider": "deepseek",
                        "model": "deepseek-v4-flash",
                        "structured_json": structured,
                    },
                )
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json()["task"]["status"], "failed")
                detail = client.get(f"/api/fpa/tasks/{task_id}")
                self.assertEqual(detail.json()["task"]["failure_stage"], "json_validation")

    def test_ai_result_rejects_known_but_wrong_task_system(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            client = self.make_client(tmp_path)
            self.login(client)
            task_id = self.create_waiting_task(client, system_code="onlineclaim", title="错误系统口径")
            structured = self.valid_structured_json()
            structured["assessment_context"]["system_code"] = "claimcar"
            structured["assessment_context"]["system_name"] = "车险理赔核心系统"
            for item in structured["frozen_items"]:
                item["system"] = "车险理赔核心系统"

            result = client.post(
                f"/api/fpa/tasks/{task_id}/ai-result",
                json={
                    "success": True,
                    "provider": "deepseek",
                    "model": "deepseek-v4-flash",
                    "structured_json": structured,
                },
            )
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["task"]["status"], "failed")
            self.assertFalse((tmp_path / "data" / "tasks" / "fpa" / task_id / "output" / "FPA工作量评估.xlsx").exists())
            detail = client.get(f"/api/fpa/tasks/{task_id}")
            self.assertEqual(detail.json()["task"]["failure_stage"], "json_validation")

    def test_system_relevance_warns_and_confirm_continue_stops_repeat_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self.make_client(Path(temp_dir))
            self.login(client)
            created = client.post(
                "/api/fpa/tasks",
                data={
                    "system_code": "claimcar",
                    "title": "明显选错系统",
                    "input_text": "在线理赔服务平台需要优化 App 视频会话、影像补传、任务状态查询和用户通知。",
                },
            )
            self.assertEqual(created.status_code, 200, created.text)
            task_id = created.json()["task"]["id"]

            first = client.get(f"/api/fpa/tasks/{task_id}/ai-request")
            self.assertEqual(first.status_code, 200, first.text)
            relevance = first.json()["system_relevance"]
            self.assertIn(relevance["status"], {"warning", "blocked"})
            self.assertEqual(relevance["best_match_system_code"], "onlineclaim")

            confirmed = client.post(f"/api/fpa/tasks/{task_id}/system-relevance/confirm")
            self.assertEqual(confirmed.status_code, 200, confirmed.text)
            second = client.get(f"/api/fpa/tasks/{task_id}/ai-request")
            self.assertEqual(second.status_code, 200, second.text)
            self.assertTrue(second.json()["system_relevance"]["confirmed"])

    def test_system_relevance_allows_missing_knowledge_system(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self.make_client(Path(temp_dir))
            self.login(client)
            task_id = self.create_waiting_task(client, system_code="clqp", title="无资料系统")

            request = client.get(f"/api/fpa/tasks/{task_id}/ai-request")
            self.assertEqual(request.status_code, 200, request.text)
            self.assertIn(request.json()["system_relevance"]["status"], {"pass", "warning"})

    def test_dev_users_seed_only_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ.pop("TEAMTOOLS_SEED_DEV_USERS", None)
            disabled_db = Path(temp_dir) / "disabled.db"
            initialize_database(disabled_db)
            with open_connection(disabled_db) as conn:
                users = conn.execute("SELECT username FROM users ORDER BY username").fetchall()
            self.assertEqual([row["username"] for row in users], [])

            os.environ["TEAMTOOLS_SEED_DEV_USERS"] = "true"
            enabled_db = Path(temp_dir) / "enabled.db"
            initialize_database(enabled_db)
            with open_connection(enabled_db) as conn:
                users = conn.execute("SELECT username FROM users ORDER BY username").fetchall()
            self.assertEqual([row["username"] for row in users], ["admin", "demo"])

    def test_auth_returns_default_system_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self.make_client(Path(temp_dir))

            response = client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["user"]["default_system_code"], "onlineclaim")
            me = client.get("/api/auth/me")
            self.assertEqual(me.status_code, 200, me.text)
            self.assertEqual(me.json()["user"]["default_system_code"], "onlineclaim")

    def test_database_migrates_missing_default_system_column(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "legacy.db"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE users (
                        id TEXT PRIMARY KEY,
                        username TEXT NOT NULL UNIQUE,
                        display_name TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        last_login_at TEXT
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

            initialize_database(db_path)
            with open_connection(db_path) as conn:
                columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            self.assertIn("default_system_code", columns)


if __name__ == "__main__":
    unittest.main()
