## Why

上线前发现 FPA 任务详情接口仍向普通用户返回 `AI分析.md` / `AI评估.md` 内容，单靠前端隐藏不足以形成权限边界。需要在后端接口层收口，确保普通用户只看到结果摘要和 Excel 下载入口。

## What Changes

- 后端任务详情按角色控制 `artifacts.ai_analysis_md`：管理员可见并返回内容，普通用户不可见且内容为空。
- 调整前端确认逻辑，确保普通用户不展示或复制 `AI分析.md` / `AI评估.md`。
- 更新 FPA 权限边界测试，覆盖普通用户和管理员查看同一完成任务的差异。
- 同步文档和 OpenSpec 口径：`AI分析.md` / `AI评估.md` 属于管理员复核/排查产物，不再是普通用户成功页产物。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `fpa-interface-ui`：任务详情页和接口产物可见性收口，普通用户不再查看或复制 `AI分析.md` / `AI评估.md`。
- `fpa-workflow`：成功任务产物边界调整为普通用户查看摘要并下载 Excel，管理员可查看 AI 分析 Markdown 和排查产物。

## Impact

- 影响后端 FPA 任务详情接口返回字段和权限测试。
- 影响前端详情页结果查看区域的角色展示确认。
- 影响 FPA 接口、页面和产物边界文档。
- 不改变数据库 schema、任务状态机、AI 提示词、Excel 生成脚本或业务流程。
