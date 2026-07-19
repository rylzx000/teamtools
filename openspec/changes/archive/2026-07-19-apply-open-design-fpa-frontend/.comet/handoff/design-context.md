# Comet Design Handoff

- Change: apply-open-design-fpa-frontend
- Phase: design
- Mode: compact
- Context hash: c45338a444b6b45888638c865f8f4ed8e60cf3ddb108495e9375174d67da189a

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/apply-open-design-fpa-frontend/proposal.md

- Source: openspec/changes/apply-open-design-fpa-frontend/proposal.md
- Lines: 1-36
- SHA256: 46d72518d09d9c96d9f2b436ff8fa1049c97a819a224a4621fc0713c7bc5ae09

```md
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

```

## openspec/changes/apply-open-design-fpa-frontend/design.md

- Source: openspec/changes/apply-open-design-fpa-frontend/design.md
- Lines: 1-75
- SHA256: 14cf13e6f767986a492d5f1a6c549f7db8b4caebcffd91a29fa8826a4cfffdc0

```md
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

```

## openspec/changes/apply-open-design-fpa-frontend/tasks.md

- Source: openspec/changes/apply-open-design-fpa-frontend/tasks.md
- Lines: 1-48
- SHA256: 903219257d3e60300dc601b54997876c8737f63d32267e80e1302847c62cb152

```md
## 1. OpenSpec / Comet 初始化

- [x] 1.1 确认 `apply-open-design-fpa-frontend` change 使用新的活跃目录，不修改已归档 `frontend-page-style-adjustment`
- [x] 1.2 补齐 proposal、design、tasks 和相关 delta spec，并通过 open 阶段校验

## 2. 后端表单配置与产物边界

- [ ] 2.1 在后端最小补充 `GET /api/fpa/form-config`，返回系统、规模计数时机、完整性级别和默认值
- [ ] 2.2 确保表单配置和系统列表不暴露 `knowledge_dir` 或服务器真实资料路径
- [ ] 2.3 预留普通用户可见的 AI Markdown 预览字段或文件角色，避免普通用户看到后台排查产物
- [ ] 2.4 补充或调整后端相关测试，覆盖表单配置和普通用户产物边界

## 3. 前端平台壳与路由入口

- [ ] 3.1 登录成功、访问 `/` 或 `/modules` 时默认进入 `/fpa/tasks`
- [ ] 3.2 首版隐藏首页模块卡片和左侧模块栏，只保留顶部模块标识、用户、角色、退出登录和 FPA 页签
- [ ] 3.3 保留任务列表、提交评估、查看详情三个页签和当前页选中态

## 4. 任务列表页

- [ ] 4.1 按 Open Design 风格重做列表页布局，压缩字体和间距并避免常规桌面横向滚动
- [ ] 4.2 默认展示任务名称、系统、状态、提交时间、完成时间、目标人天、结果中值、命中目标和操作
- [ ] 4.3 列表操作收敛为查看；已完成且可下载时额外展示下载
- [ ] 4.4 管理员提交人字段弱化展示，不挤压核心字段

## 5. 提交评估页

- [ ] 5.1 使用 `GET /api/fpa/form-config` 加载系统、规模计数时机和完整性级别
- [ ] 5.2 添加带系数前缀的规模计数时机和完整性级别下拉展示，提交真实值不拼接系数
- [ ] 5.3 保留目标人天、需求名称、Markdown 粘贴、`.md` 文件上传、API Key 本地输入和记住到本机浏览器
- [ ] 5.4 提交任务不上传 API Key，成功后跳转任务详情页

## 6. 任务详情页

- [ ] 6.1 按 `waiting_ai_call`、`validating_result`、`generating_result`、`completed`、`failed`、`cancelled/canceled` 渲染主内容
- [ ] 6.2 将细粒度状态映射为提交需求、AI评估中、生成结果中、评估完成、评估失败和已取消
- [ ] 6.3 等待 AI 调用态展示任务摘要、API Key 状态、调用模型入口和系统轻校验提示
- [ ] 6.4 完成态展示结果中值、目标命中、质量提示、Excel 下载和 AI Markdown 预览/复制
- [ ] 6.5 失败态和取消态展示脱敏原因、建议操作、返回列表、重新调用或复制重建入口
- [ ] 6.6 管理员排查信息默认折叠，普通用户不展示完整后台 JSON、payload、日志、原始模型响应或敏感路径

## 7. 验证

- [ ] 7.1 运行后端相关测试，至少覆盖 `form-config` 和 FPA MVP 主链路未回归
- [ ] 7.2 运行前端构建或项目已有类型检查
- [ ] 7.3 运行 `.\scripts\check-encoding.ps1`
- [ ] 7.4 运行 `openspec validate --all --strict`
- [ ] 7.5 如环境允许，启动本地服务并用浏览器冒烟检查任务列表、提交评估和任务详情三页

```

