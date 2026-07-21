# Comet Design Handoff

- Change: shared-frontend-model-key-quota
- Phase: design
- Mode: compact
- Context hash: c3bbab4edb102061199c7d34ef4c9a7ee8cc860f29454478d407d36dbec4efb1

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/shared-frontend-model-key-quota/proposal.md

- Source: openspec/changes/shared-frontend-model-key-quota/proposal.md
- Lines: 1-34
- SHA256: 35b5291b0a069cbd675678e5f4d8a13968c7df8b4e052e3b27dcca66b560983d

```md
## Why

当前 FPA 模块依赖用户在浏览器填写个人 API Key 后直连模型；这符合服务器无法访问公网模型的网络条件，但会增加普通用户使用门槛。团队希望管理员可以配置一个临时团队公用 API Key，让未填写个人 Key 的普通用户也能完成评估，同时按用户独立统计和控制公用 Key 可用次数。

该方案明确接受“公用 Key 会下发到浏览器”的临时信任边界：它不解决 Key 防复制、防绕过或强安全限额问题，只面向当前小团队内网试用场景。

## What Changes

- 新增平台级模型公用 Key 与个人额度能力：管理员配置公用 Key、默认个人额度、用户额度、单人重置和统一重置。
- 调整模型调用边界：保留个人 API Key 浏览器直连模式；当用户未填写个人 Key 且公用 Key 启用、个人额度未用完时，前端向后端领取公用 Key 并在浏览器侧调用模型。
- 调整 FPA 任务流程：任务记录本次模型调用来源为 `personal_key` 或 `shared_key`；只有使用公用 Key 且任务最终成功生成 Excel 时才扣减 1 次个人公用额度，并且同一任务只能扣减一次。
- 调整普通用户页面：提交页保留现有 API Key 输入框；未填写时提示将使用团队公用 Key；任务摘要增加“公用 Key 余量”行。
- 新增管理员模型配置页签：展示公用 Key 配置卡片和用户额度管理表格；调用记录可先由后端保存，页面首版不强制常驻展示。
- 新增后台记录：保存公用模型配置、用户额度和调用/扣减记录，用于管理员排查和重置。

## Capabilities

### New Capabilities

- `model-key-quota`: 平台级公用模型 API Key 配置、每用户公用额度、调用来源记录、成功后扣减和管理员额度管理。

### Modified Capabilities

- `platform-architecture`: 模型调用边界从“仅用户本地 Key”扩展为“个人 Key 优先，临时公用 Key 可下发到前端”的显式例外，并说明该模式不是强安全方案。
- `fpa-workflow`: FPA 主链路增加调用来源、额度校验、Excel 成功后扣减和防重复扣减规则。
- `fpa-interface-ui`: FPA 提交页、详情摘要和管理员可见页签增加公用 Key 与额度展示/管理行为。

## Impact

- 后端：新增模型配置、用户额度、调用记录相关表和接口；扩展 FPA AI 请求包获取/模型调用配置领取、AI 结果回传、任务完成扣减逻辑。
- 前端：提交评估页 API Key 提示轻量调整；详情任务摘要增加公用 Key 余量；管理员新增 `模型配置` 页签和用户额度表格。
- 数据库：新增平台级模型配置和额度相关表；FPA 任务需记录调用来源和公用额度扣减状态。
- 安全：公用 Key 会被前端拿到并用于浏览器直连模型，无法防止用户复制或绕过平台调用；页面和文档必须明确这是团队内部临时共享模式。
- 测试：需要覆盖个人 Key 不扣减、公用 Key 成功扣减、失败不扣减、额度不足提示、单任务防重复扣减、管理员单人/统一重置。

```

## openspec/changes/shared-frontend-model-key-quota/design.md

- Source: openspec/changes/shared-frontend-model-key-quota/design.md
- Lines: 1-116
- SHA256: bd1309076c61141464c80037c7344ae8560c69e55146fbba049cf9144886b73d

[TRUNCATED]

