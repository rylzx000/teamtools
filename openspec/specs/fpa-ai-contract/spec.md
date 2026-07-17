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

系统 MUST 将 `target_person_days` 作为可选参考目标进入提示词，并按“用户页面明确选择 > 模板默认值 > 平台兜底”的优先级确定最终写入 Excel 的项目特征；AI 的 `project_features` 只做分析参考，不直接落入 Excel。

#### Scenario: 目标人天参与提示词
- **WHEN** 用户填写目标人天
- **THEN** 提示词可以把它作为参考目标供 AI 做可解释校准
- **AND** AI 不得为了贴近目标无依据新增功能点、拆碎字段按钮、改变系统属性、改变冻结清单范围或输出最终人天

#### Scenario: 目标校准不改变拆分依据
- **WHEN** 目标人天处于可校准范围
- **THEN** AI 可以在事实支持范围内解释复用程度、修改类型、复杂度和规模计数时机
- **AND** 功能点是否计入、拆分或合并必须由变更事实、系统边界、场景路由和拆分/合并决策决定

#### Scenario: 项目特征落表优先级
- **WHEN** 后端生成 Excel 脚本 payload
- **THEN** 用户页面明确选择的项目特征优先写入
- **AND** 未选择的项目特征使用模板默认值
- **AND** 模板缺少默认值时才使用平台兜底值

#### Scenario: 首版开放的项目特征
- **WHEN** 用户提交 FPA 评估任务
- **THEN** 页面允许用户选择 `规模计数时机`，默认值为 `1.21 估算中期`
- **AND** 页面允许用户选择 `完整性级别`，默认值为 `1.10 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式`
- **AND** 其他 Excel 项目特征使用模板默认值

#### Scenario: AI 项目特征只做参考
- **WHEN** AI 输出的 `project_features` 与页面选择、模板默认值或平台兜底冲突
- **THEN** 最终 Excel payload 不采用 AI 值
- **AND** AI 值仅可进入 `AI评估.md` 或待复核提示

### Requirement: 系统资料蒸馏与长度控制

系统 SHALL 使用管理员维护的精简知识包作为 AI 请求包资料来源，并按蒸馏规则保留系统定位、边界、核心模块、业务链路、数据责任、外部接口、系统场景字典和 FPA 判断辅助信息。

#### Scenario: 有资料模式
- **WHEN** 已选系统配置了知识包目录且 `teamtools-system-brief.md` 可读
- **THEN** 请求包使用该精简知识包作为系统背景
- **AND** MVP 不读取 `source/` 下完整资料、不做动态片段检索

#### Scenario: 08 场景拆分字典可用
- **WHEN** 已选系统资料包包含 `08-FPA场景拆分字典.md`
- **THEN** 请求包必须把该文件作为关键上下文提供给 AI
- **AND** 提示词要求 AI 优先匹配系统场景编号、Excel 一级模块、Excel 二级模块和功能点计数项名称

#### Scenario: 08 场景拆分字典缺失
- **WHEN** 已选系统资料包缺少 `08-FPA场景拆分字典.md`
- **THEN** 任务允许进入无系统字典模式继续生成
- **AND** `AI评估.md` 和结构化 JSON 必须记录资料缺口、临时归类依据和待复核点

#### Scenario: 资料过长或证据不足
- **WHEN** 知识包超过长度上限或资料存在缺口
- **THEN** 系统记录配置错误或在请求包中标记资料缺口
- **AND** 不得静默截断造成事实缺失

### Requirement: AI 结果系统绑定与编号格式

系统 MUST 以当前任务选择的系统作为 AI 结构化结果的权威系统边界。`assessment_context.system_code` 必须等于当前任务系统编码，`assessment_context.system_name` 必须等于当前任务系统中文名，且 `frozen_items[].system` 必须等于当前任务系统中文名。系统 MUST 对所有追溯编号及引用编号执行格式强校验：`change_facts[].fact_id` 匹配 `^F-[0-9]{3}$`，`routing_decisions[].route_id` 匹配 `^R-[0-9]{3}$`，`split_merge_decisions[].decision_id` 匹配 `^D-[0-9]{3}$`，`frozen_items[].stable_id` 匹配 `^FP-[0-9]{3}$`；`routing_decisions[].fact_ids[]`、`split_merge_decisions[].route_ids[]`、`split_merge_decisions[].result_stable_ids[]`、`frozen_items[].fact_ids[]` 和 `frozen_items[].route_ids[]` 也必须符合对应格式。

#### Scenario: AI 返回其他已知系统
- **WHEN** 当前任务选择系统为 A，但 AI 结构化结果返回系统 B
- **THEN** 后端校验失败
- **AND** 即使系统 B 是已知系统也不得通过
- **AND** 后端不得生成 Excel

#### Scenario: 编号引用一致但格式非法
- **WHEN** AI 结构化结果中的事实、路由、决策或冻结项编号引用关系完整，但编号格式不是规定格式
- **THEN** 后端校验失败
- **AND** 后端不得生成 Excel

## Known Limits / 待确认点

- 当前请求包默认 provider/model 以 DeepSeek 口径为主；后续若支持多模型，应通过 OpenSpec change 明确请求格式、CORS 和密钥处理方式。
- AI 质量不作为首版可用性验收的人工准确性标准，首版重点验证流程、契约、文件生成和结果下载可用。
