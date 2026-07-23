---
change: align-prod-auth-and-fpa-config
design-doc: docs/superpowers/specs/2026-07-23-align-prod-auth-and-fpa-config-design.md
base-ref: 0564c72c6aaea297489dd88398465cdc0ddcc79a
archived-with: 2026-07-23-align-prod-auth-and-fpa-config
---

# 上线环境与账户密码能力 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. 本计划按用户要求不包含 `git commit`、`git push`、建 PR 或部署步骤。

**Goal:** 让本地与生产初始化用户、FPA 系统范围、默认系统、页面标题、用户菜单、修改密码和管理员重置密码能力在上线前对齐。

**Architecture:** 采用最小集中改动：在现有 SQLite `users` 表补 `initial_password_seed`，在现有 FastAPI `main.py` 增加密码接口，在 FPA service 层过滤公开系统和默认系统，在 `App.tsx` 扩展轻量用户菜单与弹窗。文档就地更新，不新建重复文档体系。

**Tech Stack:** FastAPI、SQLite、Python unittest、React、TypeScript、Vite、PowerShell、OpenSpec、Comet。

archived-with: 2026-07-23-align-prod-auth-and-fpa-config
---

## File Structure

- Modify: `backend/app/db.py`：用户表 schema、迁移、生产口径初始化用户、密码 hash 字段写入。
- Modify: `backend/app/main.py`：修改密码、管理员重置密码接口；FPA 表单配置传入当前用户。
- Modify: `backend/app/modules/fpa/service.py`：公开系统过滤、默认系统返回、任务创建系统校验。
- Modify: `scripts/import-users-from-excel.py`：导入时写入初始化密码来源但不输出明文。
- Modify: `scripts/create-user.py`：支持初始化密码来源参数。
- Modify: `backend/tests/test_fpa_mvp.py`：后端覆盖用户初始化、默认系统、改密、重置密码、系统过滤。
- Modify: `frontend/index.html`：浏览器标题。
- Modify: `frontend/src/App.tsx`：登录页文案、用户菜单、修改密码弹窗、提交页默认系统、管理员重置密码按钮。
- Modify: `frontend/src/styles.css`：用户菜单和弹窗样式。
- Modify: `docs/deployment/02-服务器部署.md`：初始化用户、初始化密码来源、生产系统列表。
- Modify: `docs/architecture/05-数据库设计.md`：`initial_password_seed` 字段和安全边界。
- Modify: `docs/modules/fpa/README.md`：生产可选系统与默认系统口径。
- Modify: `docs/ui/modules/fpa-页面设计.md`：顶部用户菜单和修改密码入口。
- Modify: `openspec/changes/align-prod-auth-and-fpa-config/tasks.md`：完成实现后按任务勾选。

### Task 1: 后端账户密码测试先行

**Files:**
- Modify: `backend/tests/test_fpa_mvp.py`
- Later modify: `backend/app/db.py`
- Later modify: `backend/app/main.py`

- [x] **Step 1: 扩展测试辅助方法**

在 `backend/tests/test_fpa_mvp.py` 的 `add_user` helper 增加 `default_system_code` 和 `initial_password_seed` 参数，并写入新列。先写成目标形态，让测试在当前 schema 下失败。

```python
    def add_user(
        self,
        db_path: Path,
        *,
        user_id: str,
        username: str,
        display_name: str,
        password: str = "pass123",
        role: str = "user",
        default_system_code: str | None = None,
        initial_password_seed: str | None = None,
    ) -> None:
        now = utc_now()
        with open_connection(db_path) as conn:
            conn.execute(
                """
                INSERT INTO users(
                    id, username, display_name, password_hash, role,
                    default_system_code, initial_password_seed, enabled, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    user_id,
                    username,
                    display_name,
                    hash_password(password),
                    role,
                    default_system_code,
                    initial_password_seed,
                    now,
                    now,
                ),
            )
            conn.commit()
```

- [x] **Step 2: 写修改密码失败测试**

在 `backend/tests/test_fpa_mvp.py` 增加：

```python
    def test_change_password_requires_current_password_and_valid_new_password(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            client = self.make_client(tmp_path)
            self.login(client, "demo", "demo123")

            wrong_current = client.post(
                "/api/auth/change-password",
                json={"current_password": "wrong-password", "new_password": "newpass1"},
            )
            self.assertEqual(wrong_current.status_code, 400, wrong_current.text)

            too_short = client.post(
                "/api/auth/change-password",
                json={"current_password": "demo123", "new_password": "12345"},
            )
            self.assertEqual(too_short.status_code, 400, too_short.text)

            blank = client.post(
                "/api/auth/change-password",
                json={"current_password": "demo123", "new_password": "      "},
            )
            self.assertEqual(blank.status_code, 400, blank.text)
```

