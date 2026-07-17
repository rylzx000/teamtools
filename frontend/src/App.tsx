import { FormEvent, useEffect, useMemo, useState } from 'react';

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
  artifacts: {
    ai_analysis_md: { available: boolean; content?: string | null };
    fpa_process_json: { available: boolean; content?: unknown };
    result_summary: { available: boolean; content?: ResultSummary | null };
    excel_result: { available: boolean; download_url: string };
  };
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

type AiRequest = {
  provider: string;
  model: string;
  request_format: 'messages' | 'plain_prompt';
  messages?: { role: string; content: string }[];
  plain_prompt?: string;
  generation_config?: Record<string, unknown>;
};

type SystemRelevance = {
  status: 'pass' | 'warning' | 'blocked';
  confirmed?: boolean;
  selected_system_code?: string;
  selected_system_name?: string;
  best_match_system_code?: string;
  best_match_system_name?: string;
  selected_score?: number;
  best_match_score?: number;
  message?: string;
};

type AiRequestResponse = {
  ai_request: AiRequest;
  system_relevance?: SystemRelevance;
};

const countTimingOptions = [
  { value: '估算早期', label: '1.39 估算早期' },
  { value: '估算中期', label: '1.21 估算中期' },
  { value: '估算晚期', label: '1.10 估算晚期' },
  { value: '项目交付后及运维阶段', label: '1.00 项目交付后及运维阶段' },
];
const integrityLevelOptions = [
  { value: '没有明确的完整性级别或等级为C/D', label: '1.00 没有明确的完整性级别或等级为C/D' },
  {
    value: '完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式',
    label: '1.10 完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式',
  },
  {
    value: '完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施',
    label: '1.30 完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施',
  },
];
const DEEPSEEK_KEY_STORAGE = 'teamtools:fpa:deepseek-key';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [path, setPath] = useState(window.location.pathname);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    api('/api/auth/me')
      .then((data) => setUser(data.user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));

    const onPop = () => setPath(window.location.pathname);
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  function navigate(nextPath: string) {
    window.history.pushState({}, '', nextPath);
    setPath(nextPath);
  }

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
    <Shell user={user} path={path} navigate={navigate} logout={logout} notice={notice}>
      <Router path={path} user={user} navigate={navigate} setNotice={setNotice} />
    </Shell>
  );
}

function Router({
  path,
  user,
  navigate,
  setNotice,
}: {
  path: string;
  user: User;
  navigate: (path: string) => void;
  setNotice: (value: string) => void;
}) {
  if (path === '/' || path === '/modules') {
    return <HomePage navigate={navigate} />;
  }
  if (path === '/fpa/submit') {
    return <SubmitPage user={user} navigate={navigate} setNotice={setNotice} />;
  }
  if (path.startsWith('/fpa/tasks/')) {
    return <DetailPage taskId={decodeURIComponent(path.split('/').pop() || '')} navigate={navigate} setNotice={setNotice} />;
  }
  if (path === '/fpa/tasks') {
    return <TasksPage user={user} navigate={navigate} setNotice={setNotice} />;
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
  children,
}: {
  user: User;
  path: string;
  navigate: (path: string) => void;
  logout: () => void;
  notice: string;
  children: React.ReactNode;
}) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="TeamTools 模块导航">
        <button className="brand-lockup" type="button" onClick={() => navigate('/')}>
          <span className="brand-mark">TT</span>
          <span><strong>TeamTools</strong><small>内部工具平台</small></span>
        </button>
        <nav className="module-nav" aria-label="模块入口">
          <p className="nav-kicker">模块</p>
          <button className="nav-link active" onClick={() => navigate('/fpa/tasks')} type="button"><span className="nav-dot" />FPA 工作量评估</button>
          <span className="nav-link is-disabled"><span className="nav-dot muted" />后续模块预留</span>
        </nav>
      </aside>

      <main className="main-shell">
        <header className="topbar">
          <div>
            <p className="crumb">TeamTools / FPA 工作量评估</p>
            <strong>{path.includes('/submit') ? '提交评估' : path.includes('/tasks/') ? '任务详情' : '任务列表'}</strong>
          </div>
          <div className="topbar-user">
            <span>{user.display_name}</span>
            <span className="role-pill">{user.role === 'admin' ? '管理员' : '普通用户'}</span>
            <button className="text-button" type="button" onClick={logout}>退出登录</button>
          </div>
        </header>

        <section className="workspace">
          <nav className="module-tabs" aria-label="FPA 页面导航">
            <button className={`module-tab ${path === '/fpa/tasks' ? 'active' : ''}`} onClick={() => navigate('/fpa/tasks')} type="button">任务列表</button>
            <button className={`module-tab ${path === '/fpa/submit' ? 'active' : ''}`} onClick={() => navigate('/fpa/submit')} type="button">提交评估</button>
            {path.includes('/fpa/tasks/') && <span className="module-tab active">任务详情</span>}
          </nav>
          {notice && <div className="toast inline">{notice}</div>}
          {children}
        </section>
      </main>
    </div>
  );
}

