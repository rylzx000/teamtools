## MODIFIED Requirements

### Requirement: FPA 主处理链路

系统 SHALL 按“提交评估 -> 生成 AI 请求包 -> 等待AI调用 -> 前端选择个人 Key 或公用 Key 调用模型 -> 回传 AI 响应 -> 提取 AI评估.md 和结构化 JSON -> 校验事实/路由/冻结清单 -> 生成 Excel -> 成功任务按需扣减公用额度 -> 下载结果”的流程处理任务，并把 AI 业务判断与脚本确定性生成分离。普通用户可见结果只包含摘要和 Excel 下载；`AI评估.md`、结构化 JSON 和过程 JSON 作为管理员复核或后台排查产物。

#### Scenario: 成功完成任务
- **WHEN** 前端回传合法 AI 响应
- **THEN** 后端提取并保存 `AI评估.md` 和 `AI结构化结果.json`
- **AND** 后端校验 JSON 中的变更事实、场景路由、拆分/合并决策和冻结功能点清单
- **AND** 后端基于同一组冻结清单生成 Excel 脚本输入 payload、`FPA生成过程.json` 和 `FPA工作量评估.xlsx`
- **AND** 任务完成后用户可以查看摘要并下载 Excel

#### Scenario: 个人 Key 调用成功
- **WHEN** 用户填写个人 API Key 并成功完成 FPA 任务
- **THEN** 任务调用来源记录为 `personal_key`
- **AND** 系统不得扣减该用户公用 Key 额度

#### Scenario: 公用 Key 调用成功
- **WHEN** 用户未填写个人 API Key，使用公用 Key 并成功生成 Excel
- **THEN** 任务调用来源记录为 `shared_key`
- **AND** 系统在 Excel 正式文件生成后扣减该用户 1 次公用额度
- **AND** 同一任务不得重复扣减

#### Scenario: 模型调用失败
- **WHEN** 前端调用模型失败并回传脱敏错误
- **THEN** 后端保存 `AI调用错误.json` 并将任务标记为失败
- **AND** 普通用户看到失败阶段、具体原因和建议操作
- **AND** 如该任务使用公用 Key，系统不得扣减公用额度

#### Scenario: JSON 校验失败
- **WHEN** AI 输出不是合法结构、枚举不符合契约、缺少冻结清单或冻结清单无法追溯到事实/路由
- **THEN** 任务失败且不生成 Excel
- **AND** 用户可以基于原输入复制或重新运行任务
- **AND** 如该任务使用公用 Key，系统不得扣减公用额度

#### Scenario: AI 回传后后端校验失败
- **WHEN** 前端成功调用模型并回传响应，但后端校验 AI 结构化结果失败
- **THEN** 后端返回任务状态 `failed`
- **AND** 前端提示 AI 结果校验失败或展示失败摘要
- **AND** 前端不得提示 Excel 已生成
- **AND** 如该任务使用公用 Key，系统不得扣减公用额度

#### Scenario: 冻结清单与产物一致
- **WHEN** 任务生成正式结果
- **THEN** `AI评估.md`、Excel 明细和过程 JSON 中的功能点数量、顺序、类型和 `stable_id` 必须保持一致
- **AND** 任一产物生成失败时不得进入 `completed`
- **AND** 公用额度扣减只能发生在正式结果进入 `completed` 之后
