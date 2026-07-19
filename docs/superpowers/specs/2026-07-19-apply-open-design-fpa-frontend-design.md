---
comet_change: apply-open-design-fpa-frontend
role: technical-design
canonical_spec: openspec
---

# FPA 前端 Open Design 落地技术设计

## 背景

`apply-open-design-fpa-frontend` 的目标是把已归档 Open Design 三页原型落到 TeamTools 运行态前端。当前 FPA 主链路已可用，但页面入口、左侧模块栏、表单配置来源、详情页信息层级和普通用户产物边界仍需要按新 OpenSpec 口径收敛。

`FPA`、`Open Design`、`TeamTools`、`AI`、`API Key`、`DeepSeek`、`Excel`、`React`、`TypeScript`、`MVP` 保留英文，是项目模块、设计方法、产品名、协议字段、第三方服务、文件类型或技术栈专有名词。

## 已确认方案

采用“补缺+收敛展示”方案：

- 保留现有 `frontend/src/App.tsx` 单文件主链路，不在本轮拆组件。
- 最小补充后端 `GET /api/fpa/form-config`，让提交页配置来自后端而不是前端常量。
- 调整运行态前端壳：登录后默认进入 `/fpa/tasks`，隐藏首页模块卡片和左侧模块栏，保留顶部模块标识、用户信息、角色、退出登录和 FPA 页签。
- 任务列表、提交评估、任务详情三页按 Open Design 原型收敛密度和信息层级。
- 详情页按任务状态渲染主内容，普通用户只看到结果摘要、AI Markdown 预览/复制和 Excel 下载入口。
- API Key 只保留在浏览器本地，不上传后端、不写入任务文件、不进入日志或数据库。

## 范围边界

### 本轮做

- 后端新增表单配置读取函数和 `GET /api/fpa/form-config` 路由。
- 后端测试覆盖表单配置接口和敏感路径不暴露。
- 前端使用表单配置接口加载系统、规模计数时机、完整性级别和默认值。
- 前端平台壳、任务列表、提交页、详情页做最小运行态调整。
- 详情页对 `AI分析.md` 或 `AI评估.md` 缺失做空态，不用过程 JSON 临时代替。

### 本轮不做

- 不修改提示词模板、AI schema、AI 请求包生成脚本、AI 校验脚本。
- 不修改 Excel 模板或 Excel 生成脚本。
- 不改数据库 schema，不重构后端状态机。
- 不拆分 `App.tsx` 为多文件组件。
- 不修改已归档的 `frontend-page-style-adjustment` change。

## 后端设计

### 表单配置接口

在 `backend/app/modules/fpa/service.py` 增加 `get_form_config(data_dir: Path) -> dict[str, Any]`：

- `systems` 复用 `load_systems(data_dir)`，只返回启用系统的前端安全字段。
- `count_timings` 从现有 `COUNT_TIMINGS` 生成 `{ value, label, coefficient }`。
- `integrity_levels` 从现有 `INTEGRITY_LEVELS` 生成 `{ value, label, coefficient }`。
- `defaults` 返回 `system_code`、`count_timing`、`integrity_level`。
- 不返回 `knowledge_dir`、本地路径、环境变量或任何模型密钥。

在 `backend/app/main.py` 增加：

```python
@app.get("/api/fpa/form-config")
async def fpa_form_config(request: Request) -> dict[str, Any]:
    require_user(request)
    return get_form_config(app_data_dir)
```

接口只做认证和读取配置，不创建任务，不改状态。

### 产物边界

本轮不新增后台文件下载接口。普通用户 Excel 下载仍走 `GET /api/fpa/tasks/{task_id}/download/excel`。任务详情如果已有 `ai_analysis_md` 内容则展示；没有时前端展示空态。后端不得为了前端展示而返回完整 `FPA生成过程.json`、脚本 payload、任务日志或原始模型响应作为普通用户主内容。

## 前端设计

### 平台壳与入口

`Router` 将 `/` 和 `/modules` 直接渲染任务列表，或通过现有 `navigate('/fpa/tasks')` 进入任务列表。`Shell` 移除左侧模块栏展示，改为单列布局：

