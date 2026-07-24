## MODIFIED Requirements

### Requirement: 三类 JSON 边界

系统 MUST 区分 `AI结构化结果.json`、Excel 脚本输入 payload 和 `FPA生成过程.json`，不得要求 AI 直接输出模板路径、输出路径、目标命中、人天结果或 Excel 单元格信息。

#### Scenario: 后端生成脚本 payload
- **WHEN** AI 结构化结果通过校验
- **THEN** 后端从冻结功能点清单映射生成脚本字段 `items`，并合并任务配置、模板配置、输出路径、目标人天、`规模计数时机` 和 `完整性级别` 生成一次性脚本 payload
- **AND** 将平台字段 `target_person_days` 映射为脚本 payload 的 `target_work_days`
- **AND** 脚本 payload 不作为普通用户可见或可下载产物
- **AND** `items` 只是冻结功能点清单进入脚本的字段名转换，必须保留 `stable_id`、`fact_ids`、`route_ids`、`system_scene_ids`、`linked_process_ids` 和 `linked_data_ids`，不得代表重新生成、重新排序或重新判断功能点

#### Scenario: 脚本生成过程 JSON
- **WHEN** Excel 脚本运行成功
- **THEN** 脚本输出 `FPA生成过程.json`
- **AND** 过程 JSON 包含标准化明细、`stable_id`、`fact_ids`、`route_ids`、`system_scene_ids`、`linked_process_ids`、`linked_data_ids`、计算结果、目标命中、结构提醒、校验门禁和脱敏输出摘要
- **AND** 过程 JSON 作为后台排查产物，不作为普通用户下载文件

### Requirement: 功能点明细与备注规范

系统 MUST 将冻结功能点清单写入模板约定列，并保证备注具备可审计的类型、复用和修改依据。

#### Scenario: 明细写入
- **WHEN** payload 包含一组 `items`
- **THEN** 脚本将系统、模块层级、功能描述、计数项、类别、复用程度、修改类型和备注写入对应明细列
- **AND** `items` 的数量、顺序、名称、类型和模块必须与冻结功能点清单一致
- **AND** 公式列只允许保留、复制或平移公式，不写业务值
- **AND** `linked_process_ids` 和 `linked_data_ids` 只保留到过程 JSON，不新增写入 Excel 明细列

#### Scenario: 备注兜底
- **WHEN** AI 输出备注缺少三段式依据
- **THEN** 脚本根据 `category`、`reuse`、`change_type`、功能描述和原始备注生成兜底三段式备注
- **AND** 备注必须包含类型依据、复用依据和修改类型依据，或包含兼容旧口径的“类别原因”“复用原因”和“修改类型原因”
- **AND** 原始备注中的关联过程或关联数据说明必须保留，不得被兜底备注覆盖丢失

### Requirement: 计算结果与页面展示

系统 MUST 由脚本按模板公式口径同步计算页面需要展示的关键结果，并写入 `FPA生成过程.json`；页面不得读取 `.xlsx` 公式缓存。

#### Scenario: 结构质量提示
- **WHEN** 备注缺失、目标偏差、模板结构异常、允许值异常或公式保护异常
- **THEN** 脚本或后端生成结构质量提示
- **AND** 质量提示用于风险提醒，不默认阻止已成功生成的 Excel 下载
- **AND** `ITEM_COUNT_TOO_LOW`、`NO_ILF` 和 `NO_EO` 不得导致 `quality_gate.status = failed`

#### Scenario: 禁止脚本业务补点
- **WHEN** 脚本生成 Excel
- **THEN** 脚本不得根据核心系统、需求等级、关键词、目标人天、条目数量、类型分布或复用比例新增、删除、拆分、合并、改变功能点或判断功能点拆分是否充分
- **AND** 功能点拆分是否充分由 AI 结构化结果中的事实、路由和拆分/合并决策负责