- [x] **Step 3: 写修改密码成功测试**

```python
    def test_change_password_replaces_login_password_and_keeps_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            client = self.make_client(tmp_path)
            self.login(client, "demo", "demo123")

            changed = client.post(
                "/api/auth/change-password",
                json={"current_password": "demo123", "new_password": "newpass1"},
            )
            self.assertEqual(changed.status_code, 200, changed.text)
            self.assertTrue(changed.json()["ok"])
            self.assertEqual(client.get("/api/auth/me").status_code, 200)

            client.post("/api/auth/logout")
            old_login = client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
            self.assertEqual(old_login.status_code, 401, old_login.text)

            new_login = client.post("/api/auth/login", json={"username": "demo", "password": "newpass1"})
            self.assertEqual(new_login.status_code, 200, new_login.text)
```

- [x] **Step 4: 写管理员重置密码测试**

```python
    def test_admin_can_reset_user_password_to_initial_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            db_path = tmp_path / "teamtools-test.db"
            client = self.make_client(tmp_path)
            self.add_user(
                db_path,
                user_id="user-reset",
                username="resetuser",
                display_name="重置用户",
                password="changed1",
                initial_password_seed="13900000000",
            )
            self.login(client, "admin", "admin123")

            response = client.post("/api/admin/users/user-reset/reset-password")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()["ok"])
            self.assertNotIn("13900000000", json.dumps(response.json(), ensure_ascii=False))

            client.post("/api/auth/logout")
            reset_login = client.post("/api/auth/login", json={"username": "resetuser", "password": "13900000000"})
            self.assertEqual(reset_login.status_code, 200, reset_login.text)
```

- [x] **Step 5: 写管理员重置边界测试**

```python
    def test_reset_password_requires_admin_and_initial_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            db_path = tmp_path / "teamtools-test.db"
            client = self.make_client(tmp_path)
            self.add_user(db_path, user_id="user-no-seed", username="noseed", display_name="无种子", password="oldpass1")

            self.login(client, "demo", "demo123")
            forbidden = client.post("/api/admin/users/user-no-seed/reset-password")
            self.assertEqual(forbidden.status_code, 403, forbidden.text)

            client.post("/api/auth/logout")
            self.login(client, "admin", "admin123")
            missing_seed = client.post("/api/admin/users/user-no-seed/reset-password")
            self.assertEqual(missing_seed.status_code, 400, missing_seed.text)
            self.assertEqual(missing_seed.json()["detail"], "该用户缺少初始化密码，无法重置")
```

- [x] **Step 6: 验证 RED**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest tests.test_fpa_mvp.FpaMvpTest.test_change_password_requires_current_password_and_valid_new_password -v
```

Expected: FAIL，原因是 `/api/auth/change-password` 不存在或 `initial_password_seed` 列不存在。

### Task 2: 后端账户密码实现

**Files:**
- Modify: `backend/app/db.py`
- Modify: `backend/app/main.py`
- Modify: `scripts/import-users-from-excel.py`
- Modify: `scripts/create-user.py`
- Test: `backend/tests/test_fpa_mvp.py`

- [x] **Step 1: 更新 users schema 和迁移**

在 `backend/app/db.py` 的 `users` 建表语句中加入：

```sql
initial_password_seed TEXT,
```

在 `migrate_current_schema` 中加入：

```python
    if "initial_password_seed" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN initial_password_seed TEXT")
```

- [x] **Step 2: 更新开发种子为生产口径字段**

在 `seed_dev_users` 中把 tuple 调整为包含 `initial_password_seed`。如仍保留测试需要的 `admin/demo`，必须把注释写明为测试/本地兼容账号，不作为生产主要账号。

```python
    users = [
        ("dev-admin", "admin", "管理员", "admin", "admin123", "admin123", None),
        ("dev-demo", "demo", "演示用户", "user", "demo123", "demo123", None),
    ]
