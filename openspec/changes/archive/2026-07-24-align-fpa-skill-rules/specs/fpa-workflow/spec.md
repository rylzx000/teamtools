## MODIFIED Requirements

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