```md
## Context

TeamTools 当前 FPA 主链路由后端生成 AI 请求包，前端浏览器使用用户本地 API Key 直连模型，再把 AI 结果回传后端生成 Excel。该模式适配“服务器不能访问公网模型 API、用户终端可访问模型 API”的网络条件，但要求每个用户都准备个人 API Key，首批团队试用不够方便。

本次变更引入管理员配置的团队公用 API Key。由于服务器仍不能访问模型 API，公用 Key 必须在用户触发调用时下发到浏览器，由浏览器直连模型。该模式是明确接受风险的内部临时共享方案，不提供 Key 防复制、防绕过或强安全限额能力。

## Goals / Non-Goals

**Goals:**

- 管理员可以配置公用模型 API Key、模型地址、模型名称、启用开关和默认个人额度。
- 普通用户页面保持轻量：用户填个人 Key 时优先使用个人 Key；未填个人 Key 时自动尝试使用公用 Key。
- 公用 Key 用量按用户独立配置和展示，默认个人额度初始值为 10 且可由管理员配置。
- 只有使用公用 Key 且任务最终成功生成 Excel 时，才扣减该用户 1 次公用额度。
- 管理员可以查看用户额度表，单独修改额度、单独重置用量、统一设置额度、统一重置用量。
- 系统记录调用来源和扣减结果，便于管理员排查。

**Non-Goals:**

- 不让服务器直接调用公网模型 API。
- 不实现 Key 防复制、防抓包、防用户绕过平台直接调用模型。
- 不实现按天、按月自动重置，不实现复杂计费、Token 统计或部门级额度。
- 不大改普通用户提交页和详情页；不新增普通用户模型配置页面。
- 不实现多供应商完整抽象，首版以 DeepSeek 兼容配置为主。

## Decisions

### Decision 1: 个人 Key 优先，公用 Key 兜底

普通用户提交页继续保留现有 API Key 输入框。前端调用模型前判断：

```text
用户填写个人 API Key -> 使用个人 Key，不消耗公用额度
用户未填写个人 API Key -> 向后端领取公用 Key 调用配置
```

理由：该方案不破坏现有用户习惯，也避免为了公用 Key 重做普通用户页面。公用 Key 只作为降低试用门槛的兜底能力。

### Decision 2: 公用 Key 下发到前端，但仅通过受控接口领取

后端保存管理员配置的公用 Key，并提供一次模型调用配置领取接口。领取时后端校验：

- 当前用户已登录。
- 当前任务属于用户本人或管理员有权访问。
- 任务处于可调用模型状态。
- 公用 Key 已启用且已配置。
- 当前用户公用额度未用完。

校验通过后，后端返回模型 API 地址、模型名和公用 Key。前端仍在浏览器侧调用模型。

理由：服务器不能访问模型 API，不能采用后端代理调用；受控领取至少可以在 TeamTools 页面内实现额度提示、调用来源标记和排查记录。

### Decision 3: 成功生成 Excel 后才扣减次数

领取公用 Key 本身不扣次数。前端回传 AI 结果后，后端校验 JSON 并生成 Excel；只有任务进入 `completed` 且 Excel 正式文件存在时，才扣减 1 次。

需要在 FPA 任务扩展信息或等价记录中保存：

- 本次调用来源：`personal_key` / `shared_key`
- 公用 Key 领取记录或调用票据。
- 公用额度是否已扣减。
- 扣减时间。

理由：用户关心的是最终能拿到可用 Excel；AI 调用失败、JSON 校验失败或 Excel 生成失败不应消耗公用次数。

### Decision 4: 额度按用户独立管理

新增平台级模型额度能力，保存每个用户的：

- 是否允许使用公用 Key。
- 总额度。
- 已用次数。
- 剩余次数。
- 最近成功扣减时间。

默认个人额度由管理员配置，初始默认值为 10。修改默认额度只影响后续新建额度记录；已有用户不自动跟随变化。管理员如需调整已有用户，通过“统一设置额度”显式执行。

理由：避免管理员修改默认值时误改已有用户剩余额度。

### Decision 5: 管理员模型配置页首版两个主区块

```

