## Why

现有 TeamTools FPA 链路要求 AI 直接输出 `items` 明细，后端校验后交给 Excel 脚本生成结果；但新版 `fpa-skill` 已调整为“变更事实清单 -> 场景路由 -> 拆分/合并决策 -> 冻结功能点清单 -> 确定性 Excel 生成”的流程。本 change 原先用于固化新版 FPA skill 工作流契约，当前已进入实现落地阶段，文档补齐用于让 OpenSpec 与已实现行为保持一致。

## What Changes

- 将 FPA AI 输出契约从“直接生成功能点明细”升级为“输出可追溯的事实清单、场景路由、拆分/合并依据和冻结功能点清单”。
- 明确系统资料精简包和 `08-FPA场景拆分字典.md` 需要支持场景路由和功能点拆分，但仍保持长度可控，不把完整系统资料全文塞入提示词。
- 调整 FPA 任务产物口径：普通用户侧保留 `AI评估.md` 和 `FPA工作量评估.xlsx`；后台保留 `AI结构化结果.json`、`FPA生成过程.json` 和必要排查摘要。
- 明确 Excel 脚本只负责确定性填充、计算、模板保真和结构校验，不再用脚本判断功能点拆分是否业务充分。
- 明确普通用户和管理员对 AI 请求包、结构化结果、过程 JSON、错误摘要和排查文件的可见性边界。
- 调整页面流程展示为简化用户流程，不展示内部 JSON、payload、路由结构或过程 JSON。
- 增加跑 AI 前的系统轻校验，减少选错系统导致的无效 token 消耗和错误结果。
- 增加用户默认系统，匹配团队成员通常长期负责固定系统的使用习惯。
- 明确 AI 结构化结果必须绑定当前任务选择系统，并对追溯编号格式做强校验。
- 覆盖 OpenSpec 契约、提示词/schema、后端任务链路、前端页面状态、Excel 脚本、测试与样例的对齐。

## Capabilities

### New Capabilities

- 无。本次沿用既有 FPA 能力规格，不新增同义 capability。

### Modified Capabilities

- `fpa-ai-contract`：调整 AI 请求包、系统资料、结构化 JSON 和校验契约，使其支持新版 `fpa-skill` 的事实清单、场景路由和冻结清单。
- `fpa-workflow`：调整任务主流程和产物保存/可见性，明确 `AI评估.md`、后台 JSON、失败排查和重新运行边界。
- `fpa-excel-output`：调整 Excel payload 与脚本职责，明确模板保真、确定性计算、结构校验和审计备注口径。
- `fpa-interface-ui`：调整提交页参数、任务详情流程展示和普通用户可见产物口径。

## Impact

- 影响文档与规格：`openspec/specs/fpa-ai-contract`、`openspec/specs/fpa-workflow`、`openspec/specs/fpa-excel-output`、`openspec/specs/fpa-interface-ui`。
- 本 change 覆盖实现文件：`data/modules/fpa/profile/skill/prompt_template.md`、`data/modules/fpa/profile/schema/result.schema.json`、`scripts/fpa/build_ai_request_package.py`、`scripts/fpa/validate_ai_result.py`、`scripts/fpa/fill_fpa_workbook.py`、`backend/app/modules/fpa/service.py`。
- 本 change 覆盖验证资产：FPA 样例 payload、AI 输出样例、Excel 生成样例、端到端任务验证。
- 本 change 不修改前端视觉设计、不新增模型供应商、不改变登录权限体系、不引入在线维护系统资料能力。
