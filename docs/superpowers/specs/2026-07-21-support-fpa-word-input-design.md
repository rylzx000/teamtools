---
comet_change: support-fpa-word-input
role: technical-design
canonical_spec: openspec
archived-with: 2026-07-22-support-fpa-word-input
status: final
---

# FPA Word 输入支持技术设计

## 目标

让 FPA 提交评估支持上传 Word `.docx` 文件，同时保持现有 `.md` 上传、粘贴文本、AI 请求包、AI 结构化校验和 Excel 生成主流程不变。`.docx` 在后端任务创建阶段被解析并归一化为统一正文，后续链路只读取 `input/merged_input.md`，不让 AI、提示词脚本或 Excel 脚本处理 Word 二进制。

`Word`、`Markdown`、`AI`、`Excel`、`FormData`、`.docx`、`.md`、`python-docx` 保留英文，是办公软件、文件格式、浏览器接口、依赖包和既有技术专有名词。

## 当前代码基线

- 后端 API 集中在 `backend/app/main.py`，`POST /api/fpa/tasks` 当前通过 `read_submission_payload()` 读取 JSON、URL 编码或 multipart 请求。
- 当前 multipart 文件解析只允许 `.md`，并把文件内容解码成 `uploaded_text` 传入 FPA service。
- FPA 任务创建集中在 `backend/app/modules/fpa/service.py:create_task()`，当前保存 `pasted_input.md`、`uploaded_input.md`、`merged_input.md` 和 `task_params.json`。
- AI 请求包生成由 `scripts/fpa/build_ai_request_package.py` 完成，只读取 `input/merged_input.md` 和 `input/task_params.json`。
- 前端提交页集中在 `frontend/src/App.tsx`，当前 `readFile()` 只接收 `.md`，读成文本后通过 `application/x-www-form-urlencoded` 提交。
- 后端测试集中在 `backend/tests/test_fpa_mvp.py`，已有轻量 ASGI client，可扩展覆盖上传和任务创建链路。

## 方案概览

采用“后端输入归一化模块 + 现有主链路复用”：

```text
前端选择/拖拽 .md 或 .docx
  -> FormData 提交 input_file
  -> 后端校验扩展名、大小、空文件
  -> 输入归一化
       .md   -> UTF-8 文本
       .docx -> python-docx 提取段落/标题/列表/表格
  -> 写 input/merged_input.md
  -> 写 input/normalized_input.json
  -> build_ai_request_package 读取 merged_input.md
  -> 后续 AI/Excel 主流程不变
```

该方案把文件格式处理固定在任务输入边界，避免提示词脚本、AI 请求包或 Excel 生成脚本出现 Word 专属分支。

## 后端设计

### 上传解析

`backend/app/main.py` 的 multipart 解析需要从“文件内容即文本”调整为“文件内容携带文件名、字节、大小和扩展名”。

建议内部 payload 形态：

```python
{
    "system_code": "...",
    "input_text": "...",
    "uploaded_file": {
        "filename": "需求说明.docx",
        "content": b"...",
        "size": 12345,
        "extension": ".docx",
    },
}
```

后端校验仍是最终可信边界：

- `.md` 文件上限 256KB。
- `.docx` 文件上限 10MB。
- 空文件拒绝。
- `.doc`、PDF、图片和其他扩展名拒绝。
- 错误提示只返回普通用户可理解文案，不包含路径、堆栈或临时文件名。

### 输入归一化

在 FPA service 附近新增小型归一化函数或模块，避免 `main.py` 承担业务解析。建议返回结构：

```python
{
    "source_file_name": "需求说明.docx",
    "source_file_type": "docx",
    "normalized_markdown": "...",
    "text_length": 1234,
    "parse_warnings": [
        {
            "code": "word_images_ignored",
            "message": "已忽略 Word 中的图片内容，如图片包含关键需求，请补充为文字后重新提交。"
        }
    ],
}
```

`.md` 处理规则：

- 按 UTF-8 读取，必要时用可控错误处理拒绝非法编码。
- 归一化正文等于 Markdown 文本。
- 文本为空或超过 2 万字符时拒绝。

`.docx` 处理规则：

- 使用 `python-docx` 打开文档。
- 提取非空段落文字；标题和列表作为普通段落文本保留。
- 表格按行转换为清晰文本或 Markdown 表格。实现阶段优先选择稳定、易测试的格式。
- 解析警告记录图片、截图、嵌入对象被忽略。
- 如果除图片或嵌入对象外没有有效文字，拒绝创建任务。
- 损坏或无法解析的 Word 统一转换为“Word 文档无法解析，请确认文件未损坏并重新上传”一类错误。

### 任务文件

任务目录继续以 `input/merged_input.md` 作为主输入。建议落盘：

- `input/pasted_input.md`：粘贴文本，保持现有行为。
- `input/uploaded_input.md`：上传文件归一化后的文本，不保存 Word 二进制为普通可见文件。
- `input/merged_input.md`：粘贴文本在前、上传归一化文本在后。
- `input/normalized_input.json`：归一化元数据和解析警告，管理员排查或任务详情摘要使用。

