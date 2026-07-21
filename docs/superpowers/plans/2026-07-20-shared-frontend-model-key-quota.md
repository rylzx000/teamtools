---
change: shared-frontend-model-key-quota
design-doc: docs/superpowers/specs/2026-07-20-shared-frontend-model-key-quota-design.md
base-ref: e5835481af6d8a7aed9dc6039bcc2458a97cfa6c
archived-with: 2026-07-21-shared-frontend-model-key-quota
---

# 公用模型 Key 与用户额度实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 实现管理员配置团队公用 API Key、每用户额度管理、普通用户个人 Key 优先且公用 Key 兜底的 FPA MVP 主链路。

**Architecture:** 后端新增 `backend/app/modules/model_keys/service.py` 负责配置、额度、ticket、调用事件和幂等扣减；`backend/app/modules/fpa/service.py` 只在任务详情、领取前置校验、AI 回传和完成扣减处调用该模块。前端保持 `frontend/src/App.tsx` 单文件结构，管理员增加“模型配置”页签，普通用户仍在提交/详情主链路中使用个人 Key 或领取公用 Key。

**Tech Stack:** FastAPI、SQLite、Python unittest、React、TypeScript、Vite。

archived-with: 2026-07-21-shared-frontend-model-key-quota
---

## 文件结构

- Modify: `backend/app/db.py`，新增三张表并迁移 `fpa_task_details` 调用来源字段。
- Create: `backend/app/modules/model_keys/__init__.py`，导出模型 Key 服务模块。
- Create: `backend/app/modules/model_keys/service.py`，集中实现配置、额度、ticket、事件、扣减和非敏感响应。
- Modify: `backend/app/main.py`，新增管理员接口和普通用户领取公用 Key 接口。
- Modify: `backend/app/modules/fpa/service.py`，接入任务详情额度、AI 回传来源记录、失败事件标记、成功幂等扣减。
- Modify: `backend/tests/test_fpa_mvp.py`，补充后端接口和流程测试。
- Modify: `frontend/src/App.tsx`，新增模型配置页、领取公用 Key 调用逻辑、任务详情额度展示。
- Modify: `frontend/src/styles.css`，补充模型配置页最小样式，沿用现有视觉体系。
- Modify: `openspec/changes/shared-frontend-model-key-quota/tasks.md`，按完成情况勾选。

### Task 1: 数据结构和服务模块

**Files:**
- Modify: `backend/app/db.py`
- Create: `backend/app/modules/model_keys/__init__.py`
- Create: `backend/app/modules/model_keys/service.py`
- Test: `backend/tests/test_fpa_mvp.py`

- [x] **Step 1: 写额度懒初始化和配置测试**

在 `backend/tests/test_fpa_mvp.py` 增加测试：管理员保存默认额度 10 后，普通用户首次查询或领取时生成 `quota_total=10, used_count=0`；管理员改默认额度为 3 后，已有用户仍为 10，新用户懒初始化为 3。

- [x] **Step 2: 写数据库表和迁移**

在 `SCHEMA_STATEMENTS` 增加 `model_key_config`、`user_model_quotas`、`model_call_events`；在 `migrate_current_schema()` 给 `fpa_task_details` 增加 `model_call_source`、`model_call_ticket`、`shared_quota_deducted_at`。

- [x] **Step 3: 实现 `model_keys.service`**

实现函数：`get_public_config()`、`save_admin_config()`、`get_or_create_quota()`、`list_admin_quotas()`、`save_user_quota()`、`reset_user_quota()`、`bulk_set_quotas()`、`bulk_reset_quotas()`、`issue_shared_key()`、`record_personal_call()`、`record_call_failure()`、`deduct_shared_quota_once()`、`quota_summary_for_user()`。所有返回普通详情的函数不得返回 `api_key`。

- [x] **Step 4: 运行后端定向测试**

Run: `cd backend; uv run python -m unittest tests.test_fpa_mvp -v`
Expected: 新增测试失败点已修复后通过。

