# Comet Design Handoff

- Change: align-prod-auth-and-fpa-config
- Phase: design
- Mode: compact
- Context hash: 7ca63d90cd83f25806f691103f77c243a7e1e23859740856f28427f1f31cfa05

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/align-prod-auth-and-fpa-config/proposal.md

- Source: openspec/changes/align-prod-auth-and-fpa-config/proposal.md
- Lines: 1-34
- SHA256: bd9be92f418675bf8046e43fc11f86f0a54327fc513716261b52b2d5f6497107

```md
## Why

系统准备上线，本地开发环境需要与生产体验保持一致，避免开发默认账号、页面品牌、系统范围和默认系统行为与生产口径不一致。同时，当前账户密码能力不足，普通用户无法自助修改密码，管理员也无法按初始化口径安全重置用户密码。

## What Changes

- 本地开发和生产初始化用户统一使用生产初始化用户口径：用户名使用拼音，初始化密码来源为手机号或等价 `initial_password_seed`，任毅为管理员，首版不保留主要使用的 `admin/admin123` 账号。
- 登录页、浏览器标题和明显用户可见的 `TeamTools` 文案统一调整为 `FPA工作量评估` 相关文案；后端包名、内部 service 字段、API 路径和项目目录名暂不改。
- FPA 可选系统收敛为 `claimcar`（车险理赔核心系统）和 `claimoth`（非车险理赔核心系统），仅从配置、接口和前端选项层隐藏 `onlineclaim`、`clqp`，不删除历史资料目录。
- 用户默认系统调整为“有有效默认系统才自动选中；没有或无效则不自动选择”，后端不再为无默认系统用户兜底 `claimcar`，提交前必须显式选择系统。
- 右上角用户区域改为点击当前用户后展开菜单，菜单包含 `修改密码` 和 `退出登录`。
- 新增已登录用户修改自己密码能力，校验当前密码、新密码长度和空格规则，更新密码 hash 后保持登录状态。
- 新增管理员重置用户密码能力，将目标用户密码重置为初始化密码来源；普通用户不得调用，缺少初始化密码来源时返回明确错误。
- 同步更新部署/初始化、账户/权限或架构、FPA 模块或配置相关文档，并补充后端测试和前端构建/静态检查验证。

## Capabilities

### New Capabilities

- `account-password-management`: 覆盖初始化用户密码来源、普通用户修改密码、管理员按初始化来源重置密码、敏感字段不返回和不记录明文密码的账户密码能力。

### Modified Capabilities

- `platform-architecture`: 调整上线前本地/生产初始化口径、用户可见系统名称和平台壳用户菜单要求。
- `fpa-workflow`: 调整生产可选系统范围、系统资料选择边界和用户默认系统无效/缺失时的行为。
- `fpa-interface-ui`: 调整登录页/浏览器标题、顶部用户菜单、提交页系统下拉框、无默认系统不自动选中以及管理员用户列表重置密码入口。

## Impact

- 后端：认证/用户初始化、密码 hash 更新、管理员用户接口、FPA 配置接口、默认系统校验、相关单元测试。
- 前端：登录页标题、浏览器标题、顶部用户菜单、修改密码弹窗或轻量表单、提交页默认系统逻辑、管理员模型配置页用户列表操作、TypeScript 构建。
- 数据：用户数据需要保存初始化密码来源字段或等价数据，不保存当前密码明文，不在普通接口返回该字段。
- 配置与资料：FPA 系统配置只对外暴露 `claimcar` 和 `claimoth`；历史资料目录暂不删除。
- 文档：部署/初始化、账户/权限或架构、FPA 模块/配置文档同步更新生产用户、系统范围、默认系统和密码管理口径。

```

## openspec/changes/align-prod-auth-and-fpa-config/design.md

- Source: openspec/changes/align-prod-auth-and-fpa-config/design.md
- Lines: 1-91
- SHA256: 56382e5d323ac7039edf92a024367782c002916e56774aedfc84f9db18303e28