## openspec/changes/apply-open-design-fpa-frontend/specs/fpa-interface-ui/spec.md

- Source: openspec/changes/apply-open-design-fpa-frontend/specs/fpa-interface-ui/spec.md
- Lines: 1-168
- SHA256: 19a55ed2b13196a590256dcaf3b2c313ffbad9c3f1a7eaa5e3123422692c73d3

[TRUNCATED]

```md
## MODIFIED Requirements

### Requirement: FPA API 资源边界

系统 SHALL 通过 FPA 任务资源接口完成提交页配置查询、系统查询、任务创建、AI 请求包获取、AI 结果回传、任务列表、任务详情、取消、重新运行和 Excel 下载。

`FPA`、`API`、`GET`、`POST`、`Excel`、`AI` 保留英文，是模块、接口协议、HTTP 方法、文件类型和能力名称的既有约定。

#### Scenario: 查询提交页配置
- **WHEN** 前端调用 `GET /api/fpa/form-config`
- **THEN** 后端返回启用系统、`规模计数时机` 选项、`完整性级别` 选项和默认值
- **AND** 系统项不得包含 `knowledge_dir` 或服务器真实资料路径
- **AND** 前端提交页必须使用该接口配置下拉选项，不得把系统和估算参数写死为运行态唯一来源

#### Scenario: 查询可选系统
- **WHEN** 前端调用 `GET /api/fpa/systems`
- **THEN** 后端只返回启用系统的编码、名称、类型和排序信息
- **AND** 响应不得包含 `knowledge_dir` 或服务器真实资料路径

#### Scenario: 创建任务
- **WHEN** 前端提交 `POST /api/fpa/tasks`
- **THEN** 后端校验输入、创建任务、生成 AI 请求包并返回任务详情地址
- **AND** 前端跳转到任务详情页

#### Scenario: 下载 Excel
- **WHEN** 用户请求 `GET /api/fpa/tasks/{id}/download/excel`
- **THEN** 后端校验任务权限和文件可下载状态
- **AND** 不允许通过该接口下载 `AI分析.md`、`AI评估.md`、`FPA生成过程.json`、任务日志或其他过程文件

### Requirement: 平台壳与 FPA 页面结构

系统 SHALL 使用统一平台壳承载登录、顶部模块标识、顶部用户信息、内容区和公共错误页；FPA 首版包含任务列表、提交评估和任务详情三个页面。当前单模块 MVP 登录后 SHALL 默认进入 `/fpa/tasks`，不展示首页模块卡片或左侧模块栏。

`MVP` 保留英文，是软件交付阶段常用专有名词。

#### Scenario: 登录后默认进入任务列表
- **WHEN** 用户登录成功，或已登录用户访问 `/`、`/modules`
- **THEN** 前端进入 `/fpa/tasks`
- **AND** 不展示首页模块卡片、后续模块预留或单独平台首页

#### Scenario: 首版平台壳
- **WHEN** 用户进入任一 FPA 页面
- **THEN** 页面顶部展示 `FPA 工作量评估` 模块标识、当前用户、角色和退出入口
- **AND** 首版不展示左侧模块栏
- **AND** 不展示 `TeamTools / FPA 工作量评估` 面包屑

#### Scenario: FPA 页面切换
- **WHEN** 用户在 FPA 模块内操作
- **THEN** 可以在 `/fpa/tasks`、`/fpa/submit` 和 `/fpa/tasks/:id` 间切换
- **AND** FPA 页签展示 `任务列表`、`提交评估`、`查看详情`
- **AND** 当前页面应有明确选中态

### Requirement: 提交评估页交互

系统 MUST 在提交评估页按后端接口和输入规则控制表单状态，提交成功后进入任务详情页等待浏览器调用模型。页面 SHALL 按 Open Design 原型形成一屏优先的紧凑表单，开放系统选择、`规模计数时机`、`完整性级别`、目标人天、需求名称、Markdown 粘贴、`.md` 文件上传和本地 API Key 配置。

`Open Design`、`Markdown`、`API Key` 保留英文，是原型方法、文件格式和接口安全字段的既有命名。

#### Scenario: 表单配置加载
- **WHEN** 用户打开提交评估页
- **THEN** 前端调用 `GET /api/fpa/form-config`
- **AND** 系统选择、`规模计数时机` 和 `完整性级别` 使用后端返回的选项和默认值
- **AND** 当用户存在有效 `default_system_code` 时优先选中该系统，否则选中第一个可用系统

#### Scenario: 表单不可提交
- **WHEN** 系统未选择，或粘贴内容与上传文件均为空，或目标人天格式非法
- **THEN** 提交按钮不可用或提交返回参数错误
- **AND** 页面显示字段级提示

#### Scenario: 规模计数时机下拉
- **WHEN** 用户打开提交评估页
- **THEN** 页面展示 `规模计数时机` 下拉框
- **AND** 下拉选项文字包含系数前缀：`1.39 估算早期`、`1.21 估算中期`、`1.10 估算晚期`、`1.00 项目交付后及运维阶段`
- **AND** 默认值以后端配置返回为准，当前默认应为 `1.21 估算中期`

#### Scenario: 完整性级别下拉
- **WHEN** 用户打开提交评估页
- **THEN** 页面展示 `完整性级别` 下拉框
- **AND** 下拉选项文字包含系数前缀：`1.00 没有明确的完整性级别或等级为C/D`、`1.10 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式`、`1.30 完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施`
- **AND** 默认值以后端配置返回为准，当前默认应为 `1.10 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式`

```

