## MODIFIED Requirements

### Requirement: 成功结果可见性

系统 SHALL 在成功任务中向普通用户展示结果摘要并提供 Excel 下载入口；`AI分析.md` / `AI评估.md`、AI 结构化结果、生成过程 JSON 和其他排查产物 SHALL 仅作为管理员复核或后台排查用途保留。

#### Scenario: 普通用户查看成功任务
- **WHEN** 普通用户打开自己已完成的任务详情
- **THEN** 页面展示结果摘要、目标命中、质量提示摘要和 Excel 下载入口
- **AND** 只有 Excel 提供普通用户下载入口
- **AND** 页面和接口不得向普通用户展示或返回 `AI分析.md`、`AI评估.md`、完整过程 JSON、结构化 JSON、payload、服务器绝对路径、内部文件角色、原始模型错误、环境变量或模型 Key

#### Scenario: 管理员查看任务
- **WHEN** 管理员查看任意 FPA 任务
- **THEN** 系统可以展示提交人、失败阶段、事件时间线、`AI分析.md` / `AI评估.md`、AI 请求摘要、AI 结构化结果、生成过程 JSON 和排查摘要
- **AND** 不得暴露模型 Key、环境变量或其他敏感内容
