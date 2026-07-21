import { DragEvent, FormEvent, useEffect, useMemo, useState } from 'react';

type User = {
  id: string;
  username: string;
  display_name: string;
  role: 'user' | 'admin';
  default_system_code?: string | null;
};

type SystemItem = {
  code: string;
  name: string;
  no_knowledge_mode?: boolean;
};

type TaskRow = {
  id: string;
  title: string;
  system_name: string;
  status: string;
  status_label: string;
  created_at: string;
  finished_at?: string | null;
  target_person_days?: number | null;
  count_timing: string;
  result_median_person_days?: number | null;
  target_hit?: boolean | null;
  can_cancel: boolean;
  can_rerun: boolean;
  can_download_excel: boolean;
  created_by?: string;
  failure_stage?: string | null;
};

type TaskDetail = {
  task: TaskRow & {
    system_code: string;
    error_summary?: string | null;
    quality_flags?: unknown[];
    can_fetch_ai_request: boolean;
    can_submit_ai_result: boolean;
  };
  model_quota?: ModelQuota;
  artifacts: {
    ai_analysis_md: { available: boolean; content?: string | null };
    fpa_process_json: { available: boolean; content?: unknown };
    result_summary: { available: boolean; content?: ResultSummary | null };
    excel_result: { available: boolean; download_url: string };
  };
};

type ModelQuota = {
  enabled: boolean;
  quota_total: number;
  used_count: number;
  remaining: number;
};

type ModelKeyConfig = {
  enabled: boolean;
  provider: string;
  api_base: string;
  model_name: string;
  default_quota: number;
  has_api_key: boolean;
  masked_key: string;
};

type ModelQuotaRow = ModelQuota & {
  user_id: string;
  username: string;
  display_name: string;
  role: 'user' | 'admin';
  last_used_at?: string | null;
  last_reset_at?: string | null;
};

type SharedModelKeyResponse = {
  provider: string;
  api_base: string;
  model: string;
  api_key: string;
  ticket: string;
  quota: ModelQuota;
};

type ResultSummary = {
  item_count?: number;
  function_point_total?: number;
  adjusted_fp_total?: number;
  work_days?: { low?: number; middle?: number; high?: number };
  target_check?: {
    hit_status?: string;
    difference_days?: number | null;
    difference_ratio?: number | null;
  };
  quality_gate?: {
    status?: string;
    failed?: boolean;
    deliverable_valid?: boolean;
    required_action?: string;
    reason_codes?: string[];
  };
  quality_warnings?: Array<{ code?: string; level?: string; message?: string; suggestion?: string }>;
  review_notes?: Array<{ code?: string; message?: string; severity?: string }>;
  uncounted_items?: Array<{ description?: string; reason?: string; related_requirement_section?: string }>;
  coverage_notes?: string;
};

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

const DEEPSEEK_KEY_STORAGE = 'teamtools:fpa:deepseek-key';
const DEEPSEEK_SESSION_KEY_STORAGE = 'teamtools:fpa:deepseek-session-key';
const LAST_DETAIL_TASK_STORAGE = 'teamtools:fpa:last-detail-task-id';
const DEFAULT_MODEL_PROVIDER = 'deepseek';
const DEFAULT_MODEL_API_BASE = 'https://api.deepseek.com';
const DEFAULT_MODEL_NAME = 'deepseek-v4-flash';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [path, setPath] = useState(window.location.pathname);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');
  const [lastRefresh, setLastRefresh] = useState('刚刚');

  useEffect(() => {
    api('/api/auth/me')
      .then((data) => setUser(data.user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));

    const onPop = () => setPath(window.location.pathname);
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  useEffect(() => {
    const page = path.includes('/model-config') ? 'model-config' : path.includes('/submit') ? 'submit' : path.includes('/tasks/') || path === '/fpa/detail' ? 'detail' : path.includes('/tasks') || path === '/' || path === '/modules' ? 'tasks' : 'login';
    document.body.dataset.page = page;
    document.body.classList.toggle('show-admin', user?.role === 'admin');
  }, [path, user?.role]);

  function navigate(nextPath: string) {
    window.history.pushState({}, '', nextPath);
    setPath(nextPath);
  }

  useEffect(() => {
    if (!loading && user && (path === '/' || path === '/modules')) {
      window.history.replaceState({}, '', '/fpa/tasks');
      setPath('/fpa/tasks');
    }
  }, [loading, user, path]);

  async function logout() {
    await api('/api/auth/logout', { method: 'POST' });
    setUser(null);
    navigate('/login');
  }

  if (loading) {
    return <main className="login-page"><section className="login-card">加载中...</section></main>;
  }

  if (!user || path === '/login') {
    return <LoginPage onLogin={setUser} navigate={navigate} />;
  }

  return (
    <Shell user={user} path={path} navigate={navigate} logout={logout} notice={notice} lastRefresh={lastRefresh}>
      <Router path={path} user={user} navigate={navigate} setNotice={setNotice} setLastRefresh={setLastRefresh} />
    </Shell>
  );
}

function Router({
  path,
  user,
  navigate,
  setNotice,
  setLastRefresh,
}: {
  path: string;
  user: User;
  navigate: (path: string) => void;
  setNotice: (value: string) => void;
  setLastRefresh: (value: string) => void;
}) {
  if (path === '/' || path === '/modules') {
    return <TasksPage user={user} navigate={navigate} setNotice={setNotice} setLastRefresh={setLastRefresh} />;
  }
  if (path === '/fpa/submit') {
    return <SubmitPage user={user} navigate={navigate} setNotice={setNotice} />;
  }
  if (path === '/fpa/detail') {
    return <LatestDetailPage navigate={navigate} setNotice={setNotice} />;
  }
  if (path === '/fpa/model-config') {
    return user.role === 'admin'
      ? <ModelConfigPage setNotice={setNotice} />
      : <section className="panel empty-state"><h2>需要管理员权限</h2><button className="button primary" onClick={() => navigate('/fpa/tasks')}>返回任务列表</button></section>;
  }
  if (path.startsWith('/fpa/tasks/')) {
    return <DetailPage taskId={decodeURIComponent(path.split('/').pop() || '')} user={user} navigate={navigate} setNotice={setNotice} />;
  }
  if (path === '/fpa/tasks') {
    return <TasksPage user={user} navigate={navigate} setNotice={setNotice} setLastRefresh={setLastRefresh} />;
  }
  return (
    <section className="panel empty-state">
      <h2>页面不存在</h2>
      <button className="button primary" onClick={() => navigate('/fpa/tasks')}>返回任务列表</button>
    </section>
  );
}

function LoginPage({ onLogin, navigate }: { onLogin: (user: User) => void; navigate: (path: string) => void }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      const data = await api('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      onLogin(data.user);
      navigate('/fpa/tasks');
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submit}>
        <span className="brand-mark">TT</span>
        <p className="eyebrow">TEAMTOOLS</p>
        <h1>登录 TeamTools</h1>
        <p className="subtle">开发账号：admin/admin123，普通用户 demo/demo123。上线前请替换密码。</p>
        <label className="field">
          <span>账号</span>
          <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
        </label>
        <label className="field">
          <span>密码</span>
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" />
        </label>
        {error && <div className="form-alert is-error">{error}</div>}
        <button className="button primary full" type="submit">登录</button>
      </form>
    </main>
  );
}

