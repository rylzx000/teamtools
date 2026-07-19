## Why

当前 Open Design 项目已经形成 TeamTools FPA 首版 PC 中后台原型，但工程仓库尚未沉淀本轮页面样式修改原则，也没有把当前 HTML/CSS/JS 原型作为开发参考版本归档到工程文档中。后续前端实现若只参考分散对话，容易回到移动端、营销页或信息过载的方向。

## What Changes

- 新增一份“前端页面样式修改”说明，固化本轮确认的 PC 中后台壳子、三页页签、字体间距、提交页一屏展示、详情页减法等设计原则。
- 将 Open Design 当前原型文件归档到工程文档目录，作为后续实现的静态参考，不直接改动业务前端代码。
- 明确原型与工程文档冲突时，以 FPA 工程文档和 OpenSpec 能力规格为准。

## Scope

- 文档新增：FPA 前端页面样式修改说明。
- 原型归档：`index.html`、`fpa-submit.html`、`fpa-tasks.html`、`fpa-detail.html`、`teamtools.css`、`teamtools.js`。
- 不修改 `frontend/`、`backend/`、数据库 schema、接口契约和业务流程实现。

## Impact

- 影响工程文档和 UI 原型归档文件。
- 不新增 capability，不新增公共接口，不改变运行时代码。
