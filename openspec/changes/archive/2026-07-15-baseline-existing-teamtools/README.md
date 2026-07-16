# baseline-existing-teamtools

TeamTools 现有成果物的 OpenSpec 基线索引，不迁移原文全文。

## 用途

- 作为 TeamTools 现有文档的 OpenSpec 基线索引。
- 记录 `README.md`、`docs/architecture/`、`docs/deployment/`、`docs/modules/` 和 `docs/ui/` 下已有 Markdown 文档的位置、标题和用途。
- 不迁移、不复制、不改写原文档全文；需要业务细节时回源阅读原文件。
- 不包含业务代码改动。

## 索引范围

### 根目录

| 文档 | 标题 | 用途 |
|---|---|---|
| `README.md` | TeamTools | 项目定位、当前范围、目录和编码检查入口 |
| `AGENTS.md` | TeamTools 项目工作规则 | 项目协作规则、编码规则和 OpenSpec / Comet 使用规则 |

### docs/architecture/

| 文档 | 标题 | 用途 |
|---|---|---|
| `docs/architecture/01-技术架构.md` | 技术架构 | 平台分层、模型调用边界、模块边界和部署原则 |
| `docs/architecture/02-数据与文件存储.md` | 数据与文件存储 | 数据目录、任务目录、运行产物和落盘规则 |
| `docs/architecture/03-任务处理与结果生成设计.md` | 任务处理与结果生成设计 | 任务状态、AI 请求包、校验、Excel 生成和失败处理 |
| `docs/architecture/04-安全边界.md` | 安全边界 | 敏感信息和记录边界 |
| `docs/architecture/05-数据库设计.md` | 数据库设计 | 用户、任务、文件、事件和 FPA 扩展表 |
| `docs/architecture/06-编码与文本文件规范.md` | 编码与文本文件规范 | UTF-8 编码规则和检查命令 |

### docs/deployment/

| 文档 | 标题 | 用途 |
|---|---|---|
| `docs/deployment/01-本地开发.md` | 本地开发 | 本地启动、数据目录和开发前提 |
| `docs/deployment/02-服务器部署.md` | 服务器部署 | 服务器目录、部署形态、持久化和安全权限 |

### docs/modules/fpa/

| 文档 | 标题 | 用途 |
|---|---|---|
| `docs/modules/fpa/README.md` | FPA 工作量评估模块 | 模块定位、文档列表和当前边界 |
| `docs/modules/fpa/01-已确认需求.md` | FPA 已确认需求 | FPA 模块目标、输入、权限、状态和非目标范围 |
| `docs/modules/fpa/02-任务流程设计.md` | FPA 任务流程设计 | 提交、AI 请求、执行阶段、取消和重新运行流程 |
| `docs/modules/fpa/03-数据与文件设计.md` | FPA 数据与文件设计 | FPA 任务目录、输入合并、结果命名和权限 |
| `docs/modules/fpa/04-FPA计算规则.md` | FPA 计算规则 | 功能点、人天、目标命中和质量提示计算口径 |
| `docs/modules/fpa/05-接口设计.md` | FPA 接口设计 | FPA API、状态码、权限和页面接口关系 |
| `docs/modules/fpa/06-资源包与生成契约设计.md` | FPA 资源包与生成契约设计 | 模板、schema、提示词、脚本和资源更新契约 |
| `docs/modules/fpa/07-AI输出与提示词契约设计.md` | FPA AI 输出与提示词契约设计 | AI JSON、提示词、枚举、禁止字段和校验 |
| `docs/modules/fpa/08-Excel映射与脚本生成设计.md` | FPA Excel 映射与脚本生成设计 | Excel 模板、映射、动态行、脚本和样例 |
| `docs/modules/fpa/09-系统资料蒸馏规则.md` | FPA 系统资料蒸馏规则 | 精简知识包结构、长度、证据和维护规则 |
| `docs/modules/fpa/10-AI请求包与提示词合成设计.md` | FPA AI 请求包与提示词合成设计 | 请求包生成、前后端职责、系统资料读取和错误处理 |

### docs/ui/

| 文档 | 标题 | 用途 |
|---|---|---|
| `docs/ui/README.md` | TeamTools 页面设计 | UI 文档入口和当前边界 |
| `docs/ui/01-整体页面设计.md` | TeamTools 整体页面设计 | 平台壳、导航、顶部栏、内容区和公共状态 |
| `docs/ui/modules/fpa-页面设计.md` | FPA 模块页面设计 | FPA 提交页、列表页、详情页、按钮和权限规则 |

## 能力规格映射

| Spec | 能力范围 | 主要来源 |
|---|---|---|
| `platform-architecture` | 平台架构、模型调用边界、部署、安全和编码底线 | `README.md`、`docs/architecture/01-技术架构.md`、`docs/deployment/` |
| `task-processing` | 统一任务、文件、事件、目录和数据库口径 | `docs/architecture/02-数据与文件存储.md`、`03-任务处理与结果生成设计.md`、`05-数据库设计.md` |
| `fpa-workflow` | FPA 输入、系统资料、主流程、取消、失败、重新运行和结果可见性 | `docs/modules/fpa/01-已确认需求.md`、`02-任务流程设计.md`、`03-数据与文件设计.md` |
| `fpa-interface-ui` | FPA API、页面结构、状态展示、按钮权限和用户可见产物 | `docs/modules/fpa/05-接口设计.md`、`docs/ui/` |
| `fpa-ai-contract` | AI 请求包、提示词、系统资料、AI JSON、校验和敏感信息边界 | `docs/modules/fpa/07-AI输出与提示词契约设计.md`、`09-系统资料蒸馏规则.md`、`10-AI请求包与提示词合成设计.md` |
| `fpa-excel-output` | 三类 JSON、脚本 payload、模板保真、功能点计算、目标命中和质量提示 | `docs/modules/fpa/04-FPA计算规则.md`、`06-资源包与生成契约设计.md`、`08-Excel映射与脚本生成设计.md` |

## 后续使用规则

- 新增功能、流程、架构或接口变更时，先基于本索引定位原始文档，再创建独立 OpenSpec change。
- 如果后续确需把某个文档内容补充为更细粒度 spec，应单独提出迁移 change，并说明迁移范围。
- 规格中的业务规则以当前代码、自动化测试和现行文档的交叉验证结果为基础。
- 文档与实现存在冲突时，不静默选择一方；在对应 spec 的“Known Limits / 待确认点”中记录。
- API 完整报文、UI 全量文案、模板单元格细节、脚本实现和历史版本说明只保留路径引用。