[TRUNCATED]

```md
## Context

系统上线前需要把本地开发环境和生产环境体验对齐。当前稳定规格中仍保留平台化描述和旧默认系统行为：FPA 提交页在没有有效默认系统时会选中第一个可用系统，顶部用户区直接展示退出入口，用户可见标题仍可能出现 `TeamTools`。同时，账户密码能力缺少普通用户修改密码和管理员按初始化来源重置密码的闭环。`TeamTools`、`FPA` 保留英文，是项目名和模块名。

本次 change 影响认证、用户初始化、FPA 配置、前端平台壳、管理员配置页、文档和测试，属于跨前后端与规格文档的上线前对齐工作。设计目标是最小改动，不改后端包名、内部 service 字段、API 路径、项目目录名，不删除历史资料目录，不引入复杂权限体系。

## Goals / Non-Goals

**Goals:**

- 本地和生产使用同一套生产初始化用户口径，初始化密码来源可用于管理员重置密码。
- 用户可见系统名称统一为 `FPA工作量评估`。
- FPA 可选系统仅对外暴露 `claimcar` 和 `claimoth`。
- 无有效默认系统时，前端不自动选中任何系统，后端不兜底 `claimcar`。
- 右上角用户区域通过菜单承载修改密码和退出登录。
- 后端提供已登录用户修改自己密码接口、管理员重置用户密码接口，并避免明文密码泄露。
- 补充后端测试、前端构建验证和相关文档。

**Non-Goals:**

- 不做忘记密码、自助找回、短信/邮箱验证码、密保问题。
- 不做管理员手动指定新密码、强制首次登录修改密码、用户删除。
- 不做大规模权限系统改造。
- 不重命名后端技术标识、API 路径、项目目录或历史资料目录。
- 不提交、不推送、不归档，除非用户后续明确要求。

## Decisions

### 1. 初始化密码来源作为重置种子保存

用户表或等价持久化结构增加 `initial_password_seed` 或复用已有安全字段保存初始化密码来源。初始化脚本写入该字段，并用其生成初始密码 hash。该字段只服务管理员重置密码，不在普通接口返回，不记录到任务事件或日志。

备选方案是只保存手机号字段并在重置时复用手机号。该方案如果项目已有手机号字段可减少字段数量；但如果手机号未来需要脱敏展示或变更，会与密码重置种子耦合。因此实现时优先复用现有初始化数据结构，必要时新增语义更明确的 `initial_password_seed`。

### 2. 不保留主要使用的 `admin/admin123`

初始化用户以生产名单为准，任毅为管理员。若现有启动或测试强依赖 `admin/admin123`，仅做最小兼容，并在测试或文档里说明该账号不是主要使用账号。这样避免上线前继续依赖开发默认密码，同时降低一次性改动风险。

### 3. FPA 系统范围在配置/接口层过滤

后端 FPA 配置接口和提交页系统列表只返回 `claimcar`、`claimoth`。历史资料目录和旧配置项暂不删除，避免误删未确认资料；如果已有 `systems.yaml` 包含 `onlineclaim`、`clqp`，本轮只在可选系统解析或对外响应处隐藏。

备选方案是删除旧系统资料和配置。该方案破坏性更强，不符合首版最小改动目标，因此不采用。

### 4. 默认系统只接受用户有效配置

后端配置接口返回当前用户有效默认系统；如果用户没有默认系统，或默认系统不在当前可选系统中，则返回空值或不返回默认系统。前端进入提交页时只在该值有效时选中，否则保持空选项。创建任务接口仍以必填系统做最终校验。

### 5. 用户菜单只改入口，不重做布局

顶部右侧保留当前用户名称/用户名展示，点击后展开轻量菜单。菜单包含 `修改密码` 和 `退出登录`。修改密码使用弹窗或轻量表单，成功后提示 `密码已修改` 并保持登录状态。

### 6. 密码接口沿用现有认证风格

新增接口优先按建议路径：

- `POST /api/auth/change-password`
- `POST /api/admin/users/{user_id}/reset-password`

如果代码已有管理员接口命名风格，路径可以最小调整，但必须覆盖同等语义。后端只接收 `current_password`、`new_password` 等必要字段；不返回密码明文；日志只记录操作成功/失败摘要和用户标识，不记录密码。

### 7. 文档就地更新

文档优先更新现有部署、架构/安全、FPA 模块或 UI 文档，不新增重复文档体系。OpenSpec delta spec 是规格变更来源，普通文档说明落地操作、初始化用户口径、生产系统列表和密码管理入口。

## Risks / Trade-offs

- 初始化数据缺少手机号或等价种子 → 实现时先检查现有初始化脚本和数据文件；不直接输出敏感内容；缺失用户重置时返回明确错误。
- 旧代码或测试依赖 `admin/admin123` → 先定位依赖；如强依赖则做最小兼容并补测试，避免扩大账号体系。
- FPA 历史系统仍存在资料目录 → 本轮只隐藏配置/接口层，避免资料误删；后续如确认无用再另开变更删除。
- 默认系统行为变化可能影响既有提交测试 → 后端和前端测试同时覆盖“无默认系统为空”和“有效默认系统选中”。
- 密码修改保持登录状态可能与会话缓存冲突 → 修改 hash 后不清理当前 session，仅影响后续登录验证。
- 管理员重置密码涉及敏感操作 → 接口严格校验管理员角色，并避免返回或记录明文初始化密码。

## Migration Plan

1. 检查现有初始化脚本、用户数据结构和测试夹具，确认生产初始化用户来源。
2. 增加或复用初始化密码来源字段，确保已有用户初始化时可写入。
3. 更新认证和管理员接口，补充修改密码、重置密码服务逻辑和测试。
4. 更新 FPA 系统配置过滤和默认系统返回逻辑。

```

