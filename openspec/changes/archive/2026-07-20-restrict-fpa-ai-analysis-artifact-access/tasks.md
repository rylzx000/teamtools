## 1. Implementation

- [x] 1.1 检查 FPA 任务详情接口、前端详情展示和相关文档中的 AI 分析 Markdown 权限口径。
- [x] 1.2 修改后端 `task_detail()`，确保普通用户响应中 `ai_analysis_md.available = false` 且 `content = null`。
- [x] 1.3 确认或最小调整前端详情页，普通用户不展示 AI 分析 Markdown 预览/复制，管理员保留。
- [x] 1.4 更新后端权限测试，覆盖普通用户、管理员、Excel 下载和 admin-only 排查产物。
- [x] 1.5 同步相关文档和 OpenSpec delta spec。

## 2. Verification

- [x] 2.1 运行后端 FPA MVP 权限相关测试。
- [x] 2.2 运行前端类型检查或构建。
- [x] 2.3 运行 `.\scripts\check-encoding.ps1`。