Full source: openspec/changes/shared-frontend-model-key-quota/design.md

## openspec/changes/shared-frontend-model-key-quota/tasks.md

- Source: openspec/changes/shared-frontend-model-key-quota/tasks.md
- Lines: 1-50
- SHA256: d32f77afe9bc21e11351121f92232ddac83db2dcea6714b642d9d7e294deab93

```md
## 1. 数据模型与配置基础

- [ ] 1.1 设计并落地公用模型配置、用户公用额度、模型调用事件三类数据结构，字段覆盖启用状态、供应商、API 地址、模型名称、Key 配置状态、默认额度、用户额度、已用次数、调用来源、扣减状态和错误摘要
- [ ] 1.2 扩展 FPA 任务记录或等价扩展信息，保存本次调用来源、调用票据、公用额度是否已扣减、扣减时间，确保同一任务可做幂等扣减判断
- [ ] 1.3 实现公用额度懒初始化：用户首次查询额度或领取公用 Key 时，按当前默认个人额度创建记录，且修改默认额度不自动改动已有用户额度
- [ ] 1.4 确保 API Key 不写入普通日志、任务响应、调用事件明细或前端静态代码，仅允许受控领取接口在校验通过后返回明文 Key

## 2. 后端接口与服务

- [ ] 2.1 新增管理员公用模型配置接口，支持读取配置状态、保存启用开关、供应商、API 地址、模型名称、公用 API Key 和默认个人额度，并对普通用户拒绝访问
- [ ] 2.2 新增管理员用户额度管理接口，支持额度列表、单人保存、单人重置、统一设置额度和统一重置用量
- [ ] 2.3 新增普通用户公用 Key 调用配置领取接口，校验登录用户、任务权限、任务状态、公用 Key 启用配置和用户剩余额度后返回调用配置与票据
- [ ] 2.4 扩展 FPA AI 结果回传和错误回传接口，记录 `personal_key` / `shared_key` 调用来源、调用状态、错误摘要和票据关联
- [ ] 2.5 扩展任务详情或额度查询接口，返回当前用户公用 Key 余量，供详情摘要展示“剩余 x / 共 y 次”
- [ ] 2.6 对所有新增接口补齐管理员与普通用户权限校验，确保普通用户不能读取公用 Key 配置、用户额度表或其他用户调用记录

## 3. FPA 工作流集成

- [ ] 3.1 在提交评估到模型调用之间接入调用来源选择：个人 Key 优先，未填个人 Key 时才领取公用 Key
- [ ] 3.2 在 Excel 正式生成且任务进入 `completed` 后扣减公用额度，且仅当任务调用来源为 `shared_key` 时扣减 1 次
- [ ] 3.3 实现防重复扣减逻辑：同一任务完成逻辑重复触发时不得重复增加已用次数
- [ ] 3.4 确保模型调用失败、AI 结构化结果校验失败、Excel 生成失败、任务取消等失败路径均不扣减公用额度
- [ ] 3.5 额度不足且未填写个人 Key 时返回或展示固定提示 `公用apikey个人用量已用完，请输入可用的apikey`
- [ ] 3.6 保持普通用户产物可见性不扩大：普通用户只看任务摘要和 Excel 下载，管理员才可查看 AI 分析或排查产物

## 4. 前端页面与交互

- [ ] 4.1 调整提交评估页 API Key 逻辑：保留现有输入框，填写个人 Key 时使用个人 Key，未填写时提示将使用团队公用 Key 并在调用前领取配置
- [ ] 4.2 在任务详情摘要最后增加公用 Key 余量行，展示后端返回的“剩余 x / 共 y 次”，不使用前端本地推算
- [ ] 4.3 为管理员增加 `模型配置` 页签和路由，普通用户不得看到页签，直接访问路径时展示无权限或跳转
- [ ] 4.4 实现公用 Key 配置卡片，包含启用开关、供应商、API 地址、模型名称、API Key 替换输入、Key 配置状态、默认个人额度、保存按钮和安全风险提示
- [ ] 4.5 实现用户额度管理表格，包含用户、角色、启用状态、总额度、已用次数、剩余次数、最近成功使用时间、单行保存、单人重置、统一设置额度和统一重置用量
- [ ] 4.6 保持普通用户页面轻量，不为普通用户新增独立模型配置页，不常驻展示调用记录区

## 5. 测试与验收

- [ ] 5.1 增加后端额度服务测试，覆盖懒初始化、默认额度变更不影响已有记录、单人调整、单人重置、统一设置额度和统一重置用量
- [ ] 5.2 增加后端接口权限测试，覆盖普通用户无法访问模型配置、额度管理和管理员排查数据
- [ ] 5.3 增加 FPA 流程测试，覆盖个人 Key 成功不扣减、公用 Key 成功生成 Excel 后扣减、失败不扣减和同一任务防重复扣减
- [ ] 5.4 增加公用 Key 领取测试，覆盖未启用、未配置、额度不足、任务无权限、任务状态不可调用和成功领取
- [ ] 5.5 增加前端关键交互验证，覆盖提交页个人 Key 优先、公用 Key 兜底、额度不足提示、详情余量展示和管理员模型配置页权限
- [ ] 5.6 验证调用事件不保存 API Key 明文，普通任务详情响应不包含公用 Key 明文或未脱敏敏感信息

## 6. 文档与交付检查

- [ ] 6.1 更新相关架构、部署或模块文档，说明公用 Key 下发浏览器是内部临时共享模式，不提供强安全限额或防复制能力
- [ ] 6.2 更新初始化或管理员操作说明，说明默认个人额度、单人重置、统一设置额度、统一重置用量和 Key 关闭回滚方式
- [ ] 6.3 运行 `openspec validate shared-frontend-model-key-quota --strict`，确保 change 文档结构和 delta spec 校验通过
- [ ] 6.4 运行后端测试、前端构建或项目约定的针对性检查，并运行 `.\scripts\check-encoding.ps1`
- [ ] 6.5 完成实现后复核 `tasks.md` 勾选状态、关键风险和未覆盖项，再进入 Comet 下一阶段验证

```

