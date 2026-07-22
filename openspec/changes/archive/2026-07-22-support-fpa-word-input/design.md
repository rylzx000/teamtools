## Context

TeamTools 当前 FPA 主链路已经把“用户输入 -> `input/merged_input.md` -> AI 请求包 -> AI 结构化结果 -> Excel 脚本”分层落地。后端 `backend/app/main.py` 当前只在上传解析处允许 `.md`，并把文件内容作为 UTF-8 文本传给 `backend/app/modules/fpa/service.py`；`scripts/fpa/build_ai_request_package.py` 只读取任务目录下的 `input/merged_input.md`，Excel 生成脚本只消费结构化 payload。

本 change 的关键是把 Word 支持收敛在“任务创建前后的输入归一化层”，不把 `.docx` 解析逻辑扩散到提示词脚本、AI 调用或 Excel 生成链路。`Markdown`、`Word`、`AI`、`Excel`、`API`、`.md`、`.docx`、`python-docx` 保留英文，是文件格式、办公软件名称、依赖包名称和既有技术/接口专有名词。

## Goals / Non-Goals

**Goals:**

- 支持 FPA 提交页上传 `.docx`，并继续支持现有 `.md` 和粘贴文本。
- 后端将 `.md` / `.docx` 归一化为同一类需求正文输入，后续 AI 请求包只读取归一化正文。
- 使用 `python-docx` 提取正文段落、标题、列表和表格文字，保持大致原文顺序。
- 对 `.docx` 图片、截图和嵌入对象记录解析警告，并向用户展示“已忽略 Word 中的图片内容，如图片包含关键需求，请补充为文字后重新提交。”
- 拒绝 `.doc`、PDF、图片、非法扩展、空文件、损坏 Word、无法解析 Word、无有效文字 Word 和超大文件。
- 保持 Excel 生成主流程、AI 输出契约和现有 FPA 结构化校验不变。

**Non-Goals:**

- 不支持 `.doc`、PDF、图片 OCR、多模态图片理解或多个文件上传。
- 不解析 Word 图片文字，不把图片或 Word 二进制发送给 AI。
- 不引入 Windows COM、LibreOffice、外部转换服务或服务端办公软件依赖。
- 不大改提交页 UI，不新增复杂预览或在线编辑。
- 不修改 Excel 生成脚本的核心 payload、模板填充、公式和下载流程。

## Decisions

### 1. 新增后端输入归一化层，继续输出 `merged_input.md`

任务创建入口先把粘贴文本和上传文件统一转换成内部结构：

```json
{
  "source_file_name": "需求说明.docx",
  "source_file_type": "docx",
  "normalized_markdown": "提取后的正文",
  "text_length": 1234,
  "parse_warnings": []
}
```

`.md` 归一化时直接读取 UTF-8 文本；`.docx` 归一化时使用 `python-docx` 提取文本。`create_task` 继续写入 `input/merged_input.md` 作为 AI 请求包唯一正文来源，并额外保存 `input/normalized_input.json` 或等价元数据文件用于排查、重新运行和任务详情提示。

备选方案是在 `scripts/fpa/build_ai_request_package.py` 中判断文件类型并解析 Word。该方案会让提示词生成脚本承担上传格式职责，破坏“请求包只读统一正文”的边界，因此不采用。

### 2. Word 表格转换为清晰文本，图片只记录警告

Word 段落、标题和列表按文档顺序提取非空文本；表格按行转换为 Markdown 表格或清晰的行文本，优先保证 AI 能理解字段关系，而不是追求 Word 版式还原。

`.docx` 包含图片、截图或嵌入对象时，解析结果增加 `ignored_word_images` 类警告；该警告不阻断任务。若文档除图片外没有任何有效文字，任务创建失败并提示用户补充文字需求。

备选方案是提取图片并做 OCR 或多模态理解。该方案会引入部署、成本、准确性和敏感信息边界复杂度，不符合首版范围。

### 3. 大小限制按文件类型区分

现有 `.md` 上传继续使用 256KB 限制和 2 万字符有效内容限制；新增 `.docx` 上传大小限制建议为 10MB，归一化后的有效文本仍执行 2 万字符限制。

这样既避免 Word 压缩包天然比 Markdown 大导致误拒，又保持进入 AI 的正文长度边界不变。前端可以做同样的快速大小提示，但后端是最终校验来源。

### 4. 解析警告进入任务详情，不进入普通文件下载

解析警告应随任务详情或结果摘要返回，普通用户能看到“图片已忽略”等可操作提示；管理员可在归一化元数据中看到更完整的解析摘要。警告不得暴露服务器路径、堆栈、临时文件路径或内部库异常。

解析警告可以进入 `quality_flags` 或新增轻量字段，具体实现阶段按现有任务详情结构最小改动处理。无论采用哪种字段，前端只展示普通用户可理解的文本。

### 5. 依赖只加到后端项目依赖文件

如实现阶段确认当前环境没有 `python-docx`，只在后端依赖文件中新增项目依赖并更新锁文件；不做全局安装，不改系统环境变量，不在 `C:` 盘安装工具。

## Risks / Trade-offs

- [Risk] Word 版式复杂导致表格或列表顺序与视觉效果不完全一致。→ Mitigation：验收以“保持大致顺序、文字可读、表格关系清晰”为准，不承诺版式还原。
- [Risk] 文档关键信息只在图片中，首版会忽略。→ Mitigation：记录用户可见警告；纯图片无文字时失败并提示补充文字。
- [Risk] `.docx` 是压缩包，损坏或异常文件可能触发解析错误。→ Mitigation：捕获并转换为普通用户可理解错误，不暴露路径或堆栈。
- [Risk] 新增依赖影响部署镜像或锁文件。→ Mitigation：仅声明项目依赖，运行后端测试和构建检查验证依赖解析。
- [Risk] 前端仅凭扩展名校验可能被绕过。→ Mitigation：后端继续做扩展名、大小、空文件和解析结果校验，前端只做体验优化。

## Migration Plan

1. OpenSpec 通过后，先实现后端归一化和 `.docx` 解析单元测试。
2. 再接入任务创建、AI 请求包输入和任务详情解析警告。
3. 最后调整前端上传控件提示与警告展示。
4. 验证通过前不切换 OpenSpec 阶段，不提交、不推送。

回滚策略：如 Word 支持验证失败，可只回滚 `.docx` 上传入口和依赖，保留现有 `.md` 提交流程不变；`input/merged_input.md` 主链路不需要回滚。

## Open Questions

- 实现阶段是否复用现有 `quality_flags` 返回解析警告，还是新增更明确的 `input_parse_warnings` 字段，需要结合前端任务详情结构做最小改动选择。
- `.docx` 表格最终采用 Markdown 表格还是按行文本，建议实现阶段优先选择代码更稳定、测试更直接的方式。