```

插入字段包含 `initial_password_seed`；已有用户更新时只用 `COALESCE(initial_password_seed, ?)` 补空，不覆盖已有来源。

- [x] **Step 3: 更新 Excel 导入脚本**

在 `scripts/import-users-from-excel.py` 的 INSERT/UPDATE SQL 中写入 `initial_password_seed = row.password`，预览保持：

```python
print(f"{row.row_number}\t{row.username}\t{row.display_name}\t{row.role}\t{default_system}\t已提供")
```

不要打印 `row.password`。

- [x] **Step 4: 更新 create-user 脚本**

在 `scripts/create-user.py` 增加参数：

```python
parser.add_argument("--initial-password-seed", help="管理员重置密码使用的初始化密码来源；不传时使用本次登录密码")
```

保存时使用：

```python
initial_password_seed = args.initial_password_seed or password
```

INSERT/UPDATE 写入该字段。

- [x] **Step 5: 新增修改密码接口**

在 `backend/app/main.py` 导入 `hash_password`：

```python
from .db import fetch_one, hash_password, initialize_database, open_connection, task_count, utc_now, verify_password
```

在 `/api/auth/me` 附近新增：

```python
    @app.post("/api/auth/change-password")
    async def change_password(request: Request) -> dict[str, bool]:
        user = require_user(request)
        payload = await read_payload(request)
        current_password = str(payload.get("current_password") or "")
        new_password = str(payload.get("new_password") or "")
        if not current_password:
            raise FpaError("当前密码不能为空", 400, "auth")
        if len(new_password) < 6 or not new_password.strip():
            raise FpaError("新密码至少 6 位且不能全为空格", 400, "auth")
        with open_connection(app_db_path) as conn:
            current = fetch_one(conn, "SELECT * FROM users WHERE id = ? AND enabled = 1", (user["id"],))
            if not current or not verify_password(current_password, current["password_hash"]):
                raise FpaError("当前密码错误", 400, "auth")
            conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (hash_password(new_password), utc_now(), user["id"]),
            )
            conn.commit()
        return {"ok": True}
```

- [x] **Step 6: 新增管理员重置接口**

在管理员额度接口附近新增：

```python
    @app.post("/api/admin/users/{user_id}/reset-password")
    async def admin_reset_user_password(request: Request, user_id: str) -> dict[str, bool]:
        require_admin(request)
        with open_connection(app_db_path) as conn:
            target = fetch_one(conn, "SELECT * FROM users WHERE id = ? AND enabled = 1", (user_id,))
            if not target:
                raise FpaError("用户不存在", 404, "permission")
            seed = str(target.get("initial_password_seed") or "")
            if not seed:
                raise FpaError("该用户缺少初始化密码，无法重置", 400, "auth")
            conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (hash_password(seed), utc_now(), user_id),
            )
            conn.commit()
        return {"ok": True}
```

- [x] **Step 7: 验证 GREEN**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest tests.test_fpa_mvp.FpaMvpTest.test_change_password_requires_current_password_and_valid_new_password tests.test_fpa_mvp.FpaMvpTest.test_change_password_replaces_login_password_and_keeps_session tests.test_fpa_mvp.FpaMvpTest.test_admin_can_reset_user_password_to_initial_seed tests.test_fpa_mvp.FpaMvpTest.test_reset_password_requires_admin_and_initial_seed -v
```

Expected: PASS。

### Task 3: FPA 系统范围与默认系统

**Files:**
- Modify: `backend/tests/test_fpa_mvp.py`
- Modify: `backend/app/modules/fpa/service.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_fpa_mvp.py`

- [x] **Step 1: 写系统过滤和默认系统测试**

在 `backend/tests/test_fpa_mvp.py` 增加或改造 `test_form_config_returns_safe_options`，断言：

```python
            system_codes = [item["code"] for item in payload["systems"]]
            self.assertEqual(system_codes, ["claimcar", "claimoth"])
            self.assertIsNone(payload["defaults"]["system_code"])
```

新增有效默认系统测试：

```python
    def test_form_config_returns_valid_user_default_system(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            db_path = tmp_path / "teamtools-test.db"
            client = self.make_client(tmp_path)
            with open_connection(db_path) as conn:
                conn.execute("UPDATE users SET default_system_code = ? WHERE username = ?", ("claimoth", "demo"))
                conn.commit()
            self.login(client, "demo", "demo123")
            response = client.get("/api/fpa/form-config")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["defaults"]["system_code"], "claimoth")
```

新增无效默认系统测试：