Full source: openspec/changes/align-prod-auth-and-fpa-config/design.md

## openspec/changes/align-prod-auth-and-fpa-config/tasks.md

- Source: openspec/changes/align-prod-auth-and-fpa-config/tasks.md
- Lines: 1-46
- SHA256: 477af188bc110284e64383ff4ee5dc8e263b6a06867d09933ed31ae897d160c8

```md
## 1. 现状定位与初始化口径

- [ ] 1.1 检查现有用户初始化脚本、用户数据文件和测试夹具，确认生产初始化用户来源，不输出手机号、密码、token 或其他敏感明细。
- [ ] 1.2 检查是否存在对 `admin/admin123` 的启动、测试或文档强依赖；如存在，仅做最小兼容并记录说明。
- [ ] 1.3 确认用户持久化结构是否已有手机号或等价初始化密码来源字段；缺失时补充 `initial_password_seed` 或等价字段。

## 2. 后端账户密码能力

- [ ] 2.1 更新用户初始化逻辑，使本地和生产使用生产初始化用户口径，用户名为拼音，初始化密码来源可用于重置，任毅为管理员。
- [ ] 2.2 新增或调整数据库初始化逻辑，保存初始化密码来源，不保存当前密码明文，普通响应不返回该字段。
- [ ] 2.3 新增已登录用户修改自己密码接口，校验当前密码、新密码至少 6 位且不能全为空格，成功后更新密码 hash 并保持登录状态。
- [ ] 2.4 新增管理员重置用户密码接口，仅管理员可调用，将目标用户密码重置为初始化密码来源，缺少来源时返回 `该用户缺少初始化密码，无法重置`。
- [ ] 2.5 确保修改密码和重置密码路径不返回明文密码，不在日志、事件或错误详情中记录明文密码。

## 3. 后端 FPA 配置与默认系统

- [ ] 3.1 调整 FPA 系统配置读取或接口响应，只对外返回 `claimcar` 和 `claimoth`，隐藏 `onlineclaim`、`clqp`，不删除历史资料目录。
- [ ] 3.2 调整 `/api/fpa/config`、`/api/fpa/form-config` 或等价接口，使无默认系统用户不返回默认系统或返回空默认系统。
- [ ] 3.3 调整有效默认系统校验：仅当用户默认系统在当前可选系统中时返回；否则视为无默认系统。
- [ ] 3.4 确认创建 FPA 任务接口仍要求用户显式传入合法系统，未选择系统时拒绝提交。

## 4. 前端页面与交互

- [ ] 4.1 将浏览器 title、登录页主标题和明显用户可见 `TeamTools` 文案统一改为 `FPA工作量评估` 相关文案，保留必要技术标识。
- [ ] 4.2 调整提交页系统下拉框，只展示后端返回的 `claimcar`、`claimoth`，无有效默认系统时保持未选择状态。
- [ ] 4.3 将右上角用户区域改为点击当前用户名称或用户名后展开菜单，菜单包含 `修改密码` 和 `退出登录`。
- [ ] 4.4 增加修改密码弹窗或轻量表单，包含当前密码、新密码、确认新密码，并完成前端校验与成功提示 `密码已修改`。
- [ ] 4.5 在管理员用户/额度配置页用户列表增加 `重置密码` 操作，二次确认后调用后端接口，成功提示 `密码已重置为初始化密码`，不展示初始化密码来源。

## 5. 文档同步

- [ ] 5.1 更新部署或初始化文档，说明本地和生产初始化用户口径、初始化密码来源、管理员和生产系统列表。
- [ ] 5.2 更新架构、安全或账户权限相关文档，说明普通用户修改密码和管理员重置密码边界。
- [ ] 5.3 更新 FPA 模块或配置文档，说明当前生产可选系统仅 `claimcar`、`claimoth`，无默认系统时前端不自动选择。

## 6. 测试与验证

- [ ] 6.1 补充后端测试：配置接口不返回多余系统；无默认系统为空；有效默认系统返回；无效默认系统为空。
- [ ] 6.2 补充后端测试：正确当前密码可修改；当前密码错误失败；新密码少于 6 位失败；修改成功后旧密码不能登录、新密码可以登录。
- [ ] 6.3 补充后端测试：普通用户不能调用管理员重置接口；管理员可重置为初始化密码；缺少初始化密码来源时重置失败。
- [ ] 6.4 完成前端静态验证：右上角菜单包含 `修改密码` 和 `退出登录`；提交页无默认系统不自动选中；系统下拉框只展示 `claimcar`、`claimoth`。
- [ ] 6.5 运行 `openspec validate align-prod-auth-and-fpa-config --strict`。
- [ ] 6.6 运行 `cd backend; .\.venv\Scripts\python.exe -m unittest tests.test_fpa_mvp -v`。
- [ ] 6.7 运行 `pnpm --dir frontend exec tsc --noEmit`。
- [ ] 6.8 运行 `pnpm --dir frontend build`。
- [ ] 6.9 运行 `.\scripts\check-encoding.ps1`。

```

