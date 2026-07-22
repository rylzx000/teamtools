---
change: support-fpa-word-input
design-doc: docs/superpowers/specs/2026-07-21-support-fpa-word-input-design.md
base-ref: e0e9ca942f8983097b89fc2c6debdbb1b9eecad6
archived-with: 2026-07-22-support-fpa-word-input
---

# FPA Word 输入支持实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 让 FPA 提交评估支持上传 `.docx`，后端先归一化为 Markdown/文本，再复用现有 AI 请求包和 Excel 生成主链路。

**Architecture:** 文件格式处理收口在任务创建入口：`backend/app/main.py` 只解析请求和文件字节，新增的 FPA 输入归一化模块负责 `.md/.docx` 校验、提取、警告和正文输出，`backend/app/modules/fpa/service.py` 继续以 `input/merged_input.md` 驱动 AI 请求包。前端保持 `frontend/src/App.tsx` 现有单文件提交页结构，只把文件状态改为 `File` 对象、提交改为 `FormData`、补充 Word 规则和解析警告展示。

**Tech Stack:** FastAPI、Python 3.11+、`python-docx`、SQLite 任务文件、Python unittest、React、TypeScript、Vite。

> `For agentic workers`、`REQUIRED SUB-SKILL`、`superpowers:*`、`FastAPI`、`python-docx`、`React`、`TypeScript`、`Vite` 等英文保留，是 Superpowers 模板关键字、技能标识或第三方技术专有名词。

archived-with: 2026-07-22-support-fpa-word-input
---

## 文件结构

- Modify: `backend/pyproject.toml`，新增项目依赖 `python-docx`。
- Modify: `backend/uv.lock`，通过项目锁文件更新 `python-docx` 及其必要依赖。
- Create: `backend/app/modules/fpa/input_normalizer.py`，封装上传文件结构、归一化结果、`.md/.docx` 解析、大小/空内容/有效文字校验、图片忽略警告。
- Modify: `backend/app/main.py`，扩展 multipart 解析，让 `input_file` 保留文件名、字节、大小和扩展名；`POST /api/fpa/tasks` 将文件对象传给 FPA service。
- Modify: `backend/app/modules/fpa/service.py`，在 `create_task()` 中调用归一化模块，落盘 `uploaded_input.md`、`merged_input.md`、`normalized_input.json`，任务详情返回解析警告。
- Modify: `backend/tests/test_fpa_mvp.py`，扩展轻量 ASGI client 支持 multipart，新增 `.md/.docx` 上传、警告、拒绝和 AI 请求包测试。
- Modify: `frontend/src/App.tsx`，上传控件支持 `.md/.docx`，保留拖拽，提交改为 `FormData`，展示解析警告。
- Modify: `openspec/changes/support-fpa-word-input/tasks.md`，只在实现和验证完成后勾选对应任务。

## 实施约束

- 不解析 `.doc`、PDF、图片 OCR 或多模态图片内容。
- 不把 Word 二进制、图片、嵌入对象或服务端临时路径写入 AI 请求包。
- 不修改 `scripts/fpa/build_ai_request_package.py` 的主逻辑；验证它继续只读取 `input/merged_input.md`。
- 不修改 Excel 生成主流程或 `scripts/fpa/fill_fpa_workbook.py`。
- 不提交、不推送、不切换分支，除非用户在后续步骤明确授权。
- 若选择 TDD 模式，必须先写失败测试并确认失败，再写生产代码。

### Task 1: 后端依赖和归一化模块

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Create: `backend/app/modules/fpa/input_normalizer.py`
- Test: `backend/tests/test_fpa_mvp.py`

- [x] **Step 1: 写归一化单元测试**

在 `backend/tests/test_fpa_mvp.py` 增加对归一化层的测试导入：

```python
from app.modules.fpa.input_normalizer import (
    WORD_IMAGES_IGNORED_MESSAGE,
    UploadedRequirementFile,
    normalize_requirement_input,
)
```

新增测试覆盖 `.md` 正常归一化、空 `.md` 拒绝、超长正文拒绝：

```python
def test_fpa_input_normalizer_accepts_markdown_upload(self) -> None:
    uploaded = UploadedRequirementFile(
        filename="需求.md",
        content="新增理赔影像补传。".encode("utf-8"),
    )

    result = normalize_requirement_input("", uploaded)

    self.assertEqual(result.source_file_name, "需求.md")
    self.assertEqual(result.source_file_type, "md")
    self.assertEqual(result.normalized_markdown, "新增理赔影像补传。")
    self.assertEqual(result.text_length, len("新增理赔影像补传。"))
    self.assertEqual(result.parse_warnings, [])

def test_fpa_input_normalizer_rejects_empty_markdown_upload(self) -> None:
    uploaded = UploadedRequirementFile(filename="空.md", content=b"  \n")

    with self.assertRaisesRegex(Exception, "未提取到有效文字|请粘贴需求文本或上传"):
        normalize_requirement_input("", uploaded)

def test_fpa_input_normalizer_rejects_too_long_normalized_text(self) -> None:
    uploaded = UploadedRequirementFile(filename="过长.md", content=("一" * 20001).encode("utf-8"))

    with self.assertRaisesRegex(Exception, "2 万字符"):
        normalize_requirement_input("", uploaded)
```

