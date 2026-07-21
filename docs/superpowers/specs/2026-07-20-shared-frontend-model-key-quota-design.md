---
comet_change: shared-frontend-model-key-quota
role: technical-design
canonical_spec: openspec
archived-with: 2026-07-21-shared-frontend-model-key-quota
status: final
---

# 公用模型 Key 与用户额度技术设计

## 目标

在不改变“浏览器调用模型、服务器不直连模型”的前提下，增加管理员配置团队公用 API Key、普通用户个人 Key 优先、公用 Key 兜底和每用户额度扣减能力。普通用户页面保持轻量；管理员新增模型配置页；公用 Key 只通过受控领取接口返回，不进入普通任务详情、日志或调用事件明细。

## 当前代码基线

- 后端入口集中在 `backend/app/main.py`，登录态通过 `require_user()` 从 session cookie 读取用户。
- 数据库初始化集中在 `backend/app/db.py`，通过 `SCHEMA_STATEMENTS` 和 `migrate_current_schema()` 演进 SQLite schema。
- FPA 主流程集中在 `backend/app/modules/fpa/service.py`：创建任务、生成 AI 请求包、获取 AI 请求包、回传 AI 结果、生成 Excel、任务详情。
- 前端集中在 `frontend/src/App.tsx`，FPA 页签、提交页、详情页、任务列表和浏览器端模型调用状态都在该文件内维护；样式在 `frontend/src/styles.css`。
- 当前测试集中在 `backend/tests/test_fpa_mvp.py`，使用轻量 ASGI client 直接调用 FastAPI app。

## 方案概览

采用独立后端服务模块 `backend/app/modules/model_keys/service.py` 承载模型 Key 与额度逻辑，FPA service 只在关键节点调用它：

```text
管理员模型配置页
  -> /api/admin/model-key/config
  -> model_keys.service 保存配置和默认额度

管理员额度表
  -> /api/admin/model-key/quotas
  -> model_keys.service 管理每用户额度

普通用户无个人 Key 调用模型
  -> /api/fpa/tasks/{task_id}/shared-model-key
  -> 校验任务、状态、配置、额度
  -> 返回 provider/api_base/model/api_key/ticket
  -> 浏览器调用模型

AI 结果或错误回传
  -> /api/fpa/tasks/{task_id}/ai-result
  -> 记录 personal_key/shared_key 调用来源和事件状态
  -> completed + Excel 存在 + shared_key + 未扣减 -> 扣减 1 次
```

## 数据模型

### 公用模型配置表

新增 `model_key_config`，首版只保存一条 `id = 'shared_default'` 记录：

- `id`
- `enabled`
- `provider`
- `api_base`
- `model_name`
- `api_key`
- `default_quota`
- `created_at`
- `updated_at`
- `updated_by`

接口返回配置时不回显完整 `api_key`，只返回 `has_api_key` 和掩码状态。保存配置时如果 `api_key` 为空则保留旧 Key；如果传入新 Key 则替换。

### 用户额度表

新增 `user_model_quotas`：

- `user_id`
- `enabled`
- `quota_total`
- `used_count`
- `last_used_at`
- `last_reset_at`
- `reset_by`
- `created_at`
- `updated_at`

懒初始化规则：当用户首次查询额度、管理员打开额度表或领取公用 Key 时，如果没有记录，则按当前 `model_key_config.default_quota` 创建，`used_count = 0`，`enabled = 1`。修改默认额度不改已有记录；管理员统一设置额度才批量改 `quota_total`。

### 调用事件表

新增 `model_call_events`：

- `id`
- `task_id`
- `user_id`
- `source`：`personal_key` / `shared_key`
- `provider`
- `model_name`
- `ticket`
- `status`：`issued` / `succeeded` / `failed`
- `deducted`
- `error_summary`
- `created_at`
- `completed_at`

调用事件不得保存 API Key 明文。公用 Key 领取时生成 ticket 并创建 `issued` 事件；AI 回传成功/失败时更新事件状态。个人 Key 不需要 ticket，可在回传时按任务创建或更新事件。

### FPA 任务扩展字段

扩展 `fpa_task_details`：

- `model_call_source`
- `model_call_ticket`
- `shared_quota_deducted_at`

其中 `shared_quota_deducted_at` 是防重复扣减的幂等标记。扣减时在同一事务中检查该字段为空、任务 source 为 `shared_key`、任务最终 completed 且 Excel 文件存在。

## 后端接口

### 管理员配置接口

- `GET /api/admin/model-key/config`
  - 仅管理员。
  - 返回启用状态、provider、api_base、model_name、default_quota、has_api_key、masked_key。
- `POST /api/admin/model-key/config`
  - 仅管理员。
  - 保存 enabled、provider、api_base、model_name、default_quota、可选 api_key。
  - 不返回明文 Key。

### 管理员额度接口

- `GET /api/admin/model-key/quotas`
  - 仅管理员。
  - 懒初始化所有启用用户额度并返回用户、角色、启用、总额度、已用、剩余、最近成功使用时间。
- `POST /api/admin/model-key/quotas/{user_id}`
  - 仅管理员。
  - 保存单人 `enabled` 和 `quota_total`。
- `POST /api/admin/model-key/quotas/{user_id}/reset`
  - 仅管理员。
  - 单人 `used_count = 0`，记录 reset 信息。
- `POST /api/admin/model-key/quotas/bulk-set`
  - 仅管理员。
  - 所有用户 `quota_total = value`，不清零 used。