function Shell({
  user,
  path,
  navigate,
  logout,
  notice,
  lastRefresh,
  children,
}: {
  user: User;
  path: string;
  navigate: (path: string) => void;
  logout: () => void;
  notice: string;
  lastRefresh: string;
  children: React.ReactNode;
}) {
  const isDetailTab = path.includes('/fpa/tasks/') || path === '/fpa/detail';
  return (
    <div className="app-shell">
      <main className="main-shell">
        <header className="topbar">
          <div className="topbar-module">
            <span className="nav-dot"></span>
            <strong>FPA 工作量评估</strong>
          </div>
          <div className="topbar-user">
            <span className="topbar-refresh">最近刷新：<strong>{lastRefresh}</strong></span>
            <span>{user.display_name}</span>
            <span className="role-pill">{user.role === 'admin' ? '管理员' : '普通用户'}</span>
            <button className="text-button" type="button" onClick={logout}>退出登录</button>
          </div>
        </header>

        <section className="workspace">
          <nav className="module-tabs" aria-label="FPA 页面导航">
            <button className={`module-tab ${path === '/fpa/tasks' ? 'active' : ''}`} onClick={() => navigate('/fpa/tasks')} type="button">任务列表</button>
            <button className={`module-tab ${path === '/fpa/submit' ? 'active' : ''}`} onClick={() => navigate('/fpa/submit')} type="button">提交评估</button>
            <button className={`module-tab ${isDetailTab ? 'active' : ''}`} onClick={() => navigate('/fpa/detail')} type="button">查看详情</button>
            {user.role === 'admin' && <button className={`module-tab ${path === '/fpa/model-config' ? 'active' : ''}`} onClick={() => navigate('/fpa/model-config')} type="button">模型配置</button>}
          </nav>
          {notice && <div className="toast inline">{notice}</div>}
          {children}
        </section>
      </main>
    </div>
  );
}


