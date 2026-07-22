from __future__ import annotations

import zipfile
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph

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
    uploaded_markdown: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_requirement_input(
    input_text: str | None,
    uploaded_file: UploadedRequirementFile | None,
) -> NormalizedRequirementInput:
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
        uploaded_markdown=uploaded_text or None,
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


def normalize_docx_file(uploaded_file: UploadedRequirementFile) -> tuple[str, str, str, list[ParseWarning]]:
    if uploaded_file.size > MAX_DOCX_BYTES:
        raise FpaError("Word .docx 文件不能超过 10MB", 400, "task_create")
    try:
        document = Document(BytesIO(uploaded_file.content))
    except (PackageNotFoundError, zipfile.BadZipFile, ValueError, KeyError) as exc:
        raise FpaError("Word 文档无法解析，请确认文件未损坏并重新上传", 400, "task_create") from exc

    blocks: list[str] = []
    for block in iter_docx_body_blocks(document):
        if isinstance(block, Paragraph):
            text = normalize_space(block.text)
            if text:
                blocks.append(text)
        else:
            table_text = table_to_markdown(block)
            if table_text:
                blocks.append(table_text)

    text = "\n\n".join(blocks).strip()
    warnings: list[ParseWarning] = []
    if docx_contains_ignored_media(uploaded_file.content):
        warnings.append(ParseWarning(code="word_images_ignored", message=WORD_IMAGES_IGNORED_MESSAGE))
    if not text:
        raise FpaError("Word 文档中未提取到有效文字，请补充文字需求后重新提交", 400, "task_create")
    return text, uploaded_file.filename, "docx", warnings


def iter_docx_body_blocks(document: Any) -> list[Paragraph | Table]:
    blocks: list[Paragraph | Table] = []
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            blocks.append(Paragraph(child, document))
        elif isinstance(child, CT_Tbl):
            blocks.append(Table(child, document))
    return blocks


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