- [x] **Step 2: 运行测试确认失败**

Run:

```powershell
cd backend
uv run python -m unittest tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_accepts_markdown_upload tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_rejects_empty_markdown_upload tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_rejects_too_long_normalized_text -v
```

Expected: FAIL，失败原因是 `app.modules.fpa.input_normalizer` 或对应函数尚不存在。

- [x] **Step 3: 新增项目依赖**

在 `backend/pyproject.toml` 的 `[project].dependencies` 增加：

```toml
  "python-docx>=1.1",
```

然后在仓库根目录运行锁文件更新：

```powershell
cd backend
uv lock
```

Expected: `backend/uv.lock` 新增 `python-docx` 及必要依赖，且没有全局安装动作。

- [x] **Step 4: 实现归一化模块骨架和 Markdown 支持**

创建 `backend/app/modules/fpa/input_normalizer.py`：

```python
from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from .service_errors import FpaError

MAX_MARKDOWN_BYTES = 256 * 1024
MAX_DOCX_BYTES = 10 * 1024 * 1024
MAX_NORMALIZED_TEXT_LENGTH = 20_000
WORD_IMAGES_IGNORED_MESSAGE = "已忽略 Word 中的图片内容，如图片包含关键需求，请补充为文字后重新提交。"


@dataclass(frozen=True)
class UploadedRequirementFile:
    filename: str
    content: bytes

    @property
    def extension(self) -> str:
        return Path(self.filename).suffix.lower()

    @property
    def size(self) -> int:
        return len(self.content)


@dataclass(frozen=True)
class ParseWarning:
    code: str
    message: str


@dataclass(frozen=True)
class NormalizedRequirementInput:
    source_file_name: str | None
    source_file_type: str | None
    normalized_markdown: str
    text_length: int
    parse_warnings: list[dict[str, str]]

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_requirement_input(input_text: str | None, uploaded_file: UploadedRequirementFile | None) -> NormalizedRequirementInput:
    pasted_text = (input_text or "").strip()
    uploaded_text = ""
    source_name: str | None = None
    source_type: str | None = None
    warnings: list[ParseWarning] = []

    if uploaded_file is not None:
        uploaded_text, source_name, source_type, warnings = normalize_uploaded_file(uploaded_file)

    merged = "\n\n".join(part for part in [pasted_text, uploaded_text] if part)
    if not merged:
        raise FpaError("请粘贴需求文本或上传 Markdown .md 或 Word .docx 文档", 400, "task_create")
    if len(merged) > MAX_NORMALIZED_TEXT_LENGTH:
        raise FpaError("输入内容不能超过 2 万字符", 400, "task_create")

    return NormalizedRequirementInput(
        source_file_name=source_name,
        source_file_type=source_type,
        normalized_markdown=merged,
        text_length=len(merged),
        parse_warnings=[asdict(item) for item in warnings],
    )


def normalize_uploaded_file(uploaded_file: UploadedRequirementFile) -> tuple[str, str, str, list[ParseWarning]]:
    extension = uploaded_file.extension
    if uploaded_file.size == 0:
        raise FpaError("上传文件不能为空", 400, "task_create")
    if extension == ".doc":
        raise FpaError("暂不支持 .doc，请另存为 .docx 后上传", 400, "task_create")
    if extension == ".md":
        return normalize_markdown_file(uploaded_file)
    if extension == ".docx":
        return normalize_docx_file(uploaded_file)
    raise FpaError("上传文件仅支持 Markdown .md 或 Word .docx 文档", 400, "task_create")


def normalize_markdown_file(uploaded_file: UploadedRequirementFile) -> tuple[str, str, str, list[ParseWarning]]:
    if uploaded_file.size > MAX_MARKDOWN_BYTES:
        raise FpaError("Markdown 文件不能超过 256KB", 400, "task_create")
    try:
        text = uploaded_file.content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FpaError("Markdown 文件必须是 UTF-8 文本", 400, "task_create") from exc
    text = text.strip()
    if not text:
        raise FpaError("上传文件中未提取到有效文字，请补充文字需求后重新提交", 400, "task_create")
    return text, uploaded_file.filename, "md", []
```

如果直接从 `service.py` 导入 `FpaError` 造成循环依赖，则同步抽出 `backend/app/modules/fpa/service_errors.py` 并让 `service.py`、`input_normalizer.py` 共同引用该异常类。