function TasksPage({
  user,
  navigate,
  setNotice,
  setLastRefresh,
}: {
  user: User;
  navigate: (path: string) => void;
  setNotice: (value: string) => void;
  setLastRefresh: (value: string) => void;
}) {
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [showAdminFields, setShowAdminFields] = useState(true);

  async function loadTasks() {
    setLoading(true);
    const status = filter === 'all' || filter === 'running' ? '' : filter;
    const data = await api(`/api/fpa/tasks${status ? `?status=${status}` : ''}`);
    setTasks(data.items);
    setLoading(false);
    const refreshTime = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    setLastRefresh(refreshTime);
  }

  useEffect(() => {
    loadTasks().catch((err) => setNotice(err instanceof Error ? err.message : '加载失败'));
  }, [filter]);

  const visibleTasks = useMemo(() => {
    if (filter !== 'running') return tasks;
    return tasks.filter((task) => ['waiting_ai_call', 'validating_result', 'generating_result'].includes(task.status));
  }, [tasks, filter]);
  const showAdminColumn = user.role === 'admin' && showAdminFields;

  return (
    <>
      <div className="page-title-row compact-title">
        <h1>任务列表</h1>
      </div>

      <section className="panel toolbar-panel">
        <div className="filter-group">
          {[
            ['all', '全部'],
            ['running', '进行中'],
            ['completed', '已完成'],
            ['failed', '失败'],
            ['canceled', '已取消'],
          ].map(([value, label]) => (
            <button key={value} className={`filter-chip ${filter === value ? 'active' : ''}`} onClick={() => setFilter(value)}>{label}</button>
          ))}
          <button className="filter-chip refresh-chip" type="button" onClick={() => loadTasks()}>手动刷新</button>
        </div>
        <div className="toolbar-meta">
          <span>当前显示 <strong>{visibleTasks.length}</strong> 条</span>
          {user.role === 'admin' && (
            <label className="switch-line">
              <input type="checkbox" checked={showAdminFields} onChange={(event) => setShowAdminFields(event.target.checked)} />
              显示管理员字段
            </label>
          )}
        </div>
      </section>

      <section className="table-panel">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>任务名称</th>
                <th>系统</th>
                <th>状态</th>
                <th>提交时间</th>
                <th>完成时间</th>
                <th>目标人天</th>
                <th>结果中值</th>
                <th>命中目标</th>
                {showAdminColumn && <th>提交人</th>}
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={showAdminColumn ? 10 : 9}>加载中...</td></tr>
              ) : visibleTasks.length ? visibleTasks.map((task) => (
                <tr key={task.id}>
                  <td><button className="task-link link-button" onClick={() => navigate(`/fpa/tasks/${task.id}`)}>{task.title}</button></td>
                  <td>{task.system_name}</td>
                  <td><span className={`status ${statusTone(task.status)}`}>{displayStatusLabel(task.status)}</span></td>
                  <td>{formatTime(task.created_at)}</td>
                  <td>{formatTime(task.finished_at)}</td>
                  <td>{dash(task.target_person_days)}</td>
                  <td>{dash(task.result_median_person_days)}</td>
                  <td>{task.target_hit == null ? '未设置目标' : task.target_hit ? '命中' : '未命中'}</td>
                  {showAdminColumn && <td>{task.created_by || '-'}</td>}
                  <td className="row-actions">
                    <button className="mini-button" onClick={() => navigate(`/fpa/tasks/${task.id}`)}>查看</button>
                    {task.can_download_excel && <a className="mini-button" href={`/api/fpa/tasks/${task.id}/download/excel`}>下载</a>}
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={showAdminColumn ? 10 : 9}>暂无任务</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function LatestDetailPage({ navigate, setNotice }: { navigate: (path: string) => void; setNotice: (value: string) => void }) {
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    async function openDetail() {
      const cachedTaskId = window.localStorage.getItem(LAST_DETAIL_TASK_STORAGE);
      if (cachedTaskId) {
        try {
          await api(`/api/fpa/tasks/${cachedTaskId}`);
          navigate(`/fpa/tasks/${cachedTaskId}`);
          return;
        } catch {
          window.localStorage.removeItem(LAST_DETAIL_TASK_STORAGE);
        }
      }

      try {
        const data = await api('/api/fpa/tasks');
        const latest = data.items?.[0];
        if (latest?.id) {
          navigate(`/fpa/tasks/${latest.id}`);
        } else {
          setEmpty(true);
        }
      } catch (err) {
        setNotice(err instanceof Error ? err.message : '最新任务加载失败');
        setEmpty(true);
      }
    }

    openDetail();
  }, [navigate, setNotice]);

  if (!empty) return <section className="panel">正在打开最新任务...</section>;

  return (
    <section className="panel empty-state">
      <h2>暂无任务</h2>
      <button className="button primary" onClick={() => navigate('/fpa/submit')} type="button">提交评估</button>
    </section>
  );
}

function SubmitPage({ user, navigate, setNotice }: { user: User; navigate: (path: string) => void; setNotice: (value: string) => void }) {
  const [systems, setSystems] = useState<SystemItem[]>([]);
  const [systemCode, setSystemCode] = useState('');
  const [title, setTitle] = useState('');
  const [targetDays, setTargetDays] = useState('');
  const [countTiming, setCountTiming] = useState('估算中期');
  const [integrityLevel, setIntegrityLevel] = useState('完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式');
  const [inputText, setInputText] = useState('');
  const [fileText, setFileText] = useState('');
  const [fileName, setFileName] = useState('');
  const [fileSize, setFileSize] = useState<number | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [countTimingOptions, setCountTimingOptions] = useState<SelectOption[]>([]);
  const [integrityLevelOptions, setIntegrityLevelOptions] = useState<SelectOption[]>([]);
  const [submitApiKey, setSubmitApiKey] = useState('');
  const [rememberSubmitApiKey, setRememberSubmitApiKey] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const localKey = window.localStorage.getItem(DEEPSEEK_KEY_STORAGE) || '';
    const sessionKey = window.sessionStorage.getItem(DEEPSEEK_SESSION_KEY_STORAGE) || '';
    setSubmitApiKey(localKey || sessionKey);
    setRememberSubmitApiKey(Boolean(localKey));
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
  }, [user.default_system_code]);

  const targetDaysError = targetDays.trim() && !/^\d+(\.\d)?$/.test(targetDays.trim()) ? '目标人天最多保留 1 位小数' : '';

  function changeSubmitRemember(nextRemember: boolean) {
    setRememberSubmitApiKey(nextRemember);
    if (!nextRemember) {
      window.localStorage.removeItem(DEEPSEEK_KEY_STORAGE);
    }
  }

  async function readFile(file: File | undefined) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.md')) {
      setError('只支持上传 .md 文件');
      return;
    }
    if (file.size > 256 * 1024) {
      setError('上传文件不能超过 256KB');
      return;
    }
    setFileName(file.name);
    setFileSize(file.size);
    setFileText(await file.text());
    setError('');
  }

  function clearFile() {
    setFileName('');
    setFileSize(null);
    setFileText('');
    setFileInputKey((value) => value + 1);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    readFile(event.dataTransfer.files?.[0]).catch((err) => setError(err instanceof Error ? err.message : '文件读取失败'));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (targetDaysError) {
      setError(targetDaysError);
      return;
    }
    const form = new URLSearchParams();
    form.set('system_code', systemCode);
    form.set('title', title);
    form.set('input_text', inputText);
    form.set('uploaded_text', fileText);
    form.set('uploaded_name', fileName);
    form.set('count_timing', countTiming);
    form.set('integrity_level', integrityLevel);
    if (targetDays.trim()) form.set('target_person_days', targetDays.trim());
    try {
      const trimmedKey = submitApiKey.trim();
      if (trimmedKey) {
        window.sessionStorage.setItem(DEEPSEEK_SESSION_KEY_STORAGE, trimmedKey);
      } else {
        window.sessionStorage.removeItem(DEEPSEEK_SESSION_KEY_STORAGE);
      }
      if (rememberSubmitApiKey && trimmedKey) {
        window.localStorage.setItem(DEEPSEEK_KEY_STORAGE, trimmedKey);
      } else {
        window.localStorage.removeItem(DEEPSEEK_KEY_STORAGE);
      }
      const data = await api('/api/fpa/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
      });
      setNotice('任务已创建，AI 请求包已生成');
      navigate(data.task.detail_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败');
    }
  }

  const disabled = !systemCode || (!inputText.trim() && !fileText.trim()) || Boolean(targetDaysError);

  return (
    <>
      <div className="page-title-row compact-title">
        <h1>提交评估</h1>
      </div>

      <form className="form-panel" onSubmit={submit} noValidate>
        <div className="form-main">
          <div className="field-grid">
            <label className="field">
              <span>系统选择</span>
              <select value={systemCode} onChange={(event) => setSystemCode(event.target.value)} required>
                <option value="">请选择系统</option>
                {systems.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}
              </select>
            </label>
            <label className="field">
              <span>规模计数时机</span>
              <select value={countTiming} onChange={(event) => setCountTiming(event.target.value)}>
                {countTimingOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label className="field">
              <span>完整性级别</span>
              <select value={integrityLevel} onChange={(event) => setIntegrityLevel(event.target.value)}>
                {integrityLevelOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label className="field field-target-days">
              <span>目标人天</span>
              <input value={targetDays} onChange={(event) => setTargetDays(event.target.value)} inputMode="decimal" placeholder="如 8.5" />
            </label>
          </div>
          {targetDaysError && <div className="field-error">{targetDaysError}</div>}

          <label className="field">
            <span>需求名称</span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="可选，为空时由后端自动生成" />
          </label>

          <label className="field">
            <span>粘贴 Markdown 内容</span>
            <textarea className="markdown-input" value={inputText} onChange={(event) => setInputText(event.target.value)} maxLength={20000} placeholder="在这里粘贴需求 Markdown、流程说明、接口说明或评审记录。" />
            <small><strong>{inputText.length}</strong> / 20000 字符</small>
          </label>

          <label
            className={`upload-box ${isDragging ? 'is-dragging' : ''} ${fileName ? 'is-selected' : ''}`}
            onDragEnter={(event) => { event.preventDefault(); setIsDragging(true); }}
            onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
            onDragLeave={(event) => { event.preventDefault(); setIsDragging(false); }}
            onDrop={handleDrop}
          >
            <input key={fileInputKey} type="file" accept=".md,text/markdown,text/plain" onChange={(event) => readFile(event.target.files?.[0])} />
            <span className="upload-icon" aria-hidden="true">MD</span>
            <span>
              <strong>{fileName ? '已选择 Markdown 文件' : '拖动 .md 文件到这里，或点击选择文件'}</strong>
              <small>{fileName ? `${fileName} · ${formatFileSize(fileSize)}` : '文件不超过 256KB；可与粘贴内容同时提交。'}</small>
            </span>
            {fileName && <button className="mini-button" type="button" onClick={(event) => { event.preventDefault(); event.stopPropagation(); clearFile(); }}>移除</button>}
          </label>
        </div>

        <aside className="rule-panel">
          <h2>提交规则</h2>
          <ul className="rule-list">
            <li>粘贴内容和上传文件至少提供一个。</li>
            <li>文本不超过 2 万字符，文件不超过 256KB。</li>
            <li>目标人天最多 1 位小数。</li>
          </ul>
          {error && <div className="form-alert is-error">{error}</div>}
          <div className="form-actions">
            <button className="button primary" type="submit" disabled={disabled}>提交</button>
          </div>
          <section className="model-panel model-panel-side" aria-label="模型调用设置">
            <div className="panel-heading compact">
              <h2>模型调用设置</h2>
              <span className="status muted">本机使用</span>
            </div>
            <p className="model-brief">个人 Key 优先；留空时使用团队公用 Key</p>
            <label className="field model-key">
              <span>API Key</span>
              <input type="password" value={submitApiKey} onChange={(event) => setSubmitApiKey(event.target.value)} autoComplete="off" placeholder="本地 DeepSeek API Key" />
            </label>
            <label className="check-line">
              <input type="checkbox" checked={rememberSubmitApiKey} onChange={(event) => changeSubmitRemember(event.target.checked)} />
              记住到本机浏览器
            </label>
            <p className="helper-text">个人 API Key 只保存在本机浏览器，不上传后端；留空时详情页会领取团队公用 Key。</p>
          </section>
        </aside>
      </form>
    </>
  );
}

function ModelConfigPage({ setNotice }: { setNotice: (value: string) => void }) {
  const [config, setConfig] = useState<ModelKeyConfig | null>(null);
  const [quotas, setQuotas] = useState<ModelQuotaRow[]>([]);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [bulkQuota, setBulkQuota] = useState('10');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadAll() {
    setLoading(true);
    const [configData, quotaData] = await Promise.all([
      api('/api/admin/model-key/config'),
      api('/api/admin/model-key/quotas'),
    ]);
    setConfig(configData.config);
    setQuotas(quotaData.items);
    setBulkQuota(String(configData.config.default_quota ?? 10));
    setLoading(false);
  }

  useEffect(() => {
    loadAll().catch((err) => {
      setError(err instanceof Error ? err.message : '模型配置加载失败');
      setLoading(false);
    });
  }, []);

  function updateConfig<K extends keyof ModelKeyConfig>(key: K, value: ModelKeyConfig[K]) {
    if (!config) return;
    setConfig({ ...config, [key]: value });
  }

  function updateQuota(userId: string, patch: Partial<ModelQuotaRow>) {
    setQuotas((items) => items.map((item) => item.user_id === userId ? { ...item, ...patch } : item));
  }

  async function saveConfig(event: FormEvent) {
    event.preventDefault();
    if (!config) return;
    setError('');
    const saved = await api('/api/admin/model-key/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: config.enabled,
        provider: config.provider,
        api_base: config.api_base,
        model_name: config.model_name,
        api_key: apiKeyInput,
        default_quota: Number(config.default_quota),
      }),
    });
    setConfig(saved.config);
    setApiKeyInput('');
    setNotice('模型配置已保存');
  }

  async function saveQuota(row: ModelQuotaRow) {
    const saved = await api(`/api/admin/model-key/quotas/${row.user_id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: row.enabled, quota_total: Number(row.quota_total) }),
    });
    updateQuota(row.user_id, saved.quota);
    setNotice('用户额度已保存');
  }

  async function resetQuota(row: ModelQuotaRow) {
    const saved = await api(`/api/admin/model-key/quotas/${row.user_id}/reset`, { method: 'POST' });
    updateQuota(row.user_id, saved.quota);
    setNotice('用户用量已重置');
  }

  async function bulkSet() {
    await api('/api/admin/model-key/quotas/bulk-set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quota_total: Number(bulkQuota) }),
    });
    await loadAll();
    setNotice('已统一设置额度');
  }

  async function bulkReset() {
    await api('/api/admin/model-key/quotas/bulk-reset', { method: 'POST' });
    await loadAll();
    setNotice('已统一重置用量');
  }

  if (loading) return <section className="panel">加载中...</section>;
  if (error) return <section className="panel form-alert is-error">{error}</section>;
  if (!config) return <section className="panel empty-state"><h2>模型配置不可用</h2></section>;

  return (
    <>
      <div className="page-title-row compact-title">
        <h1>模型配置</h1>
      </div>
      <section className="model-config-grid">
        <form className="panel model-config-card shared-key-card" onSubmit={saveConfig}>
          <div className="shared-key-row">
            <div className="shared-key-title">
              <h2>公用 Key 配置</h2>
              <span className={`status ${config.enabled ? 'done' : 'muted'}`}>{config.enabled ? '已启用' : '未启用'}</span>
            </div>
            <label className="field shared-key-field">
              <span>公用 API Key</span>
              <input type="password" value={apiKeyInput} onChange={(event) => setApiKeyInput(event.target.value)} autoComplete="off" placeholder={config.has_api_key ? `已配置：${config.masked_key}；留空不替换` : '请输入公用 API Key'} />
            </label>
            <label className="field shared-quota-field">
              <span>默认额度</span>
              <input type="number" min="0" value={config.default_quota} onChange={(event) => updateConfig('default_quota', Number(event.target.value))} />
            </label>
            <label className="check-line shared-key-check">
              <input type="checkbox" checked={config.enabled} onChange={(event) => updateConfig('enabled', event.target.checked)} />
              启用公用 Key
            </label>
            <button className="button primary" type="submit">保存配置</button>
          </div>
        </form>

        <section className="panel model-config-card">
          <div className="panel-heading">
            <h2>用户额度管理</h2>
            <div className="bulk-actions">
              <input value={bulkQuota} onChange={(event) => setBulkQuota(event.target.value)} inputMode="numeric" aria-label="统一额度" />
              <button className="mini-button" type="button" onClick={bulkSet}>统一设置</button>
              <button className="mini-button" type="button" onClick={bulkReset}>统一重置</button>
            </div>
          </div>
          <div className="table-scroll">
            <table className="data-table quota-table">
              <thead>
                <tr>
                  <th>用户</th>
                  <th>角色</th>
                  <th>启用</th>
                  <th>总额度</th>
                  <th>已用</th>
                  <th>剩余</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {quotas.map((row) => (
                  <tr key={row.user_id}>
                    <td>{row.display_name}<span className="subtle">（{row.username}）</span></td>
                    <td>{row.role === 'admin' ? '管理员' : '普通用户'}</td>
                    <td><input type="checkbox" checked={row.enabled} onChange={(event) => updateQuota(row.user_id, { enabled: event.target.checked })} /></td>
                    <td><input className="quota-input" type="number" min="0" value={row.quota_total} onChange={(event) => updateQuota(row.user_id, { quota_total: Number(event.target.value) })} /></td>
                    <td>{row.used_count}</td>
                    <td>{row.remaining}</td>
                    <td className="row-actions">
                      <button className="mini-button" type="button" onClick={() => saveQuota(row)}>保存</button>
                      <button className="mini-button" type="button" onClick={() => resetQuota(row)}>重置</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </>
  );
}

function DetailPage({
  taskId,
  user,
  navigate,
  setNotice,
}: {
  taskId: string;
  user: User;
  navigate: (path: string) => void;
  setNotice: (value: string) => void;
}) {
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [error, setError] = useState('');
  const [calling, setCalling] = useState(false);
  const [callError, setCallError] = useState('');

  async function loadDetail() {
    const data = await api(`/api/fpa/tasks/${taskId}`);
    setDetail(data);
  }

  useEffect(() => {
    if (taskId) {
      window.localStorage.setItem(LAST_DETAIL_TASK_STORAGE, taskId);
    }
    loadDetail().catch((err) => setError(err instanceof Error ? err.message : '任务加载失败'));
  }, [taskId]);

  if (error) return <section className="panel form-alert is-error">{error}</section>;
  if (!detail) return <section className="panel">加载中...</section>;

  const task = detail.task;
  const summary = detail.artifacts.result_summary.content;
  const middleDays = summary?.work_days?.middle ?? task.result_median_person_days;
  const targetStatus = summary?.target_check?.hit_status;
  const markdown = detail.artifacts.ai_analysis_md.content || '';

  async function copyTaskId() {
    await navigator.clipboard.writeText(task.id);
    setNotice('任务 ID 已复制');
  }

  async function callModel() {
    setCalling(true);
    setCallError('');
    let source: 'personal_key' | 'shared_key' = 'personal_key';
    let ticket = '';
    let apiKey = (window.localStorage.getItem(DEEPSEEK_KEY_STORAGE) || window.sessionStorage.getItem(DEEPSEEK_SESSION_KEY_STORAGE) || '').trim();
    let apiBase = DEFAULT_MODEL_API_BASE;
    let model = DEFAULT_MODEL_NAME;
    try {
      if (!apiKey) {
        const shared: SharedModelKeyResponse = await api(`/api/fpa/tasks/${task.id}/shared-model-key`, { method: 'POST' });
        source = 'shared_key';
        ticket = shared.ticket;
        apiKey = shared.api_key;
        apiBase = shared.api_base || apiBase;
        model = shared.model || model;
      }
      const request = await api(`/api/fpa/tasks/${task.id}/ai-request`);
      const aiRequest = request.ai_request || {};
      const modelResponse = await fetch(`${apiBase.replace(/\/$/, '')}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          messages: aiRequest.messages || [{ role: 'user', content: aiRequest.plain_prompt || '' }],
          temperature: aiRequest.temperature ?? 0.2,
        }),
      });
      const rawResponse = await modelResponse.json().catch(() => ({}));
      if (!modelResponse.ok) {
        const message = rawResponse?.error?.message || rawResponse?.message || `模型调用失败：HTTP ${modelResponse.status}`;
        await api(`/api/fpa/tasks/${task.id}/ai-result`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            success: false,
            model_call_source: source,
            model_call_ticket: ticket,
            error: { code: 'model_call_failed', message },
          }),
        });
        throw new Error(message);
      }
      await api(`/api/fpa/tasks/${task.id}/ai-result`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          success: true,
          provider: DEFAULT_MODEL_PROVIDER,
          model,
          model_call_source: source,
          model_call_ticket: ticket,
          raw_response: rawResponse,
        }),
      });
      setNotice(source === 'shared_key' ? '已使用团队公用 Key 完成 AI 评估' : '已使用个人 Key 完成 AI 评估');
      await loadDetail();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'AI 评估失败';
      setCallError(message);
      setNotice(message);
      await loadDetail().catch(() => undefined);
    } finally {
      setCalling(false);
    }
  }

  return (
    <>
      <div className="page-title-row detail-title-row">
        <div>
          <h1>最新任务详情</h1>
        </div>
        <div className="actions detail-task-actions">
          <button className="button" onClick={copyTaskId}>复制任务 ID</button>
          <button className="button" onClick={() => navigate('/fpa/tasks')}>返回任务列表</button>
        </div>
      </div>
      <p className="detail-task-meta subtle">{task.title} · 任务 ID：{task.id} · {task.system_name} · {formatTime(task.created_at)}</p>

      <section className="detail-grid detail-primary-grid">
        <StatusProgressCard status={task.status} />
        <div className="detail-side-stack">
          <TaskSummaryCard
            task={task}
            middleDays={middleDays}
            targetStatus={targetStatus}
            excel={detail.artifacts.excel_result}
            modelQuota={detail.model_quota}
            calling={calling}
            callError={callError}
            onCallModel={callModel}
          />
        </div>
      </section>

      {user.role === 'admin' && (
        <ResultWorkbench
          task={task}
          summary={summary}
          markdown={markdown}
          excel={detail.artifacts.excel_result}
        />
      )}
    </>
  );
}

