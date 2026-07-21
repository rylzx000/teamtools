## ADDED Requirements

### Requirement: 管理员额度分页查询

系统 SHALL 为管理员用户额度列表提供分页查询。接口 MUST 使用统一 `page` / `page_size` 请求参数和统一分页响应结构，并保持普通用户禁止访问管理员额度接口。

#### Scenario: 额度列表分页排序
- **WHEN** 管理员分页查询用户额度列表
- **THEN** 后端默认按管理员优先排序
- **AND** 同一角色内按用户名或展示名稳定排序
- **AND** 响应包含当前页用户额度和统一分页元数据

#### Scenario: 普通用户禁止分页查询额度
- **WHEN** 普通用户请求 `/api/admin/model-key/quotas?page=1&page_size=20`
- **THEN** 后端拒绝访问
- **AND** 响应不得包含任何用户额度列表
