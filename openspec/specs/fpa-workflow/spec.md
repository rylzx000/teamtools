# fpa-workflow Specification

## Purpose
定义 FPA 工作量评估模块的用户输入、系统资料、任务生命周期、失败/取消/重新运行、历史任务和结果产物边界。

## Source Documents

- `docs/modules/fpa/README.md`
- `docs/modules/fpa/01-已确认需求.md`
- `docs/modules/fpa/02-任务流程设计.md`
- `docs/modules/fpa/03-数据与文件设计.md`
- `docs/modules/fpa/06-资源包与生成契约设计.md`
## Requirements
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

### Requirement: 系统资料与无资料模式

系统 MUST 根据用户选择的单一系统读取配置和精简知识包；生产与本地当前仅对外提供 `claimcar`（车险理赔核心系统）和 `claimoth`（非车险理赔核心系统）。选择其他系统、系统未启用或配置为空资料目录时进入无资料模式或被提交入口拒绝。已配置系统资料缺少 `08-FPA场景拆分字典.md` 时允许继续，但必须标记为无系统字典模式；已配置系统基础资料缺失时不得静默降级。`claimcar`、`claimoth` 保留英文，是系统编码。

#### Scenario: 已配置系统资料可用
- **WHEN** `systems.yaml` 中的 `claimcar` 或 `claimoth` 启用且知识包文件存在
- **THEN** 后端优先读取 `08-FPA场景拆分字典.md` 作为场景路由关键资料
- **AND** 后端读取 `teamtools-system-brief.md` 作为系统背景资料
- **AND** 前端不得直接读取服务器资料目录

#### Scenario: 生产可选系统范围
- **WHEN** 前端加载 FPA 提交配置或系统列表
- **THEN** 后端仅返回 `claimcar` 和 `claimoth`
- **AND** 前端系统下拉框仅展示车险理赔核心系统和非车险理赔核心系统
- **AND** 系统不得展示、初始化或默认选择 `onlineclaim`、`clqp`

#### Scenario: 08 字典缺失
- **WHEN** 已配置系统存在基础资料但缺少 `08-FPA场景拆分字典.md`
- **THEN** 任务允许进入无系统字典模式
- **AND** `AI评估.md` 必须说明系统字典缺失、临时归类依据和待复核点

#### Scenario: 其他系统或空资料目录
- **WHEN** 用户选择其他系统或系统配置明确为空资料目录
- **THEN** 任务进入无资料模式或被提交入口拒绝
- **AND** AI 请求包中应说明无资料模式边界

#### Scenario: 已配置基础资料缺失
- **WHEN** 系统配置了知识目录但必要基础资料缺失或不可读
- **THEN** 任务失败并记录系统资料配置错误
- **AND** 系统不得自动降级为无资料模式

### Requirement: FPA 主处理链路

系统 SHALL 按“提交评估 -> 生成 AI 请求包 -> 等待AI调用 -> 前端选择个人 Key 或公用 Key 调用模型 -> 回传 AI 响应 -> 提取 AI评估.md 和结构化 JSON -> 校验事实/路由/冻结清单 -> 生成 Excel -> 成功任务按需扣减公用额度 -> 下载结果”的流程处理任务，并把 AI 业务判断与脚本确定性生成分离。普通用户可见结果只包含摘要和 Excel 下载；`AI评估.md`、结构化 JSON、Excel payload 和过程 JSON 作为管理员复核或后台排查产物。`AI`、`Key`、`Excel`、`payload` 保留英文，是既有能力、模型调用凭据概念、办公软件名称和机器可读数据结构专有名词。

#### Scenario: 成功完成任务
- **WHEN** 前端回传合法 AI 响应
- **THEN** 后端提取并保存 `AI评估.md` 和 `AI结构化结果.json`
- **AND** 后端校验 JSON 中的变更事实、场景路由、拆分/合并决策和冻结功能点清单
- **AND** 后端基于同一组 `frozen_items` 生成 Excel 脚本输入 payload、`FPA生成过程.json` 和 `FPA工作量评估.xlsx`
- **AND** 任务完成后用户可以查看摘要并下载 Excel

#### Scenario: 冻结清单与产物一致
- **WHEN** 任务生成正式结果
- **THEN** `AI评估.md`、Excel 明细和过程 JSON 中的功能点数量、顺序、类型和 `stable_id` 必须保持一致
- **AND** 过程 JSON 必须保留冻结项中的 `fact_ids`、`route_ids`、`system_scene_ids`、`linked_process_ids` 和 `linked_data_ids`
- **AND** 任一产物生成失败时不得进入 `completed`
- **AND** 公用额度扣减只能发生在正式结果进入 `completed` 之后

### Requirement: 取消、失败和重新运行

系统 MUST 支持取消仍在执行中的任务、保留失败任务排查信息，并通过新任务实现重新运行而不是覆盖原任务。

#### Scenario: 取消可执行任务
- **WHEN** 用户取消 `waiting_ai_call`、`validating_result` 或 `generating_result` 状态的任务
- **THEN** 系统记录取消请求、取消人和取消时间
- **AND** 状态最终进入 `cancelled` 并保留任务记录

#### Scenario: 失败任务重新运行
- **WHEN** 用户对失败任务执行重新运行
- **THEN** 系统基于原输入创建新任务
- **AND** 原任务状态、排查文件和事件记录不得被覆盖

#### Scenario: 历史任务保留
- **WHEN** 任务完成、失败或取消
- **THEN** 系统保留历史记录
- **AND** 首版不提供删除历史任务记录能力