如实现阶段决定保存原始 `.docx`，必须登记为 internal/admin-only，不得进入普通用户文件列表或下载入口。首版可优先不保存原始二进制，以减少可见性和存储风险。

### AI 请求包边界

`scripts/fpa/build_ai_request_package.py` 不解析 `.docx`。它继续只读取：

- `input/merged_input.md`
- `input/task_params.json`
- FPA profile、schema 和系统资料

如需要在 `AI请求摘要.json` 中体现输入来源，可由后端任务详情或摘要读取 `normalized_input.json`，不把原始 Word 路径写入请求包。

## 前端设计

### 提交页上传控件

保持现有上传框结构和拖拽能力，只改文案、accept 和校验：

- `accept=".md,.docx,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"`
- 上传提示改为“拖动 Markdown / Word 文档到这里，或点击选择文件”。
- 已选文件继续展示文件名、大小和移除按钮。
- 上传图标可从 `MD` 改为 `MD/DOCX` 或简短文案，不引入新复杂组件。

### 前端状态与提交

当前前端把 `.md` 文件读成 `fileText`，再用 URL 编码提交；这不能传递 `.docx` 二进制。因此需要：

- 用 `File` 对象保存上传文件。
- `.md` 可继续读文本用于本地字符计数和旧体验。
- `.docx` 不在前端解析，字符数以服务端归一化结果为准。
- 提交请求改为 `FormData`，包含现有表单字段和 `input_file` 文件字段。
- 不手动设置 multipart `Content-Type`，交给浏览器生成 boundary。

### 提交规则文案

规则面板建议使用短版：

```text
粘贴内容和上传文件至少提供一个。
正文不超过 2 万字符。
Markdown 不超过 256KB，Word .docx 不超过 10MB。
目标人天最多 1 位小数。
Word 图片内容会被忽略，请将关键图片信息补充为文字。
```

这能回应用户关注的规则区块，同时不扩大提交页 UI。

### 解析警告展示

后端返回 `word_images_ignored` 或等价警告时，详情页在现有质量提示或失败/状态提示区展示：

```text
已忽略 Word 中的图片内容，如图片包含关键需求，请补充为文字后重新提交。
```

该提示不是失败，也不影响 Excel 下载；它只是需求完整性提醒。

## 错误处理

普通用户可见错误建议：

- 非法扩展名：`上传文件仅支持 Markdown .md 或 Word .docx 文档`
- `.doc`：`暂不支持 .doc，请另存为 .docx 后上传`
- `.md` 超限：`Markdown 文件不能超过 256KB`
- `.docx` 超限：`Word .docx 文件不能超过 10MB`
- Word 损坏：`Word 文档无法解析，请确认文件未损坏并重新上传`
- Word 无有效文字：`Word 文档中未提取到有效文字，请补充文字需求后重新提交`

管理员排查可通过内部元数据查看警告码和解析摘要，但也不需要暴露服务器绝对路径或完整堆栈给普通用户。

## 测试计划

### 后端测试

在 `backend/tests/test_fpa_mvp.py` 或相邻测试文件中补充：

- `.md` 上传仍可创建任务，`merged_input.md` 内容正确。
- `.docx` 段落、标题和列表文字可提取。
- `.docx` 表格文字可提取并进入 AI 请求包。
- `.docx` 含图片且有文字时创建任务成功，并返回图片忽略警告。
- 只有图片没有有效文字的 `.docx` 创建失败。
- `.doc` 被拒绝。
- PDF、图片和其他非法扩展被拒绝。
- `.md` 超过 256KB、`.docx` 超过 10MB 被拒绝。
- 损坏 Word 被拒绝且错误脱敏。
- `AI请求包.json` 使用归一化正文，不依赖原始 Word 文件。

测试生成 `.docx` 可直接用 `python-docx` 在临时目录中构造，图片场景可用最小内嵌图片或构造包含图片 relationship 的文档；若最小图片构造成本过高，优先测试解析层能识别 document relationships 中的图片对象。

### 前端验证

- 运行前端构建，确保 TypeScript 和 Vite 通过。
- 手动或测试验证 `.md / .docx` 文件选择、拖拽、大小提示和移除按钮状态。
- 验证 `FormData` 提交不再手动设置 multipart `Content-Type`。

### 综合验证

- `openspec validate support-fpa-word-input --strict`
- 后端相关测试
- 前端构建或相关检查
- `.\scripts\check-encoding.ps1`

## 实施顺序

1. 后端依赖和归一化函数。
2. 后端 multipart payload 和 `create_task()` 输入接入。
3. 任务详情解析警告返回。
4. 前端上传控件和 `FormData` 提交。
5. 测试和验证。

## 设计边界

- 不提交、不推送。
- 不支持 `.doc`、PDF、OCR 或多模态图片理解。
- 不把 Word 二进制或图片发给 AI。
- 不修改 AI 输出 JSON 契约。
- 不修改 Excel 脚本 payload 或模板生成逻辑。
- 不重构前端为多文件结构，除非现有单文件结构无法保持构建通过。