- 顶部左侧展示 `FPA 工作量评估` 和当前页面名称。
- 顶部右侧展示当前用户、角色、退出登录。
- 内容区顶部保留 FPA 页签：任务列表、提交评估、查看详情。

### 任务列表

列表保留核心列：任务名称、系统、状态、提交时间、完成时间、目标人天、结果中值、命中目标、操作。管理员提交人弱化展示，避免挤压核心字段。操作列默认展示“查看”，完成且可下载时展示“下载”。

样式上压缩表格字号和单元格间距，长任务名省略，尽量避免 1366/1440 桌面宽度出现横向滚动。

### 提交评估页

新增 `FormConfig` 类型，提交页 `useEffect` 调用 `/api/fpa/form-config`。系统默认值按用户 `default_system_code` 优先，否则使用接口默认系统或第一个可用系统。

下拉展示使用后端返回的 `label`，提交值使用 `value`。API Key 本地输入复用 `DEEPSEEK_KEY_STORAGE`，用户取消记住时立即清理 localStorage；创建任务请求体不包含 API Key。

### 任务详情页

详情页按后端状态划分主内容：

- `waiting_ai_call`：显示任务摘要、API Key 状态、获取请求包、系统轻校验提示和浏览器调用 DeepSeek 入口。
- `validating_result` / `generating_result`：显示简化进度和任务摘要，不展示后台技术细节。
- `completed`：显示结果中值、目标命中、质量提示、Excel 下载和 AI Markdown 预览/复制。
- `failed`：显示失败阶段、脱敏原因、建议操作、重新调用或复制重建入口。
- `canceled` / `cancelled`：显示取消状态、返回列表和复制重建入口。

管理员排查信息如保留，默认折叠；普通用户不展示完整过程 JSON、payload、日志、原始模型响应、敏感路径、环境变量或 API Key。

## 数据流

1. 用户登录后进入 `/fpa/tasks`。
2. 用户打开提交页，前端请求 `/api/fpa/form-config` 获取系统和下拉配置。
3. 用户提交需求，前端向 `/api/fpa/tasks` 发送任务字段，不包含 API Key。
4. 后端创建 `waiting_ai_call` 任务并生成 AI 请求包。
5. 前端详情页用本地 API Key 调用 DeepSeek，再把模型响应回传 `/api/fpa/tasks/{task_id}/ai-result`。
6. 后端生成结果摘要和 Excel。
7. 前端完成态展示摘要、AI Markdown 预览和 Excel 下载。

## 错误处理

- 表单配置加载失败时，提交页展示错误并保持提交按钮不可用。
- 目标人天、系统选择、Markdown 内容仍由前端和后端双重校验。
- DeepSeek 调用失败只在浏览器端展示和选择性回传失败，不记录 API Key。
- 任务失败详情只展示后端脱敏后的 `failure_stage` 和 `error_summary`。

## 测试策略

- 后端：在 `backend/tests/test_fpa_mvp.py` 增加或调整 `form-config` 测试，断言接口返回默认值、下拉 label/value、启用系统，以及不包含 `knowledge_dir`。
- 后端：运行既有 FPA MVP 测试，确认任务创建、AI 请求包、AI 结果回传、Excel 下载不回归。
- 前端：运行 `npm run build`，确认 TypeScript 和 Vite 构建通过。
- 全局：运行 `.\scripts\check-encoding.ps1` 和 `openspec validate --all --strict`。
- 如环境允许：启动本地服务并用浏览器冒烟检查 `/fpa/tasks`、`/fpa/submit`、`/fpa/tasks/:id`。

## 风险与缓解

- `App.tsx` 继续偏大：本轮不拆组件，后续可用单独 change 做前端结构整理。
- Open Design 原型和真实接口字段不完全一致：以 OpenSpec 和当前接口为准，不复制静态模拟数据。
- Markdown 产物命名未最终稳定：前端兼容 `AI分析.md`/`AI评估.md` 空态，等待提示词脚本对话稳定后再统一。
- 后端权限边界可能还有历史字段：本轮只收敛普通用户主内容和最小接口，不引入大范围权限重构。
