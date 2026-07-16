from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import urlencode

from app.config import get_config
from app.db import initialize_database, open_connection
from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALID_SYSTEM_NAME = "车险理赔核心系统"
VALID_ITEM = {
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

    def create_waiting_task(self, client: AsgiClient, *, title: str = "理赔影像补传", target_days: str = "3.0") -> str:
        created = client.post(
            "/api/fpa/tasks",
            data={
                "system_code": "claimcar",
                "title": title,
                "input_text": "新增理赔影像补传、查询和审核结果通知。",
                "target_person_days": target_days,
                "count_timing": "估算早期",
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["task"]["status"], "waiting_ai_call")
        return created.json()["task"]["id"]

    def valid_structured_json(self) -> dict:
        return {
            "requirement_name": "理赔影像补传",
            "items": [
                dict(VALID_ITEM),
                {
                    **VALID_ITEM,
                    "function_description": "查询影像补传处理结果",
                    "count_item_name": "补传结果查询",
                    "category": "EQ",
                    "remark": "EQ 查询；中复用；新增查询入口",
                },
                {
                    **VALID_ITEM,
                    "function_description": "维护理赔影像补传记录",
                    "count_item_name": "影像补传记录",
                    "category": "ILF",
                    "reuse": "低",
                    "remark": "ILF 数据组；低复用；新增记录",
                },
            ],
            "analysis_notes": "已按 FPA 类别拆分。",
            "uncounted_items": [
                {
                    "description": "历史影像批量迁移",
                    "reason": "属于存量数据处理，不纳入本次新增功能点。",
                    "related_requirement_section": "迁移说明",
                }
            ],
            "quality_notes": [
                {"code": "REVIEW_IMAGE_FLOW", "message": "建议复核影像补传流程边界。", "severity": "medium"}
            ],
            "coverage_notes": "已覆盖提交、查询和记录维护。",
            "uncertainties": ["是否需要外部影像平台接口需人工确认。"],
        }

    def test_fpa_happy_path_creates_task_generates_request_and_excel(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self.make_client(Path(temp_dir))
            self.login(client)

            systems = client.get("/api/fpa/systems")
            self.assertEqual(systems.status_code, 200)
            self.assertEqual(
                [item["code"] for item in systems.json()["items"]],
                ["claimcar", "claimoth", "onlineclaim", "clqp"],
            )

            task_id = self.create_waiting_task(client)

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

            result = client.post(
                f"/api/fpa/tasks/{task_id}/ai-result",
                json={
                    "success": True,
                    "provider": "deepseek",
                    "model": "deepseek-v4-flash",
                    "raw_response": {"choices": [{"message": {"content": "{}"}}]},
                    "structured_json": self.valid_structured_json(),
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
            process = body["artifacts"]["fpa_process_json"]["content"]
            self.assertEqual(process["schema_version"], "fpa.excel_process.v1")
            self.assertIn("estimates", process)
            self.assertIsInstance(process["quality_gate"], dict)
            self.assertEqual(process["assessment_context"]["uncounted_items"][0]["description"], "历史影像批量迁移")
            self.assertEqual(process["assessment_context"]["quality_notes"][0]["code"], "REVIEW_IMAGE_FLOW")
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

            payload_path = Path(temp_dir) / "data" / "tasks" / "fpa" / task_id / "runtime" / "Excel脚本输入payload.json"
            process_path = Path(temp_dir) / "data" / "tasks" / "fpa" / task_id / "runtime" / "FPA生成过程.json"
            self.assertTrue(payload_path.exists())
            self.assertTrue(process_path.exists())
            excel_payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(excel_payload["target_work_days"], 3.0)
            self.assertEqual(excel_payload["assessment_context"]["task_id"], task_id)
            self.assertIn("quality_notes", excel_payload["assessment_context"])

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

    def test_ai_result_rejects_system_code_and_backend_output_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self.make_client(Path(temp_dir))
            self.login(client)

            for structured in [
                {**self.valid_structured_json(), "items": [{**VALID_ITEM, "system": "onlineclaim"}]},
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


if __name__ == "__main__":
    unittest.main()
