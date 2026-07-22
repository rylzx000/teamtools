## MODIFIED Requirements

### Requirement: AI 请求包由后端生成

系统 SHALL 由后端读取归一化后的用户需求正文、系统配置、系统知识包、提示词模板、JSON 契约和页面参数，生成任务级 AI 请求包快照。`.docx` 解析 MUST 发生在任务输入归一化层，AI 请求包生成脚本 MUST 不直接解析 Word 文件。`AI`、`JSON`、`Word`、`.docx` 保留英文，是既有能力、数据格式、办公软件名称和文件格式专有名词。

#### Scenario: Markdown 请求包生成成功
- **WHEN** FPA 任务由粘贴文本或 `.md` 文件创建，且所需资源存在
- **THEN** 后端基于归一化正文生成 `AI请求包.json` 和 `AI请求摘要.json`
- **AND** 请求包保存后不随资源文件后续修改自动变化

#### Scenario: Word 请求包生成成功
- **WHEN** FPA 任务由 `.docx` 文件创建，且 Word 归一化正文非空
- **THEN** 后端基于归一化后的 Markdown 或文本内容生成 `AI请求包.json` 和 `AI请求摘要.json`
- **AND** 请求包正文不得包含原始 Word 二进制、图片、嵌入对象或服务器临时文件路径

#### Scenario: 请求包不解析 Word
- **WHEN** 后端生成 AI 请求包
- **THEN** 请求包生成逻辑只读取统一正文输入文件和必要任务参数
- **AND** 不得在提示词脚本中直接打开、解压、解析 `.docx` 或执行 OCR

#### Scenario: 模板或契约缺失
- **WHEN** 提示词模板、JSON schema 或必要系统知识包缺失
- **THEN** 任务失败并记录配置错误
- **AND** 系统不得使用隐藏默认提示词继续执行

#### Scenario: 归一化正文缺失
- **WHEN** 任务输入归一化结果为空、缺失或不可读取
- **THEN** AI 请求包生成失败
- **AND** 任务不得进入等待 AI 调用状态
