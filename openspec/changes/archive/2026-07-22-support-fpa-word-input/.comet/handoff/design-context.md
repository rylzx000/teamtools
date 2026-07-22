# Comet Design Handoff

- Change: support-fpa-word-input
- Phase: design
- Mode: compact
- Context hash: e69963f034cb0d3e23e329a12f83c5520e47b3d0d2a12b77a6fbf4f6130c262d

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/support-fpa-word-input/proposal.md

- Source: openspec/changes/support-fpa-word-input/proposal.md
- Lines: 1-39
- SHA256: 48d3fc68214519c09fc955bcf24197e926c444f67e8f2909843d627f8e44de9f

```md
## Why

当前 FPA 提交评估只支持粘贴文本或上传 `.md` 文件，许多需求材料实际以 Word `.docx` 流转，用户需要先手工转 Markdown 才能提交，增加了操作成本和格式丢失风险。

本 change 让后端在任务创建阶段把 `.md` 和 `.docx` 统一归一化为需求正文，继续复用既有 AI 请求包、结构化校验和 Excel 生成链路，避免让 AI 直接处理 Word 二进制文件。

`Markdown`、`Word`、`AI`、`Excel`、`API`、`.md`、`.docx` 保留英文，是文件格式、办公软件名称和既有技术/接口专有名词。

## What Changes

- FPA 提交输入从“粘贴文本或单个 `.md` 文件”扩展为“粘贴文本、单个 `.md` 文件或单个 `.docx` 文件”。
- 后端新增输入归一化边界：`.md` 直接按文本读取，`.docx` 提取正文段落、标题、列表和表格文字后生成统一 Markdown/文本内容。
- `.docx` 图片、截图和嵌入对象首版不解析、不 OCR、不发送给 AI；存在此类内容时记录解析警告并向用户提示已忽略图片内容。
- 后续 AI 请求包生成只读取归一化后的正文输入，不在提示词脚本中直接解析 Word。
- 后端只允许 `.md` / `.docx`，拒绝 `.doc`、PDF、图片和其他非法扩展；新增 `.docx` 大小上限建议为 10MB。
- 前端提交页上传控件支持 `.md / .docx`，保留拖拽上传能力，并展示 Markdown / Word 文档支持提示。
- 任务详情或提交结果展示后端返回的 Word 解析警告，尤其是图片内容被忽略的提示。
- 不改变 AI 输出契约、FPA Excel 脚本 payload、Excel 生成模板和结果下载主流程。

## Capabilities

### New Capabilities

- 无。本次是既有 FPA 提交与评估能力的输入格式扩展，不新增同义 capability。

### Modified Capabilities

- `fpa-workflow`：修改 FPA 任务输入、文件校验、输入归一化、Word 图片忽略告警和任务主链路前置处理要求。
- `fpa-interface-ui`：修改提交页上传控件、格式提示、前端校验和任务详情解析警告展示要求。
- `fpa-ai-contract`：明确 AI 请求包只消费归一化正文，`.docx` 解析不进入提示词脚本，AI 不接收 Word 二进制、图片或嵌入对象。

## Impact

- 影响后端接口与任务创建链路：`backend/app/main.py` 的上传解析、`backend/app/modules/fpa/service.py` 的任务输入保存、归一化元数据和任务详情返回。
- 影响后端依赖：建议在项目后端依赖文件中新增 `python-docx`，不做全局安装，不引入 Windows COM、LibreOffice 或外部转换服务。
- 影响前端提交页：`frontend/src/App.tsx` 的文件选择、拖拽校验、大小限制提示和解析警告展示；样式尽量复用现有上传控件。
- 影响 AI 请求包生成边界：`scripts/fpa/build_ai_request_package.py` 继续只读取 `input/merged_input.md`，必要时只读取归一化元数据摘要，不解析原始 Word 文件。
- 影响测试：补充 `.md` 保持可用、`.docx` 段落/表格提取、图片忽略警告、纯图片 Word 失败、`.doc`/非法扩展/超大/损坏 Word 拒绝、AI 请求包使用归一化正文等用例。
- 非目标：不支持 `.doc`、PDF、图片 OCR、多模态图片理解、页眉页脚强解析、多个文件上传、Excel 生成主流程调整或 AI 直接处理二进制文件。

```

## openspec/changes/support-fpa-word-input/design.md

- Source: openspec/changes/support-fpa-word-input/design.md
- Lines: 1-90
- SHA256: ab318f45de83b688ffab2567040bdc89f6db9ff65cf4f729b11c390d5851caf0

[TRUNCATED]

```md
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

```

Full source: openspec/changes/support-fpa-word-input/design.md

## openspec/changes/support-fpa-word-input/tasks.md

- Source: openspec/changes/support-fpa-word-input/tasks.md
- Lines: 1-45
- SHA256: f7aa507c11fe20e1a27bb4f4f7672421c19b14aaff2d8712bd67f12e85a41e80

