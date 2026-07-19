## Why

已归档的 `frontend-page-style-adjustment` 只保存 Open Design 原型和页面样式原则，当前 TeamTools 运行态前端仍保留首页模块卡片、左侧模块栏、前端硬编码表单配置和较旧的信息层级。本 change 用一个新的运行时落地变更，把 FPA 三页原型转换为可运行、可验证的 MVP 前端。

`Open Design`、`TeamTools`、`FPA`、`MVP` 保留英文，是因为它们分别是设计方法、产品名、模块名和软件交付阶段常用专有名词。

## What Changes

- 登录成功后默认进入 `/fpa/tasks`，不再展示首页模块卡片。
- 首版去掉左侧模块栏，只保留顶部模块标识、当前用户、角色、退出登录和 FPA 页签。
- 按 Open Design 原型重做任务列表、提交评估、查看详情三页的运行态布局和样式。
- 任务列表收敛为核心字段和短操作列，管理员字段不挤压普通用户核心字段。
- 提交评估页使用后端配置加载系统、规模计数时机和完整性级别，API Key 只在浏览器本地使用。
- 任务详情页按 `waiting_ai_call`、`validating_result`、`generating_result`、`completed`、`failed`、`cancelled/canceled` 渲染主内容。
- 普通用户主内容只展示结果摘要、`AI分析.md`/`AI评估.md` 预览复制和 Excel 下载入口，不展示完整后台排查文件。
- 如后端缺少 `GET /api/fpa/form-config`，本 change 最小补充该接口和测试，不改数据库 schema 或 FPA 核心状态机。

## Capabilities

### New Capabilities

- 无。本次落地既有 FPA 前端能力，不新增同义 capability。

### Modified Capabilities

- `fpa-interface-ui`：更新 FPA 运行态页面入口、三页布局、表单配置来源、状态渲染、产物可见性和按钮位置要求。
- `platform-architecture`：补充当前单模块 MVP 可直接进入 FPA 任务列表并隐藏左侧模块栏的入口口径，同时保留平台后续多模块扩展边界。

## Impact

- 前端运行时代码：`frontend/src/App.tsx`、`frontend/src/styles.css`。
- 后端最小配置接口：`backend/app/main.py`、`backend/app/modules/fpa/service.py`。
- 后端测试：`backend/tests/test_fpa_mvp.py`。
- OpenSpec change：`openspec/changes/apply-open-design-fpa-frontend/`。
- 验证命令：前端构建、后端相关测试、编码检查、`openspec validate --all --strict`；如环境允许，再启动本地服务并用浏览器检查 FPA 三页。
- 不修改 AI 提示词生成逻辑、Excel 生成脚本、数据库 schema、FPA 核心任务状态机或已归档的 `frontend-page-style-adjustment` change。