- [x] **Step 5: 运行 Markdown 归一化测试**

Run:

```powershell
cd backend
uv run python -m unittest tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_accepts_markdown_upload tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_rejects_empty_markdown_upload tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_rejects_too_long_normalized_text -v
```

Expected: PASS。

### Task 2: Word 提取、图片警告和拒绝规则

**Files:**
- Modify: `backend/app/modules/fpa/input_normalizer.py`
- Modify: `backend/tests/test_fpa_mvp.py`

- [x] **Step 1: 写 `.docx` 段落、标题、列表和表格测试**

在 `backend/tests/test_fpa_mvp.py` 增加测试辅助函数：

```python
def build_docx_bytes(self, paragraphs: list[str] | None = None, table_rows: list[list[str]] | None = None) -> bytes:
    from docx import Document
    from io import BytesIO

    document = Document()
    for text in paragraphs or []:
        document.add_paragraph(text)
    if table_rows:
        table = document.add_table(rows=len(table_rows), cols=max(len(row) for row in table_rows))
        for row_index, row in enumerate(table_rows):
            for col_index, value in enumerate(row):
                table.cell(row_index, col_index).text = value
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
```

新增测试：

```python
def test_fpa_input_normalizer_extracts_docx_paragraphs_and_table(self) -> None:
    content = self.build_docx_bytes(
        paragraphs=["需求标题", "1. 新增理赔材料上传", "2. 审核结果通知"],
        table_rows=[["模块", "功能"], ["理赔", "影像补传"]],
    )
    uploaded = UploadedRequirementFile(filename="需求.docx", content=content)

    result = normalize_requirement_input("", uploaded)

    self.assertEqual(result.source_file_type, "docx")
    self.assertIn("需求标题", result.normalized_markdown)
    self.assertIn("新增理赔材料上传", result.normalized_markdown)
    self.assertIn("审核结果通知", result.normalized_markdown)
    self.assertIn("模块", result.normalized_markdown)
    self.assertIn("影像补传", result.normalized_markdown)
```

- [x] **Step 2: 写图片忽略和无有效文字测试**

在测试文件中增加一个最小 PNG 常量和图片文档辅助函数：

```python
MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
    b"\x00\x05\xfe\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
)

def build_docx_with_image_bytes(self, text: str = "") -> bytes:
    from docx import Document
    from io import BytesIO
    import tempfile

    document = Document()
    if text:
        document.add_paragraph(text)
    with tempfile.TemporaryDirectory() as temp_dir:
        image_path = Path(temp_dir) / "image.png"
        image_path.write_bytes(MINIMAL_PNG)
        document.add_picture(str(image_path))
        buffer = BytesIO()
        document.save(buffer)
    return buffer.getvalue()
```

新增测试：

```python
def test_fpa_input_normalizer_warns_when_docx_contains_image(self) -> None:
    uploaded = UploadedRequirementFile(filename="含图.docx", content=self.build_docx_with_image_bytes("新增影像材料上传"))

    result = normalize_requirement_input("", uploaded)

    self.assertIn("新增影像材料上传", result.normalized_markdown)
    self.assertIn(
        {"code": "word_images_ignored", "message": WORD_IMAGES_IGNORED_MESSAGE},
        result.parse_warnings,
    )

def test_fpa_input_normalizer_rejects_image_only_docx(self) -> None:
    uploaded = UploadedRequirementFile(filename="仅图片.docx", content=self.build_docx_with_image_bytes())

    with self.assertRaisesRegex(Exception, "未提取到有效文字"):
        normalize_requirement_input("", uploaded)
```

- [x] **Step 3: 写非法格式、超大和损坏 Word 测试**

新增测试：

```python
def test_fpa_input_normalizer_rejects_unsupported_extensions_and_limits(self) -> None:
    with self.assertRaisesRegex(Exception, "暂不支持 \\.doc"):
        normalize_requirement_input("", UploadedRequirementFile(filename="旧格式.doc", content=b"abc"))
    with self.assertRaisesRegex(Exception, "仅支持 Markdown \\.md 或 Word \\.docx"):
        normalize_requirement_input("", UploadedRequirementFile(filename="需求.pdf", content=b"%PDF"))
    with self.assertRaisesRegex(Exception, "Word \\.docx 文件不能超过 10MB"):
        normalize_requirement_input("", UploadedRequirementFile(filename="过大.docx", content=b"x" * (10 * 1024 * 1024 + 1)))
    with self.assertRaisesRegex(Exception, "Word 文档无法解析"):
        normalize_requirement_input("", UploadedRequirementFile(filename="损坏.docx", content=b"not-a-docx"))
```

- [x] **Step 4: 运行测试确认失败**

Run:

```powershell
cd backend
uv run python -m unittest tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_extracts_docx_paragraphs_and_table tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_warns_when_docx_contains_image tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_rejects_image_only_docx tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_rejects_unsupported_extensions_and_limits -v
```

