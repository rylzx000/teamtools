# fpa-interface-ui Specification

## Purpose
定义 FPA 模块 API、页面结构、状态展示、按钮权限和用户可见产物规则，确保前端交互与后端任务状态一致。

## Source Documents

- `docs/modules/fpa/05-接口设计.md`
- `docs/ui/README.md`
- `docs/ui/01-整体页面设计.md`
- `docs/ui/modules/fpa-页面设计.md`
## Requirements
### Requirement: FPA API 资源边界

系统 SHALL 通过 FPA 任务资源接口完成提交页配置查询、系统查询、任务创建、AI 请求包获取、AI 结果回传、任务列表、任务详情、取消、重新运行和 Excel 下载。

`FPA`、`API`、`GET`、`POST`、`Excel`、`AI` 保留英文，是模块、接口协议、HTTP 方法、文件类型和能力名称的既有约定。

#### Scenario: 任务详情隐藏普通用户 AI 分析 Markdown
- **WHEN** 普通用户请求自己的已完成任务详情，且任务目录中存在 `AI分析.md` 或 `AI评估.md`
- **THEN** 后端返回 `artifacts.ai_analysis_md.available = false`
- **AND** `artifacts.ai_analysis_md.content = null`
- **AND** 响应不得包含 AI 分析 Markdown 正文、后台排查 JSON、任务日志、原始模型响应、服务器路径、环境变量或模型 Key

#### Scenario: 管理员任务详情返回 AI 分析 Markdown
- **WHEN** 管理员请求已完成任务详情，且任务目录中存在 `AI分析.md` 或 `AI评估.md`
- **THEN** 后端返回 `artifacts.ai_analysis_md.available = true`
- **AND** `artifacts.ai_analysis_md.content` 包含对应 Markdown 正文
- **AND** 响应仍不得包含模型 Key、环境变量或服务器敏感路径

### Requirement: 平台壳与 FPA 页面结构

系统 SHALL 使用统一平台壳承载登录、顶部模块标识、顶部用户信息、内容区和公共错误页；FPA 首版包含任务列表、提交评估和任务详情三个普通用户页面。管理员 SHALL 额外看到 `模型配置` 页签，用于配置团队公用 Key 和用户公用额度。当前单模块 MVP 登录后 SHALL 默认进入 `/fpa/tasks`，不展示首页模块卡片或左侧模块栏。

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
- **WHEN** 普通用户在 FPA 模块内操作
- **THEN** 可以在 `/fpa/tasks`、`/fpa/submit` 和 `/fpa/tasks/:id` 间切换
- **AND** FPA 页签展示 `任务列表`、`提交评估`、`查看详情`
- **AND** 当前页面应有明确选中态

#### Scenario: 管理员模型配置页签
- **WHEN** 管理员进入 FPA 模块
- **THEN** FPA 页签额外展示 `模型配置`
- **AND** 普通用户不得看到或访问该页签

### Requirement: 提交评估页交互

系统 MUST 在提交评估页按后端接口和输入规则控制表单状态，提交成功后进入任务详情页等待浏览器调用模型。页面 SHALL 按 Open Design 原型形成一屏优先的紧凑表单，开放系统选择、`规模计数时机`、`完整性级别`、目标人天、需求名称、Markdown 粘贴、`.md` / `.docx` 文件上传和 API Key 配置。用户填写个人 API Key 时使用个人 Key；未填写时自动尝试使用团队公用 Key。`Open Design`、`Markdown`、`Word`、`API Key`、`.docx` 保留英文，是原型方法、文件格式、办公软件名称和接口安全字段的既有命名。

#### Scenario: 表单配置加载
- **WHEN** 用户打开提交评估页
- **THEN** 前端调用 `GET /api/fpa/form-config`
- **AND** 系统选择、`规模计数时机` 和 `完整性级别` 使用后端返回的选项和默认值
- **AND** 当用户存在有效 `default_system_code` 时优先选中该系统，否则选中第一个可用系统

#### Scenario: 表单不可提交
- **WHEN** 系统未选择，或粘贴内容与上传文件均为空，或目标人天格式非法
- **THEN** 提交按钮不可用或提交返回参数错误
- **AND** 页面显示字段级提示

#### Scenario: 上传控件支持 Markdown 和 Word
- **WHEN** 用户在提交页选择或拖拽上传文件
- **THEN** 上传控件允许 `.md` 和 `.docx`
- **AND** 页面提示支持 Markdown / Word 文档
- **AND** 上传控件保留文件名、文件大小和移除能力

#### Scenario: 前端拒绝明显非法文件
- **WHEN** 用户选择 `.doc`、PDF、图片或 `.md` / `.docx` 以外的文件
- **THEN** 前端显示字段级提示并阻止提交
- **AND** 后端仍必须执行最终格式校验

#### Scenario: 前端文件大小提示
- **WHEN** 用户上传 `.md` 超过 256KB 或 `.docx` 超过 10MB
- **THEN** 前端显示文件过大提示并阻止提交
- **AND** 后端仍必须执行最终大小校验

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

#### Scenario: API Key 选择逻辑
- **WHEN** 用户在提交评估页填写个人 API Key
- **THEN** 前端使用该个人 Key 调用模型
- **AND** 任务不消耗公用 Key 额度

#### Scenario: 未填写 API Key 使用公用 Key
- **WHEN** 用户未填写个人 API Key
- **THEN** 页面提示未填写时将使用团队公用 Key 并消耗个人公用额度
- **AND** 调用模型前由前端向后端领取公用 Key 调用配置

#### Scenario: 公用额度已用完提示
- **WHEN** 用户未填写个人 API Key 且公用额度已用完
- **THEN** 页面提示 `公用apikey个人用量已用完，请输入可用的apikey`
- **AND** 前端不得继续使用公用 Key 调用模型

