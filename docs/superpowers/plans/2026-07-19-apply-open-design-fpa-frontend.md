---
change: apply-open-design-fpa-frontend
design-doc: docs/superpowers/specs/2026-07-19-apply-open-design-fpa-frontend-design.md
base-ref: f7d6b726a474fd251a92b29afdc41cfab12180a3
---

# FPA 前端 Open Design 落地实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 本项目当前规则禁止自动 commit/push，因此步骤中使用 diff/stat 和测试结果作为检查点，不包含提交或推送操作。

**Goal:** 把已归档 Open Design FPA 三页原型落到现有 TeamTools 运行态前端，并补齐最小后端表单配置接口。

**Architecture:** 保留现有 React 单文件主链路，使用最小后端 `form-config` 接口消除前端配置硬编码。前端只收敛壳、列表、提交页、详情页展示与状态映射，不改 FPA 后端状态机、AI 契约、Excel 生成脚本或数据库 schema。

**Tech Stack:** FastAPI、SQLite、Python unittest、React、TypeScript、Vite、CSS。

---

### Task 1: 后端表单配置接口

**Files:**
- Modify: `D:\project\teamtools\backend\app\modules\fpa\service.py`
- Modify: `D:\project\teamtools\backend\app\main.py`
- Test: `D:\project\teamtools\backend\tests\test_fpa_mvp.py`

- [x] **Step 1: 在测试中先覆盖 form-config**

在 `backend/tests/test_fpa_mvp.py` 的 FPA 测试类中增加测试方法：

```python
def test_form_config_returns_safe_options(self) -> None:
    with self.client() as client:
        response = client.get("/api/fpa/form-config")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertIn("systems", payload)
        self.assertIn("count_timings", payload)
        self.assertIn("integrity_levels", payload)
        self.assertIn("defaults", payload)
        self.assertEqual(payload["defaults"]["count_timing"], "估算中期")
        self.assertEqual(
            payload["defaults"]["integrity_level"],
            "完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
        )
        self.assertIn("1.21 估算中期", [item["label"] for item in payload["count_timings"]])
        self.assertIn(
            "1.10 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式",
            [item["label"] for item in payload["integrity_levels"]],
        )
        dumped = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("knowledge_dir", dumped)
        self.assertNotIn(str(self.data_dir), dumped)
```

- [x] **Step 2: 运行测试确认当前失败**

Run:

```powershell
cd D:\project\teamtools\backend
uv run python -m unittest tests.test_fpa_mvp -v
cd ..
```

Expected: 新增测试因 `/api/fpa/form-config` 不存在或响应字段缺失而失败。

- [x] **Step 3: 增加 `get_form_config`**

在 `backend/app/modules/fpa/service.py` 中复用现有 `COUNT_TIMINGS`、`INTEGRITY_LEVELS`、`DEFAULT_COUNT_TIMING`、`DEFAULT_INTEGRITY_LEVEL` 和 `load_systems` 增加函数：

```python
def get_form_config(data_dir: Path) -> dict[str, Any]:
    systems = load_systems(data_dir)
    default_system = systems[0]["code"] if systems else None
    return {
        "systems": systems,
        "count_timings": [
            {"value": item["value"], "label": f'{item["coefficient"]:.2f} {item["value"]}', "coefficient": item["coefficient"]}
            for item in COUNT_TIMINGS
        ],
        "integrity_levels": [
            {"value": item["value"], "label": f'{item["coefficient"]:.2f} {item["value"]}', "coefficient": item["coefficient"]}
            for item in INTEGRITY_LEVELS
        ],
        "defaults": {
            "system_code": default_system,
            "count_timing": DEFAULT_COUNT_TIMING,
            "integrity_level": DEFAULT_INTEGRITY_LEVEL,
        },
    }
```

- [x] **Step 4: 暴露路由**

在 `backend/app/main.py` 导入 `get_form_config`，并在 `/api/fpa/systems` 附近增加：

```python
@app.get("/api/fpa/form-config")
async def fpa_form_config(request: Request) -> dict[str, Any]:
    require_user(request)
    return get_form_config(app_data_dir)
```

- [x] **Step 5: 运行后端测试确认通过**

Run:

```powershell
cd D:\project\teamtools\backend
uv run python -m unittest tests.test_fpa_mvp -v
cd ..
```

Expected: `tests.test_fpa_mvp` 通过。

### Task 2: 前端类型与表单配置加载

**Files:**
- Modify: `D:\project\teamtools\frontend\src\App.tsx`
- Modify: `D:\project\teamtools\frontend\src\styles.css`