function HomePage({ navigate }: { navigate: (path: string) => void }) {
  return (
    <>
      <div className="page-title-row">
        <div>
          <p className="eyebrow">PLATFORM HOME</p>
          <h1>TeamTools</h1>
          <p className="subtle">首版聚焦 FPA 工作量评估主链路：提交需求、浏览器调用 DeepSeek、回传结果、下载 Excel。</p>
        </div>
        <button className="button primary" onClick={() => navigate('/fpa/tasks')}>进入 FPA</button>
      </div>
      <article className="module-card">
        <div>
          <p className="eyebrow">FPA MODULE</p>
          <h2>FPA 工作量评估</h2>
          <p className="subtle">后端生成 AI 请求包，API Key 仅在浏览器本地使用，Excel 由后端确定性脚本生成。</p>
        </div>
        <button className="button" onClick={() => navigate('/fpa/submit')}>提交评估</button>
      </article>
    </>
  );
}

function TasksPage({
  user,
  navigate,
  setNotice,
}: {
  user: User;
  navigate: (path: string) => void;
  setNotice: (value: string) => void;
}) {
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  async function loadTasks() {
    setLoading(true);
    const status = filter === 'all' || filter === 'running' ? '' : filter;
    const data = await api(`/api/fpa/tasks${status ? `?status=${status}` : ''}`);
    setTasks(data.items);
    setLoading(false);
    setNotice(`最近刷新：${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`);
  }

  useEffect(() => {
    loadTasks().catch((err) => setNotice(err instanceof Error ? err.message : '加载失败'));
  }, [filter]);

  const visibleTasks = useMemo(() => {
    if (filter !== 'running') return tasks;
    return tasks.filter((task) => ['waiting_ai_call', 'validating_result', 'generating_result'].includes(task.status));
  }, [tasks, filter]);

  return (
    <>
      <div className="page-title-row">
        <div>
          <p className="eyebrow">FPA MODULE</p>
          <h1>FPA 任务</h1>
          <p className="subtle">查看评估状态、调用模型、下载 Excel，普通用户只看到自己的任务。</p>
        </div>
        <div className="actions">
          <button className="button primary" onClick={() => navigate('/fpa/submit')}>提交评估</button>
          <button className="button" onClick={() => loadTasks()}>手动刷新</button>
        </div>
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
        </div>
        <div className="toolbar-meta">当前显示 <strong>{visibleTasks.length}</strong> 条</div>
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
                <th>是否命中</th>
                {user.role === 'admin' && <th>提交人</th>}
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={10}>加载中...</td></tr>
              ) : visibleTasks.length ? visibleTasks.map((task) => (
                <tr key={task.id}>
                  <td><button className="link-button" onClick={() => navigate(`/fpa/tasks/${task.id}`)}>{task.title}</button></td>
                  <td>{task.system_name}</td>
                  <td><span className={`status ${statusTone(task.status)}`}>{displayStatusLabel(task.status)}</span></td>
                  <td>{formatTime(task.created_at)}</td>
                  <td>{formatTime(task.finished_at)}</td>
                  <td>{dash(task.target_person_days)}</td>
                  <td>{dash(task.result_median_person_days)}</td>
                  <td>{task.target_hit == null ? '未设置目标' : task.target_hit ? '命中' : '未命中'}</td>
                  {user.role === 'admin' && <td>{task.created_by || '-'}</td>}
                  <td>
                    <button className="text-button" onClick={() => navigate(`/fpa/tasks/${task.id}`)}>查看</button>
                    {task.can_download_excel && <a className="text-button" href={`/api/fpa/tasks/${task.id}/download/excel`}>下载</a>}
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={10}>暂无任务</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
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
  const [error, setError] = useState('');

  useEffect(() => {
    api('/api/fpa/systems')
      .then((data) => {
        setSystems(data.items);
        const preferred = data.items.some((item: SystemItem) => item.code === user.default_system_code)
          ? user.default_system_code
          : data.items[0]?.code || '';
        setSystemCode(preferred || '');
      })
      .catch((err) => setError(err instanceof Error ? err.message : '系统列表加载失败'));
  }, [user.default_system_code]);

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
    setFileText(await file.text());
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    const form = new URLSearchParams();
    form.set('system_code', systemCode);
    form.set('title', title);
    form.set('input_text', inputText);
    form.set('uploaded_text', fileText);
    form.set('uploaded_name', fileName);
    form.set('count_timing', countTiming);
    form.set('integrity_level', integrityLevel);
    if (targetDays) form.set('target_person_days', targetDays);
    try {
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

  const disabled = !systemCode || (!inputText.trim() && !fileText.trim());

  return (
    <>
      <div className="page-title-row">
        <div>
          <h1>提交评估</h1>
          <p className="subtle">提交后进入任务详情页，由浏览器使用本地 API Key 调用 DeepSeek。</p>
        </div>
        <button className="button" onClick={() => navigate('/fpa/tasks')}>返回任务列表</button>
      </div>

      <form className="form-panel" onSubmit={submit}>
        <div className="form-main">
          <div className="field-grid">
            <label className="field">
              <span>系统选择</span>
              <select value={systemCode} onChange={(event) => setSystemCode(event.target.value)} required>
                {systems.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}
              </select>
            </label>
            <label className="field">
              <span>目标人天</span>
              <input value={targetDays} onChange={(event) => setTargetDays(event.target.value)} inputMode="decimal" placeholder="可选，例如 8.5" />
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
          </div>

          <label className="field">
            <span>需求名称</span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="可选，为空时后端兜底" />
          </label>

          <label className="field">
            <span>粘贴 Markdown 内容</span>
            <textarea value={inputText} onChange={(event) => setInputText(event.target.value)} rows={10} placeholder="粘贴需求正文..." />
          </label>

          <label className="upload-zone">
            <input type="file" accept=".md,text/markdown" onChange={(event) => readFile(event.target.files?.[0])} />
            <strong>{fileName || '上传 Markdown 文件'}</strong>
            <span>粘贴内容和上传文件会按顺序合并，单文件不超过 256KB。</span>
          </label>

          {error && <div className="form-alert is-error">{error}</div>}
          <div className="actions end">
            <button className="button primary" type="submit" disabled={disabled}>提交并生成 AI 请求包</button>
          </div>
        </div>
        <aside className="form-side panel">
          <h2>模型调用边界</h2>
          <p>API Key 只在任务详情页浏览器本地使用，不上传后端、不进入 AI 请求包、不写入任务文件。</p>
          <p>AI 只输出结构化 JSON；最终人天、目标命中和 Excel 均由后端生成。</p>
        </aside>
      </form>
    </>
  );
}

function DetailPage({
  taskId,
  navigate,
  setNotice,
}: {
  taskId: string;
  navigate: (path: string) => void;
  setNotice: (value: string) => void;
}) {
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [error, setError] = useState('');

  async function loadDetail() {
    const data = await api(`/api/fpa/tasks/${taskId}`);
    setDetail(data);
  }

  useEffect(() => {
    loadDetail().catch((err) => setError(err instanceof Error ? err.message : '任务加载失败'));
  }, [taskId]);

  async function cancel() {
    await api(`/api/fpa/tasks/${taskId}/cancel`, { method: 'POST' });
    setNotice('任务已取消');
    await loadDetail();
  }

  async function rerun() {
    const data = await api(`/api/fpa/tasks/${taskId}/rerun`, { method: 'POST' });
    setNotice('已基于原输入创建新任务');
    navigate(data.task.detail_url);
  }

  if (error) return <section className="panel form-alert is-error">{error}</section>;
  if (!detail) return <section className="panel">加载中...</section>;

  const task = detail.task;
  const summary = detail.artifacts.result_summary.content;
  const displayLabel = displayStatusLabel(task.status);
  const middleDays = summary?.work_days?.middle ?? task.result_median_person_days;
  const functionPoints = summary?.function_point_total;
  const adjustedFp = summary?.adjusted_fp_total;
  const targetStatus = summary?.target_check?.hit_status;

  return (
    <>
      <div className="page-title-row">
        <div>
          <p className="eyebrow">TASK DETAIL</p>
          <h1>{task.title}</h1>
          <p className="subtle">任务 ID：{task.id} · {task.system_name} · 提交时间 {formatTime(task.created_at)}</p>
        </div>
        <div className="actions">
          {task.can_cancel && <button className="button" onClick={cancel}>取消任务</button>}
          {task.can_rerun && <button className="button" onClick={rerun}>复制并重新生成</button>}
          <button className="button" onClick={() => navigate('/fpa/tasks')}>返回任务列表</button>
        </div>
      </div>

      <section className="summary-strip">
        <div><span>当前状态</span><strong><span className={`status ${statusTone(task.status)}`}>{displayLabel}</span></strong></div>
        <div><span>目标人天</span><strong>{dash(task.target_person_days)}</strong></div>
        <div><span>结果中值</span><strong>{dash(middleDays)}</strong></div>
        <div><span>目标校验</span><strong>{targetStatus ? targetHitLabel(targetStatus) : task.target_hit == null ? '-' : task.target_hit ? '命中' : '未命中'}</strong></div>
      </section>

      <section className="ai-call-hero">
        {task.status === 'waiting_ai_call' ? (
          <AiCallPanel taskId={task.id} onDone={loadDetail} setNotice={setNotice} />
        ) : (
          <article className="panel ai-panel">
            <div className="panel-heading">
              <h2>AI 调用区</h2>
              <span className={`status ${statusTone(task.status)}`}>{displayLabel}</span>
            </div>
            <p className="subtle">{nextStepText(task.status)}</p>
          </article>
        )}
      </section>

      <section className="detail-grid">
        <article className="panel">
          <div className="panel-heading">
            <h2>状态进度</h2>
            <span className={`status ${statusTone(task.status)}`}>{displayLabel}</span>
          </div>
          <ol className="progress-list">
            {progressLabels(task.status).map((label, index) => (
              <li key={`${label}-${index}`} className={progressClass(task.status, index)}>
                <strong>{label}</strong>
                <span>{progressText(label)}</span>
              </li>
            ))}
          </ol>
        </article>

        <ResultMetricsCard
          functionPoints={functionPoints}
          adjustedFp={adjustedFp}
          middleDays={middleDays}
          qualityGate={summary?.quality_gate}
        />
      </section>

      <section className="result-grid">
        <article className="panel">
          <div className="panel-heading">
            <h2>结果摘要</h2>
            {detail.artifacts.excel_result.available && <a className="button primary" href={detail.artifacts.excel_result.download_url}>下载 Excel</a>}
          </div>
          <ResultSummaryReview summary={summary} status={task.status} errorSummary={task.error_summary} />
        </article>
        <article className="panel">
          <div className="panel-heading"><h2>AI评估.md</h2></div>
          <pre>{detail.artifacts.ai_analysis_md.content || (task.status === 'failed' ? task.error_summary : '') || 'AI评估说明待生成'}</pre>
        </article>
      </section>
    </>
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

function AiCallPanel({ taskId, onDone, setNotice }: { taskId: string; onDone: () => Promise<void>; setNotice: (value: string) => void }) {
  const [apiKey, setApiKey] = useState('');
  const [remember, setRemember] = useState(false);
  const [aiRequest, setAiRequest] = useState<AiRequest | null>(null);
  const [systemRelevance, setSystemRelevance] = useState<SystemRelevance | null>(null);
  const [relevanceConfirmed, setRelevanceConfirmed] = useState(false);
  const [calling, setCalling] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const saved = window.localStorage.getItem(DEEPSEEK_KEY_STORAGE);
    if (saved) {
      setApiKey(saved);
      setRemember(true);
    }
  }, []);

  function changeRemember(nextRemember: boolean) {
    setRemember(nextRemember);
    if (!nextRemember) {
      window.localStorage.removeItem(DEEPSEEK_KEY_STORAGE);
    }
  }

  async function fetchRequest(): Promise<AiRequestResponse> {
    const data = await api(`/api/fpa/tasks/${taskId}/ai-request`) as AiRequestResponse;
    setAiRequest(data.ai_request);
    setSystemRelevance(data.system_relevance || null);
    if (data.system_relevance && ['warning', 'blocked'].includes(data.system_relevance.status) && !data.system_relevance.confirmed) {
      setError(data.system_relevance.message || '系统选择可能与需求不匹配，请确认是否继续。');
    } else {
      setError('');
      setNotice('AI 请求包已获取');
    }
    return data;
  }

  async function callDeepSeek() {
    const trimmedApiKey = apiKey.trim();
    if (!trimmedApiKey) {
      setError('请先输入 DeepSeek API Key');
      return;
    }
    const requestData = aiRequest ? { ai_request: aiRequest, system_relevance: systemRelevance || undefined } : await fetchRequest();
    const relevance = requestData.system_relevance;
    if (relevance && ['warning', 'blocked'].includes(relevance.status) && !relevance.confirmed && !relevanceConfirmed) {
      setSystemRelevance(relevance);
      setError(relevance.message || '系统选择可能与需求不匹配，请确认是否继续。');
      return;
    }
    const request = requestData.ai_request;
    setCalling(true);
    setError('');
    if (remember) {
      window.localStorage.setItem(DEEPSEEK_KEY_STORAGE, trimmedApiKey);
    } else {
      window.localStorage.removeItem(DEEPSEEK_KEY_STORAGE);
    }
    try {
      const body = {
        model: request.model,
        messages: request.request_format === 'messages'
          ? request.messages
          : [{ role: 'user', content: request.plain_prompt || '' }],
        temperature: request.generation_config?.temperature ?? 0.2,
      };
      const response = await fetch('https://api.deepseek.com/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${trimmedApiKey}`,
        },
        body: JSON.stringify(body),
      });
      const raw = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(raw?.error?.message || `DeepSeek HTTP ${response.status}`);
      }
      const result = await api(`/api/fpa/tasks/${taskId}/ai-result`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ success: true, provider: 'deepseek', model: request.model, raw_response: raw }),
      });
      const status = result?.task?.status;
      if (status === 'completed') {
        setNotice('AI 结果已回传，Excel 已生成');
      } else if (status === 'failed') {
        setNotice('AI 结果校验失败，请查看错误摘要或复制任务重跑');
      } else {
        setNotice(`AI 结果已回传，当前状态：${displayStatusLabel(status || '')}`);
      }
      await onDone();
    } catch (err) {
      const message = err instanceof TypeError ? 'Failed to fetch：可能是 CORS 或网络问题' : err instanceof Error ? err.message : '模型调用失败';
      setError(message);
    } finally {
      setCalling(false);
    }
  }

  async function confirmFailure() {
    await api(`/api/fpa/tasks/${taskId}/ai-result`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ success: false, provider: 'deepseek', model: aiRequest?.model || 'deepseek-v4-flash', error: { code: 'browser_call_failed', message: error || '用户确认模型调用失败' } }),
    });
    setNotice('模型调用失败已回传后端');
    await onDone();
  }

  async function confirmSystemRelevance() {
    const data = await api(`/api/fpa/tasks/${taskId}/system-relevance/confirm`, { method: 'POST' });
    setSystemRelevance(data.system_relevance || null);
    setRelevanceConfirmed(true);
    setError('');
    setNotice('已确认按当前系统继续评估');
  }

  const needsSystemConfirm = Boolean(
    systemRelevance && ['warning', 'blocked'].includes(systemRelevance.status) && !systemRelevance.confirmed && !relevanceConfirmed,
  );

  return (
    <article className="panel ai-panel">
      <div className="panel-heading">
        <h2>AI 调用区</h2>
        <span className="status running">等待AI调用</span>
      </div>
      <label className="field">
        <span>DeepSeek API Key</span>
        <input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="仅浏览器本地使用，不上传后端" />
      </label>
      <label className="switch-line">
        <input type="checkbox" checked={remember} onChange={(event) => changeRemember(event.target.checked)} />
        仅保存到当前浏览器 localStorage
      </label>
      <div className="actions">
        <button className="button" onClick={fetchRequest}>获取 AI 请求包</button>
        {needsSystemConfirm && <button className="button" onClick={confirmSystemRelevance}>仍然继续</button>}
        <button className="button primary" onClick={callDeepSeek} disabled={calling}>{calling ? '调用中...' : '浏览器调用 DeepSeek'}</button>
        {error && !needsSystemConfirm && <button className="button danger" onClick={confirmFailure}>确认失败并回传</button>}
      </div>
      {aiRequest && <pre>{JSON.stringify({ provider: aiRequest.provider, model: aiRequest.model, request_format: aiRequest.request_format }, null, 2)}</pre>}
      {error && <div className="form-alert is-error">{error}</div>}
    </article>
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

function dash(value?: number | string | null) {
  return value === null || value === undefined || value === '' ? '-' : value;
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

function nextStepText(status: string) {
  if (status === 'completed') return '任务已生成正式 Excel，可在结果摘要中查看质量提示并下载。';
  if (status === 'failed') return '任务失败，请查看错误摘要或复制任务重新生成。';
  if (status === 'canceled') return '任务已取消，可复制后重新提交。';
  return '后端正在处理结果，请稍后刷新详情。';
}

function statusTone(status: string) {
  if (status === 'completed') return 'done';
  if (status === 'failed') return 'failed';
  if (status === 'canceled') return 'muted';
  return 'running';
}

function displayStatusLabel(status: string) {
  if (status === 'completed') return '评估完成';
  if (status === 'failed') return '评估失败';
  if (status === 'canceled' || status === 'cancelled') return '已取消';
  if (status === 'validating_result' || status === 'generating_result') return '生成结果中';
  return 'AI评估中';
}

function progressLabels(status: string) {
  const terminal = status === 'failed' ? '评估失败' : status === 'canceled' || status === 'cancelled' ? '已取消' : '评估完成';
  return ['提交需求', 'AI评估中', '生成结果中', terminal];
}

function progressClass(status: string, index: number) {
  const activeMap: Record<string, number> = {
    waiting_ai_call: 1,
    validating_result: 2,
    generating_result: 2,
    completed: 3,
    failed: 3,
    canceled: 3,
    cancelled: 3,
  };
  const active = activeMap[status] ?? 1;
  if (index < active) return 'done';
  if (index === active) return 'active';
  return '';
}

function progressText(label: string) {
  const map: Record<string, string> = {
    提交需求: '已接收需求和任务参数',
    AI评估中: '浏览器调用模型并回传评估结果',
    生成结果中: '后端生成摘要和 Excel',
    评估完成: '结果已生成，可下载 Excel',
    评估失败: '评估失败，可复制任务重新生成',
    已取消: '任务已取消',
  };
  return map[label] || '';
}