Expected: FAIL，失败原因是 `.docx` 解析和图片识别尚未实现。

- [x] **Step 5: 实现 `.docx` 解析**

在 `backend/app/modules/fpa/input_normalizer.py` 补充：

```python
def normalize_docx_file(uploaded_file: UploadedRequirementFile) -> tuple[str, str, str, list[ParseWarning]]:
    if uploaded_file.size > MAX_DOCX_BYTES:
        raise FpaError("Word .docx 文件不能超过 10MB", 400, "task_create")
    try:
        document = Document(BytesIO(uploaded_file.content))
    except (PackageNotFoundError, zipfile.BadZipFile, ValueError, KeyError) as exc:
        raise FpaError("Word 文档无法解析，请确认文件未损坏并重新上传", 400, "task_create") from exc

    blocks: list[str] = []
    for paragraph in document.paragraphs:
        text = normalize_space(paragraph.text)
        if text:
            blocks.append(text)
    for table in document.tables:
        table_text = table_to_markdown(table)
        if table_text:
            blocks.append(table_text)

    text = "\n\n".join(blocks).strip()
    warnings: list[ParseWarning] = []
    if docx_contains_ignored_media(uploaded_file.content):
        warnings.append(ParseWarning(code="word_images_ignored", message=WORD_IMAGES_IGNORED_MESSAGE))
    if not text:
        raise FpaError("Word 文档中未提取到有效文字，请补充文字需求后重新提交", 400, "task_create")
    return text, uploaded_file.filename, "docx", warnings


def normalize_space(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def table_to_markdown(table: Any) -> str:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = [normalize_space(cell.text) for cell in row.cells]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    header = padded[0]
    separator = ["---"] * width
    body = padded[1:]
    lines = [
        "| " + " | ".join(escape_markdown_cell(cell) for cell in header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    lines.extend("| " + " | ".join(escape_markdown_cell(cell) for cell in row) + " |" for row in body)
    return "\n".join(lines)


def escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|")


def docx_contains_ignored_media(content: bytes) -> bool:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile:
        return False
    return any(
        name.startswith("word/media/")
        or name.startswith("word/embeddings/")
        or name.startswith("word/activeX/")
        for name in names
    )
```

- [x] **Step 6: 运行 Word 归一化测试**

Run:

```powershell
cd backend
uv run python -m unittest tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_extracts_docx_paragraphs_and_table tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_warns_when_docx_contains_image tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_rejects_image_only_docx tests.test_fpa_mvp.FpaMvpTest.test_fpa_input_normalizer_rejects_unsupported_extensions_and_limits -v
```

Expected: PASS。

### Task 3: 提交接口和任务落盘接入

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/modules/fpa/service.py`
- Modify: `backend/tests/test_fpa_mvp.py`

- [x] **Step 1: 扩展测试客户端 multipart 能力**

在 `backend/tests/test_fpa_mvp.py` 的 `AsgiClient.post()` 和 `AsgiClient.request()` 增加 `files=None` 参数，并在 `_request()` 中支持 multipart：

```python
def post(self, path: str, *, json=None, data=None, files=None):
    return self.request("POST", path, json=json, data=data, files=files)

def request(self, method: str, path: str, *, json=None, data=None, files=None):
    import asyncio

    return asyncio.run(self._request(method, path, json=json, data=data, files=files))
