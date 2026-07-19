# 前端页面样式修改设计说明

## 背景

本 change 用于沉淀 Open Design 当前 TeamTools FPA 页面原型的视觉与交互原则，并把当前静态原型归档到工程文档中，方便后续前端开发按同一套页面节奏落地。

## 决策

- 保留 TeamTools PC 中后台平台壳，不再向移动端或营销页方向扩展。
- FPA 模块保持三页结构：任务列表、提交评估、查看详情。
- 当前原型作为开发视觉参考；字段、状态、权限和产物规则仍以工程文档与 OpenSpec 规格为准。
- 本次只新增文档与归档原型，不改运行时代码。

## 归档位置

- 样式原则文档：`docs/ui/modules/fpa-前端页面样式修改.md`
- 当前原型归档目录：`docs/ui/prototypes/open-design-teamtools-fpa-current/`

## 验收口径

- 文档能解释本轮页面修改原则和开发约束。
- 归档目录包含当前 Open Design 项目 6 个原型文件。
- 归档 HTML 能通过相对路径引用同目录下 CSS/JS。