### Task 2: 后端接口和 FPA 流程接入

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/modules/fpa/service.py`
- Test: `backend/tests/test_fpa_mvp.py`

- [x] **Step 1: 写接口权限测试**

覆盖普通用户访问 `/api/admin/model-key/config`、`/api/admin/model-key/quotas`、额度修改、重置接口均被拒绝；管理员可读取和保存配置但不回显明文 Key。

- [x] **Step 2: 增加管理员接口**

在 `backend/app/main.py` 增加 `require_admin()`，注册 `GET/POST /api/admin/model-key/config`、`GET /api/admin/model-key/quotas`、单人保存、单人重置、统一设置、统一重置接口。

- [x] **Step 3: 增加普通用户领取接口**

注册 `POST /api/fpa/tasks/{task_id}/shared-model-key`，只允许任务所有者或管理员在 `waiting_ai_call` 状态领取；公用 Key 未启用、未配置、额度不足、任务无权限、任务状态不可调用均返回明确错误，额度不足消息固定为 `公用apikey个人用量已用完，请输入可用的apikey`。

- [x] **Step 4: 接入 AI 回传来源和扣减**

在 `handle_ai_result()` 读取 `model_call_source` 和 `model_call_ticket`；失败时只记录事件失败不扣减；成功生成 Excel 且任务进入 `completed` 后调用 `deduct_shared_quota_once()`；个人 Key 成功不扣减。

- [x] **Step 5: 接入任务详情额度摘要**

`task_detail()` 增加 `model_quota` 字段，管理员查看任务时展示任务创建人的额度摘要，普通用户只展示自己的额度摘要，均不包含明文 Key。

### Task 3: 前端主链路和管理员配置页

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [x] **Step 1: 扩展前端类型和 API 调用**

增加 `ModelQuota`、`ModelKeyConfig`、`ModelQuotaRow` 类型；增加领取公用 Key 的调用函数，返回配置只在内存中用于本次模型调用。

- [x] **Step 2: 调整提交页说明**

保留现有 API Key 输入和本机保存逻辑；未填写个人 Key 时提示将使用团队公用 Key，不上传个人 Key。

- [x] **Step 3: 调整详情页调用模型逻辑**

调用模型前优先使用本地个人 Key；没有个人 Key 时调用后端领取公用 Key；回传 `/ai-result` 时只带 `model_call_source` 和 `model_call_ticket`，不得带 `apiKey`。

- [x] **Step 4: 增加额度展示**

在 `TaskSummaryCard` 最后一行展示 `公用 Key 余量：剩余 x / 共 y 次`，值来自 `detail.model_quota`。

- [x] **Step 5: 增加管理员模型配置页**

Shell 管理员页签增加 `模型配置`；普通用户不展示，访问 `/fpa/model-config` 时显示无权限或返回任务列表。页面包含公用 Key 配置卡片和用户额度管理表格，不展示调用记录常驻区。

- [x] **Step 6: 补充最小样式**

在 `frontend/src/styles.css` 复用现有 panel、button、field、table 风格，仅补充模型配置页布局，不改整体视觉体系。

### Task 4: 测试、文档和 Comet 收口

**Files:**
- Modify: `backend/tests/test_fpa_mvp.py`
- Modify: `openspec/changes/shared-frontend-model-key-quota/tasks.md`

- [x] **Step 1: 完成流程测试**

覆盖个人 Key 成功不扣减、公用 Key 成功生成 Excel 后扣减、失败不扣减、同一任务重复完成不重复扣减、调用事件不保存 API Key 明文、普通任务详情不暴露公用 Key。

- [x] **Step 2: 运行验证命令**

Run:
`openspec validate shared-frontend-model-key-quota --strict`
`cd backend; uv run python -m unittest tests.test_fpa_mvp -v`
`cd frontend; npm run build`
`.\scripts\check-encoding.ps1`

- [x] **Step 3: 勾选 OpenSpec tasks**

只勾选已实现和已验证项；如发现文档无需改动，在最终总结说明原因，不做无意义文档修改。

- [x] **Step 4: 运行 Comet build guard**

Run: `node .codex/skills/comet/scripts/comet-guard.mjs shared-frontend-model-key-quota build --apply`
Expected: Build 阶段通过并进入 Verify。

## 自检

- 覆盖 OpenSpec 目标：配置、额度、领取、扣减、权限、前端管理员页、普通用户兜底。
- 排除非目标：不做强安全防复制，不做 token 计费，不改提示词/schema/Excel 模板，不直连模型 API。
- 安全检查：Key 不写前端静态代码、普通日志、调用事件明细或普通任务详情；只有受控领取接口短暂返回明文 Key。
