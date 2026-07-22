## MODIFIED Requirements

### Requirement: FPA 任务输入

系统 SHALL 允许用户为单个需求提交一次 FPA 评估任务，并支持系统选择、可选需求名称、粘贴文本、单个 Markdown 或 Word `.docx` 文件、可选目标人天、`规模计数时机` 和 `完整性级别`。`Markdown`、`Word`、`.docx`、`AI`、`Excel` 保留英文，是文件格式、办公软件名称和既有模块能力名称。

#### Scenario: 有效 Markdown 输入提交
- **WHEN** 用户选择一个系统，并提供粘贴文本或上传 `.md` 文件中的至少一项
- **THEN** 系统创建 FPA 任务并保存输入、上传文件和任务参数快照
- **AND** 粘贴内容和上传文件同时存在时按“粘贴文本在前、上传文件在后”合并
- **AND** 后续 AI 请求包使用合并后的归一化正文

#### Scenario: 有效 Word 输入提交
- **WHEN** 用户选择一个系统，并上传可解析且包含有效文字的 `.docx` 文件
- **THEN** 后端提取 Word 正文段落、标题、列表和表格文字
- **AND** 系统把提取内容归一化为 Markdown 或清晰文本后创建 FPA 任务
- **AND** 后续 AI 请求包只读取归一化后的正文，不读取原始 Word 二进制文件

#### Scenario: 输入超限
- **WHEN** 粘贴文本、上传 Markdown 有效内容或 Word 归一化后有效内容超过 2 万字符，或上传 `.md` 文件超过 256KB，或上传 `.docx` 文件超过 10MB
- **THEN** 系统拒绝创建任务或返回参数错误
- **AND** 错误信息必须面向普通用户脱敏且可理解

#### Scenario: 不支持的文件格式
- **WHEN** 用户上传 `.doc`、PDF、图片或 `.md` / `.docx` 以外的文件
- **THEN** 系统拒绝创建任务
- **AND** 错误信息说明仅支持 Markdown 或 Word `.docx` 文档

#### Scenario: Word 无法解析
- **WHEN** 用户上传损坏、空文件、格式不合法或无法解析的 `.docx`
- **THEN** 系统拒绝创建任务
- **AND** 错误信息不得暴露服务器路径、堆栈或内部临时文件名

#### Scenario: Word 无有效文字
- **WHEN** `.docx` 只包含图片、截图、嵌入对象或其他无法转为文字的内容
- **THEN** 系统拒绝创建任务
- **AND** 错误信息提示用户补充文字需求后重新提交

#### Scenario: 需求名称为空
- **WHEN** 用户未填写需求名称
- **THEN** 系统使用上传文件名、需求文本摘要、AI/脚本总结短名称或 `FPA工作量评估-YYYYMMDD-HHmm` 生成兜底名称
- **AND** 后续脚本 payload 中的 `requirement_name` 必须有值

#### Scenario: Excel 参数默认值
- **WHEN** 用户未调整 Excel 参数
- **THEN** `规模计数时机` 默认使用 `估算中期`
- **AND** `完整性级别` 默认使用 `完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式`

## ADDED Requirements

### Requirement: FPA 输入归一化

系统 MUST 在生成 AI 请求包前把用户粘贴文本、`.md` 文件和 `.docx` 文件归一化为统一需求正文，并保留可排查的来源元数据。归一化结构 SHALL 至少包含 `source_file_name`、`source_file_type`、`normalized_markdown` 或 `normalized_text`、`text_length` 和 `parse_warnings`。

#### Scenario: Markdown 归一化
- **WHEN** 用户上传 `.md` 文件
- **THEN** 后端按 UTF-8 文本读取文件内容并写入归一化正文
- **AND** `source_file_type` 记录为 `md`

#### Scenario: Word 段落标题列表提取
- **WHEN** 用户上传包含正文段落、标题或列表的 `.docx`
- **THEN** 后端提取非空文字并保持文档原有大致顺序
- **AND** 空段落可以忽略

#### Scenario: Word 表格提取
- **WHEN** 用户上传包含表格的 `.docx`
- **THEN** 后端提取表格中的文字
- **AND** 表格可以转换为 Markdown 表格或按行转换为清晰文本
- **AND** 表格文字进入同一份归一化正文

#### Scenario: Word 图片内容被忽略
- **WHEN** `.docx` 包含图片、截图或嵌入对象，且文档中仍存在有效文字
- **THEN** 后端继续创建任务
- **AND** `parse_warnings` 记录图片内容已忽略
- **AND** 用户可见提示包含“已忽略 Word 中的图片内容，如图片包含关键需求，请补充为文字后重新提交。”

#### Scenario: AI 请求包使用归一化正文
- **WHEN** 后端生成 FPA AI 请求包
- **THEN** 请求包正文来自归一化后的 Markdown 或文本内容
- **AND** 请求包生成逻辑不得直接解析 `.docx`、读取 Word 二进制、提取图片或调用 OCR
- **AND** Excel 生成主流程不因输入来源为 Word 而改变