## openspec/changes/align-prod-auth-and-fpa-config/specs/account-password-management/spec.md

- Source: openspec/changes/align-prod-auth-and-fpa-config/specs/account-password-management/spec.md
- Lines: 1-62
- SHA256: da9b703794ae501f44cdc2172413aac633af6e26873358655898374a1f94d496

```md
## ADDED Requirements

### Requirement: 初始化用户与初始密码来源
系统 SHALL 在本地开发环境和生产环境使用同一套生产初始化用户口径。初始化用户的用户名 SHALL 使用拼音，初始化密码 SHALL 来自手机号或等价 `initial_password_seed` 字段；任毅 SHALL 具备管理员角色。系统 MUST 保存可用于管理员重置密码的初始化密码来源，但 MUST NOT 保存当前密码明文，普通用户接口 MUST NOT 返回该字段。`initial_password_seed` 保留英文，是数据字段命名。

#### Scenario: 本地和生产使用同一初始化口径
- **WHEN** 本地开发环境或生产环境执行用户初始化
- **THEN** 系统使用项目内已有初始化用户数据或脚本创建生产初始化用户
- **AND** 用户名为拼音
- **AND** 初始化密码来源为手机号或等价初始密码来源字段
- **AND** 任毅为管理员
- **AND** 系统不把 `admin/admin123` 作为主要使用账号初始化

#### Scenario: 初始化密码来源不进入普通响应
- **WHEN** 普通用户或管理员调用非重置用途的当前用户、用户列表或 FPA 配置接口
- **THEN** 响应不得包含初始化密码来源、当前密码明文或密码 hash

#### Scenario: 技术兜底账号兼容
- **WHEN** 现有代码强依赖技术兜底 `admin` 账号才能启动或测试
- **THEN** 系统 MAY 以最小兼容方式保留该依赖
- **AND** 文档必须说明该账号不是主要使用账号
- **AND** 不得扩大为新的账号体系

### Requirement: 用户修改自己的密码
系统 SHALL 允许已登录的普通用户和管理员修改自己的密码。接口 MUST 校验当前密码正确、新密码长度至少 6 位且不能全为空格，成功后更新密码 hash，并保持当前登录状态。系统 MUST NOT 返回、记录或写入日志中的明文密码。`hash` 保留英文，是密码存储技术术语。

#### Scenario: 正确当前密码修改成功
- **WHEN** 已登录用户提交正确当前密码和合法新密码
- **THEN** 系统更新该用户密码 hash
- **AND** 返回成功结果且不包含明文密码
- **AND** 当前登录状态保持有效

#### Scenario: 当前密码错误
- **WHEN** 已登录用户提交错误当前密码
- **THEN** 系统拒绝修改密码
- **AND** 原密码仍可使用
- **AND** 新密码不可用于登录

#### Scenario: 新密码不合法
- **WHEN** 已登录用户提交少于 6 位或全为空格的新密码
- **THEN** 系统拒绝修改密码
- **AND** 返回面向用户的明确错误

### Requirement: 管理员重置用户密码
系统 SHALL 允许管理员将目标用户密码重置为初始化密码来源。接口 MUST 仅允许管理员调用；普通用户 MUST NOT 重置其他用户密码。目标用户缺少初始化密码来源时，系统 MUST 返回明确错误。重置成功后系统 MUST 更新密码 hash，但 MUST NOT 返回或记录明文初始化密码。

#### Scenario: 管理员重置成功
- **WHEN** 管理员请求重置存在初始化密码来源的用户密码
- **THEN** 系统将目标用户密码 hash 更新为初始化密码来源对应的 hash
- **AND** 返回成功结果且不包含明文初始化密码
- **AND** 可记录后台事件或日志，但不得记录明文密码

#### Scenario: 普通用户不能重置别人密码
- **WHEN** 普通用户请求管理员重置密码接口
- **THEN** 系统拒绝请求并返回无权限
- **AND** 目标用户密码不变

#### Scenario: 缺少初始化密码来源
- **WHEN** 管理员请求重置缺少初始化密码来源的用户密码
- **THEN** 系统拒绝重置
- **AND** 返回 `该用户缺少初始化密码，无法重置`
- **AND** 目标用户密码不变

```