## openspec/changes/shared-frontend-model-key-quota/specs/fpa-interface-ui/spec.md

- Source: openspec/changes/shared-frontend-model-key-quota/specs/fpa-interface-ui/spec.md
- Lines: 1-117
- SHA256: ce1bee71e0e529b2e822734789998cfa115f857b1b4421e90c361d920f748057

[TRUNCATED]

```md
## MODIFIED Requirements

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

系统 MUST 在提交评估页按后端接口和输入规则控制表单状态，提交成功后进入任务详情页等待浏览器调用模型。页面 SHALL 按 Open Design 原型形成一屏优先的紧凑表单，开放系统选择、`规模计数时机`、`完整性级别`、目标人天、需求名称、Markdown 粘贴、`.md` 文件上传和 API Key 配置。用户填写个人 API Key 时使用个人 Key；未填写时自动尝试使用团队公用 Key。

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

```

Full source: openspec/changes/shared-frontend-model-key-quota/specs/fpa-interface-ui/spec.md

## openspec/changes/shared-frontend-model-key-quota/specs/fpa-workflow/spec.md

- Source: openspec/changes/shared-frontend-model-key-quota/specs/fpa-workflow/spec.md
- Lines: 1-48
- SHA256: 20a54f0e1f9e53dc50dbd0fa2209d752b9b4c8f337f3196cccb44b78918785af

