## Why

新版 `fpa-skill` 已把冻结功能点清单、系统场景字典命名、数据功能支撑过程和普通用户/管理员可见性边界收紧。TeamTools 现有 FPA 主链路已可用，但提示词、AI JSON 契约、校验脚本、Excel 过程 JSON 和文档仍存在旧 `items` 口径或业务充分性门禁残留，容易导致 AI 输出与 Excel 生成依据不一致。

## What Changes

- 将提示词模板更新为“冻结清单唯一依据”口径，命中系统 `08-FPA场景拆分字典.md` 时要求原样使用 `Excel一级模块`、`Excel二级模块` 和 `功能点计数项名称`。
- 在 AI 输出 schema 和校验脚本中支持 `frozen_items[].linked_process_ids`、`frozen_items[].linked_data_ids`，并校验 `stable_id` 格式和引用有效性。
- 强化 `ILF/EIF` 数据功能支撑过程校验：缺少关联过程时必须在备注或 `review_notes` 中说明既有过程、资料不足、列入复核或无法明确支撑过程等原因。
- 调整 Excel 生成脚本：过程 JSON 保留新增追溯字段，Excel 明细不新增列；业务拆分充分性提示不再阻断交付。
- 检查并补齐后端从 `frozen_items` 到 Excel payload 的追溯字段透传。
- 同步 FPA 文档和 OpenSpec 规格，清理旧 `items` 契约描述，明确普通用户只看摘要和 Excel 下载，排查产物仅供管理员或后台使用。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `fpa-ai-contract`: AI 输出契约从旧 `items` 口径统一到 `change_facts`、`routing_decisions`、`split_merge_decisions`、`frozen_items`，并补充数据功能双向追溯规则。
- `fpa-workflow`: 主链路要求 `AI评估.md`、Excel payload 和过程 JSON 均来自同一组 `frozen_items`，普通用户和管理员可见性边界保持清晰。
- `fpa-excel-output`: Excel 脚本只做确定性填表和结构校验，不根据条目数量、类型分布或核心系统判断业务拆分是否充分。

## Impact

- 影响资源文件：`data/modules/fpa/profile/skill/prompt_template.md`、`data/modules/fpa/profile/schema/result.schema.json`。
- 影响脚本：`scripts/fpa/validate_ai_result.py`、`scripts/fpa/fill_fpa_workbook.py`。
- 影响后端映射：`backend/app/modules/fpa/service.py`。
- 影响测试：`backend/tests/test_fpa_mvp.py`。
- 影响文档和规格：FPA 模块文档、`openspec/specs/fpa-ai-contract/spec.md`、`openspec/specs/fpa-workflow/spec.md`、`openspec/specs/fpa-excel-output/spec.md`。
