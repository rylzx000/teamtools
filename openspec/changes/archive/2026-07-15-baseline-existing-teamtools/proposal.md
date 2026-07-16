# Proposal: baseline-existing-teamtools

TeamTools 已形成平台架构、部署、任务处理、FPA 模块、接口、AI 契约、Excel 生成和 UI 设计文档，但关键能力分散在 `README.md` 与 `docs/` 下，缺少可供后续变更复用的结构化规格基线。现在需要把现有成果物提炼为 OpenSpec 能力规格，降低后续需求变更时的理解偏差，同时继续保留原文档作为详细事实来源。

## Goals

- 将现有项目成果物整理为 OpenSpec 基线，不新增或改变任何业务功能。
- 建立 6 个正式能力规格：平台架构、任务处理、FPA 主流程、FPA 接口与页面、FPA AI 契约、FPA Excel 生成。
- 建立基线索引，说明每个 spec 的来源文档和回源路径。
- 接入 Comet / OpenSpec 项目工作流规则，后续改动优先走 change 流程。

## Non-Goals

- 不修改业务代码、测试代码、运行数据或原有 `docs/` 内容。
- 不迁移原文档全文，不复制完整接口报文、模板单元格表或脚本实现细节。
- 不自动提交、推送、打 tag、创建或切换分支。
- 不声明未运行验证的业务功能已经通过。

## Impact

- 协作规则：`AGENTS.md`、`.codex/`、`.comet/`。
- OpenSpec：`openspec/config.yaml`、`openspec/specs/`、`openspec/changes/archive/2026-07-15-baseline-existing-teamtools/`。

## Risks

- 现有文档有少量部署与执行模型口径差异，基线规格需要记录为待确认点。
- 规格提炼不应替代原文档，后续实现仍需回源阅读细节。