```md
## MODIFIED Requirements

### Requirement: FPA 主处理链路

系统 SHALL 按“提交评估 -> 生成 AI 请求包 -> 等待AI调用 -> 前端选择个人 Key 或公用 Key 调用模型 -> 回传 AI 响应 -> 提取 AI评估.md 和结构化 JSON -> 校验事实/路由/冻结清单 -> 生成 Excel -> 成功任务按需扣减公用额度 -> 下载结果”的流程处理任务，并把 AI 业务判断与脚本确定性生成分离。普通用户可见结果只包含摘要和 Excel 下载；`AI评估.md`、结构化 JSON 和过程 JSON 作为管理员复核或后台排查产物。

#### Scenario: 成功完成任务
- **WHEN** 前端回传合法 AI 响应
- **THEN** 后端提取并保存 `AI评估.md` 和 `AI结构化结果.json`
- **AND** 后端校验 JSON 中的变更事实、场景路由、拆分/合并决策和冻结功能点清单
- **AND** 后端基于同一组冻结清单生成 Excel 脚本输入 payload、`FPA生成过程.json` 和 `FPA工作量评估.xlsx`
- **AND** 任务完成后用户可以查看摘要并下载 Excel

#### Scenario: 个人 Key 调用成功
- **WHEN** 用户填写个人 API Key 并成功完成 FPA 任务
- **THEN** 任务调用来源记录为 `personal_key`
- **AND** 系统不得扣减该用户公用 Key 额度

#### Scenario: 公用 Key 调用成功
- **WHEN** 用户未填写个人 API Key，使用公用 Key 并成功生成 Excel
- **THEN** 任务调用来源记录为 `shared_key`
- **AND** 系统在 Excel 正式文件生成后扣减该用户 1 次公用额度
- **AND** 同一任务不得重复扣减

#### Scenario: 模型调用失败
- **WHEN** 前端调用模型失败并回传脱敏错误
- **THEN** 后端保存 `AI调用错误.json` 并将任务标记为失败
- **AND** 普通用户看到失败阶段、具体原因和建议操作
- **AND** 如该任务使用公用 Key，系统不得扣减公用额度

#### Scenario: JSON 校验失败
- **WHEN** AI 输出不是合法结构、枚举不符合契约、缺少冻结清单或冻结清单无法追溯到事实/路由
- **THEN** 任务失败且不生成 Excel
- **AND** 用户可以基于原输入复制或重新运行任务
- **AND** 如该任务使用公用 Key，系统不得扣减公用额度

#### Scenario: AI 回传后后端校验失败
- **WHEN** 前端成功调用模型并回传响应，但后端校验 AI 结构化结果失败
- **THEN** 后端返回任务状态 `failed`
- **AND** 前端提示 AI 结果校验失败或展示失败摘要
- **AND** 前端不得提示 Excel 已生成
- **AND** 如该任务使用公用 Key，系统不得扣减公用额度

#### Scenario: 冻结清单与产物一致
- **WHEN** 任务生成正式结果
- **THEN** `AI评估.md`、Excel 明细和过程 JSON 中的功能点数量、顺序、类型和 `stable_id` 必须保持一致
- **AND** 任一产物生成失败时不得进入 `completed`
- **AND** 公用额度扣减只能发生在正式结果进入 `completed` 之后

```

## openspec/changes/shared-frontend-model-key-quota/specs/model-key-quota/spec.md

- Source: openspec/changes/shared-frontend-model-key-quota/specs/model-key-quota/spec.md
- Lines: 1-113
- SHA256: e22dc9640a04c3e92d4cb60fb3e8828b3c1ec62e1d15e7d87fa7883e3cf43152

[TRUNCATED]