function TaskSummaryCard({
  task,
  middleDays,
  targetStatus,
  excel,
  modelQuota,
  calling,
  callError,
  onCallModel,
}: {
  task: TaskDetail['task'];
  middleDays?: number | null;
  targetStatus?: string;
  excel: TaskDetail['artifacts']['excel_result'];
  modelQuota?: ModelQuota;
  calling: boolean;
  callError: string;
  onCallModel: () => void;
}) {
  return (
    <article className="panel task-summary-card">
      <div className="panel-heading">
        <h2>任务摘要</h2>
        {excel.available ? <a className="button small" href={excel.download_url}>下载 Excel</a> : <button className="button small" type="button" disabled>Excel 生成后可下载</button>}
      </div>
      <section className="summary-strip vertical">
        <div><span>目标人天</span><strong>{dash(task.target_person_days)}</strong></div>
        <div><span>结果中值</span><strong>{dash(middleDays)}</strong></div>
        <div><span>是否命中目标</span><strong>{targetStatus ? targetHitLabel(targetStatus) : task.target_hit == null ? '-' : task.target_hit ? '命中' : '未命中'}</strong></div>
        <div><span>耗时</span><strong>{formatDuration(task.created_at, task.finished_at)}</strong></div>
        <div><span>公用 Key 余量</span><strong>{modelQuota ? `剩余 ${modelQuota.remaining} / 共 ${modelQuota.quota_total} 次` : '-'}</strong></div>
      </section>
      {task.can_submit_ai_result && (
        <div className="model-call-inline">
          <button className="button primary small" type="button" onClick={onCallModel} disabled={calling}>
            {calling ? 'AI 评估中...' : '开始 AI 评估'}
          </button>
          <span className="helper-text">优先使用本机个人 Key；未配置时使用团队公用 Key。</span>
        </div>
      )}
      {callError && <div className="form-alert is-error">{callError}</div>}
    </article>
  );
}

