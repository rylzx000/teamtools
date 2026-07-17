## MODIFIED Requirements

### Requirement: AI 输出只包含业务判断

系统 SHALL 约束 AI 一次响应包含面向用户的 `AI评估.md` 内容和面向后端的 `AI结构化结果.json` 内容；AI 不得输出 Excel 文件、模板路径、输出路径、公式、人天计算结果或其他确定性生成字段。

#### Scenario: 合法 AI 响应
- **WHEN** AI 输出响应
- **THEN** 响应包含可提取的 `AI评估.md` 内容和 `AI结构化结果.json` 内容
- **AND** `AI评估.md` 面向普通用户说明需求理解、系统资料使用情况、拆分过程、关键假设、目标校准、待复核点和功能点摘要
- **AND** `AI结构化结果.json` 包含 `assessment_context`、`change_facts`、`routing_decisions`、`split_merge_decisions` 和 `frozen_items`
- **AND** `frozen_items` 是后续 `AI评估.md`、Excel 和过程 JSON 的唯一功能点明细来源
- **AND** `change_facts[].fact_id`、`routing_decisions[].route_id`、`split_merge_decisions[].decision_id` 和 `frozen_items[].stable_id` 必须在各自集合内唯一，且符合规定编号格式

#### Scenario: AI 响应提取失败
- **WHEN** 后端无法从 AI 响应中提取 `AI评估.md` 或合法 JSON
- **THEN** 任务进入失败状态
- **AND** 不得生成 Excel

#### Scenario: 合法冻结功能点明细
- **WHEN** AI 输出 `frozen_items`
- **THEN** 每条明细包含 `stable_id`、系统中文名、模块层级、功能描述、计数项名称、类别、复用程度、修改类型和判断依据
- **AND** 每条明细必须包含非空 `fact_ids` 和非空 `route_ids`，并引用已存在的 `change_facts[].fact_id` 和 `routing_decisions[].route_id`
- **AND** 命中系统场景字典时，每条明细必须包含 `system_scene_ids` 或等价系统场景编号，以便追溯系统字典映射
- **AND** `category`、`reuse`、`change_type`、`system` 必须使用契约允许值

#### Scenario: 字段级追溯校验失败
- **WHEN** AI 输出存在重复编号、缺少 `fact_ids` 或 `route_ids`、引用不存在的事实/路由编号，或命中系统字典但缺少系统场景编号
- **THEN** 后端校验失败
- **AND** 不得保存为成功的 `AI评估.md` 或进入 Excel 生成阶段

#### Scenario: 禁止 AI 输出计算字段
- **WHEN** AI 输出包含 `template_path`、`output_path`、`target_work_days`、`target_hit`、`adjusted_work_days_middle`、`ufp`、`us` 或其他 Excel 计算字段
- **THEN** 后端校验失败
- **AND** 不得把该输出传给 Excel 生成脚本

#### Scenario: 禁止填表阶段改变业务判断
- **WHEN** AI 已输出冻结功能点清单
- **THEN** 后端和 Excel 脚本不得在生成阶段临时新增、删除、改名、重排或改变功能点类型
- **AND** 如需调整业务拆分，必须重新生成或重新提交 AI 结构化结果

## ADDED Requirements

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

## MODIFIED Requirements

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
