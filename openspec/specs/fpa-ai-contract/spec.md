# fpa-ai-contract Specification

## Purpose
定义 FPA AI 请求包、提示词合成、系统资料读取、AI 输出 JSON、校验和敏感信息边界，确保 AI 只做业务判断，确定性计算和 Excel 生成由后端与脚本完成。

## Source Documents

- `docs/modules/fpa/07-AI输出与提示词契约设计.md`
- `docs/modules/fpa/09-系统资料蒸馏规则.md`
- `docs/modules/fpa/10-AI请求包与提示词合成设计.md`
- `data/modules/fpa/profile/README.md`
- `data/modules/fpa/profile/profile.yaml`
- `data/modules/fpa/profile/schema/result.schema.json`

## Requirements

### Requirement: AI 请求包由后端生成

系统 SHALL 由后端读取用户输入、系统配置、系统知识包、提示词模板、JSON 契约和页面参数，生成任务级 AI 请求包快照。

#### Scenario: 请求包生成成功
- **WHEN** FPA 任务创建且所需资源存在
- **THEN** 后端生成 `AI请求包.json` 和 `AI请求摘要.json`
- **AND** 请求包保存后不随资源文件后续修改自动变化

#### Scenario: 模板或契约缺失
- **WHEN** 提示词模板、JSON schema 或必要系统知识包缺失
- **THEN** 任务失败并记录配置错误
- **AND** 系统不得使用隐藏默认提示词继续执行

### Requirement: 前后端模型调用职责分离

系统 MUST 让前端按后端请求包执行外部模型调用，并把原始响应、结构化 JSON、分析说明或调用错误回传给后端。

#### Scenario: messages 格式调用
- **WHEN** `AI请求包.json` 的 `request_format` 为 `messages`
- **THEN** 前端只向模型发送 `messages` 和必要生成参数
- **AND** 不得把 `metadata`、任务路径、排查字段或请求摘要发送给模型

#### Scenario: plain_prompt 格式调用
- **WHEN** `request_format` 为 `plain_prompt`
- **THEN** 前端只发送后端生成的完整文本提示词
- **AND** 不得同时发送 `messages` 与 `plain_prompt` 导致重复上下文

### Requirement: AI 输出只包含业务判断

系统 SHALL 约束 AI 结构化 JSON 只输出需求名称建议、评估上下文、项目特征参考、功能点明细、分析说明、未计数项、质量提示、覆盖说明和不确定点。

#### Scenario: 合法 AI 明细
- **WHEN** AI 输出 `items`
- **THEN** 每条明细包含系统中文名、模块层级、功能描述、计数项名称、类别、复用程度、修改类型和判断依据
- **AND** `category`、`reuse`、`change_type`、`system` 必须使用契约允许值

#### Scenario: 禁止 AI 输出计算字段
- **WHEN** AI 输出包含 `template_path`、`output_path`、`target_work_days`、`target_hit`、`adjusted_work_days_middle`、`ufp`、`us` 或其他 Excel 计算字段
- **THEN** 后端校验失败
- **AND** 不得把该输出传给 Excel 生成脚本

### Requirement: 目标人天和项目特征优先级

系统 MUST 将 `target_person_days` 作为可选参考目标进入提示词，并由页面参数、平台默认值、模板默认值和 AI 参考值按优先级合并项目特征。

#### Scenario: 目标人天参与提示词
- **WHEN** 用户填写目标人天
- **THEN** 提示词可以把它作为参考目标供 AI 做可解释校准
- **AND** AI 不得为了贴近目标无依据新增功能点、拆碎字段按钮、改变系统属性或输出最终人天

#### Scenario: 项目特征冲突
- **WHEN** AI 输出的项目特征与页面选择冲突
- **THEN** 页面选择值优先
- **AND** AI 的 `project_features` 仅作为分析参考，不作为最终 Excel 参数来源

### Requirement: 系统资料蒸馏与长度控制

系统 SHALL 使用管理员维护的精简知识包作为 AI 请求包资料来源，并按蒸馏规则保留系统定位、边界、核心模块、业务链路、数据责任、外部接口和 FPA 判断辅助信息。

#### Scenario: 有资料模式
- **WHEN** 已选系统配置了知识包目录且 `teamtools-system-brief.md` 可读
- **THEN** 请求包使用该精简知识包
- **AND** MVP 不读取 `source/` 下完整资料、不做动态片段检索

#### Scenario: 资料过长或证据不足
- **WHEN** 知识包超过长度上限或资料存在缺口
- **THEN** 系统记录配置错误或在请求包中标记资料缺口
- **AND** 不得静默截断造成事实缺失

## Known Limits / 待确认点

- 当前请求包默认 provider/model 以 DeepSeek 口径为主；后续若支持多模型，应通过 OpenSpec change 明确请求格式、CORS 和密钥处理方式。
- AI 质量不作为首版可用性验收的人工准确性标准，首版重点验证流程、契约、文件生成和结果下载可用。