function StatusProgressCard({ status }: { status: string }) {
  return (
    <article className="panel status-workbench-card">
      <div className="panel-heading">
        <h2>状态进度</h2>
        <span className={`status ${statusTone(status)}`}>{displayStatusLabel(status)}</span>
      </div>
      <ol className="progress-list">
        {progressSteps().map((step, index) => (
          <li key={step.title} className={progressClass(status, index)}>
            <strong>{step.title}</strong>
            <span>{step.description}</span>
          </li>
        ))}
      </ol>
    </article>
  );
}

function ResultWorkbench({
  task,
  summary,
  markdown,
  excel,
}: {
  task: TaskDetail['task'];
  summary?: ResultSummary | null;
  markdown: string;
  excel: TaskDetail['artifacts']['excel_result'];
}) {
  return (
    <section className="detail-grid lower single result-workbench">
      <article className="panel result-workbench-panel">
        <div className="panel-heading">
          <h2>结果查看</h2>
          {excel.available && <a className="button primary" href={excel.download_url}>下载 Excel</a>}
        </div>
        <div className="artifact-list compact-artifacts">
          <details className="artifact-item">
            <summary>结果摘要 · 查看</summary>
            <ResultSummaryReview summary={summary} status={task.status} errorSummary={task.error_summary} />
          </details>
          <details className="artifact-item">
            <summary>AI分析.md 预览 · 复制</summary>
            <div className="artifact-heading">
              <span>管理员可查看和复制，不提供下载。</span>
              <button className="mini-button" type="button" onClick={() => navigator.clipboard.writeText(markdown)} disabled={!markdown}>复制</button>
            </div>
            <pre>{markdown || (task.status === 'failed' ? task.error_summary : '') || 'AI评估说明待生成'}</pre>
          </details>
        </div>
      </article>
    </section>
  );
}