- [x] **Step 1: 增加表单配置类型并移除运行态依赖硬编码**

在 `frontend/src/App.tsx` 顶部增加：

```ts
type SelectOption = {
  value: string;
  label: string;
  coefficient?: number;
};

type FormConfig = {
  systems: SystemItem[];
  count_timings: SelectOption[];
  integrity_levels: SelectOption[];
  defaults: {
    system_code?: string | null;
    count_timing: string;
    integrity_level: string;
  };
};
```

保留 `DEEPSEEK_KEY_STORAGE`，删除或降级 `countTimingOptions`、`integrityLevelOptions` 的运行态使用。

- [x] **Step 2: 提交页改用 `/api/fpa/form-config`**

在 `SubmitPage` 中新增状态：

```ts
const [countTimingOptions, setCountTimingOptions] = useState<SelectOption[]>([]);
const [integrityLevelOptions, setIntegrityLevelOptions] = useState<SelectOption[]>([]);
const [submitApiKey, setSubmitApiKey] = useState('');
const [rememberSubmitApiKey, setRememberSubmitApiKey] = useState(false);
```

把 `api('/api/fpa/systems')` 替换为：

```ts
api('/api/fpa/form-config')
  .then((data: FormConfig) => {
    setSystems(data.systems);
    setCountTimingOptions(data.count_timings);
    setIntegrityLevelOptions(data.integrity_levels);
    setCountTiming(data.defaults.count_timing);
    setIntegrityLevel(data.defaults.integrity_level);
    const preferred = data.systems.some((item) => item.code === user.default_system_code)
      ? user.default_system_code
      : data.defaults.system_code || data.systems[0]?.code || '';
    setSystemCode(preferred || '');
  })
  .catch((err) => setError(err instanceof Error ? err.message : '表单配置加载失败'));
```

- [x] **Step 3: 提交页增加 API Key 本地输入但不提交**

在提交页侧栏或表单底部增加本地 API Key 输入：

```tsx
<label className="field">
  <span>DeepSeek API Key</span>
  <input
    type="password"
    value={submitApiKey}
    onChange={(event) => setSubmitApiKey(event.target.value)}
    placeholder="仅保存到当前浏览器，不上传后端"
  />
</label>
<label className="switch-line">
  <input
    type="checkbox"
    checked={rememberSubmitApiKey}
    onChange={(event) => {
      const checked = event.target.checked;
      setRememberSubmitApiKey(checked);
      if (!checked) window.localStorage.removeItem(DEEPSEEK_KEY_STORAGE);
    }}
  />
  记住到本机浏览器
</label>
```

提交成功前后只允许：

```ts
if (rememberSubmitApiKey && submitApiKey.trim()) {
  window.localStorage.setItem(DEEPSEEK_KEY_STORAGE, submitApiKey.trim());
} else {
  window.localStorage.removeItem(DEEPSEEK_KEY_STORAGE);
}
```

不得向 `URLSearchParams` 添加 API Key。

- [x] **Step 4: 构建前端确认类型正确**

Run:

```powershell
cd D:\project\teamtools\frontend
npm run build
cd ..
```

Expected: 构建通过。

### Task 3: 平台壳与任务列表收敛

**Files:**
- Modify: `D:\project\teamtools\frontend\src\App.tsx`
- Modify: `D:\project\teamtools\frontend\src\styles.css`

- [x] **Step 1: `/` 和 `/modules` 默认显示任务列表**

在 `Router` 中把：

```tsx
if (path === '/' || path === '/modules') {
  return <HomePage navigate={navigate} />;
}
```

改为：

```tsx
if (path === '/' || path === '/modules') {
  return <TasksPage user={user} navigate={navigate} setNotice={setNotice} />;
}
```

`HomePage` 可以保留未使用，或删除组件及相关样式；若删除，确认没有引用。

- [x] **Step 2: 移除首版左侧栏展示**

在 `Shell` 中删除 `<aside className="sidebar">...</aside>` 渲染，保留单列 `<main className="main-shell">`。顶部标题改为：

```tsx
<p className="eyebrow">FPA 工作量评估</p>
<strong>{path.includes('/submit') ? '提交评估' : path.includes('/tasks/') ? '查看详情' : '任务列表'}</strong>
```

不展示 `TeamTools / FPA 工作量评估` 面包屑。

- [x] **Step 3: 调整 CSS 单列壳和紧凑列表**

在 `frontend/src/styles.css` 调整：

