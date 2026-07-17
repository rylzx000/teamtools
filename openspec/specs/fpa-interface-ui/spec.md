# fpa-interface-ui Specification

## Purpose
定义 FPA 模块 API、页面结构、状态展示、按钮权限和用户可见产物规则，确保前端交互与后端任务状态一致。

## Source Documents

- `docs/modules/fpa/05-接口设计.md`
- `docs/ui/README.md`
- `docs/ui/01-整体页面设计.md`
- `docs/ui/modules/fpa-页面设计.md`
## Requirements
### Requirement: FPA API 资源边界

系统 SHALL 通过 FPA 任务资源接口完成系统查询、任务创建、AI 请求包获取、AI 结果回传、任务列表、任务详情、取消、重新运行和 Excel 下载。

#### Scenario: 查询可选系统
- **WHEN** 前端调用 `GET /api/fpa/systems`
- **THEN** 后端只返回启用系统的编码、名称、类型和排序信息
- **AND** 响应不得包含 `knowledge_dir` 或服务器真实资料路径

#### Scenario: 创建任务
- **WHEN** 前端提交 `POST /api/fpa/tasks`
- **THEN** 后端校验输入、创建任务、生成 AI 请求包并返回任务详情地址
- **AND** 前端跳转到任务详情页

#### Scenario: 下载 Excel
- **WHEN** 用户请求 `GET /api/fpa/tasks/{id}/download/excel`
- **THEN** 后端校验任务权限和文件可下载状态
- **AND** 不允许通过该接口下载 `AI分析.md`、`FPA生成过程.json`、任务日志或其他过程文件

### Requirement: 平台壳与 FPA 页面结构

系统 SHALL 使用统一平台壳承载登录、模块导航、顶部用户信息、内容区和公共错误页；FPA 首版包含任务列表、提交评估和任务详情三个页面。

#### Scenario: 平台导航
- **WHEN** 用户登录后进入平台
- **THEN** 页面展示 TeamTools 平台名、当前模块、当前用户、角色和退出入口
- **AND** 左侧导航只展示已启用模块

#### Scenario: FPA 页面切换
- **WHEN** 用户在 FPA 模块内操作
- **THEN** 可以在 `/fpa/tasks`、`/fpa/submit` 和 `/fpa/tasks/:id` 间切换
- **AND** 当前模块和当前页面应有明确选中态

### Requirement: 提交评估页交互

系统 MUST 在提交评估页按后端接口和输入规则控制表单状态，提交成功后进入任务详情页等待浏览器调用模型。首版页面应保持输入简洁，只开放系统选择、需求输入、目标人天、`规模计数时机` 和 `完整性级别`。

#### Scenario: 表单不可提交
- **WHEN** 系统未选择，或粘贴内容与上传文件均为空，或目标人天格式非法
- **THEN** 提交按钮不可用或提交返回参数错误
- **AND** 页面显示字段级提示

#### Scenario: 规模计数时机下拉
- **WHEN** 用户打开提交评估页
- **THEN** 页面展示 `规模计数时机` 下拉框
- **AND** 下拉选项文字包含系数前缀：`1.39 估算早期`、`1.21 估算中期`、`1.10 估算晚期`、`1.00 项目交付后及运维阶段`
- **AND** 默认选中 `1.21 估算中期`

#### Scenario: 完整性级别下拉
- **WHEN** 用户打开提交评估页
- **THEN** 页面展示 `完整性级别` 下拉框
- **AND** 下拉选项文字包含系数前缀：`1.00 没有明确的完整性级别或等级为C/D`、`1.10 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式`、`1.30 完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施`
- **AND** 默认选中 `1.10 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式`

#### Scenario: 默认系统选中
- **WHEN** 用户打开提交评估页，且登录态返回有效的 `default_system_code`
- **THEN** 页面优先选中该默认系统
- **AND** 默认系统为空、不可用或不在系统列表中时，页面回退选中第一个可用系统

#### Scenario: 成功提交
- **WHEN** 任务创建成功
- **THEN** 页面跳转到任务详情页
- **AND** 详情页展示任务已创建、AI 请求包已生成、等待浏览器调用模型

### Requirement: 任务列表与详情状态展示

系统 SHALL 以后端状态、权限字段和产物可见性驱动页面展示；列表页默认手动刷新，详情页可以按约定轮询。页面展示流程 SHALL 使用面向用户的简化阶段，不展示后台 JSON、payload、路由结构或过程文件。

#### Scenario: 任务列表筛选
- **WHEN** 用户筛选“进行中”“已完成”“失败”或“已取消”
- **THEN** 页面按后端状态枚举展示对应任务
- **AND** 列表页不自动轮询，只提供手动刷新

#### Scenario: 详情页 AI 调用区
- **WHEN** 任务处于 `waiting_ai_call`
- **THEN** 页面展示 AI 请求包获取、API Key 本地填写和浏览器调用模型入口
- **AND** API Key 不上传后端、不写入请求包、不明文展示已保存值

#### Scenario: 系统轻校验提示
- **WHEN** 详情页 AI 调用区获取 AI 请求包，且后端返回 `system_relevance.status` 为 `warning` 或 `blocked`
- **THEN** 页面展示后端规则校验生成的系统可能选错提示
- **AND** 页面提供“仍然继续”操作
- **AND** 系统轻校验不得调用大模型、不消耗模型 token

#### Scenario: 用户确认继续后不重复拦截
- **WHEN** 用户已对当前任务的系统轻校验提示确认仍然继续
- **THEN** 页面再次获取 AI 请求包或调用模型时不重复拦截
- **AND** 页面仍以当前任务选择系统作为最终权威口径
- **AND** 后端 AI 结果系统绑定校验仍必须执行

#### Scenario: 页面简化阶段
- **WHEN** 用户查看任务详情
- **THEN** 页面以 `提交需求`、`AI评估中`、`生成结果中`、`评估完成`、`评估失败` 或 `已取消` 表达任务进度
- **AND** 页面不得展示 `change_facts`、`routing_decisions`、`split_merge_decisions`、`frozen_items`、payload 或完整过程 JSON

#### Scenario: 详情页结果展示
- **WHEN** 任务已完成
- **THEN** 页面展示摘要条、质量提示、`AI评估.md` 预览和 Excel 下载入口
- **AND** 结果字段来自后端和 `FPA生成过程.json` 的后台汇总，不得从 Excel 公式缓存读取
- **AND** 普通用户不得下载或查看 `AI结构化结果.json`、`FPA生成过程.json`、AI 请求包、脚本 payload、任务日志或其他排查文件

### Requirement: 按钮与权限展示

系统 MUST 将按钮状态作为展示辅助，并由后端接口执行最终权限校验。

#### Scenario: 下载按钮
- **WHEN** 任务已完成且后端返回 `can_download_excel = true`
- **THEN** 页面展示下载 Excel 入口
- **AND** 后端仍必须在下载接口校验当前用户权限

#### Scenario: 取消按钮
- **WHEN** 后端返回 `can_cancel = true`
- **THEN** 页面展示取消入口
- **AND** 请求到达后端后仍必须校验任务状态和用户权限

## Known Limits / 待确认点

- 接口文档建议任务详情页每 2-3 秒轮询，现有页面实现是否完全采用该频率需以代码和实际测试为准。
- FPA 页面设计引用 Open Design 原型，但 OpenSpec 只保留行为契约，不固化所有视觉细节。