function ResultMetricsCard({
  functionPoints,
  adjustedFp,
  middleDays,
  qualityGate,
}: {
  functionPoints?: number;
  adjustedFp?: number;
  middleDays?: number | null;
  qualityGate?: ResultSummary['quality_gate'];
}) {
  return (
    <article className="panel">
      <div className="panel-heading">
        <h2>估算结果</h2>
        {qualityGate?.status && <span className={`status ${qualityGate.failed ? 'failed' : qualityGate.status === 'passed' ? 'done' : 'running'}`}>{qualityGateLabel(qualityGate.status)}</span>}
      </div>
      <div className="metric-grid">
        <div><span>功能点合计</span><strong>{dash(functionPoints)}</strong></div>
        <div><span>调整后功能点</span><strong>{dash(adjustedFp)}</strong></div>
        <div><span>中值人天</span><strong>{dash(middleDays)}</strong></div>
      </div>
      {qualityGate?.required_action && <p className="subtle">{qualityGate.required_action}</p>}
    </article>
  );
}

function ResultSummaryReview({
  summary,
  status,
  errorSummary,
}: {
  summary?: ResultSummary | null;
  status: string;
  errorSummary?: string | null;
}) {
  if (!summary) {
    return <p className="subtle">{status === 'failed' ? errorSummary || '评估失败，请复制任务重新生成。' : '结果摘要待生成。'}</p>;
  }
  return (
    <div className="review-stack">
      <div className="metric-grid">
        <div><span>质量门槛</span><strong>{qualityGateLabel(summary.quality_gate?.status)}</strong></div>
        <div><span>功能点条目</span><strong>{dash(summary.item_count)}</strong></div>
        <div><span>目标差异</span><strong>{dash(summary.target_check?.difference_days)}</strong></div>
      </div>

      <ReviewList
        title="质量提示"
        items={(summary.quality_warnings || []).map((item) => ({
          title: item.code || item.level || 'QUALITY',
          body: [item.message, item.suggestion].filter(Boolean).join(' '),
        }))}
        empty="暂无质量提示。"
      />
      <ReviewList
        title="AI 复核提示"
        items={(summary.review_notes || []).map((item) => ({
          title: item.code || item.severity || 'NOTE',
          body: item.message || '',
        }))}
        empty="暂无 AI 复核提示。"
      />
      <ReviewList
        title="未计数项"
        items={(summary.uncounted_items || []).map((item) => ({
          title: item.description || '未计数项',
          body: [item.reason, item.related_requirement_section].filter(Boolean).join(' · '),
        }))}
        empty="暂无未计数项。"
      />
      {summary.coverage_notes && (
        <div className="review-note">
          <strong>覆盖说明</strong>
          <p>{summary.coverage_notes}</p>
        </div>
      )}
    </div>
  );
}