## openspec/changes/align-prod-auth-and-fpa-config/specs/fpa-interface-ui/spec.md

- Source: openspec/changes/align-prod-auth-and-fpa-config/specs/fpa-interface-ui/spec.md
- Lines: 1-131
- SHA256: 16939188197dbfb0f001e7771d0c7803e4cb06881ac675c65083e886c252eb93

[TRUNCATED]

```md
## MODIFIED Requirements

### Requirement: 平台壳与 FPA 页面结构

系统 SHALL 使用统一平台壳承载登录、顶部模块标识、顶部用户信息、内容区和公共错误页；FPA 首版包含任务列表、提交评估和任务详情三个普通用户页面。管理员 SHALL 额外看到 `模型配置` 页签，用于配置团队公用 Key、用户公用额度和管理员重置用户密码。当前单模块 MVP 登录后 SHALL 默认进入 `/fpa/tasks`，不展示首页模块卡片或左侧模块栏。浏览器标题、登录页主标题和明显用户可见系统名称 SHALL 使用 `FPA工作量评估`，不得展示明显的 `TeamTools` 用户可见文案。`MVP`、`Key` 保留英文，是软件交付阶段和密钥字段的既有命名。

#### Scenario: 登录页与浏览器标题
- **WHEN** 用户打开登录页
- **THEN** 浏览器标题展示 `FPA工作量评估`
- **AND** 登录页主标题或系统名称展示 `FPA工作量评估`
- **AND** 页面不展示明显的 `TeamTools` 用户可见文案

#### Scenario: 登录后默认进入任务列表
- **WHEN** 用户登录成功，或已登录用户访问 `/`、`/modules`
- **THEN** 前端进入 `/fpa/tasks`
- **AND** 不展示首页模块卡片、后续模块预留或单独平台首页

#### Scenario: 首版平台壳
- **WHEN** 用户进入任一 FPA 页面
- **THEN** 页面顶部展示 `FPA 工作量评估` 模块标识和当前用户
- **AND** 首版不展示左侧模块栏
- **AND** 不展示 `TeamTools / FPA 工作量评估` 面包屑

#### Scenario: 右上角用户菜单
- **WHEN** 用户点击右上角当前用户名称或用户名区域
- **THEN** 页面展开用户菜单
- **AND** 菜单项包含 `修改密码` 和 `退出登录`
- **AND** 退出登录入口不再裸露在右上角常驻展示

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

系统 MUST 在提交评估页按后端接口和输入规则控制表单状态，提交成功后进入任务详情页等待浏览器调用模型。页面 SHALL 按 Open Design 原型形成一屏优先的紧凑表单，开放系统选择、`规模计数时机`、`完整性级别`、目标人天、需求名称、Markdown 粘贴、`.md` / `.docx` 文件上传和 API Key 配置。系统选择 SHALL 仅展示 `claimcar` 和 `claimoth`；无有效默认系统时 SHALL 不自动选中任何系统。用户填写个人 API Key 时使用个人 Key；未填写时自动尝试使用团队公用 Key。`Open Design`、`Markdown`、`Word`、`API Key`、`.docx`、`claimcar`、`claimoth` 保留英文，是原型方法、文件格式、办公软件名称、接口安全字段和系统编码的既有命名。

#### Scenario: 表单配置加载
- **WHEN** 用户打开提交评估页
- **THEN** 前端调用 `GET /api/fpa/form-config`
- **AND** 系统选择、`规模计数时机` 和 `完整性级别` 使用后端返回的选项和默认值
- **AND** 系统下拉框仅展示 `claimcar` 和 `claimoth`
- **AND** 当用户存在有效 `default_system_code` 且该系统在当前选项中时优先选中该系统
- **AND** 当用户没有默认系统或默认系统不在当前选项中时，不自动选中任何系统

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

```

