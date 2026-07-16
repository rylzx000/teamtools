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

系统 SHALL 以平台公共能力承载业务模块，并将认证、用户、任务、文件、配置、日志和结果下载作为可复用能力；业务模块只维护自己的输入契约、输出契约、脚本和资源文件。

#### Scenario: 新增业务模块
- **WHEN** 后续新增 `ops` 或其他业务模块
- **THEN** 模块通过公共任务、文件、配置和日志能力接入
- **AND** 模块不得直接修改其他模块内部实现或把平台入口写死为 FPA 专属逻辑

#### Scenario: 平台首页路由
- **WHEN** 当前只启用 FPA 模块
- **THEN** 首页可以引导用户进入 FPA
- **AND** 代码和文档不得把平台长期能力描述为只能服务 FPA

### Requirement: 模型调用边界

系统 MUST 由后端生成任务级 AI 请求包，并由前端或用户端调用外部模型；首版后端不得保存模型 API Key，也不得把公网模型调用作为服务器侧主链路。

#### Scenario: 前端获取请求包并调用模型
- **WHEN** 用户提交任务后进入模型调用步骤
- **THEN** 后端提供已生成的 AI 请求包
- **AND** 前端使用用户本地填写的 API Key 调用外部模型并回传结果或失败信息

#### Scenario: 后端生成请求包
- **WHEN** 后端生成 AI 请求包
- **THEN** 请求包由模块模板、用户输入、系统资料摘要和页面参数组成
- **AND** 前端不得自行拼接完整提示词、读取服务器资料目录或决定 FPA 计算规则

### Requirement: 部署与持久化边界

系统 SHALL 支持本地轻量开发和服务器单机部署，并保证运行数据、上传文件、任务结果、SQLite 数据库和日志位于可持久化目录。

#### Scenario: 本地开发
- **WHEN** 开发者在本地运行 TeamTools
- **THEN** 前端、后端和数据目录按 README 与部署文档约定启动
- **AND** `TEAMTOOLS_DATA_DIR` 默认指向项目根目录下的 `data/`

#### Scenario: 服务器部署
- **WHEN** 服务以 Docker Compose 或无 Docker 方式部署到服务器
- **THEN** `data/` 与 `logs/` 必须挂载或放置在持久化目录
- **AND** 容器重建、镜像更新或服务重启不得丢失上传文件、任务结果和数据库

### Requirement: 安全与编码底线

系统 MUST 不向前端、普通用户、AI 请求包或日志暴露模型密钥、Cookie、环境变量、服务器敏感路径、其他用户任务数据或未脱敏错误详情。

#### Scenario: 用户查看任务失败原因
- **WHEN** 普通用户查看失败任务
- **THEN** 页面只展示脱敏后的失败阶段、原因和建议操作
- **AND** 完整堆栈、服务器路径和敏感配置仅允许管理员排查或不进入用户可见响应

#### Scenario: 交付前编码检查
- **WHEN** 修改文本文件、Markdown、JSON、YAML、TypeScript、JavaScript、Python、HTML、CSS 或 PowerShell 脚本
- **THEN** 文件必须保持 UTF-8 编码
- **AND** 交付前优先运行 `.\scripts\check-encoding.ps1`

## Known Limits / 待确认点

- README 当前描述“单机、无 Docker、无 Nginx”，架构文档和服务器部署文档同时给出 Docker Compose 推荐形态；后续变更需要明确当前实际部署口径。
- 当前 MVP 不引入 Redis、消息队列、Nginx、微服务拆分或服务端模型代理；这些能力只能通过后续 OpenSpec change 引入。