function ReviewList({ title, items, empty }: { title: string; items: Array<{ title: string; body: string }>; empty: string }) {
  return (
    <div className="review-list">
      <h3>{title}</h3>
      {items.length ? items.map((item, index) => (
        <div className="review-item" key={`${title}-${index}`}>
          <strong>{item.title}</strong>
          <p>{item.body || '-'}</p>
        </div>
      )) : <p className="subtle">{empty}</p>}
    </div>
  );
}

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { credentials: 'include', ...init });
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof data === 'object' && data && 'detail' in data ? String(data.detail) : `HTTP ${response.status}`;
    throw new Error(message);
  }
  return data;
}

function formatTime(value?: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function formatDuration(start?: string | null, end?: string | null) {
  if (!start || !end) return '-';
  const startTime = new Date(start).getTime();
  const endTime = new Date(end).getTime();
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime) || endTime < startTime) return '-';
  const minutes = Math.max(1, Math.round((endTime - startTime) / 60000));
  if (minutes < 60) return `约 ${minutes} 分钟`;
  const hours = Math.round(minutes / 60);
  return `约 ${hours} 小时`;
}

function dash(value?: number | string | null) {
  return value === null || value === undefined || value === '' ? '-' : value;
}

function formatFileSize(value?: number | null) {
  if (!value) return '0KB';
  return `${(value / 1024).toFixed(1)}KB`;
}

