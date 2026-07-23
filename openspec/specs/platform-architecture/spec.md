# platform-architecture Specification

## Purpose
定义 TeamTools 作为轻量内网 AI 工具平台的总体架构、模块边界、模型调用边界、部署和安全底线，确保后续模块扩展复用平台能力而不是把平台固化为单一 FPA 应用。

## Source Documents

- `README.md`
- `docs/architecture/01-技术架构.md`
- `docs/architecture/04-安全边界.md`
- `docs/architecture/06-编码与文本文件规范.md`
- `docs/deployment/01-本地开发.md`
- `docs/deployment/02-服务器部署.md`
## Requirements
### Requirement: 平台分层与模块边界

系统 SHALL 以平台公共能力承载业务模块，并将认证、用户、任务、文件、配置、日志和结果下载作为可复用能力；业务模块只维护自己的输入契约、输出契约、脚本和资源文件。当前单模块 MVP MAY 在登录后直接进入 `/fpa/tasks`，并在首版隐藏左侧模块栏；上线首版用户可见系统名称 SHALL 统一为 `FPA工作量评估`，但实现不得把后端包名、内部 service 字段、API 路径或项目目录名重命名为 FPA 专属命名，也不得把平台长期入口、权限模型或公共能力写死为只能服务 FPA。`MVP`、`FPA`、`service`、`API` 保留英文，是软件交付阶段、模块名和技术标识。

#### Scenario: 新增业务模块
- **WHEN** 后续新增 `ops` 或其他业务模块
- **THEN** 模块通过公共任务、文件、配置和日志能力接入
- **AND** 模块不得直接修改其他模块内部实现或把平台入口写死为 FPA 专属逻辑

#### Scenario: 当前单模块入口
- **WHEN** 当前只启用 FPA 模块且用户登录成功
- **THEN** 前端可以默认进入 `/fpa/tasks`
- **AND** 页面可以隐藏首页模块卡片和左侧模块栏
- **AND** 顶部平台壳仍应保留模块标识、当前用户、角色和 FPA 页签
- **AND** 用户操作入口通过右上角用户菜单承载修改密码和退出登录

#### Scenario: 平台首页路由
- **WHEN** 当前只启用 FPA 模块
- **THEN** 首页可以引导用户进入 FPA 或直接重定向到 FPA 任务列表
- **AND** 代码和文档不得把平台长期能力描述为只能服务 FPA

### Requirement: 模型调用边界

系统 MUST 由后端生成任务级 AI 请求包，并由前端或用户端调用外部模型；首版后端不得把公网模型调用作为服务器侧主链路。系统 SHALL 支持两种前端直连模式：用户填写个人 API Key 时使用个人 Key；用户未填写个人 Key 且管理员启用公用 Key 时，通过后端受控接口领取公用 Key 调用配置并在浏览器侧调用模型。公用 Key 下发到前端是明确接受风险的团队内部临时共享模式，不提供 Key 防复制、防绕过或强安全限额能力。

#### Scenario: 前端获取请求包并调用模型
- **WHEN** 用户提交任务后进入模型调用步骤
- **THEN** 后端提供已生成的 AI 请求包
- **AND** 前端优先使用用户本地填写的 API Key 调用外部模型并回传结果或失败信息

#### Scenario: 未填写个人 Key 时使用公用 Key
- **WHEN** 用户未填写个人 API Key，且公用 Key 已启用、已配置、该用户公用额度未用完
- **THEN** 前端通过后端受控接口领取公用 Key 调用配置
- **AND** 前端使用领取到的公用 Key 在浏览器侧调用外部模型
- **AND** 系统记录该任务调用来源为公用 Key

#### Scenario: 后端生成请求包
- **WHEN** 后端生成 AI 请求包
- **THEN** 请求包由模块模板、用户输入、系统资料摘要和页面参数组成
- **AND** 前端不得自行拼接完整提示词、读取服务器资料目录或决定 FPA 计算规则

### Requirement: 部署与持久化边界

系统 SHALL 支持本地轻量开发和服务器单机部署，并保证运行数据、上传文件、任务结果、SQLite 数据库和日志位于可持久化目录。本地开发环境和生产环境 SHALL 使用同一套生产初始化用户口径，避免本地默认账号和生产账号体验不一致。`SQLite` 保留英文，是数据库名称。

