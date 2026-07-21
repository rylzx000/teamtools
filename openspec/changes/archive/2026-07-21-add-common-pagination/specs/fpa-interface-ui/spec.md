## ADDED Requirements

### Requirement: FPA 列表分页展示

系统 SHALL 在 FPA 任务列表和管理员模型配置页用户额度列表中使用统一分页控件。前端可选每页条数 MUST 为 10、20、50，并支持上一页、下一页、可点击页码、当前页禁用态和总条数展示。

#### Scenario: 任务列表分页
- **WHEN** 用户打开 FPA 任务列表
- **THEN** 前端按 `page` 和 `page_size` 请求 `/api/fpa/tasks`
- **AND** 页面展示后端返回的当前页任务
- **AND** 任务默认按创建时间倒序展示，最新任务在前

#### Scenario: 管理员额度列表分页
- **WHEN** 管理员打开模型配置页
- **THEN** 前端按 `page` 和 `page_size` 请求 `/api/admin/model-key/quotas`
- **AND** 页面展示后端返回的当前页用户额度
- **AND** 单人保存、单人重置、统一设置额度和统一重置用量仍可使用

#### Scenario: 每页条数切换
- **WHEN** 用户在分页控件中切换每页条数为 10、20 或 50
- **THEN** 前端重新请求第一页
- **AND** 不提供跳页输入框、无限滚动或复杂筛选能力