```css
.app-shell {
  min-height: 100vh;
  display: block;
}

.main-shell {
  min-width: 0;
  display: grid;
  grid-template-rows: auto 1fr;
}

.workspace {
  max-width: 1440px;
  margin: 0 auto;
  padding: 18px 22px 40px;
}

.data-table {
  min-width: 0;
  table-layout: fixed;
}

.data-table th,
.data-table td {
  padding: 9px 10px;
  font-size: 13px;
}

.data-table td:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

- [x] **Step 4: 检查前端构建**

Run:

```powershell
cd D:\project\teamtools\frontend
npm run build
cd ..
```

Expected: 构建通过。

### Task 4: 详情页状态主内容与普通用户产物边界

**Files:**
- Modify: `D:\project\teamtools\frontend\src\App.tsx`
- Modify: `D:\project\teamtools\frontend\src\styles.css`

- [x] **Step 1: 增加状态判断辅助函数**

在底部辅助函数区域增加：

```ts
function isCancelledStatus(status: string) {
  return status === 'canceled' || status === 'cancelled';
}

function isGeneratingStatus(status: string) {
  return status === 'validating_result' || status === 'generating_result';
}
```

并用这些函数替换重复判断。

- [x] **Step 2: 分态渲染详情主内容**

在 `DetailPage` 中把非等待态的 AI 调用区替换为用户视角状态卡：

```tsx
<StatusMainPanel
  task={task}
  summary={summary}
  markdown={detail.artifacts.ai_analysis_md.content}
  excel={detail.artifacts.excel_result}
  onRerun={rerun}
  onBack={() => navigate('/fpa/tasks')}
/>
```

新增 `StatusMainPanel` 组件函数，按 `waiting_ai_call`、处理中、完成、失败、取消返回不同内容。完成态只展示摘要、下载入口、Markdown 预览/复制；失败态展示 `failure_stage`、`error_summary` 和复制重建；取消态展示返回列表和复制重建。

- [x] **Step 3: AI 请求包只展示安全摘要**

在 `AiCallPanel` 保留：

```tsx
{aiRequest && <pre>{JSON.stringify({ provider: aiRequest.provider, model: aiRequest.model, request_format: aiRequest.request_format }, null, 2)}</pre>}
```

不得展示完整 prompt、messages、payload 或 API Key。

- [x] **Step 4: 增加复制 Markdown 按钮**

在完成态 Markdown 卡片中增加：

```tsx
<button
  className="text-button"
  type="button"
  onClick={() => navigator.clipboard.writeText(detail.artifacts.ai_analysis_md.content || '')}
  disabled={!detail.artifacts.ai_analysis_md.content}
>
  复制
</button>
```

缺失时显示 `AI评估说明待生成`。

- [x] **Step 5: 构建前端确认无回归**

Run:

```powershell
cd D:\project\teamtools\frontend
npm run build
cd ..
```

Expected: 构建通过。

### Task 5: 验证与收尾

**Files:**
- Modify: `D:\project\teamtools\openspec\changes\apply-open-design-fpa-frontend\tasks.md`

- [x] **Step 1: 运行编码检查**

Run:

```powershell
cd D:\project\teamtools
.\scripts\check-encoding.ps1
```

Expected: 编码检查通过。

- [x] **Step 2: 运行后端编译和测试**

Run:

```powershell
cd D:\project\teamtools\backend
uv run python -m py_compile app\config.py app\db.py app\main.py app\modules\fpa\service.py app\worker.py
uv run python -m unittest tests.test_fpa_mvp -v
cd ..
```

Expected: 编译和测试通过。

- [x] **Step 3: 运行前端构建**

Run:

```powershell
cd D:\project\teamtools\frontend
npm run build
cd ..
```

Expected: 构建通过。

- [x] **Step 4: 运行 OpenSpec 严格校验**

Run:

```powershell
cd D:\project\teamtools
openspec validate --all --strict
```

Expected: 全部 OpenSpec 校验通过。

- [x] **Step 5: 更新 change 任务清单**

把 `openspec/changes/apply-open-design-fpa-frontend/tasks.md` 中实际完成项勾选为 `[x]`。若某项因最终 AI schema 或环境限制未做，保持未勾选并在最终总结说明原因。

- [x] **Step 6: 查看本轮 diff 范围**

Run:

```powershell
cd D:\project\teamtools
git diff --stat
git status --short
```

Expected: diff 仅包含本 change 相关 OpenSpec/Superpowers 文档、前端运行态文件、最小后端接口和后端测试；不包含提交、推送、tag 或分支操作。
