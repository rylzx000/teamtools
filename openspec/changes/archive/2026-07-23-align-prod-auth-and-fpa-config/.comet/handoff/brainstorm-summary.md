# Brainstorm Summary

- Change: align-prod-auth-and-fpa-config
- Date: 2026-07-23
- Status: 已确认

## 确认的事实

- 后端用户表当前包含 `password_hash` 和 `default_system_code`，尚无初始化密码来源字段。
- `initialize_database` 仅在 `TEAMTOOLS_SEED_DEV_USERS` 开启时调用 `seed_dev_users`，当前开发种子为 `admin/admin123` 和 `demo/demo123`。
- `scripts/import-users-from-excel.py` 已支持从 Excel 导入用户，预览只显示“密码已提供”，不会输出密码明文；当前导入时只保存密码 hash，不保存初始化密码来源。
- FPA 默认系统在 `get_form_config` 中由 `systems[0]["code"]` 兜底生成；前端 `SubmitPage` 也会在无默认系统时回退到 `data.defaults.system_code || data.systems[0]?.code`。
- FPA 系统清单当前包含 `claimcar`、`claimoth`、`onlineclaim`、`clqp`，数据配置文件和内置常量都包含四项。
- 前端登录页当前预填 `admin/admin123`，并展示 `TEAMTOOLS`、`登录 TeamTools`。
- 顶部用户区当前常驻展示 `退出登录`，管理员模型配置页已具备用户额度表，可在该表增加重置密码操作。

## 候选方案

### 方案 A：最小集中改动（推荐）

- 在 `users` 表增加 `initial_password_seed`，由初始化脚本、Excel 导入脚本和命令行创建用户脚本写入。
- 将开发种子改为生产初始化用户口径；如测试仍需要稳定账号，用测试夹具显式创建，不再把 `admin/admin123` 作为主要账号。
- 在 `main.py` 内新增两个认证相关接口，复用现有 `require_user`、`require_admin`、`hash_password`、`verify_password`。
- 在 FPA service 层定义生产可选系统集合，只让 `load_systems`、`get_form_config` 和任务创建入口接受 `claimcar`、`claimoth`；保留历史目录和资料文件。
- 前端在 `App.tsx` 内最小扩展用户菜单、修改密码表单、管理员重置按钮和默认系统逻辑；新增少量 CSS。
- 文档就地更新部署、数据库/安全、FPA 模块或 UI 文档。

### 方案 B：抽出独立 auth service

- 新建认证服务模块承载登录、改密、重置、用户初始化字段处理。
- 优点是边界更清晰；缺点是当前 `main.py` 规模尚可，短期会引入更多迁移和导入改动。

### 方案 C：重做用户管理页

- 新增完整管理员用户管理能力，把重置密码、角色、默认系统统一搬到新页面。
- 优点是长期更完整；缺点明显超出本轮“不做大规模权限系统改造”和最小改动目标。

## 推荐技术方案

采用方案 A。它贴合现有单文件 FastAPI 路由和前端单页结构，能最小实现上线前对齐需求，同时避免新建过多抽象或重构。

## 关键取舍与风险

- `initial_password_seed` 会保存手机号或等价初始化密码来源，属于敏感字段；实现中只用于重置，不进入 `public_user`、用户额度列表、FPA 配置接口或日志。
- Excel 导入脚本现有密码长度要求是 8 位；需求的新密码最少 6 位只适用于修改密码接口，不强行降低导入脚本规则，避免放宽初始化安全门槛。
- 对外仅展示 `claimcar`、`claimoth`，但不删除 `onlineclaim`、`clqp` 资料目录；历史测试和样例里引用旧系统的用例需要按“接口隐藏”目标调整或保留为内部校验。
- 修改密码成功后保持当前 session，不清理其他 session；本轮不做会话全量失效。
- 前端只做构建和静态验证，不引入新的前端测试框架。

## 测试策略

- 后端在 `backend/tests/test_fpa_mvp.py` 中补充配置接口、默认系统、修改密码、管理员重置密码、缺少初始化密码来源和普通用户越权测试。
- 后端复用现有测试客户端和 SQLite 临时库，测试用户通过夹具显式创建。
- 前端通过 `pnpm --dir frontend exec tsc --noEmit` 和 `pnpm --dir frontend build` 验证类型和构建。
- OpenSpec 和编码通过 `openspec validate align-prod-auth-and-fpa-config --strict`、`.\scripts\check-encoding.ps1` 验证。

## Spec Patch

当前暂不需要回写 delta spec。若实现中发现生产初始化用户数据无法落地或接口路径必须偏离建议路径，再补充对应 delta spec。

