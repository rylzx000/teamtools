## Context

当前 TeamTools 已跑通 FPA 主链路：用户创建任务，后端生成 AI 请求包，前端浏览器调用 DeepSeek，后端接收 AI 结果并生成 Excel。已归档的 `frontend-page-style-adjustment` 保存了 Open Design 三页原型，但运行态前端仍保留首页模块卡片、左侧模块栏、前端硬编码表单配置和偏后台的信息展示层级。

本 change 只把已确认的 FPA 前端原型落到现有运行态，不改变提示词、AI schema、Excel 模板、数据库 schema 或 FPA 核心状态机。`TeamTools`、`FPA`、`AI`、`API`、`Open Design`、`DeepSeek`、`Excel`、`React`、`TypeScript`、`MVP` 保留英文，是产品名、模块名、协议/技术栈或第三方专有名词。

## Goals / Non-Goals

**Goals:**

- 登录后默认进入 `/fpa/tasks`，首版隐藏首页模块卡片和左侧模块栏。
- 按 Open Design 原型重做任务列表、提交评估和任务详情三页的运行态布局。
- 提交评估页从后端 `GET /api/fpa/form-config` 加载系统、规模计数时机和完整性级别。
- 详情页按后端任务状态展示用户可理解的主内容，普通用户不看到后台排查文件。
- 保留任务创建、浏览器端调用 DeepSeek、AI 结果回传、Excel 下载、取消和复制重建等既有能力。

**Non-Goals:**

- 不修改 AI 提示词生成逻辑、AI 校验脚本、Excel 生成脚本或 Excel 模板。
- 不实现最终 AI 响应解析、最终 JSON schema 校验、JSON 到 Excel payload 的最终映射。
- 不改数据库 schema，不重构 FPA 核心状态机，不拆分大型前端组件结构。
- 不修改已归档的 `frontend-page-style-adjustment` change。

## Decisions

### Decision 1: 以现有 `App.tsx` 做 MVP 落地

本轮直接在 `frontend/src/App.tsx` 和 `frontend/src/styles.css` 内最小调整运行态页面，不先拆组件。这样能保持现有登录、路由、任务创建、AI 调用和下载逻辑连续，降低回归风险。

替代方案是先拆出 FPA 页面组件和设计系统，再改页面。该方案更整洁，但会扩大文件范围和测试面，不符合本轮“可跑 MVP”目标。

### Decision 2: 补最小 `GET /api/fpa/form-config`

提交页下拉项以 `backend/app/modules/fpa/service.py` 中已有 FPA 配置常量为来源，并通过 `backend/app/main.py` 暴露最小只读接口。接口仅返回前端表单所需字段，不返回 `knowledge_dir` 或服务器资料路径。

替代方案是继续使用前端常量。该方案实现更快，但会让运行态继续偏离接口设计文档，也不利于后续 Excel 模板参数口径统一。

### Decision 3: 状态展示在前端做轻量映射

后端细粒度状态保持不变，前端将 `waiting_ai_call` 映射为 AI 评估中，将 `validating_result`、`generating_result` 映射为生成结果中，将完成、失败、取消映射为对应简化阶段。详情页仍按原始状态选择主内容区，但用户看到的是简化流程语言。

替代方案是改后端状态机。该方案会扩大业务流程风险，本轮不采用。

### Decision 4: 产物可见性由后端字段和前端展示共同收敛

普通用户主内容只展示结果摘要、`AI分析.md` 或 `AI评估.md` 预览/复制和 Excel 下载入口；后台排查产物不作为普通用户主内容展示。后端任务详情可预留 Markdown 预览字段，文件列表或下载能力不得暴露完整过程文件给普通用户。

替代方案是在前端简单隐藏所有 JSON 文本但保留下载入口。该方案容易遗留后台文件暴露路径，因此需要后端接口边界同步收敛。

### Decision 5: API Key 只留在浏览器本地

提交页和详情页沿用浏览器本地 API Key 逻辑。创建任务、获取 AI 请求包、回传 AI 结果都不上传 API Key；用户取消记住时清理 localStorage 中的旧值。

替代方案是后端托管模型调用。该方案违背当前平台模型调用边界，本轮不采用。

## Risks / Trade-offs

- [Risk] `App.tsx` 继续变大，后续维护成本上升。→ Mitigation：本轮只做运行态落地，后续可在单独 change 中拆组件。
- [Risk] Open Design 静态原型和真实接口字段存在差异。→ Mitigation：以现有接口和 OpenSpec delta 为准，不复制静态模拟数据。
- [Risk] 1366/1440 桌面宽度仍可能因真实任务名过长产生横向拥挤。→ Mitigation：列表仅保留核心字段，长文本省略，管理员字段弱化。
- [Risk] `AI分析.md` 产物可能尚未存在。→ Mitigation：完成页兼容 `AI分析.md`、`AI评估.md`，缺失时展示空态，不用过程 JSON 临时代替。
- [Risk] 本地服务浏览器检查可能受端口、账号或数据目录影响。→ Mitigation：优先完成构建和接口测试；如环境可用，再做浏览器冒烟。

## Migration Plan

1. 新增或调整后端表单配置接口和相关测试。
2. 更新前端运行态页面入口、FPA 三页结构和样式。
3. 保持旧任务数据兼容，详情页对缺失 Markdown 预览显示空态。
4. 运行后端测试、前端构建、编码检查和 OpenSpec 严格校验。
5. 如需回滚，可回退本 change 涉及的前端文件和最小后端配置接口；不涉及数据库迁移。

## Open Questions

- `AI分析.md` 与 `AI评估.md` 的最终产物命名是否统一，需要等待提示词脚本对话和产物契约稳定后再定。
- 后续是否拆分 `App.tsx` 为 FPA 子组件，应作为独立前端维护 change 处理。
