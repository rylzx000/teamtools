# model-key-quota Specification

## Purpose
TBD - created by archiving change shared-frontend-model-key-quota. Update Purpose after archive.
## Requirements
### Requirement: 公用模型配置

系统 MUST 支持管理员配置团队公用模型调用参数，包括启用开关、模型供应商、API 地址、模型名称、公用 API Key 和默认个人额度。公用 API Key 当前允许由后端保存并按受控接口下发到浏览器，但不得写入前端代码、普通日志或普通用户任务响应。

`API Key`、`DeepSeek` 保留英文，是第三方接口凭证和模型供应商专有名词。

#### Scenario: 管理员保存公用 Key 配置
- **WHEN** 管理员提交公用模型配置
- **THEN** 系统保存启用状态、供应商、API 地址、模型名称、公用 API Key 和默认个人额度
- **AND** 默认个人额度缺省值为 10，且管理员可以修改
- **AND** 页面后续只显示 Key 已配置状态或掩码状态，不默认回显完整明文 Key

#### Scenario: 普通用户不能查看公用 Key 配置
- **WHEN** 普通用户请求公用模型配置管理接口
- **THEN** 系统拒绝访问
- **AND** 响应不得包含公用 API Key 明文、掩码或配置详情

#### Scenario: 公用 Key 关闭
- **WHEN** 管理员关闭公用 Key
- **THEN** 普通用户未填写个人 API Key 时不得领取公用 Key 调用配置
- **AND** 页面提示用户输入可用的 API Key

### Requirement: 用户公用额度

系统 MUST 为每个用户维护独立的公用 Key 额度，包括是否启用、总额度、已用次数、剩余次数和最近成功使用时间。新建额度记录 MUST 使用当前默认个人额度；修改默认个人额度不得自动修改已有用户额度。

#### Scenario: 新用户额度初始化
- **WHEN** 用户首次需要公用 Key 额度记录，且该用户尚无额度记录
- **THEN** 系统按当前默认个人额度创建额度记录
- **AND** 初始已用次数为 0
- **AND** 初始启用状态为允许使用公用 Key

#### Scenario: 管理员单独调整用户额度
- **WHEN** 管理员修改某个用户的总额度或启用状态并保存
- **THEN** 系统只更新该用户额度记录
- **AND** 剩余次数按 `max(总额度 - 已用次数, 0)` 计算

#### Scenario: 管理员单独重置用户用量
- **WHEN** 管理员对某个用户执行重置
- **THEN** 系统将该用户已用次数清零
- **AND** 记录重置时间和操作管理员

#### Scenario: 管理员统一设置额度
- **WHEN** 管理员输入新的统一额度并确认
- **THEN** 系统将所有用户的总额度设置为该值
- **AND** 不自动清零已用次数，除非管理员另行执行统一重置

#### Scenario: 管理员统一重置用量
- **WHEN** 管理员确认统一重置用量
- **THEN** 系统将所有用户的已用次数清零
- **AND** 记录统一重置时间和操作管理员

### Requirement: 公用 Key 调用配置领取

系统 SHALL 在用户未填写个人 API Key 时，允许前端为当前 FPA 任务领取公用 Key 调用配置。领取接口 MUST 校验登录用户、任务访问权限、任务状态、公用 Key 启用状态和用户剩余额度。

#### Scenario: 领取公用 Key 成功
- **WHEN** 普通用户未填写个人 API Key，当前任务可调用模型，公用 Key 已启用且该用户剩余额度大于 0
- **THEN** 后端返回模型供应商、API 地址、模型名称、公用 API Key 和调用票据
- **AND** 后端记录本次任务调用来源为 `shared_key`
- **AND** 领取本身不得扣减已用次数

#### Scenario: 公用额度已用完
- **WHEN** 普通用户未填写个人 API Key，且个人公用额度剩余次数为 0
- **THEN** 系统不得返回公用 API Key
- **AND** 前端提示 `公用apikey个人用量已用完，请输入可用的apikey`

#### Scenario: 使用个人 Key
- **WHEN** 普通用户填写个人 API Key 并调用模型
- **THEN** 前端不得领取公用 Key 调用配置
- **AND** 后端记录本次任务调用来源为 `personal_key`
- **AND** 该任务不得消耗公用 Key 额度

### Requirement: 成功后扣减公用额度

系统 MUST 仅在任务使用公用 Key 且最终成功生成 Excel 后扣减用户公用额度。AI 调用失败、AI 结果校验失败、Excel 生成失败或任务取消不得扣减公用额度。

#### Scenario: 公用 Key 成功生成 Excel 后扣减
- **WHEN** FPA 任务调用来源为 `shared_key`，且任务状态进入 `completed`
- **THEN** 系统扣减提交用户 1 次公用额度
- **AND** 记录扣减时间、任务 ID 和调用票据

#### Scenario: 失败任务不扣减
- **WHEN** FPA 任务调用来源为 `shared_key`，但任务进入 `failed` 或 `cancelled`
- **THEN** 系统不得增加该用户已用次数
- **AND** 调用记录应标记为未扣减

#### Scenario: 防重复扣减
- **WHEN** 同一任务完成逻辑被重复触发，且该任务已经完成公用额度扣减
- **THEN** 系统不得再次扣减该用户公用额度
- **AND** 调用记录保持一次扣减结果

### Requirement: 调用记录与管理员排查

系统 SHALL 记录通过 TeamTools 页面发起的模型调用事件，包括用户、任务、调用来源、供应商、模型、状态、是否扣减、错误摘要、创建时间和完成时间。调用记录不得保存 API Key 明文。

#### Scenario: 记录公用 Key 调用
- **WHEN** 用户领取公用 Key 调用配置
- **THEN** 系统创建调用记录
- **AND** 记录调用来源为 `shared_key`
- **AND** 记录不得包含公用 API Key 明文

#### Scenario: 记录个人 Key 调用来源
- **WHEN** 用户使用个人 API Key 回传 AI 结果或调用错误
- **THEN** 系统记录调用来源为 `personal_key`
- **AND** 记录不得包含用户个人 API Key 明文

#### Scenario: 管理员查看额度与调用状态
- **WHEN** 管理员打开模型配置页
- **THEN** 系统返回公用 Key 配置状态和用户额度列表
- **AND** 首版 MAY 不常驻展示调用记录区，但后端必须保留调用记录供后续排查
