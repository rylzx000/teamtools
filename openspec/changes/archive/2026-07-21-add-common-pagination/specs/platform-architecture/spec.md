## ADDED Requirements

### Requirement: 公共分页响应协议

系统 SHALL 提供可复用的后端分页能力，用于平台内列表接口统一解析 `page` 和 `page_size` 参数、限制页大小、计算 `LIMIT/OFFSET` 并返回统一分页元数据。默认 `page = 1`，默认 `page_size = 20`，`page_size` 最大值为 100。

#### Scenario: 默认分页参数
- **WHEN** 列表接口未传入 `page` 或 `page_size`
- **THEN** 后端使用 `page = 1` 和 `page_size = 20`
- **AND** 响应包含 `items`、`total`、`page`、`page_size`、`pages`、`has_next` 和 `has_prev`

#### Scenario: 页大小上限
- **WHEN** 客户端传入 `page_size` 大于 100
- **THEN** 后端将实际 `page_size` 限制为 100
- **AND** `limit`、`offset` 和响应元数据均以限制后的值计算

#### Scenario: 分页元数据计算
- **WHEN** 后端已知总数、当前页和页大小
- **THEN** `pages` 按总数向上取整计算，空列表总页数为 0
- **AND** `has_prev` 仅在当前页大于 1 时为 `true`
- **AND** `has_next` 仅在当前页小于总页数时为 `true`
