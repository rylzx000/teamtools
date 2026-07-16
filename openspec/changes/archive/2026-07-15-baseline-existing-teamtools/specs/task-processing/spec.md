# task-processing Specification

## Purpose
定义 TeamTools 统一任务、文件、事件、运行目录和数据库口径，确保 FPA 与后续模块可以共享任务生命周期、权限、失败排查和结果产物管理。

## Source Documents

- `docs/architecture/02-数据与文件存储.md`
- `docs/architecture/03-任务处理与结果生成设计.md`
- `docs/architecture/05-数据库设计.md`
- `docs/deployment/01-本地开发.md`
- `docs/deployment/02-服务器部署.md`

## Requirements

### Requirement: 统一任务状态流转

系统 SHALL 使用统一任务表记录模块、标题、提交人、状态、关键时间、取消标记、失败摘要和重新运行来源，并用模块扩展表保存模块专属字段。

#### Scenario: FPA 任务创建
- **WHEN** 用户提交 FPA 评估任务
- **THEN** 系统创建 `tasks` 主记录和 `fpa_task_details` 扩展记录
- **AND** 初始可执行状态进入 `waiting_ai_call`

#### Scenario: 后端接收 AI 成功结果
- **WHEN** 前端回传模型成功结果
- **THEN** 任务依次进入 `validating_result` 和 `generating_result`
- **AND** 校验与结果生成成功后进入 `completed`

#### Scenario: 校验或生成失败
- **WHEN** JSON 校验、脚本执行或文件处理失败
- **THEN** 任务进入 `failed`
- **AND** 系统记录普通用户可见的脱敏摘要和管理员可见的排查详情

### Requirement: 任务文件按角色索引

系统 MUST 将任务输入、AI 请求与响应、生成过程、正式输出、日志和错误详情保存为任务文件，并用 `task_files.file_role` 索引其角色、相对路径和可见性。

#### Scenario: 保存 FPA 输入与 AI 产物
- **WHEN** FPA 任务创建并完成模型调用
- **THEN** 系统在 `data/tasks/fpa/{task_id}/input/` 保存输入和参数快照
- **AND** 在 `data/tasks/fpa/{task_id}/ai/` 保存请求包、摘要、原始响应、调用错误、分析说明或结构化结果

#### Scenario: 保存正式输出
- **WHEN** FPA Excel 生成成功
- **THEN** 系统在 `data/tasks/fpa/{task_id}/output/` 保存 `FPA生成过程.json` 和 `FPA工作量评估.xlsx`
- **AND** 只有正式文件生成后才登记为可见或可下载产物

### Requirement: 原子落盘与临时文件

系统 SHALL 对关键产物先写入 `.tmp` 临时文件，成功后再改名为正式文件；失败时不得把临时文件登记为普通用户可见产物。

#### Scenario: 生成过程文件成功落盘
- **WHEN** 脚本生成 `FPA生成过程.json`
- **THEN** 系统先写入临时文件并在成功后原子替换为正式文件
- **AND** 文件索引只登记正式路径

#### Scenario: 文件生成失败
- **WHEN** 临时文件写入、校验或重命名失败
- **THEN** 任务进入失败状态
- **AND** 普通用户不能直接查看临时文件，管理员可以按日志排查

### Requirement: 权限与任务事件

系统 MUST 以后端权限判断作为最终依据，并记录任务创建、请求包生成、请求包获取、AI 结果回传、校验、生成、取消、失败、完成和重新运行事件。

#### Scenario: 普通用户查询任务
- **WHEN** 普通用户访问任务列表、详情、取消、重新运行或下载接口
- **THEN** 后端按 `tasks.created_by` 限制只能访问自己的任务
- **AND** 前端按钮隐藏或置灰不得作为权限依据

#### Scenario: 管理员排查任务
- **WHEN** 管理员查看任务详情
- **THEN** 系统可以展示更完整的失败阶段、事件时间线和排查摘要
- **AND** 大体积日志仍应通过文件系统保存并由文件索引关联

## Known Limits / 待确认点

- SQLite 是 MVP 口径；推广到部门或并发上升时，需要以 OpenSpec change 明确 PostgreSQL 迁移范围。
- 当前文档中存在“首版不需要独立后台任务进程”和代码已有 Worker 进程并存的描述，后续变更需明确 Worker 在实际链路中的职责。