### Requirement: 成功结果可见性

系统 SHALL 在成功任务中向普通用户展示结果摘要并提供 Excel 下载入口；`AI评估.md`、AI 结构化结果、Excel payload、生成过程 JSON 和其他排查产物 SHALL 仅作为管理员复核或后台排查用途保留。

#### Scenario: 普通用户查看成功任务
- **WHEN** 普通用户打开自己已完成的任务详情
- **THEN** 页面展示结果摘要、目标命中、质量提示摘要和 Excel 下载入口
- **AND** 只有 Excel 提供普通用户下载入口
- **AND** 页面和接口不得向普通用户展示或返回 `AI评估.md`、完整过程 JSON、结构化 JSON、payload、服务器绝对路径、内部文件角色、原始模型错误、环境变量或模型 Key

#### Scenario: 管理员查看任务
- **WHEN** 管理员查看任意 FPA 任务
- **THEN** 系统可以展示提交人、失败阶段、事件时间线、`AI评估.md`、AI 请求摘要、AI 结构化结果、Excel payload、生成过程 JSON 和排查摘要
- **AND** 不得暴露模型 Key、环境变量或其他敏感内容

### Requirement: FPA 产物保存

系统 MUST 将 `AI评估.md`、AI 结构化结果和生成过程 JSON 保存为任务产物，并区分普通用户可见说明、正式交付和管理员排查用途。

#### Scenario: 保存 AI 评估说明
- **WHEN** AI 结构化结果通过校验且冻结清单可用
- **THEN** 后端保存 AI 响应中的 `AI评估.md`
- **AND** `AI评估.md` 必须说明需求理解、资料使用情况、变更事实摘要、场景路由摘要、拆分/合并摘要、冻结功能点清单摘要、数据功能关联表、目标人天校准说明和待复核点
- **AND** 如果系统资料提供关键链路、后段链路或核心链路复核表，`AI评估.md` 必须逐项说明是否涉及、是否单独计数、对应 `stable_id`、合并或不计原因
- **AND** 文件内容必须引用同一组 `stable_id`，不得与 Excel 明细另行生成不同清单

#### Scenario: 保存排查文件
- **WHEN** 后端保存 AI 请求包、原始响应、AI 结构化结果、脚本 payload 或调用错误
- **THEN** 这些文件必须登记为内部或管理员排查用途
- **AND** 普通用户不得通过文件列表或下载接口直接获取排查文件

### Requirement: 跑 AI 前系统轻校验

系统 SHALL 在用户获取 AI 请求包或调用 AI 前，对需求文本和当前选择系统做轻量相关性检查。该检查不得调用大模型，不得消耗模型 token；检查依据包括系统配置、系统编码、系统中文名、系统资料简包和可用的 `08-FPA场景拆分字典.md`。系统轻校验只是选错系统防呆，不替代 AI 结构化结果校验，也不替代当前任务系统绑定校验。

#### Scenario: 跑 AI 前发现系统可能选错
- **WHEN** 用户选择的系统与需求文本明显不匹配，且另一个系统得分显著更高
- **THEN** 系统返回 `warning` 或 `blocked` 的系统相关性检查结果
- **AND** 结果包含当前选择系统编码、当前选择系统名称、最佳匹配系统编码、最佳匹配系统名称、当前系统得分、最佳匹配系统得分和面向用户的提示信息
- **AND** 系统不得因此调用大模型

#### Scenario: 用户确认按当前系统继续
- **WHEN** 系统相关性检查返回 `warning` 或 `blocked`，且用户选择仍然继续
- **THEN** 系统记录确认结果
- **AND** 同一任务后续获取 AI 请求包时不重复拦截
- **AND** 后端最终仍以当前任务系统作为 AI 结果校验的权威边界

### Requirement: 用户默认系统

系统 SHALL 支持用户级默认系统 `default_system_code`，并在登录态和 `/api/auth/me` 返回该字段。FPA 提交页 SHALL 仅在当前用户存在有效 `default_system_code` 且该系统属于当前可选系统时默认选中该系统；当用户没有默认系统或默认系统无效时，前端 SHALL 不自动选中任何系统。后端 MUST NOT 为没有默认系统的用户兜底默认 `claimcar`。MVP 不要求提供个人设置页面或管理员配置页面。`MVP` 保留英文，是软件交付阶段常用专有名词。

#### Scenario: 使用用户默认系统创建任务
- **WHEN** 用户打开 FPA 提交页，且登录用户存在有效 `default_system_code`
- **THEN** 页面默认选中该系统
- **AND** 用户仍可手动切换到其他可用系统

#### Scenario: 无默认系统
- **WHEN** 用户默认系统为空或不存在
- **THEN** 页面不自动选中任何系统
- **AND** 后端配置接口不返回默认系统或返回空默认系统
- **AND** 用户必须明确选择系统后才能提交任务

#### Scenario: 默认系统不可用
- **WHEN** 用户默认系统不在当前系统列表中
- **THEN** 页面不自动选中任何系统
- **AND** 后端不得兜底返回 `claimcar`
- **AND** 用户必须明确选择系统后才能提交任务

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

## Known Limits / 待确认点

- 首版不实现草稿保存、在线编辑结果、人工审批、多人复核、批量评估、评估结果对比、页面维护系统资料、模板版本管理和非 Markdown 输入解析。
- 目标人天只做参考、结果对照和风险提示，不得用于反推或凑值生成。