```md
## ADDED Requirements

### Requirement: 公用模型配置

系统 MUST 支持管理员配置团队公用模型调用参数，包括启用开关、模型供应商、API 地址、模型名称、公用 API Key 和默认个人额度。公用 API Key 当前允许由后端保存并按受控接口下发到浏览器，但不得写入前端代码、普通日志或普通用户任务响应。

`API Key`、`DeepSeek` 保留英文，是第三方接口凭证和模型供应商专有名词。

#### Scenario: 管理员保存公用 Key 配置
- **WHEN** 管理员提交公用模型配置
- **THEN** 系统保存启用状态、供应商、API 地址、模型名称、公用 API Key 和默认个人额度
- **AND** 默认个人额度缺省值为 10，且管理员可以修改
- **AND** 页面后续只显示 Key 已配置状态或掩码状态，不默认回显完整明文 Key

#### Scenario: 普通用户不能查看公用 Key 配置
- **WHEN** 普通用户请求公用模型配置管理接口
- **THEN** 系统拒绝访问
- **AND** 响应不得包含公用 API Key 明文、掩码或配置详情

#### Scenario: 公用 Key 关闭
- **WHEN** 管理员关闭公用 Key
- **THEN** 普通用户未填写个人 API Key 时不得领取公用 Key 调用配置
- **AND** 页面提示用户输入可用的 API Key

### Requirement: 用户公用额度

系统 MUST 为每个用户维护独立的公用 Key 额度，包括是否启用、总额度、已用次数、剩余次数和最近成功使用时间。新建额度记录 MUST 使用当前默认个人额度；修改默认个人额度不得自动修改已有用户额度。

#### Scenario: 新用户额度初始化
- **WHEN** 用户首次需要公用 Key 额度记录，且该用户尚无额度记录
- **THEN** 系统按当前默认个人额度创建额度记录
- **AND** 初始已用次数为 0
- **AND** 初始启用状态为允许使用公用 Key

#### Scenario: 管理员单独调整用户额度
- **WHEN** 管理员修改某个用户的总额度或启用状态并保存
- **THEN** 系统只更新该用户额度记录
- **AND** 剩余次数按 `max(总额度 - 已用次数, 0)` 计算

#### Scenario: 管理员单独重置用户用量
- **WHEN** 管理员对某个用户执行重置
- **THEN** 系统将该用户已用次数清零
- **AND** 记录重置时间和操作管理员

#### Scenario: 管理员统一设置额度
- **WHEN** 管理员输入新的统一额度并确认
- **THEN** 系统将所有用户的总额度设置为该值
- **AND** 不自动清零已用次数，除非管理员另行执行统一重置

#### Scenario: 管理员统一重置用量
- **WHEN** 管理员确认统一重置用量
- **THEN** 系统将所有用户的已用次数清零
- **AND** 记录统一重置时间和操作管理员

### Requirement: 公用 Key 调用配置领取

系统 SHALL 在用户未填写个人 API Key 时，允许前端为当前 FPA 任务领取公用 Key 调用配置。领取接口 MUST 校验登录用户、任务访问权限、任务状态、公用 Key 启用状态和用户剩余额度。

#### Scenario: 领取公用 Key 成功
- **WHEN** 普通用户未填写个人 API Key，当前任务可调用模型，公用 Key 已启用且该用户剩余额度大于 0
- **THEN** 后端返回模型供应商、API 地址、模型名称、公用 API Key 和调用票据
- **AND** 后端记录本次任务调用来源为 `shared_key`
- **AND** 领取本身不得扣减已用次数

#### Scenario: 公用额度已用完
- **WHEN** 普通用户未填写个人 API Key，且个人公用额度剩余次数为 0
- **THEN** 系统不得返回公用 API Key
- **AND** 前端提示 `公用apikey个人用量已用完，请输入可用的apikey`

#### Scenario: 使用个人 Key
- **WHEN** 普通用户填写个人 API Key 并调用模型
- **THEN** 前端不得领取公用 Key 调用配置
- **AND** 后端记录本次任务调用来源为 `personal_key`
- **AND** 该任务不得消耗公用 Key 额度

### Requirement: 成功后扣减公用额度

系统 MUST 仅在任务使用公用 Key 且最终成功生成 Excel 后扣减用户公用额度。AI 调用失败、AI 结果校验失败、Excel 生成失败或任务取消不得扣减公用额度。

#### Scenario: 公用 Key 成功生成 Excel 后扣减

```

Full source: openspec/changes/shared-frontend-model-key-quota/specs/model-key-quota/spec.md

## openspec/changes/shared-frontend-model-key-quota/specs/platform-architecture/spec.md

- Source: openspec/changes/shared-frontend-model-key-quota/specs/platform-architecture/spec.md
- Lines: 1-40
- SHA256: c32eb51b5de48bc75a86fa9eda3ab42de03c69e6078f53845940cbceec64db87

```md
## MODIFIED Requirements

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

```