```python
    def test_form_config_ignores_unavailable_default_system(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            db_path = tmp_path / "teamtools-test.db"
            client = self.make_client(tmp_path)
            with open_connection(db_path) as conn:
                conn.execute("UPDATE users SET default_system_code = ? WHERE username = ?", ("onlineclaim", "demo"))
                conn.commit()
            self.login(client, "demo", "demo123")
            response = client.get("/api/fpa/form-config")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIsNone(response.json()["defaults"]["system_code"])
```

- [x] **Step 2: 验证 RED**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest tests.test_fpa_mvp.FpaMvpTest.test_form_config_returns_safe_options -v
```

Expected: FAIL，当前返回四个系统或默认第一个系统。

- [x] **Step 3: 实现公开系统过滤**

在 `backend/app/modules/fpa/service.py` 增加：

```python
PUBLIC_SYSTEM_CODES = {"claimcar", "claimoth"}


def public_system_entries(data_dir: Path) -> list[dict[str, Any]]:
    return [item for item in system_entries(data_dir) if item.get("code") in PUBLIC_SYSTEM_CODES]
```

调整 `load_systems` 使用 `public_system_entries`。

- [x] **Step 4: 实现用户默认系统**

调整 `get_form_config` 签名：

```python
def get_form_config(data_dir: Path, user: dict[str, Any] | None = None) -> dict[str, Any]:
    systems = load_systems(data_dir)
    system_codes = {item["code"] for item in systems}
    default_system = user.get("default_system_code") if user else None
    if default_system not in system_codes:
        default_system = None
```

`defaults.system_code` 使用 `default_system`。

在 `backend/app/main.py` 中改为：

```python
    @app.get("/api/fpa/form-config")
    async def fpa_form_config(request: Request) -> dict[str, Any]:
        user = require_user(request)
        return get_form_config(app_data_dir, user)
```

- [x] **Step 5: 拒绝非公开系统提交**

在 `system_by_code` 找到系统后，如果 `code not in PUBLIC_SYSTEM_CODES`，抛出：

```python
raise FpaError("系统编码不存在", 400, "task_create")
```

保留 `system_entries` 返回全部配置，供内部或后续资料维护使用。

- [x] **Step 6: 验证 GREEN**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest tests.test_fpa_mvp.FpaMvpTest.test_form_config_returns_safe_options tests.test_fpa_mvp.FpaMvpTest.test_form_config_returns_valid_user_default_system tests.test_fpa_mvp.FpaMvpTest.test_form_config_ignores_unavailable_default_system -v
```

Expected: PASS。

### Task 4: 前端标题、用户菜单、改密和管理员重置

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [x] **Step 1: 修改标题和登录页文案**

在 `frontend/index.html`：

```html
<title>FPA工作量评估</title>
```

在 `LoginPage`：

```tsx
const [username, setUsername] = useState('');
const [password, setPassword] = useState('');
```

展示文案改为：

```tsx
<span className="brand-mark">FPA</span>
<p className="eyebrow">工作量评估</p>
<h1>FPA工作量评估</h1>
<p className="subtle">请输入分配的账号和初始化密码登录。</p>
```

- [x] **Step 2: 前端默认系统不兜底**

在 `SubmitPage` 的 form-config 加载逻辑中替换 `preferred` 计算：

```tsx
const defaultSystem = data.defaults.system_code || '';
const preferred = data.systems.some((item) => item.code === defaultSystem) ? defaultSystem : '';
setSystemCode(preferred);
```

不要使用 `data.systems[0]?.code` 兜底。

- [x] **Step 3: 增加修改密码状态与提交函数**

在 `App` 中增加状态：

```tsx
const [showPasswordDialog, setShowPasswordDialog] = useState(false);
```

把 `Shell` 参数扩展为 `onChangePassword={() => setShowPasswordDialog(true)}`，并在 Shell 后渲染：

```tsx
{showPasswordDialog && (
  <ChangePasswordDialog
    onClose={() => setShowPasswordDialog(false)}
    setNotice={setNotice}
  />
)}
```

新增组件 `ChangePasswordDialog`，校验当前密码、新密码、确认密码后调用 `/api/auth/change-password`，成功提示 `密码已修改`。

- [x] **Step 4: 改造 Shell 用户菜单**

在 `Shell` 中增加 `onChangePassword` 参数，新增 `menuOpen` state。替换 `.topbar-user` 中裸露退出按钮为：