function qualityGateLabel(value?: string) {
  if (value === 'passed') return '通过';
  if (value === 'review_required') return '建议复核';
  if (value === 'failed') return '需复核';
  return '-';
}

function targetHitLabel(value?: string) {
  if (value === 'hit') return '命中';
  if (value === 'out_of_range') return '未命中';
  if (value === 'not_provided') return '-';
  return value;
}


function isCancelledStatus(status: string) {
  return status === 'canceled' || status === 'cancelled';
}

function statusTone(status: string) {
  if (status === 'completed') return 'done';
  if (status === 'failed') return 'failed';
  if (isCancelledStatus(status)) return 'muted';
  return 'running';
}

function displayStatusLabel(status: string) {
  if (status === 'completed') return '评估完成';
  if (status === 'failed') return '评估失败';
  if (status === 'canceled' || status === 'cancelled') return '已取消';
  if (status === 'validating_result' || status === 'generating_result') return '生成结果中';
  return 'AI评估中';
}

function progressSteps() {
  return [
    { title: '任务创建', description: '接收任务和输入内容' },
    { title: 'AI请求包已生成', description: '后端已生成模型请求内容' },
    { title: '等待AI调用', description: '浏览器使用本地 API Key 调用模型' },
    { title: '结果校验中', description: '后端校验 AI 结构化 JSON' },
    { title: '生成结果中', description: '后端写入 Excel 模板' },
    { title: '已完成 / 失败 / 已取消', description: '输出最终状态' },
  ];
}

function progressClass(status: string, index: number) {
  const activeMap: Record<string, number> = {
    waiting_ai_call: 2,
    validating_result: 3,
    generating_result: 4,
    completed: 5,
    failed: 5,
    canceled: 5,
    cancelled: 5,
  };
  const active = activeMap[status] ?? 2;
  if (index < active) return 'done';
  if (index === active) return 'active';
  return '';
}
