## Context

当前前端详情页已经基本按管理员角色展示 `结果查看 / AI分析.md` 区域，但后端 `task_detail()` 仍会在 `artifacts.ai_analysis_md.content` 中返回 Markdown 内容。普通用户只要直接调用接口，仍可能获得后台复核内容。

## Goals / Non-Goals

- 目标：在后端接口层强制区分普通用户和管理员的 AI 分析 Markdown 可见性。
- 目标：普通用户保留自己的任务状态、结果摘要、质量提示摘要和 Excel 下载能力。
- 目标：管理员保留查看全部任务以及页面查看/复制 AI 分析 Markdown 的能力。
- 非目标：不新增文件下载类型，不调整任务状态机，不修改 AI schema、提示词或 Excel 生成脚本。

## Solution

1. 在 `backend/app/modules/fpa/service.py` 的任务详情构造逻辑中，将 `ai_analysis_md` 的可见性绑定到 `is_admin`。
2. 当文件存在且当前用户是管理员时，返回 `available = true` 和 `content`；普通用户统一返回 `available = false`、`content = None`。
3. 保持 Excel 下载权限不变：普通用户仍可下载自己的完成任务 Excel。
4. 前端只在管理员且后端声明可见时展示 `结果查看 / AI分析.md` 预览和复制入口。
5. 更新测试和文档，删除普通用户可看 AI 分析 Markdown 的旧断言和旧描述。

## Risks

- 若外部调用方曾依赖普通用户接口中的 `artifacts.ai_analysis_md.content`，本修复会改变其可见字段；这是预期的权限收口。
- 文档中可能存在历史“普通用户可查看 AI评估.md”的描述，需要针对相关文件搜索后最小同步。