Full source: openspec/changes/align-prod-auth-and-fpa-config/specs/fpa-interface-ui/spec.md

## openspec/changes/align-prod-auth-and-fpa-config/specs/fpa-workflow/spec.md

- Source: openspec/changes/align-prod-auth-and-fpa-config/specs/fpa-workflow/spec.md
- Lines: 1-53
- SHA256: 952a0c7e9891c2e894d8c3f94a358696a6f73521c0f29b7e928c8f07b116786e

```md
## MODIFIED Requirements

### Requirement: 系统资料与无资料模式

系统 MUST 根据用户选择的单一系统读取配置和精简知识包；生产与本地当前仅对外提供 `claimcar`（车险理赔核心系统）和 `claimoth`（非车险理赔核心系统）。选择其他系统、系统未启用或配置为空资料目录时进入无资料模式或被提交入口拒绝。已配置系统资料缺少 `08-FPA场景拆分字典.md` 时允许继续，但必须标记为无系统字典模式；已配置系统基础资料缺失时不得静默降级。`claimcar`、`claimoth` 保留英文，是系统编码。

#### Scenario: 已配置系统资料可用
- **WHEN** `systems.yaml` 中的 `claimcar` 或 `claimoth` 启用且知识包文件存在
- **THEN** 后端优先读取 `08-FPA场景拆分字典.md` 作为场景路由关键资料
- **AND** 后端读取 `teamtools-system-brief.md` 作为系统背景资料
- **AND** 前端不得直接读取服务器资料目录

#### Scenario: 生产可选系统范围
- **WHEN** 前端加载 FPA 提交配置或系统列表
- **THEN** 后端仅返回 `claimcar` 和 `claimoth`
- **AND** 前端系统下拉框仅展示车险理赔核心系统和非车险理赔核心系统
- **AND** 系统不得展示、初始化或默认选择 `onlineclaim`、`clqp`

#### Scenario: 08 字典缺失
- **WHEN** 已配置系统存在基础资料但缺少 `08-FPA场景拆分字典.md`
- **THEN** 任务允许进入无系统字典模式
- **AND** `AI评估.md` 必须说明系统字典缺失、临时归类依据和待复核点

#### Scenario: 其他系统或空资料目录
- **WHEN** 用户选择其他系统或系统配置明确为空资料目录
- **THEN** 任务进入无资料模式或被提交入口拒绝
- **AND** AI 请求包中应说明无资料模式边界

#### Scenario: 已配置基础资料缺失
- **WHEN** 系统配置了知识目录但必要基础资料缺失或不可读
- **THEN** 任务失败并记录系统资料配置错误
- **AND** 系统不得自动降级为无资料模式

### Requirement: 用户默认系统

系统 SHALL 支持用户级默认系统 `default_system_code`，并在登录态和 `/api/auth/me` 返回该字段。FPA 提交页 SHALL 仅在当前用户存在有效 `default_system_code` 且该系统属于当前可选系统时默认选中该系统；当用户没有默认系统或默认系统无效时，前端 SHALL 不自动选中任何系统。后端 MUST NOT 为没有默认系统的用户兜底默认 `claimcar`。MVP 不要求提供个人设置页面或管理员配置页面。`MVP` 保留英文，是软件交付阶段常用专有名词。

#### Scenario: 使用用户默认系统创建任务
- **WHEN** 用户打开 FPA 提交页，且登录用户存在有效 `default_system_code`
- **THEN** 页面默认选中该系统
- **AND** 用户仍可手动切换到其他可用系统

#### Scenario: 无默认系统
- **WHEN** 用户默认系统为空或不存在
- **THEN** 页面不自动选中任何系统
- **AND** 后端配置接口不返回默认系统或返回空默认系统
- **AND** 用户必须明确选择系统后才能提交任务

#### Scenario: 默认系统不可用
- **WHEN** 用户默认系统不在当前系统列表中
- **THEN** 页面不自动选中任何系统
- **AND** 后端不得兜底返回 `claimcar`
- **AND** 用户必须明确选择系统后才能提交任务

```

## openspec/changes/align-prod-auth-and-fpa-config/specs/platform-architecture/spec.md

- Source: openspec/changes/align-prod-auth-and-fpa-config/specs/platform-architecture/spec.md
- Lines: 1-44
- SHA256: d5f7343d56f75c55ef024a468fd30f7ef841bc96193b207c4d4c63b3a965c501

```md
## MODIFIED Requirements

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

```
