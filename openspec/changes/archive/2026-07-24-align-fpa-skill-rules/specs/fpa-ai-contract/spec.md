## MODIFIED Requirements

### Requirement: AI 输出只包含业务判断

系统 SHALL 约束 AI 结构化 JSON 只输出需求名称建议、评估上下文、项目特征参考、变更事实、场景路由、拆分/合并决策、冻结功能点清单和复核提示。冻结功能点清单 SHALL 是 `AI评估.md`、Excel payload 和过程 JSON 的唯一明细依据；系统不得恢复旧 `items` 顶层契约。`AI`、`JSON`、`Excel` 保留英文，是既有能力、数据格式和办公软件名称专有名词。

#### Scenario: 合法 AI 冻结清单
- **WHEN** AI 输出 `frozen_items`
- **THEN** 每条冻结项包含系统中文名、模块层级、功能描述、计数项名称、类别、复用程度、修改类型、判断依据、`fact_ids` 和 `route_ids`
- **AND** `category`、`reuse`、`change_type`、`system` 必须使用契约允许值
- **AND** `fact_ids` 和 `route_ids` 必须引用已存在的变更事实和场景路由

#### Scenario: 冻结清单追溯字段
- **WHEN** AI 输出 `frozen_items[].linked_process_ids` 或 `frozen_items[].linked_data_ids`
- **THEN** 字段必须是数组，元素必须匹配 `^FP-[0-9]{3}$`
- **AND** 每个引用必须指向同一组 `frozen_items` 中已存在的 `stable_id`
- **AND** `linked_process_ids` 表示数据功能关联的事务功能，`linked_data_ids` 表示事务功能维护或引用的数据功能

#### Scenario: 禁止 AI 输出计算字段
- **WHEN** AI 输出包含 `template_path`、`output_path`、`target_work_days`、`target_hit`、`adjusted_work_days_middle`、`ufp`、`us` 或其他 Excel 计算字段
- **THEN** 后端校验失败
- **AND** 不得把该输出传给 Excel 生成脚本

### Requirement: 系统资料蒸馏与长度控制

系统 SHALL 使用管理员维护的精简知识包作为 AI 请求包资料来源，并按蒸馏规则保留系统定位、边界、核心模块、业务链路、数据责任、外部接口、系统场景字典和 FPA 判断辅助信息。

#### Scenario: 08 场景拆分字典可用
- **WHEN** 已选系统资料包包含 `08-FPA场景拆分字典.md`
- **THEN** 请求包必须把该文件作为关键上下文提供给 AI
- **AND** 提示词要求 AI 优先匹配系统场景编号
- **AND** 命中系统字典时，冻结清单、Excel payload 和过程 JSON 中的 `Excel一级模块`、`Excel二级模块` 和 `功能点计数项名称` 必须原样使用系统字典值

### Requirement: AI 结果系统绑定与编号格式

系统 MUST 以当前任务选择的系统作为 AI 结构化结果的权威系统边界。`assessment_context.system_code` 必须等于当前任务系统编码，`assessment_context.system_name` 必须等于当前任务系统中文名，且 `frozen_items[].system` 必须等于当前任务系统中文名。系统 MUST 对所有追溯编号及引用编号执行格式强校验：`change_facts[].fact_id` 匹配 `^F-[0-9]{3}$`，`routing_decisions[].route_id` 匹配 `^R-[0-9]{3}$`，`split_merge_decisions[].decision_id` 匹配 `^D-[0-9]{3}$`，`frozen_items[].stable_id` 匹配 `^FP-[0-9]{3}$`；`routing_decisions[].fact_ids[]`、`split_merge_decisions[].route_ids[]`、`split_merge_decisions[].result_stable_ids[]`、`frozen_items[].fact_ids[]`、`frozen_items[].route_ids[]`、`frozen_items[].linked_process_ids[]` 和 `frozen_items[].linked_data_ids[]` 也必须符合对应格式。

#### Scenario: 数据功能缺少支撑过程说明
- **WHEN** `frozen_items[]` 中 `category` 为 `ILF` 或 `EIF`，且 `linked_process_ids` 为空或缺失
- **THEN** 后端校验必须要求该条 `remark` 说明既有过程、资料不足、列入复核、无法明确支撑过程或不硬补事务功能等原因
- **AND** 如果通过 `review_notes` 说明，则对应提示必须包含该条 `stable_id` 或 `count_item_name`，且说明上述原因
- **AND** 缺少说明时校验失败

#### Scenario: 事务功能关联数据悬空
- **WHEN** `EI`、`EO` 或 `EQ` 条目填写 `linked_data_ids`
- **THEN** 每个引用必须指向已存在的 `ILF` 或 `EIF` 数据功能条目
- **AND** 引用不存在或指向事务功能时校验失败
