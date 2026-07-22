# Brainstorm Summary

- Change: support-fpa-word-input
- Date: 2026-07-21
- Status: 用户已确认采用方案 A（后端归一化模块 + 现有主链路复用）

## 确认的事实与约束

- 当前 FPA 主链路以 `input/merged_input.md` 作为 AI 请求包唯一需求正文来源。
- `.docx` 支持必须收敛在后端输入归一化层，不让 AI、提示词脚本或 Excel 脚本读取 Word 二进制。
- 前端需要改为 `FormData` 上传真实文件，否则 `.docx` 二进制无法交给后端解析。
- `.md` 仍保持现有能力；`.docx` 新增 10MB 文件大小上限，归一化后正文仍受 2 万字符限制。
- Word 图片、截图和嵌入对象首版只记录警告，不解析、不 OCR、不发送给 AI。

## 候选方案

### 方案 A：后端归一化模块 + 现有主链路复用（推荐）

- 在后端新增 FPA 输入归一化函数或小模块，统一返回 `source_file_name`、`source_file_type`、`normalized_markdown`、`text_length`、`parse_warnings`。
- `.md` 直接读取 UTF-8 文本，`.docx` 用 `python-docx` 提取段落、标题、列表和表格文字。
- `create_task` 继续生成 `input/merged_input.md`，并保存 `input/normalized_input.json` 作为排查元数据。
- 任务详情返回解析警告，前端在质量提示区展示图片忽略提醒。

推荐理由：边界清楚、对 AI 请求包和 Excel 生成影响最小，测试也能直接覆盖输入归一化。

### 方案 B：在 AI 请求包脚本里解析 Word（不推荐）

- `scripts/fpa/build_ai_request_package.py` 根据上传来源解析 `.docx`。
- 优点是任务创建改动较少。
- 缺点是提示词脚本会承担上传格式解析职责，破坏统一正文输入边界，也更难复用任务重跑和前端警告展示。

### 方案 C：外部转换或 OCR（排除）

- 使用 LibreOffice、Windows COM、外部转换服务或 OCR 提取 Word/PDF/图片内容。
- 能覆盖更多复杂文档，但部署复杂、依赖重、敏感信息边界扩大，且超出首版需求。

## 待确认的技术方案

建议采用方案 A。

### 后端设计

- `backend/app/main.py` 的 multipart 解析保留为入口，但需要支持 `.md` 和 `.docx`，并返回真实文件名、字节内容和文件类型。
- `backend/app/modules/fpa/service.py` 在创建任务前调用归一化逻辑；只要归一化正文为空即失败。
- `.docx` 解析失败统一转换为普通用户可读错误，例如“Word 文档无法解析，请确认文件未损坏并重新上传”。
- `input/merged_input.md` 仍是 AI 请求包正文来源；`input/uploaded_input.md` 可继续保存归一化文本，原始文件是否另存为 internal/debug 由实现阶段按最小改动决定。
- `input/normalized_input.json` 保存来源文件名、类型、文本长度、解析警告和可脱敏解析摘要。

### 前端设计

- 提交页上传控件文案改为支持 Markdown / Word 文档。
- `readFile` 从“读成文本”改为保存 `File` 对象；`.md` 可继续读文本用于字符计数，`.docx` 不做前端解析。
- 提交请求改为 `FormData`，字段名沿用 `input_file` 或后端最终约定字段。
- 提交规则文案改为：粘贴文本和归一化后的文档正文不超过 2 万字符；Markdown 不超过 256KB，Word `.docx` 不超过 10MB；Word 图片内容会被忽略。
- 任务详情质量提示区展示后端返回的 Word 图片忽略警告。

### 数据与可见性

- 普通用户只看到可操作警告和脱敏错误，不看到解析堆栈、服务器路径或原始内部元数据。
- 管理员可在任务详情或排查文件中查看归一化元数据摘要。
- AI 请求包摘要可以记录 `input_chars`，但不需要记录原始 Word 路径。

## 关键取舍与风险

- 选择 `FormData` 会比当前 URL 编码提交多改一点前端，但这是支持 `.docx` 二进制上传的必要改动。
- `python-docx` 不保证视觉版式完全还原，验收应以文字顺序和表格关系清晰为准。
- 纯图片 Word 会失败，避免用户误以为系统已读取图片需求。
- 若保存原始 `.docx`，必须标记为非普通用户可下载产物；如实现成本可控，首版可只保存归一化文本和元数据。

## 测试策略

- 后端新增输入归一化单元测试，覆盖 `.md`、普通 `.docx`、表格 `.docx`、含图片 `.docx`、纯图片 `.docx`、损坏 Word、`.doc`、非法扩展和超大文件。
- 端到端测试覆盖 `.md` 旧流程仍可创建任务，以及 `.docx` 任务生成的 `AI请求包.json` 包含归一化正文。
- 前端构建检查覆盖 TypeScript 编译和上传控件状态。
- 编码检查继续运行 `.\scripts\check-encoding.ps1`。

## Spec Patch

无。当前 delta spec 已覆盖设计发现；仅补充了 tasks.md 中前端 `FormData` 实施任务。