```md
## 1. OpenSpec 与契约确认

- [ ] 1.1 用户确认本 change 的 proposal、design、tasks 和 delta spec 范围后，再进入实现阶段
- [ ] 1.2 确认 `fpa-workflow`、`fpa-interface-ui`、`fpa-ai-contract` 的 delta spec 与需求边界一致
- [ ] 1.3 运行 `openspec validate support-fpa-word-input --strict`

## 2. 后端输入归一化

- [ ] 2.1 在后端项目依赖中新增 `python-docx`，仅写入项目依赖文件和必要锁文件，不做全局安装
- [ ] 2.2 设计并实现 FPA 输入归一化结构，包含 `source_file_name`、`source_file_type`、`normalized_markdown` 或 `normalized_text`、`text_length`、`parse_warnings`
- [ ] 2.3 保持 `.md` 上传和粘贴文本现有行为可用，并继续生成 `input/merged_input.md`
- [ ] 2.4 实现 `.docx` 正文段落、标题、列表和表格文字提取，保持大致顺序
- [ ] 2.5 对 Word 图片、截图和嵌入对象记录解析警告，不解析图片文字，不发送图片给 AI
- [ ] 2.6 拒绝 `.doc`、PDF、图片、非法扩展、空文件、超大文件、损坏 Word、无法解析 Word 和无有效文字 Word
- [ ] 2.7 确保错误提示面向普通用户可理解，不暴露服务器路径、堆栈或内部临时文件名

## 3. AI 请求包与任务详情

- [ ] 3.1 确保 `scripts/fpa/build_ai_request_package.py` 继续只读取归一化后的 `input/merged_input.md`
- [ ] 3.2 确保 AI 请求包不包含原始 Word 二进制、图片、嵌入对象或服务器临时路径
- [ ] 3.3 保存或返回解析警告，任务详情可展示 Word 图片忽略提示
- [ ] 3.4 确认 Excel 脚本输入 payload 和 Excel 生成主流程不因输入来源为 Word 而改变

## 4. 前端提交页

- [ ] 4.1 上传控件从仅支持 `.md` 调整为支持 `.md / .docx`
- [ ] 4.2 保留拖拽上传能力，更新上传提示为支持 Markdown / Word 文档
- [ ] 4.3 前端增加 `.docx` 10MB 和 `.md` 256KB 的快速校验提示，后端仍作为最终校验来源
- [ ] 4.4 将提交请求从 URL 编码文本改为 `FormData`，确保 `.docx` 二进制文件由后端解析
- [ ] 4.5 在任务详情或提交结果中展示后端返回的 Word 图片忽略警告
- [ ] 4.6 不大改现有提交页 UI 和模型调用区

## 5. 测试与验证

- [ ] 5.1 验证 `.md` 上传仍然可用
- [ ] 5.2 验证 `.docx` 正常提取段落、标题和列表文字
- [ ] 5.3 验证 `.docx` 正常提取表格文字
- [ ] 5.4 验证 `.docx` 包含图片时任务可继续，并返回图片忽略警告
- [ ] 5.5 验证只有图片没有有效文字的 `.docx` 失败
- [ ] 5.6 验证 `.doc`、非法扩展名、超大文件和损坏 Word 被拒绝
- [ ] 5.7 验证 AI 请求包使用归一化正文，不依赖原始 Word 文件
- [ ] 5.8 运行后端相关测试
- [ ] 5.9 运行前端构建或相关检查
- [ ] 5.10 运行 `.\scripts\check-encoding.ps1`
- [ ] 5.11 如任一检查无法运行，在最终汇总中说明原因和可手动执行命令

```

## openspec/changes/support-fpa-word-input/specs/fpa-ai-contract/spec.md

- Source: openspec/changes/support-fpa-word-input/specs/fpa-ai-contract/spec.md
- Lines: 1-30
- SHA256: 75d400b54a088de28bf24e5c761622556e56c65c906971fc9d1d97f2ac313ffe

```md
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

```

## openspec/changes/support-fpa-word-input/specs/fpa-interface-ui/spec.md

- Source: openspec/changes/support-fpa-word-input/specs/fpa-interface-ui/spec.md
- Lines: 1-88
- SHA256: 618d1230cc49546907df8fc47ac5051210834ba19d2b0834445a9bf666637b3a

[TRUNCATED]