#### Scenario: 本地开发
- **WHEN** 开发者在本地运行系统
- **THEN** 前端、后端和数据目录按 README 与部署文档约定启动
- **AND** `TEAMTOOLS_DATA_DIR` 默认指向项目根目录下的 `data/`
- **AND** 用户初始化使用生产初始化用户口径

#### Scenario: 服务器部署
- **WHEN** 服务以 Docker Compose 或无 Docker 方式部署到服务器
- **THEN** `data/` 与 `logs/` 必须挂载或放置在持久化目录
- **AND** 容器重建、镜像更新或服务重启不得丢失上传文件、任务结果和数据库
- **AND** 用户初始化使用生产初始化用户口径

#### Scenario: 初始化密码来源持久化
- **WHEN** 初始化脚本创建或更新用户数据
- **THEN** 系统持久化管理员重置密码所需的初始化密码来源
- **AND** 不持久化当前密码明文
- **AND** 普通接口不得返回初始化密码来源

### Requirement: 安全与编码底线

系统 MUST 不向普通用户、AI 请求包或日志暴露 Cookie、环境变量、服务器敏感路径、其他用户任务数据或未脱敏错误详情。模型密钥的默认安全边界是不得写入前端代码、日志或普通任务响应；仅在管理员启用公用 Key 且用户通过受控接口领取调用配置时，系统 MAY 将公用 API Key 下发到当前浏览器用于模型调用，并必须在文档和管理员页面说明该模式无法防止用户复制或绕过平台使用。

#### Scenario: 用户查看任务失败原因
- **WHEN** 普通用户查看失败任务
- **THEN** 页面只展示脱敏后的失败阶段、原因和建议操作
- **AND** 完整堆栈、服务器路径和敏感配置仅允许管理员排查或不进入用户可见响应

#### Scenario: 公用 Key 不进入普通日志
- **WHEN** 用户领取公用 Key 或回传模型调用结果
- **THEN** 系统日志、任务事件和调用记录不得保存 API Key 明文
- **AND** 普通任务详情响应不得包含公用 Key，除非该响应是专用调用配置领取接口的返回

#### Scenario: 交付前编码检查
- **WHEN** 修改文本文件、Markdown、JSON、YAML、TypeScript、JavaScript、Python、HTML、CSS 或 PowerShell 脚本
- **THEN** 文件必须保持 UTF-8 编码
- **AND** 交付前优先运行 `.\scripts\check-encoding.ps1`

### Requirement: 公共分页响应协议

系统 SHALL 提供可复用的后端分页能力，用于平台内列表接口统一解析 `page` 和 `page_size` 参数、限制页大小、计算 `LIMIT/OFFSET` 并返回统一分页元数据。默认 `page = 1`，默认 `page_size = 20`，`page_size` 最大值为 100。

#### Scenario: 默认分页参数
- **WHEN** 列表接口未传入 `page` 或 `page_size`
- **THEN** 后端使用 `page = 1` 和 `page_size = 20`
- **AND** 响应包含 `items`、`total`、`page`、`page_size`、`pages`、`has_next` 和 `has_prev`

#### Scenario: 页大小上限
- **WHEN** 客户端传入 `page_size` 大于 100
- **THEN** 后端将实际 `page_size` 限制为 100
- **AND** `limit`、`offset` 和响应元数据均以限制后的值计算

#### Scenario: 分页元数据计算
- **WHEN** 后端已知总数、当前页和页大小
- **THEN** `pages` 按总数向上取整计算，空列表总页数为 0
- **AND** `has_prev` 仅在当前页大于 1 时为 `true`
- **AND** `has_next` 仅在当前页小于总页数时为 `true`

## Known Limits / 待确认点

- README 当前描述“单机、无 Docker、无 Nginx”，架构文档和服务器部署文档同时给出 Docker Compose 推荐形态；后续变更需要明确当前实际部署口径。
- 当前 MVP 不引入 Redis、消息队列、Nginx、微服务拆分或服务端模型代理；这些能力只能通过后续 OpenSpec change 引入。
