---
comet_change: align-prod-auth-and-fpa-config
role: technical-design
canonical_spec: openspec
archived-with: 2026-07-23-align-prod-auth-and-fpa-config
status: final
---

# 上线环境与账户密码能力技术设计

## 背景

本次变更用于上线前对齐本地和生产体验，并补齐账户密码闭环。OpenSpec 变更 `align-prod-auth-and-fpa-config` 已定义四类契约：生产初始化用户、账户密码管理、FPA 系统范围和默认系统行为、前端标题与用户菜单。

当前实现较集中：

- `backend/app/db.py` 负责数据库 schema、密码 hash、用户初始化和迁移。
- `backend/app/main.py` 负责认证路由、当前用户、管理员校验和 FPA/API 路由注册。
- `backend/app/modules/fpa/service.py` 负责 FPA 系统配置、表单配置和任务创建。
- `scripts/import-users-from-excel.py` 已支持从 Excel 导入初始化用户，预览只显示“密码已提供”，适合继续沿用。
- `frontend/src/App.tsx` 承载登录页、顶部壳、提交页和管理员模型配置页。

设计目标是最小集中改动，不重命名后端技术标识、不重做用户管理页、不删除历史资料目录、不提交或推送。

## 方案

采用方案 A：最小集中改动。

### 用户数据与初始化

在 `users` 表增加 `initial_password_seed TEXT`。该字段保存初始化密码来源，例如手机号或等价初始化种子，仅用于管理员重置密码。它不进入 `public_user`、用户额度列表、FPA 表单配置、日志或事件消息。

`initialize_database` 的迁移逻辑补齐该列。生产和本地开发的正式初始化路径优先复用项目内已有导入脚本，用户名使用拼音、初始密码来源写入 `initial_password_seed`、任毅为管理员。由于真实初始化用户和手机号属于敏感数据，代码实现不在日志和测试输出中打印明细。若现有自动化测试仍强依赖稳定账号，`seed_dev_users` 仅保留为测试/本地兼容兜底，不作为生产主要账号。

`scripts/import-users-from-excel.py` 在导入时将 Excel 中的初始化密码同时用于 `password_hash` 和 `initial_password_seed`。预览继续只显示“已提供”，不输出明文。`scripts/create-user.py` 增加可选 `--initial-password-seed`；不传时可用本次设置的密码作为初始来源，便于管理员重置。

### 认证接口

在 `backend/app/main.py` 中沿用现有认证风格新增：

- `POST /api/auth/change-password`
- `POST /api/admin/users/{user_id}/reset-password`

修改密码流程：

1. `require_user` 校验登录。
2. 读取 `current_password` 和 `new_password`。
3. 校验当前密码正确。
4. 校验新密码长度至少 6 位且 `new_password.strip()` 非空。
5. 更新当前用户 `password_hash` 和 `updated_at`。
6. 返回 `{ "ok": true }`，保持当前 session。

管理员重置流程：

1. `require_admin` 校验管理员。
2. 查询目标用户。
3. 若用户不存在或禁用，返回明确错误。
4. 若 `initial_password_seed` 为空，返回 `该用户缺少初始化密码，无法重置`。
5. 使用 `hash_password(initial_password_seed)` 更新目标用户 `password_hash`。
6. 返回 `{ "ok": true }`，不返回初始化来源。

### FPA 系统范围与默认系统

在 `backend/app/modules/fpa/service.py` 中定义生产可选系统集合，例如 `PUBLIC_SYSTEM_CODES = {"claimcar", "claimoth"}`。

- `load_systems` 只返回这两个系统。
- `get_form_config` 接收可选 `user` 参数，仅当用户 `default_system_code` 在可选系统中时返回 `defaults.system_code`，否则返回 `None`。
- `system_by_code` 用于任务创建时拒绝非公开系统，避免用户绕过前端提交 `onlineclaim` 或 `clqp`。
- 历史资料目录、样例和旧配置不删除。

前端提交页只消费后端返回的系统列表。无有效默认系统时保持空选项，不再回退到 `data.defaults.system_code || data.systems[0]?.code`。

### 前端交互

`frontend/index.html` 的浏览器标题改为 `FPA工作量评估`。登录页去掉 `TEAMTOOLS`、`登录 TeamTools` 和开发账号提示，改为生产口径文案。登录框不再预填 `admin/admin123`。

顶部用户区改为按钮触发菜单：

- 按钮展示当前用户展示名和角色。
- 菜单包含 `修改密码` 和 `退出登录`。
- `退出登录` 不再常驻裸露。

修改密码使用轻量弹窗或表单：

- 字段：当前密码、新密码、确认新密码。
- 前端校验：当前密码不能为空，新密码至少 6 位，新密码和确认新密码一致。
- 成功后提示 `密码已修改`，关闭弹窗，保持登录状态。

管理员模型配置页在用户额度表操作列增加 `重置密码`。点击后用 `window.confirm` 做二次确认，成功后提示 `密码已重置为初始化密码`，不展示初始化来源。

### 文档

就地更新现有文档：

- `docs/deployment/02-服务器部署.md`：说明初始化用户导入、初始化密码来源、任毅管理员、生产系统列表。
- `docs/architecture/05-数据库设计.md` 或安全相关文档：说明 `initial_password_seed` 只用于管理员重置，不进入普通响应。
- `docs/modules/fpa/README.md` 或现有 FPA 配置文档：说明生产可选系统仅 `claimcar`、`claimoth`，无默认系统不自动选择。
- `docs/ui/modules/fpa-页面设计.md`：说明顶部用户菜单和修改密码入口。

## 测试策略

后端测试集中补充在 `backend/tests/test_fpa_mvp.py`：

- 配置接口只返回 `claimcar`、`claimoth`。
- 无默认系统用户返回空默认系统。
- 有有效默认系统用户返回该默认系统。
- 默认系统不在可选系统中时返回空默认系统。
- 正确当前密码可修改；当前密码错误失败；新密码少于 6 位失败。
- 修改成功后旧密码不能登录，新密码可以登录。
- 普通用户不能调用管理员重置接口。
- 管理员可重置用户密码为初始化密码。
- 缺少初始化密码来源时重置失败。
- 普通接口不返回 `initial_password_seed`。

前端不新增测试框架，通过 TypeScript 和构建验证：

- `pnpm --dir frontend exec tsc --noEmit`
- `pnpm --dir frontend build`

全量指定验证：

- `openspec validate align-prod-auth-and-fpa-config --strict`
- `cd backend; .\.venv\Scripts\python.exe -m unittest tests.test_fpa_mvp -v`
- `pnpm --dir frontend exec tsc --noEmit`
- `pnpm --dir frontend build`
- `.\scripts\check-encoding.ps1`

## 风险与缓解

- 初始化密码来源敏感：只持久化必要字段，不进入普通响应或日志。
- 真实初始化数据可能不在仓库内：先复用现有导入脚本；如需读取桌面 Excel，只做结构检查和导入，不输出敏感内容。
- 旧测试依赖 `admin/admin123`：测试夹具显式创建稳定用户，不把开发默认账号继续作为产品口径。
- 旧系统样例仍引用 `onlineclaim`、`clqp`：本轮只约束公开接口和任务创建入口，不删除历史样例。
- 修改密码保持 session：符合需求；本轮不实现全设备登出。

## 实施边界

不做忘记密码、验证码、管理员手动指定新密码、首次登录强制改密、用户删除、大权限改造、历史资料目录删除、提交、推送或归档。


