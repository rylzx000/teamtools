# Brainstorm Summary

- Change: shared-frontend-model-key-quota
- Date: 2026-07-20

## 确认的技术方案

采用“独立模型 Key 服务模块 + FPA 最小集成 + 前端轻量页签”的方案：

- 后端新增 `backend/app/modules/model_keys/service.py`，集中管理公用模型配置、用户额度、调用票据、调用事件和成功扣减。
- `backend/app/db.py` 新增模型配置、用户额度和调用事件表，并扩展 `fpa_task_details` 保存调用来源、票据和扣减状态。
- `backend/app/main.py` 增加管理员配置接口、额度管理接口和任务级公用 Key 领取接口。
- `backend/app/modules/fpa/service.py` 仅在任务详情、AI 回传、完成生成 Excel 后调用模型 Key 服务，不把额度逻辑大面积写入 FPA 主流程。
- 前端 `frontend/src/App.tsx` 保留个人 API Key 输入框；用户未填写个人 Key 时调用后端领取公用 Key；管理员新增 `模型配置` 页签。

## 关键取舍与风险

- 个人 Key 优先，公用 Key 兜底，保持普通用户页面和已有调用流程稳定。
- 公用 Key 会下发浏览器，这是内部临时共享模式，不能防复制、防抓包或防绕过；管理员页面和文档必须明确该边界。
- 成功扣减放在 Excel 正式生成并任务进入 `completed` 后，失败、取消、校验失败不扣减。
- 同一任务通过 `shared_quota_deducted_at` 和调用事件扣减状态做幂等保护。
- 不做多供应商完整抽象、不做 token 计费、不做调用记录常驻页面，避免扩大 MVP 范围。

## 测试策略

- 后端单元/接口测试覆盖：额度懒初始化、默认额度变更不影响已有用户、单人调整、单人重置、统一设置额度、统一重置用量。
- 后端权限测试覆盖：普通用户不能访问配置和额度管理接口，普通任务详情不暴露公用 Key。
- FPA 流程测试覆盖：个人 Key 成功不扣减、公用 Key 成功生成 Excel 后扣减、失败不扣减、重复完成不重复扣减。
- 公用 Key 领取测试覆盖：未启用、未配置、额度不足、任务无权限、任务状态不可调用、成功领取。
- 前端以构建检查覆盖类型与基础集成，关键安全边界由后端测试保证。

## Spec Patch

无。本轮 OpenSpec delta spec 已覆盖实现边界。
