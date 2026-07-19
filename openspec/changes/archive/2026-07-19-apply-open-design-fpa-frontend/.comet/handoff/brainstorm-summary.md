# Brainstorm Summary

- Change: apply-open-design-fpa-frontend
- Date: 2026-07-19

## 当前状态

- 已确认本 change 是新的运行态前端落地 change，不修改已归档 `frontend-page-style-adjustment`。
- open 阶段 proposal、design、tasks、delta spec 已补齐并通过 `openspec validate apply-open-design-fpa-frontend --strict`。
- Comet design 交接包已由脚本生成：`openspec/changes/apply-open-design-fpa-frontend/.comet/handoff/design-context.md`。

## 确认的技术方案

推荐方案是“补缺+收敛展示”：保留现有 React 单文件结构和 FPA 主链路，只补最小后端 `GET /api/fpa/form-config`，前端从接口加载表单配置，并按 Open Design 调整平台壳、三页密度、状态主内容和普通用户产物可见性。

## 关键取舍与风险

- 不拆 `App.tsx`，减少回归风险，但文件会继续偏大。
- 不改后端状态机，只在前端做简化阶段映射，避免扩大业务流程风险。
- 不使用过程 JSON 代替 Markdown 预览；缺少 `AI分析.md` 或 `AI评估.md` 时显示空态。
- 管理员排查信息先默认折叠或弱化，不暴露敏感路径、环境变量、API Key 或完整后台排查产物。

## 测试策略

- 后端补测 `GET /api/fpa/form-config`，验证系统配置不含 `knowledge_dir`。
- 后端回归 FPA MVP 测试，覆盖任务创建、AI 请求包、结果回传和 Excel 下载不破坏。
- 前端运行 `npm run build`，必要时浏览器冒烟三页。
- 全局运行 `.\scripts\check-encoding.ps1` 和 `openspec validate --all --strict`。

## Spec Patch

暂无。当前 delta spec 已覆盖本轮范围，若后续实现中发现接口字段或可见性边界缺口，再最小回写。