Full source: openspec/changes/apply-open-design-fpa-frontend/specs/fpa-interface-ui/spec.md

## openspec/changes/apply-open-design-fpa-frontend/specs/platform-architecture/spec.md

- Source: openspec/changes/apply-open-design-fpa-frontend/specs/platform-architecture/spec.md
- Lines: 1-23
- SHA256: 5101e08000c1fbfb7adb6804b46ad4d96e493f2a72e7e77257e42fbcc800435f

```md
## MODIFIED Requirements

### Requirement: 平台分层与模块边界

系统 SHALL 以平台公共能力承载业务模块，并将认证、用户、任务、文件、配置、日志和结果下载作为可复用能力；业务模块只维护自己的输入契约、输出契约、脚本和资源文件。当前单模块 MVP MAY 在登录后直接进入 FPA 任务列表，并在首版隐藏左侧模块栏，但实现不得把平台长期入口、权限模型或公共能力写死为只能服务 FPA。

`MVP`、`FPA` 保留英文，是软件交付阶段和模块名的项目既有专有词。

#### Scenario: 新增业务模块
- **WHEN** 后续新增 `ops` 或其他业务模块
- **THEN** 模块通过公共任务、文件、配置和日志能力接入
- **AND** 模块不得直接修改其他模块内部实现或把平台入口写死为 FPA 专属逻辑

#### Scenario: 当前单模块入口
- **WHEN** 当前只启用 FPA 模块且用户登录成功
- **THEN** 前端可以默认进入 `/fpa/tasks`
- **AND** 页面可以隐藏首页模块卡片和左侧模块栏
- **AND** 顶部平台壳仍应保留模块标识、当前用户、角色、退出登录和 FPA 页签

#### Scenario: 平台首页路由
- **WHEN** 当前只启用 FPA 模块
- **THEN** 首页可以引导用户进入 FPA 或直接重定向到 FPA 任务列表
- **AND** 代码和文档不得把平台长期能力描述为只能服务 FPA

```