```md
## MODIFIED Requirements

### Requirement: 提交评估页交互

系统 MUST 在提交评估页按后端接口和输入规则控制表单状态，提交成功后进入任务详情页等待浏览器调用模型。页面 SHALL 按 Open Design 原型形成一屏优先的紧凑表单，开放系统选择、`规模计数时机`、`完整性级别`、目标人天、需求名称、Markdown 粘贴、`.md` / `.docx` 文件上传和 API Key 配置。用户填写个人 API Key 时使用个人 Key；未填写时自动尝试使用团队公用 Key。`Open Design`、`Markdown`、`Word`、`API Key`、`.docx` 保留英文，是原型方法、文件格式、办公软件名称和接口安全字段的既有命名。

#### Scenario: 表单配置加载
- **WHEN** 用户打开提交评估页
- **THEN** 前端调用 `GET /api/fpa/form-config`
- **AND** 系统选择、`规模计数时机` 和 `完整性级别` 使用后端返回的选项和默认值
- **AND** 当用户存在有效 `default_system_code` 时优先选中该系统，否则选中第一个可用系统

#### Scenario: 表单不可提交
- **WHEN** 系统未选择，或粘贴内容与上传文件均为空，或目标人天格式非法
- **THEN** 提交按钮不可用或提交返回参数错误
- **AND** 页面显示字段级提示

#### Scenario: 上传控件支持 Markdown 和 Word
- **WHEN** 用户在提交页选择或拖拽上传文件
- **THEN** 上传控件允许 `.md` 和 `.docx`
- **AND** 页面提示支持 Markdown / Word 文档
- **AND** 上传控件保留文件名、文件大小和移除能力

#### Scenario: 前端拒绝明显非法文件
- **WHEN** 用户选择 `.doc`、PDF、图片或 `.md` / `.docx` 以外的文件
- **THEN** 前端显示字段级提示并阻止提交
- **AND** 后端仍必须执行最终格式校验

#### Scenario: 前端文件大小提示
- **WHEN** 用户上传 `.md` 超过 256KB 或 `.docx` 超过 10MB
- **THEN** 前端显示文件过大提示并阻止提交
- **AND** 后端仍必须执行最终大小校验

#### Scenario: 规模计数时机下拉
- **WHEN** 用户打开提交评估页
- **THEN** 页面展示 `规模计数时机` 下拉框
- **AND** 下拉选项文字包含系数前缀：`1.39 估算早期`、`1.21 估算中期`、`1.10 估算晚期`、`1.00 项目交付后及运维阶段`
- **AND** 默认值以后端配置返回为准，当前默认应为 `1.21 估算中期`

#### Scenario: 完整性级别下拉
- **WHEN** 用户打开提交评估页
- **THEN** 页面展示 `完整性级别` 下拉框
- **AND** 下拉选项文字包含系数前缀：`1.00 没有明确的完整性级别或等级为C/D`、`1.10 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式`、`1.30 完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施`
- **AND** 默认值以后端配置返回为准，当前默认应为 `1.10 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式`

#### Scenario: API Key 选择逻辑
- **WHEN** 用户在提交评估页填写个人 API Key
- **THEN** 前端使用该个人 Key 调用模型
- **AND** 任务不消耗公用 Key 额度

#### Scenario: 未填写 API Key 使用公用 Key
- **WHEN** 用户未填写个人 API Key
- **THEN** 页面提示未填写时将使用团队公用 Key 并消耗个人公用额度
- **AND** 调用模型前由前端向后端领取公用 Key 调用配置

#### Scenario: 公用额度已用完提示
- **WHEN** 用户未填写个人 API Key 且公用额度已用完
- **THEN** 页面提示 `公用apikey个人用量已用完，请输入可用的apikey`
- **AND** 前端不得继续使用公用 Key 调用模型

#### Scenario: 成功提交
- **WHEN** 任务创建成功
- **THEN** 页面跳转到任务详情页
- **AND** 详情页展示任务已创建、AI 请求包已生成、等待浏览器调用模型

### Requirement: 任务列表与详情状态展示

系统 SHALL 以后端状态、权限字段、输入解析警告和产物可见性驱动页面展示；列表页默认手动刷新，详情页可以按约定轮询。页面展示流程 SHALL 使用面向用户的简化阶段，不展示后台 JSON、payload、路由结构或过程文件。任务详情摘要 SHALL 增加当前用户公用 Key 余量展示。

#### Scenario: 详情页结果展示
- **WHEN** 任务已完成且普通用户打开自己的任务详情
- **THEN** 页面展示摘要条、目标命中、质量提示、Excel 下载入口和公用 Key 余量
- **AND** 普通用户不得查看、复制或下载 `AI分析.md`、`AI评估.md`、`AI结构化结果.json`、完整 `FPA生成过程.json`、AI 请求包、AI 请求摘要、脚本 payload、任务日志、原始模型响应或其他排查文件

#### Scenario: Word 图片忽略警告展示
- **WHEN** 任务详情或提交结果中包含 Word 图片内容被忽略的解析警告
- **THEN** 页面向用户展示“已忽略 Word 中的图片内容，如图片包含关键需求，请补充为文字后重新提交。”
- **AND** 页面不得展示服务器路径、堆栈、原始解析异常或内部临时文件名

#### Scenario: 公用 Key 余量展示

```

Full source: openspec/changes/support-fpa-word-input/specs/fpa-interface-ui/spec.md

## openspec/changes/support-fpa-word-input/specs/fpa-workflow/spec.md

- Source: openspec/changes/support-fpa-word-input/specs/fpa-workflow/spec.md
- Lines: 1-81
- SHA256: c06de244e89472e1479f2c7bdde74a98f64e183d6742d3f96ad9e33bcb30ce48

[TRUNCATED]

```md
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

```

Full source: openspec/changes/support-fpa-word-input/specs/fpa-workflow/spec.md
