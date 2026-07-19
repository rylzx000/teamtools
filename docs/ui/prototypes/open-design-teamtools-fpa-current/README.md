# Open Design TeamTools FPA 当前原型快照

本目录保存 Open Design 当前 TeamTools FPA PC 中后台原型，作为后续前端开发视觉和交互参考。

保留英文术语说明：`Open Design`、`TeamTools`、`FPA`、`HTML/CSS/JS` 是工具、产品、模块和文件类型名称，按技术约定保留英文。

## 文件

- `index.html`：跳转入口，登录后默认进入 FPA 任务列表。
- `fpa-tasks.html`：FPA 任务列表。
- `fpa-submit.html`：FPA 提交评估。
- `fpa-detail.html`：FPA 查看详情。
- `teamtools.css`：共享样式。
- `teamtools.js`：静态原型交互。

## 使用方式

直接打开 `index.html` 会进入 FPA 任务列表。该快照只用于开发参考，不作为正式前端源代码。

## 首版布局口径

- 登录后直接进入 `fpa-tasks.html`，不展示独立首页、模块卡片或后续模块预留。
- 首版只有 FPA 模块，不展示左侧模块栏；顶部左侧固定展示带绿色点的 `FPA 工作量评估`。
- `任务列表`、`提交评估`、`查看详情` 是 FPA 模块内页签，保留在主工作区顶部。
## 对齐规则

- 页面视觉与节奏参考 `docs/ui/modules/fpa-前端页面样式修改.md`。
- 字段、状态、权限、接口和产物规则以 `docs/ui/modules/fpa-页面设计.md`、`docs/modules/fpa/` 和 `openspec/specs/` 为准。
- `系统选择`、`规模计数时机`、`完整性级别` 在正式开发中必须来自后端配置，不写死在前端。

## 列表操作与详情摘要更新

- 任务列表操作列只保留 `查看`；已完成且可下载时额外展示 `下载`。
- `取消任务`、`复制并重新生成` 放在查看详情页的任务操作折叠区。
- 查看详情页任务摘要不重复展示当前状态，Excel 下载入口放在任务摘要区；结果查看区只保留 `AI分析.md` 和 `FPA生成过程.json` 预览/复制。
