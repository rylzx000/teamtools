# Design: baseline-existing-teamtools

本次工作是 existing artifacts baseline conversion：建立对现状的结构化描述，而不是设计新功能。OpenSpec 内容默认使用简体中文，change id、spec id 和目录使用英文 kebab-case，`Requirement`、`Scenario` 等固定结构关键字保留英文。

## 来源与范围

- 根文档：`README.md`、`AGENTS.md`。
- 平台文档：`docs/architecture/`、`docs/deployment/`。
- FPA 文档：`docs/modules/fpa/`。
- UI 文档：`docs/ui/`。
- 实现与样例路径仅作为规格来源引用，不复制脚本和样例全文。

## 规格拆分

1. `platform-architecture`：平台架构、模型调用边界、部署、安全和编码底线。
2. `task-processing`：统一任务、文件、事件、运行目录和数据库口径。
3. `fpa-workflow`：FPA 用户输入、系统资料、主链路、取消、失败、重新运行和结果可见性。
4. `fpa-interface-ui`：FPA API、页面结构、状态展示、按钮权限和用户可见产物。
5. `fpa-ai-contract`：AI 请求包、提示词、系统资料、AI JSON、校验和敏感信息边界。
6. `fpa-excel-output`：三类 JSON、脚本 payload、模板保真、功能点计算、目标命中和质量提示。

## 提炼原则

- 只提炼稳定业务要求、系统边界和可验证验收场景。
- 原文档中的完整接口示例、表结构明细、Excel 单元格细节和脚本实现保持原文引用。
- 文档与实现可能存在冲突的地方写入“Known Limits / 待确认点”。
- OpenSpec 作为结构化基线，不替代详细设计文档。

## 验证策略

- 运行 `openspec validate --all --strict` 校验规格结构。
- 运行 `.\scripts\check-encoding.ps1` 校验文本编码。
- 运行 `rg` 检查迁移后的 Comet 配置中没有遗留 `selfCam` 绝对路径或业务描述。