- `POST /api/admin/model-key/quotas/bulk-reset`
  - 仅管理员。
  - 所有用户 `used_count = 0`。

### 普通用户领取公用 Key

- `POST /api/fpa/tasks/{task_id}/shared-model-key`
  - 登录用户可调用。
  - 校验任务权限与状态，状态必须是 `waiting_ai_call`。
  - 校验公用 Key enabled、api_key 非空、用户额度启用且剩余大于 0。
  - 额度不足固定报错：`公用apikey个人用量已用完，请输入可用的apikey`。
  - 成功返回 provider、api_base、model、api_key、ticket、quota。
  - 同时记录 `model_call_source = shared_key`、`model_call_ticket = ticket`，创建调用事件。

### 任务详情额度展示

`task_detail()` 增加 `model_quota` 字段：

```json
{
  "model_quota": {
    "enabled": true,
    "quota_total": 10,
    "used_count": 2,
    "remaining": 8
  }
}
```

普通用户只能拿到自己的额度摘要；管理员查看任务时也按任务创建人的额度展示。该字段不包含 API Key。

## FPA 流程集成

### 个人 Key 来源

当前前端不会把个人 API Key 上传给后端。为了记录调用来源，`POST /api/fpa/tasks/{task_id}/ai-result` 增加非敏感字段：

- `model_call_source`: `personal_key` / `shared_key`
- `model_call_ticket`: 公用 Key 领取返回的 ticket，个人 Key 为空

后端只信任 `shared_key` 时 ticket 必须匹配本任务已领取事件；否则按 `personal_key` 记录。回传 payload 继续走 `safe_ai_result_payload()`，避免 API Key 明文落盘。

### 成功扣减

在 `handle_ai_result()` 生成 Excel 并准备把任务更新为 `completed` 后调用模型 Key 服务：

```text
if source == shared_key and excel exists and not deducted:
    user quota used_count += 1
    fpa_task_details.shared_quota_deducted_at = now
    model_call_events.deducted = 1, status = succeeded
```

如果 AI 调用失败、JSON 校验失败、Excel 生成失败或任务取消，不调用扣减。失败回传会把事件标记为 `failed`，但 `deducted = 0`。

## 前端设计

### 提交页

保留现有 API Key 输入和 localStorage/sessionStorage 逻辑。文案改为：

- 输入个人 Key：使用个人 Key，不消耗团队公用额度。
- 未输入个人 Key：将尝试使用团队公用 Key；若额度不足，提示固定文案。

### 详情页调用模型

详情页或现有调用逻辑在实际调用 DeepSeek 前：

```text
有个人 API Key -> 使用个人 Key，回传 model_call_source=personal_key
无个人 API Key -> POST shared-model-key 领取配置
  成功 -> 使用返回 api_key/api_base/model，回传 model_call_source=shared_key + ticket
  失败 -> 展示后端错误，尤其额度不足固定文案
```

注意：公用 Key 不写 localStorage，不展示明文，不写任务详情。

### 详情摘要

`TaskSummaryCard` 最后一行展示：

```text
公用 Key 余量：剩余 x / 共 y 次
```

使用后端 `model_quota`，不做本地推算。

### 管理员模型配置页

管理员 `Shell` 页签增加 `模型配置`。普通用户不展示；直接访问 `/fpa/model-config` 时显示无权限或返回任务列表。

页面两个区块：

1. 公用 Key 配置卡片：启用、provider、api_base、model_name、api_key 替换输入、has_api_key、default_quota、风险说明、保存按钮。
2. 用户额度管理表格：用户、角色、启用、总额度、已用、剩余、最近成功使用、保存、重置、统一设置额度、统一重置用量。

## 安全边界

- 公用 Key 只在 `shared-model-key` 领取接口成功时返回。
- 管理员配置读取接口不返回完整 Key。
- 任务详情、任务列表、调用事件、任务事件、AI 原始响应和日志都不得保存或返回 API Key 明文。
- 公用 Key 下发浏览器是明确接受风险的内部临时共享模式；管理员页面必须展示风险提示。

## 测试计划

后端测试优先新增到 `backend/tests/test_fpa_mvp.py`，保持现有轻量 ASGI 测试方式：

- 懒初始化额度：普通用户查询/领取时创建默认额度。
- 默认额度变更：已有用户额度不跟随变化，新用户或无记录用户使用新默认。
- 单人调整额度、单人重置、统一设置额度、统一重置用量。
- 普通用户访问管理员配置和额度接口被拒绝。
- 公用 Key 未启用、未配置、额度不足、任务无权限、任务状态不可调用。
- 个人 Key 成功不扣减。
- 公用 Key 成功生成 Excel 后扣减。
- 失败任务不扣减。
- 同一任务重复扣减保护。
- 调用事件不保存 API Key 明文。
- 普通任务详情不暴露公用 Key 或敏感字段。

前端验证使用 `npm run build`；后端验证使用 `uv run python -m unittest tests.test_fpa_mvp -v`；整体检查使用 `openspec validate shared-frontend-model-key-quota --strict` 和 `.\scripts\check-encoding.ps1`。

## 实施边界

- 不提交、不推送。
- 不修改 AI 提示词、AI schema、Excel 模板或 Excel 生成脚本。
- 不重构前端为多文件结构，除非构建无法维持；本轮保持 `App.tsx` 单文件风格。
- 不处理强安全限额、token 统计、调用记录前端常驻展示或多供应商完整抽象。