```tsx
<div className="user-menu">
  <button className="user-menu-trigger" type="button" onClick={() => setMenuOpen((value) => !value)}>
    <span>{user.display_name || user.username}</span>
    <span className="role-pill">{user.role === 'admin' ? '管理员' : '普通用户'}</span>
  </button>
  {menuOpen && (
    <div className="user-menu-panel">
      <button type="button" onClick={() => { setMenuOpen(false); onChangePassword(); }}>修改密码</button>
      <button type="button" onClick={() => { setMenuOpen(false); logout(); }}>退出登录</button>
    </div>
  )}
</div>
```

- [x] **Step 5: 管理员重置密码按钮**

在 `ModelConfigPage` 增加：

```tsx
async function resetPassword(row: ModelQuotaRow) {
  if (!window.confirm(`确认将 ${row.display_name} 的密码重置为初始化密码？`)) return;
  await api(`/api/admin/users/${row.user_id}/reset-password`, { method: 'POST' });
  setNotice('密码已重置为初始化密码');
}
```

在操作列增加：

```tsx
<button className="mini-button" type="button" onClick={() => resetPassword(row)}>重置密码</button>
```

- [x] **Step 6: 增加 CSS**

在 `frontend/src/styles.css` 增加 `.user-menu`、`.user-menu-trigger`、`.user-menu-panel`、`.dialog-backdrop`、`.dialog-card`、`.dialog-actions` 样式，保持现有颜色和 8px 左右圆角，不引入大改布局。

- [x] **Step 7: 前端验证**

Run:

```powershell
pnpm --dir frontend exec tsc --noEmit
pnpm --dir frontend build
```

Expected: 两条命令均成功。

### Task 5: 文档同步

**Files:**
- Modify: `docs/deployment/02-服务器部署.md`
- Modify: `docs/architecture/05-数据库设计.md`
- Modify: `docs/modules/fpa/README.md`
- Modify: `docs/ui/modules/fpa-页面设计.md`

- [x] **Step 1: 更新部署/初始化文档**

在 `docs/deployment/02-服务器部署.md` 的用户初始化部分说明：

```markdown
生产和本地开发均使用生产初始化用户口径：用户名使用拼音，初始化密码来源为手机号或等价初始密码来源；任毅为管理员。管理员可将用户密码重置为初始化密码，但页面和接口不展示初始化密码来源。
```

并把示例默认系统从 `onlineclaim` 改为 `claimcar` 或空默认系统。

- [x] **Step 2: 更新数据库设计文档**

在 `docs/architecture/05-数据库设计.md` 的 `users` 表字段中增加：

```markdown
| `initial_password_seed` | TEXT | 否 | 初始化密码来源，仅用于管理员重置密码；普通接口不返回 |
```

并在安全说明中写明不保存当前密码明文。

- [x] **Step 3: 更新 FPA 模块文档**

在 `docs/modules/fpa/README.md` 增加当前生产可选系统：

```markdown
- `claimcar`：车险理赔核心系统
- `claimoth`：非车险理赔核心系统
```

说明无默认系统时提交页不自动选择系统，必须用户明确选择。

- [x] **Step 4: 更新 UI 文档**

在 `docs/ui/modules/fpa-页面设计.md` 把“顶部直接退出登录”调整为“用户菜单包含修改密码和退出登录”。

### Task 6: 全量验证与 Comet 任务勾选

**Files:**
- Modify: `openspec/changes/align-prod-auth-and-fpa-config/tasks.md`

- [x] **Step 1: 运行 OpenSpec 验证**

Run:

```powershell
openspec validate align-prod-auth-and-fpa-config --strict
```

Expected: `Change 'align-prod-auth-and-fpa-config' is valid`。

- [x] **Step 2: 运行后端测试**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest tests.test_fpa_mvp -v
```

Expected: 所有测试通过。

- [x] **Step 3: 运行前端检查**

Run:

```powershell
pnpm --dir frontend exec tsc --noEmit
pnpm --dir frontend build
```

Expected: 两条命令均成功。

- [x] **Step 4: 运行编码检查**

Run:

```powershell
.\scripts\check-encoding.ps1
```

Expected: 无编码错误。

- [x] **Step 5: 更新 Comet tasks**

在 `openspec/changes/align-prod-auth-and-fpa-config/tasks.md` 中把已经完成的任务改为 `- [x]`。不要提交。

- [x] **Step 6: 查看工作区摘要**

Run:

```powershell
git status --short
git diff --stat
```

Expected: 只包含本 change 相关文件；不提交、不推送。

<!-- standard review: requesting-code-review skill loaded; subagent dispatch failed in this host, manual lightweight review completed before build guard; no Critical or Important issues found. No commit/push per user instruction. -->

