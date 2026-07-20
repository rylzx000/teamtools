## MODIFIED Requirements

### Requirement: 任务列表与详情状态展示

系统 SHALL 以后端状态、权限字段和产物可见性驱动页面展示；列表页默认手动刷新，详情页可以按约定轮询。页面展示流程 SHALL 使用面向用户的简化阶段，不展示后台 JSON、payload、路由结构或过程文件。

#### Scenario: 详情页结果展示
- **WHEN** 任务已完成且普通用户打开自己的任务详情
- **THEN** 页面展示摘要条、目标命中、质量提示和 Excel 下载入口
- **AND** 普通用户不得查看、复制或下载 `AI分析.md`、`AI评估.md`、`AI结构化结果.json`、完整 `FPA生成过程.json`、AI 请求包、AI 请求摘要、脚本 payload、任务日志、原始模型响应或其他排查文件

#### Scenario: 管理员查看 AI 分析 Markdown
- **WHEN** 管理员打开已完成任务详情，且后端返回 `artifacts.ai_analysis_md.available = true`
- **THEN** 页面可以展示并复制 `AI分析.md` 或 `AI评估.md`
- **AND** 页面不得展示模型 Key、环境变量、服务器敏感路径或未脱敏堆栈

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
