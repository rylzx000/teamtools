## Context

TeamTools FPA 已采用 AI 先输出结构化结果、后端校验、Excel 脚本确定性生成的主链路。新版 `fpa-skill` 将“候选/冻结功能点清单”定义为唯一评估依据，并新增数据功能与事务功能之间的双向追溯要求。当前实现已经有 `change_facts`、`routing_decisions`、`split_merge_decisions`、`frozen_items` v2 结构，但仍缺少 `linked_process_ids`、`linked_data_ids`，文档也残留旧 `items` 描述。

## Goals / Non-Goals

**Goals:**

- 让 AI prompt、schema、校验器、后端 payload、Excel 过程 JSON 和文档使用同一组冻结功能点清单。
- 让 `ILF/EIF` 的支撑过程规则可机器校验、可人工复核。
- 让 Excel 脚本保持模板填表和结构校验职责，不判断业务拆分是否充分。
- 保持普通用户结果视图简单，只暴露摘要和 Excel 下载。

**Non-Goals:**

- 不新增前端页面、普通用户下载项、数据库表或系统资料全文检索。
- 不引入多模型评测或新的模型调用方式。
- 不改历史系统资料目录和已归档 change。

## Decisions

- **新增追溯字段保持可选。** `linked_process_ids` 与 `linked_data_ids` 在 schema 中设为可选数组，默认空数组；校验器在字段存在时强校验格式和引用，并对数据功能缺少支撑过程时要求说明原因。这样兼容旧样例和已有 happy path，同时让新版 prompt 引导 AI 尽量补全。
- **后端 payload 透传完整冻结项。** 后端继续从 `structured["frozen_items"]` 构造 Excel payload `items`，不重新命名、不重排、不删减追溯字段，确保过程 JSON 能保存管理员排查所需上下文。
- **Excel 明细列不扩展。** `linked_process_ids`、`linked_data_ids` 只进入过程 JSON，不写入 Excel 明细列，避免修改模板契约和普通用户表格视图。
- **业务充分性提示降级。** `ITEM_COUNT_TOO_LOW`、`NO_ILF`、`NO_EO` 不再由 Excel 脚本生成或阻断交付；目标偏离保留为结构/结果复核提醒。业务拆分充分性回到 AI 事实、路由、拆分/合并和 `AI评估.md` 中处理。

## Risks / Trade-offs

- `linked_process_ids` 和 `linked_data_ids` 初期为可选，旧 AI 输出仍可通过；通过 prompt 和校验器数据功能规则逐步提高输出质量。
- Excel 脚本不阻断少条目结果后，业务漏拆需要依赖 AI 评估说明和人工复核；这是职责边界调整，不是放弃复核。
- 文档更新范围较多，需用 OpenSpec strict 校验和后端测试防止契约漂移。