```

新增构造函数：

```python
def build_multipart_body(data: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    boundary = "----teamtools-test-boundary"
    chunks: list[bytes] = []
    for name, value in data.items():
        chunks.extend([
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
            str(value).encode("utf-8"),
            b"\r\n",
        ])
    for name, (filename, content, content_type) in files.items():
        chunks.extend([
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8"),
            content,
            b"\r\n",
        ])
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"
```

在 `_request()` 的 body 分支增加：

```python
elif files is not None:
    body, content_type = build_multipart_body(data or {}, files)
    headers.append((b"content-type", content_type.encode("utf-8")))
```

- [x] **Step 2: 写接口级上传测试**

新增测试：

```python
def test_fpa_task_create_accepts_markdown_file_upload(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        client = self.make_client(tmp_path)
        self.login(client)

        created = client.post(
            "/api/fpa/tasks",
            data={"system_code": "claimcar", "title": "Markdown 上传"},
            files={"input_file": ("需求.md", "新增理赔影像补传。".encode("utf-8"), "text/markdown")},
        )

        self.assertEqual(created.status_code, 200, created.text)
        task_id = created.json()["task"]["id"]
        merged = (tmp_path / "data" / "tasks" / "fpa" / task_id / "input" / "merged_input.md").read_text(encoding="utf-8")
        self.assertIn("新增理赔影像补传", merged)

def test_fpa_task_create_accepts_docx_file_upload_and_persists_normalized_metadata(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        client = self.make_client(tmp_path)
        self.login(client)
        content = self.build_docx_bytes(paragraphs=["新增理赔材料上传"], table_rows=[["模块", "功能"], ["理赔", "影像补传"]])

        created = client.post(
            "/api/fpa/tasks",
            data={"system_code": "claimcar", "title": "Word 上传"},
            files={
                "input_file": (
                    "需求.docx",
                    content,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

        self.assertEqual(created.status_code, 200, created.text)
        task_id = created.json()["task"]["id"]
        task_root = tmp_path / "data" / "tasks" / "fpa" / task_id
        merged = (task_root / "input" / "merged_input.md").read_text(encoding="utf-8")
        metadata = json.loads((task_root / "input" / "normalized_input.json").read_text(encoding="utf-8"))
        self.assertIn("新增理赔材料上传", merged)
        self.assertIn("影像补传", merged)
        self.assertEqual(metadata["source_file_type"], "docx")
        self.assertEqual(metadata["source_file_name"], "需求.docx")
```

- [x] **Step 3: 运行接口测试确认失败**

Run:

```powershell
cd backend
uv run python -m unittest tests.test_fpa_mvp.FpaMvpTest.test_fpa_task_create_accepts_markdown_file_upload tests.test_fpa_mvp.FpaMvpTest.test_fpa_task_create_accepts_docx_file_upload_and_persists_normalized_metadata -v
```

Expected: FAIL，失败原因是 multipart 文件仍被当作文本或 service 未接收 `UploadedRequirementFile`。

- [x] **Step 4: 修改 `main.py` 的上传 payload**

在 `backend/app/main.py` 导入：

```python
from app.modules.fpa.input_normalizer import UploadedRequirementFile
```

调整 `fpa_create_task()` 传参：

```python
uploaded_file = payload.get("uploaded_file")
return create_task(
    app_db_path,
    app_data_dir,
    user,
    system_code=str(payload.get("system_code") or ""),
    title=str(payload.get("title") or ""),
    input_text=str(payload.get("input_text") or ""),
    uploaded_text=str(payload.get("uploaded_text") or ""),
    uploaded_file=uploaded_file if isinstance(uploaded_file, UploadedRequirementFile) else None,
    uploaded_name=str(payload.get("uploaded_name") or ""),
    target_person_days=target,
    count_timing=str(payload.get("count_timing") or "估算中期"),
    integrity_level=str(
        payload.get("integrity_level")
        or "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式"
    ),
)
```

调整 `read_submission_payload()`：保留旧 `input_file` 文本兼容，同时支持新的 `uploaded_file`：

```python
async def read_submission_payload(request: Request) -> dict[str, Any]:
    payload = await read_payload(request)
    if "input_file" in payload and not payload.get("uploaded_text") and not payload.get("uploaded_file"):
        payload["uploaded_text"] = str(payload.get("input_file") or "")
    return payload
```

调整 `parse_simple_multipart()` 文件分支：

```python
if filename:
    payload["uploaded_file"] = UploadedRequirementFile(filename=filename, content=value)
    payload["uploaded_name"] = filename
else:
    payload[name] = value.decode("utf-8", errors="replace")
```

- [x] **Step 5: 修改 `service.py` 的任务创建**

在 `backend/app/modules/fpa/service.py` 导入：

```python
from .input_normalizer import NormalizedRequirementInput, UploadedRequirementFile, normalize_requirement_input
```

扩展 `create_task()` 签名：

```python
uploaded_file: UploadedRequirementFile | None = None,
```

在输入校验和落盘前替换为归一化结果：

```python
input_text = (input_text or "").strip()
legacy_uploaded_file = UploadedRequirementFile(uploaded_name or "uploaded.md", uploaded_text.encode("utf-8")) if uploaded_text else None
normalized = normalize_requirement_input(input_text, uploaded_file or legacy_uploaded_file)
uploaded_normalized_text = ""
if normalized.source_file_name:
    merged_parts = normalized.normalized_markdown.split("\n\n", 1)
    uploaded_normalized_text = merged_parts[1] if input_text and len(merged_parts) > 1 else normalized.normalized_markdown
```

落盘时：

```python
if input_text:
    (paths.input_dir / "pasted_input.md").write_text(input_text, encoding="utf-8")
    register_file(db_path, data_dir, task_id, "input_pasted", paths.input_dir / "pasted_input.md", viewable=True)
if uploaded_normalized_text:
    (paths.input_dir / "uploaded_input.md").write_text(uploaded_normalized_text, encoding="utf-8")
    register_file(
        db_path,
        data_dir,
        task_id,
        "input_uploaded",
        paths.input_dir / "uploaded_input.md",
        original_name=normalized.source_file_name,
        viewable=True,
    )
(paths.input_dir / "merged_input.md").write_text(normalized.normalized_markdown, encoding="utf-8")
(paths.input_dir / "normalized_input.json").write_text(
    json.dumps(normalized.to_json_dict(), ensure_ascii=False, indent=2),
    encoding="utf-8",
)
```

并注册 `normalized_input` 为管理员可见或普通不可下载的内部文件：

```python
register_file(db_path, data_dir, task_id, "normalized_input", paths.input_dir / "normalized_input.json", admin_only=True)
```

- [x] **Step 6: 运行接口上传测试**

Run:

```powershell
cd backend
uv run python -m unittest tests.test_fpa_mvp.FpaMvpTest.test_fpa_task_create_accepts_markdown_file_upload tests.test_fpa_mvp.FpaMvpTest.test_fpa_task_create_accepts_docx_file_upload_and_persists_normalized_metadata -v
```

Expected: PASS。

### Task 4: 任务详情警告和 AI 请求包边界验证

**Files:**
- Modify: `backend/app/modules/fpa/service.py`
- Modify: `backend/tests/test_fpa_mvp.py`

- [x] **Step 1: 写图片警告任务详情测试**

新增测试：

```python
def test_fpa_task_detail_exposes_docx_image_warning(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        client = self.make_client(tmp_path)
        self.login(client)

        created = client.post(
            "/api/fpa/tasks",
            data={"system_code": "claimcar", "title": "含图 Word"},
            files={
                "input_file": (
                    "含图.docx",
                    self.build_docx_with_image_bytes("新增影像补传"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

        self.assertEqual(created.status_code, 200, created.text)
        task_id = created.json()["task"]["id"]
        detail = client.get(f"/api/fpa/tasks/{task_id}")
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertIn(
            {"code": "word_images_ignored", "message": WORD_IMAGES_IGNORED_MESSAGE},
            detail.json()["task"]["parse_warnings"],
        )
```

新增 AI 请求包边界测试：

```python
def test_fpa_ai_request_package_uses_normalized_docx_text_only(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        client = self.make_client(tmp_path)
        self.login(client)
        content = self.build_docx_bytes(paragraphs=["新增理赔资料上传"])

        created = client.post(
            "/api/fpa/tasks",
            data={"system_code": "claimcar", "title": "AI 包验证"},
            files={
                "input_file": (
                    "需求.docx",
                    content,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

        self.assertEqual(created.status_code, 200, created.text)
        task_id = created.json()["task"]["id"]
        ai_package_path = tmp_path / "data" / "tasks" / "fpa" / task_id / "ai" / "AI请求包.json"
        ai_package = json.loads(ai_package_path.read_text(encoding="utf-8"))
        raw = json.dumps(ai_package, ensure_ascii=False)
        self.assertIn("新增理赔资料上传", raw)
        self.assertNotIn("word/media", raw)
        self.assertNotIn("需求.docx", raw)
```

- [x] **Step 2: 运行测试确认失败**

Run:

```powershell
cd backend
uv run python -m unittest tests.test_fpa_mvp.FpaMvpTest.test_fpa_task_detail_exposes_docx_image_warning tests.test_fpa_mvp.FpaMvpTest.test_fpa_ai_request_package_uses_normalized_docx_text_only -v
```

Expected: 第一个测试 FAIL，因为任务详情尚未返回 `parse_warnings`；第二个测试若已通过，也保留为边界回归测试。

- [x] **Step 3: 修改任务详情返回解析警告**

在 `backend/app/modules/fpa/service.py` 增加读取函数：

```python
def read_normalized_input(paths: FpaPaths) -> dict[str, Any]:
    path = paths.input_dir / "normalized_input.json"
    if not path.exists():
        return {"parse_warnings": []}
    data = read_json(path)
    return data if isinstance(data, dict) else {"parse_warnings": []}
```

在 `task_detail()` 中读取并放入 `task_public`：

```python
normalized_input = read_normalized_input(paths)
task_public["parse_warnings"] = normalized_input.get("parse_warnings") or []
```

- [x] **Step 4: 运行任务详情和 AI 请求包测试**

Run:

```powershell
cd backend
uv run python -m unittest tests.test_fpa_mvp.FpaMvpTest.test_fpa_task_detail_exposes_docx_image_warning tests.test_fpa_mvp.FpaMvpTest.test_fpa_ai_request_package_uses_normalized_docx_text_only -v
```

Expected: PASS。

### Task 5: 前端上传页和警告展示

**Files:**
- Modify: `frontend/src/App.tsx`

- [x] **Step 1: 调整前端类型**

在 `TaskDetail['task']` 类型中增加：

```typescript
parse_warnings?: Array<{ code: string; message: string }>;
```

在 `SubmitPage` 状态中用 `File` 保存上传文件：

```typescript
const [selectedFile, setSelectedFile] = useState<File | null>(null);
const [fileName, setFileName] = useState('');
const [fileSize, setFileSize] = useState<number | null>(null);
const [fileText, setFileText] = useState('');
```

- [x] **Step 2: 调整文件选择和大小校验**

替换 `readFile()`：

```typescript
async function readFile(file: File | undefined) {
  if (!file) return;
  const lowerName = file.name.toLowerCase();
  const isMarkdown = lowerName.endsWith('.md');
  const isDocx = lowerName.endsWith('.docx');
  if (!isMarkdown && !isDocx) {
    setError('上传文件仅支持 Markdown .md 或 Word .docx 文档');
    return;
  }
  if (lowerName.endsWith('.doc')) {
    setError('暂不支持 .doc，请另存为 .docx 后上传');
    return;
  }
  if (isMarkdown && file.size > 256 * 1024) {
    setError('Markdown 文件不能超过 256KB');
    return;
  }
  if (isDocx && file.size > 10 * 1024 * 1024) {
    setError('Word .docx 文件不能超过 10MB');
    return;
  }
  setSelectedFile(file);
  setFileName(file.name);
  setFileSize(file.size);
  setFileText(isMarkdown ? await file.text() : '');
  setError('');
}
```

更新 `clearFile()`：

```typescript
function clearFile() {
  setSelectedFile(null);
  setFileName('');
  setFileSize(null);
  setFileText('');
  setFileInputKey((value) => value + 1);
}
```

- [x] **Step 3: 改为 `FormData` 提交**

替换 `submit()` 中的请求体组装：

```typescript
const form = new FormData();
form.set('system_code', systemCode);
form.set('title', title);
form.set('input_text', inputText);
form.set('count_timing', countTiming);
form.set('integrity_level', integrityLevel);
if (selectedFile) form.set('input_file', selectedFile, selectedFile.name);
if (targetDays.trim()) form.set('target_person_days', targetDays.trim());
```

调用 API 时不要手动设置 `Content-Type`：

```typescript
const data = await api('/api/fpa/tasks', {
  method: 'POST',
  body: form,
});
```

禁用条件改为：

```typescript
const disabled = !systemCode || (!inputText.trim() && !selectedFile) || Boolean(targetDaysError);
```

- [x] **Step 4: 更新上传控件和提交规则文案**

调整 input 和上传框：

```tsx
<input
  key={fileInputKey}
  type="file"
  accept=".md,.docx,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  onChange={(event) => readFile(event.target.files?.[0])}
/>
<span className="upload-icon" aria-hidden="true">MD/DOCX</span>
<span>
  <strong>{fileName ? '已选择文档' : '拖动 Markdown / Word 文档到这里，或点击选择文件'}</strong>
  <small>{fileName ? `${fileName} · ${formatFileSize(fileSize)}` : 'Markdown 不超过 256KB，Word .docx 不超过 10MB。'}</small>
</span>
```

规则面板替换为：

```tsx
<li>粘贴内容和上传文件至少提供一个。</li>
<li>正文不超过 2 万字符。</li>
<li>Markdown 不超过 256KB，Word .docx 不超过 10MB。</li>
<li>目标人天最多 1 位小数。</li>
<li>Word 图片内容会被忽略，请将关键图片信息补充为文字。</li>
```

- [x] **Step 5: 展示后端解析警告**

在 `TaskSummaryCard` 参数增加：

```typescript
parseWarnings?: Array<{ code: string; message: string }>;
```

调用处传入：

```tsx
parseWarnings={task.parse_warnings}
```

在 `TaskSummaryCard` 内 `callError` 附近增加：

```tsx
{parseWarnings?.map((warning) => (
  <div className="form-alert" key={warning.code}>{warning.message}</div>
))}
```

Expected: Word 图片警告显示在任务摘要区，不作为失败状态。

- [x] **Step 6: 运行前端构建**

Run:

```powershell
cd frontend
npm run build
```

Expected: PASS。

### Task 6: 后端错误场景、回归和 OpenSpec tasks

**Files:**
- Modify: `backend/tests/test_fpa_mvp.py`
- Modify: `openspec/changes/support-fpa-word-input/tasks.md`

- [x] **Step 1: 写接口级拒绝测试**

在 `backend/tests/test_fpa_mvp.py` 增加：

```python
def test_fpa_task_create_rejects_doc_pdf_image_large_and_broken_word(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        client = self.make_client(Path(temp_dir))
        self.login(client)
        cases = [
            ("旧格式.doc", b"abc", "暂不支持 .doc"),
            ("需求.pdf", b"%PDF", "仅支持 Markdown .md 或 Word .docx"),
            ("截图.png", MINIMAL_PNG, "仅支持 Markdown .md 或 Word .docx"),
            ("损坏.docx", b"not-a-docx", "Word 文档无法解析"),
        ]
        for filename, content, message in cases:
            response = client.post(
                "/api/fpa/tasks",
                data={"system_code": "claimcar", "title": filename},
                files={"input_file": (filename, content, "application/octet-stream")},
            )
            self.assertEqual(response.status_code, 400, response.text)
            self.assertIn(message, response.text)

def test_fpa_task_create_rejects_oversized_uploads(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        client = self.make_client(Path(temp_dir))
        self.login(client)
        oversized_md = client.post(
            "/api/fpa/tasks",
            data={"system_code": "claimcar", "title": "大 Markdown"},
            files={"input_file": ("过大.md", b"x" * (256 * 1024 + 1), "text/markdown")},
        )
        self.assertEqual(oversized_md.status_code, 400, oversized_md.text)
        self.assertIn("Markdown 文件不能超过 256KB", oversized_md.text)

        oversized_docx = client.post(
            "/api/fpa/tasks",
            data={"system_code": "claimcar", "title": "大 Word"},
            files={"input_file": ("过大.docx", b"x" * (10 * 1024 * 1024 + 1), "application/octet-stream")},
        )
        self.assertEqual(oversized_docx.status_code, 400, oversized_docx.text)
        self.assertIn("Word .docx 文件不能超过 10MB", oversized_docx.text)
```

- [x] **Step 2: 运行后端全量 FPA 测试**

Run:

```powershell
cd backend
uv run python -m unittest tests.test_fpa_mvp -v
```

Expected: PASS。

- [x] **Step 3: 验证 AI 请求脚本无 Word 解析分支**

Run:

```powershell
rg -n "docx|python-docx|Document\\(" scripts/fpa/build_ai_request_package.py scripts/fpa/fill_fpa_workbook.py
```

Expected: 无匹配；若只有注释或错误消息匹配，确认不包含 Word 解析逻辑。

- [x] **Step 4: 运行 OpenSpec 和编码检查**

Run:

```powershell
openspec validate support-fpa-word-input --strict
.\scripts\check-encoding.ps1
```

Expected: 两项均 PASS。

- [x] **Step 5: 勾选 OpenSpec tasks**

在 `openspec/changes/support-fpa-word-input/tasks.md` 中只勾选已完成项。最少应覆盖：

- 1.1 到 1.3：OpenSpec 范围已确认且 validate 通过。
- 2.1 到 2.7：依赖、归一化、Word 提取、警告和拒绝规则已实现。
- 3.1 到 3.4：AI 请求包和 Excel 主流程边界已验证。
- 4.1 到 4.6：前端提交页支持 `.md/.docx` 且 UI 未大改。
- 5.1 到 5.11：测试和验证命令按实际运行结果勾选；无法运行的项不勾选，并在最终总结说明。

### Task 7: Comet build 收口

**Files:**
- Modify: `openspec/changes/support-fpa-word-input/.comet.yaml`

- [x] **Step 1: 确认 build 选项已写入**

根据用户后续选择写入：

```powershell
node $state set support-fpa-word-input isolation <branch|worktree>
node $state set support-fpa-word-input build_mode <executing-plans|subagent-driven-development>
node $state set support-fpa-word-input tdd_mode <tdd|direct>
node $state set support-fpa-word-input review_mode <off|standard|thorough>
```

若用户选择 `subagent-driven-development`，还需确认真实后台 agent 调度能力并写入：

```powershell
node $state set support-fpa-word-input subagent_dispatch confirmed
```

- [x] **Step 2: 运行 build 守卫**

Run:

```powershell
$cometEnv = Get-ChildItem -Path '.','D:\project\teamtools\.codex\skills','C:\Users\ry134\.codex\skills','C:\Users\ry134\.agents\skills' -Recurse -Filter 'comet-env.mjs' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
$scriptsDir = node $cometEnv
$guard = Join-Path $scriptsDir 'comet-guard.mjs'
node $guard support-fpa-word-input build --apply
```

Expected: PASS，`.comet.yaml` 进入 `phase: verify`。

## 自检

- Spec 覆盖：计划覆盖 `.md` 保持可用、`.docx` 段落/标题/列表/表格提取、图片忽略警告、无有效文字失败、非法格式/超限/损坏拒绝、归一化正文落盘、AI 请求包边界、前端上传与警告展示、验证命令。
- 边界排除：未加入 `.doc`、PDF、OCR、多模态、Word 二进制入 AI、Excel 主流程改造、多文件上传或大规模 UI 重构。
- 类型一致性：后端上传对象统一使用 `UploadedRequirementFile`，归一化结果统一使用 `NormalizedRequirementInput`，前端详情警告统一命名为 `parse_warnings`。
- 执行风险：`python-docx` 依赖会更新 `backend/uv.lock`；如果当前环境无法联网锁依赖，需要用户在可联网环境手动运行 `cd backend; uv lock`。

