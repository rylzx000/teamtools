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

系统 SHALL 允许用户为单个需求提交一次 FPA 评估任务，并支持系统选择、可选需求名称、粘贴文本、单个 Markdown 文件、可选目标人天和规模计数时机。

#### Scenario: 有效输入提交
- **WHEN** 用户选择一个系统，并提供粘贴文本或上传 `.md` 文件中的至少一项
- **THEN** 系统创建 FPA 任务并保存输入、上传文件和任务参数快照
- **AND** 粘贴内容和上传文件同时存在时按“粘贴文本在前、上传文件在后”合并

#### Scenario: 输入超限
- **WHEN** 粘贴文本或上传 Markdown 有效内容超过 2 万字符，或上传文件超过 256KB
- **THEN** 系统拒绝创建任务或返回参数错误
- **AND** 错误信息必须面向普通用户脱敏且可理解

#### Scenario: 需求名称为空
- **WHEN** 用户未填写需求名称
- **THEN** 系统使用上传文件名、需求文本摘要、AI/脚本总结短名称或 `FPA工作量评估-YYYYMMDD-HHmm` 生成兜底名称
- **AND** 后续脚本 payload 中的 `requirement_name` 必须有值

### Requirement: 系统资料与无资料模式

系统 MUST 根据用户选择的单一系统读取配置和精简知识包；选择其他系统或配置为空时进入无资料模式，已配置系统资料缺失时不得静默降级。

#### Scenario: 已配置系统资料可用
- **WHEN** `systems.yaml` 中的系统启用且知识包文件存在
- **THEN** 后端读取 `teamtools-system-brief.md` 用于 AI 请求包
- **AND** 前端不得直接读取服务器资料目录

#### Scenario: 其他系统或空资料目录
- **WHEN** 用户选择其他系统或系统配置明确为空资料目录
- **THEN** 任务进入无资料模式
- **AND** AI 请求包中应说明无资料模式边界

#### Scenario: 已配置资料缺失
- **WHEN** 系统配置了知识目录但精简知识包缺失或不可读
- **THEN** 任务失败并记录系统资料配置错误
- **AND** 系统不得自动降级为无资料模式

### Requirement: FPA 主处理链路

系统 SHALL 按“提交评估 -> 等待AI调用 -> 回传结果 -> 校验 JSON -> 生成 Excel -> 下载结果”的流程处理任务，并把 AI 理解与脚本确定性生成分离。

#### Scenario: 成功完成任务
- **WHEN** 前端回传合法 AI 结构化结果
- **THEN** 后端校验 JSON、生成 Excel 脚本输入 payload，并调用脚本生成 `FPA生成过程.json` 和 `FPA工作量评估.xlsx`
- **AND** 任务完成后用户可以查看摘要并下载 Excel

#### Scenario: 模型调用失败
- **WHEN** 前端调用模型失败并回传脱敏错误
- **THEN** 后端保存 `AI调用错误.json` 并将任务标记为失败
- **AND** 普通用户看到失败阶段、具体原因和建议操作

#### Scenario: JSON 校验失败
- **WHEN** AI 输出不是合法结构或枚举不符合契约
- **THEN** 任务失败且不生成 Excel
- **AND** 用户可以基于原输入复制或重新运行任务

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

系统 SHALL 在成功任务中保留 Excel 文件、AI 分析说明和生成过程 JSON，并按用户角色限制查看与下载方式。

#### Scenario: 普通用户查看成功任务
- **WHEN** 普通用户打开自己已完成的任务详情
- **THEN** 页面展示结果中值、目标命中、质量提示、`AI分析.md` 预览和 `FPA生成过程.json` 预览
- **AND** 只有 Excel 提供下载入口

#### Scenario: 管理员查看任务
- **WHEN** 管理员查看任意 FPA 任务
- **THEN** 系统可以展示提交人、失败阶段和排查摘要
- **AND** 不得暴露模型 Key、环境变量或其他敏感内容

## Known Limits / 待确认点

- 首版不实现草稿保存、在线编辑结果、人工审批、多人复核、批量评估、评估结果对比、页面维护系统资料、模板版本管理和非 Markdown 输入解析。
- 目标人天只做参考、结果对照和风险提示，不得用于反推或凑值生成。