#### Scenario: 成功提交
- **WHEN** 任务创建成功
- **THEN** 页面跳转到任务详情页
- **AND** 详情页展示任务已创建、AI 请求包已生成、等待浏览器调用模型

### Requirement: 任务列表与详情状态展示

系统 SHALL 以后端状态、权限字段、输入解析警告和产物可见性驱动页面展示；列表页默认手动刷新，详情页可以按约定轮询。页面展示流程 SHALL 使用面向用户的简化阶段，不展示后台 JSON、payload、路由结构或过程文件。任务详情摘要 SHALL 增加当前用户公用 Key 余量展示。

#### Scenario: 详情页结果展示
- **WHEN** 任务已完成且普通用户打开自己的任务详情
- **THEN** 页面展示摘要条、目标命中、质量提示、Excel 下载入口和公用 Key 余量
- **AND** 普通用户不得查看、复制或下载 `AI分析.md`、`AI评估.md`、`AI结构化结果.json`、完整 `FPA生成过程.json`、AI 请求包、AI 请求摘要、脚本 payload、任务日志、原始模型响应或其他排查文件

#### Scenario: Word 图片忽略警告展示
- **WHEN** 任务详情或提交结果中包含 Word 图片内容被忽略的解析警告
- **THEN** 页面向用户展示“已忽略 Word 中的图片内容，如图片包含关键需求，请补充为文字后重新提交。”
- **AND** 页面不得展示服务器路径、堆栈、原始解析异常或内部临时文件名

#### Scenario: 公用 Key 余量展示
- **WHEN** 用户打开任务详情页
- **THEN** 任务摘要最后展示 `公用 Key 余量：剩余 x / 共 y 次`
- **AND** 该信息使用后端返回的当前用户额度，不根据前端本地计数推算

#### Scenario: 管理员查看 AI 分析 Markdown
- **WHEN** 管理员打开已完成任务详情，且后端返回 `artifacts.ai_analysis_md.available = true`
- **THEN** 页面可以展示并复制 `AI分析.md` 或 `AI评估.md`
- **AND** 页面不得展示模型 Key、环境变量、服务器敏感路径或未脱敏堆栈

### Requirement: 按钮与权限展示

系统 MUST 将按钮状态作为展示辅助，并由后端接口执行最终权限校验。低频操作 SHALL 放在详情页任务操作区或失败/排查区，不挤压列表核心操作。

#### Scenario: 下载按钮
- **WHEN** 任务已完成且后端返回 `can_download_excel = true`
- **THEN** 页面在列表和详情摘要区展示下载 Excel 入口
- **AND** 后端仍必须在下载接口校验当前用户权限

#### Scenario: 取消按钮
- **WHEN** 后端返回 `can_cancel = true`
- **THEN** 页面在详情页任务操作区展示取消入口
- **AND** 请求到达后端后仍必须校验任务状态和用户权限

#### Scenario: 复制并重新生成按钮
- **WHEN** 后端返回 `can_rerun = true`
- **THEN** 页面在详情页任务操作区或失败建议区展示复制并重新生成入口
- **AND** 任务列表页不得常驻展示该入口

### Requirement: 管理员模型配置页

系统 SHALL 为管理员提供 `模型配置` 页面。首版页面 MUST 包含单行公用 Key 配置区和用户额度管理表格；调用记录可以先由后端保存，不要求作为常驻页面区块展示。

#### Scenario: 公用 Key 配置区
- **WHEN** 管理员打开模型配置页
- **THEN** 页面单行展示公用 Key 启用状态、API Key 替换输入、默认个人额度、启用开关和保存按钮
- **AND** 页面说明公用 Key 会下发到浏览器，仅适合团队内部临时共享

#### Scenario: 用户额度管理表格
- **WHEN** 管理员打开模型配置页
- **THEN** 页面展示用户额度表格
- **AND** 表格列包含用户、角色、公用 Key 启用状态、总额度、已用次数、剩余次数和操作
- **AND** 操作包含单行保存、单人重置、统一设置额度和统一重置用量

#### Scenario: 普通用户禁止访问模型配置页
- **WHEN** 普通用户访问模型配置页路径或接口
- **THEN** 系统返回无权限
- **AND** 页面不得展示公用 Key 配置、用户额度表或管理员操作按钮

### Requirement: FPA 列表分页展示

系统 SHALL 在 FPA 任务列表和管理员模型配置页用户额度列表中使用统一分页控件。前端可选每页条数 MUST 为 10、20、50，并支持上一页、下一页、可点击页码、当前页禁用态和总条数展示。

#### Scenario: 任务列表分页
- **WHEN** 用户打开 FPA 任务列表
- **THEN** 前端按 `page` 和 `page_size` 请求 `/api/fpa/tasks`
- **AND** 页面展示后端返回的当前页任务
- **AND** 任务默认按创建时间倒序展示，最新任务在前

#### Scenario: 管理员额度列表分页
- **WHEN** 管理员打开模型配置页
- **THEN** 前端按 `page` 和 `page_size` 请求 `/api/admin/model-key/quotas`
- **AND** 页面展示后端返回的当前页用户额度
- **AND** 单人保存、单人重置、统一设置额度和统一重置用量仍可使用

#### Scenario: 每页条数切换
- **WHEN** 用户在分页控件中切换每页条数为 10、20 或 50
- **THEN** 前端重新请求第一页
- **AND** 不提供跳页输入框、无限滚动或复杂筛选能力

## Known Limits / 待确认点

- 接口文档建议任务详情页每 2-3 秒轮询，现有页面实现是否完全采用该频率需以代码和实际测试为准。
- FPA 页面设计引用 Open Design 原型，但 OpenSpec 只保留行为契约，不固化所有视觉细节。
