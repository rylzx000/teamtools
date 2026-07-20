# TeamTools 项目工作规则

## 编码规则

- 文本文件统一使用 UTF-8。
- Markdown、Python、JSON、YAML、TypeScript、JavaScript、HTML、CSS、PowerShell 脚本必须保存为 UTF-8。
- 面向 Excel 直接打开的 `.csv` 文件优先使用 UTF-8 with BOM。
- 不新增 GBK、UTF-16 或其他混合编码文本文件。
- PowerShell 写中文文件时必须显式指定 `-Encoding utf8`。
- Python 读写文本文件必须显式使用 `encoding="utf-8"`；写给 Excel 打开的 CSV 使用 `encoding="utf-8-sig"`。
- Node.js 写文本文件必须显式使用 `"utf8"`。
- `subprocess.run(..., text=True)` 捕获中文输出时必须显式指定 `encoding="utf-8"`，必要时加 `errors="replace"`。
- 提交或交付前运行：

```powershell
.\scripts\check-encoding.ps1
```

## OpenSpec / Comet 使用规则

- 本项目已接入 OpenSpec 与 Comet：OpenSpec 根目录为 `openspec/`，Comet 项目配置为 `.comet/`，Codex 侧技能与规则位于 `.codex/`。
- 本项目的实施请求默认先由 Comet 根据任务性质路由：新增 capability、公共接口、schema、跨页面状态流或架构调整使用 `full`；不新增 capability 的明确既有行为修复使用 `hotfix`；文档、配置、prompt 和可收敛为单一 change 的轻中量修改使用 `tweak`。
- 用户明确指定 `comet`、`comet-hotfix`、`comet-tweak` 或要求不使用 Comet 时，以用户选择为准；只读检查、分析和方案输出不启动实施 workflow。
- 如果存在与当前请求匹配的 active change，默认恢复该 change；如果 active change 不匹配或同时存在多个候选，先让用户确认继续哪个 change 或创建新 change。
- 涉及新功能、业务流程、接口、配置体系、技术架构、页面状态流或跨模块能力的改动，优先先创建或更新 OpenSpec change，再进入实现。
- 当前能力基线位于 `openspec/specs/`；`openspec/changes/archive/2026-07-15-baseline-existing-teamtools/` 保留现有成果物基线化过程、来源映射和历史验收场景。
- 需要理解现有业务规则时，先阅读 `openspec/specs/` 下的对应能力规格，再通过归档基线定位并回源阅读 `README.md`、`docs/architecture/`、`docs/deployment/`、`docs/modules/` 或 `docs/ui/` 下的原文件；不要把原文档全文迁移进 OpenSpec。
- 使用 Comet 时遵循阶段守卫、脏工作区检查和验证要求；不要绕过 Comet/OpenSpec 流程直接扩大改动范围。
- 接入 OpenSpec / Comet 不改变本项目既有安全红线：未经用户当前任务明确授权，不自动 commit、push、打 tag、创建或切换分支；不修改无关业务代码，不新增无关文档。
- 每次任务的最终汇总必须在最后一行说明本轮 Comet、OpenSpec、Superpowers 的使用情况；已使用时写明阶段或用途，未使用时明确写“未使用”。
- 凡涉及 Comet 流程的对话，最终回复必须主动说明下一步建议处理内容；如果当前流程已完成且没有必要继续操作，也要明确说明“可暂时停止，等待下一项需求”。`Comet` 保留英文是因为它是流程工具专有名词，需兼容工具命名。
- 工具使用情况固定使用格式：`工具使用情况：Comet（...）；OpenSpec（...）；Superpowers（...）。`

## OpenSpec 命名与语言规则

- 项目内所有文字内容，在不影响代码标识符、协议字段、第三方专有名词、模板关键字和工具要求的前提下，能使用中文的都必须使用中文。
- 项目文档、需求说明、设计说明、测试说明、变更记录、版本说明和提交备注必须优先使用中文。
- OpenSpec 文档正文、标题、背景、设计说明、验收场景默认使用简体中文。
- OpenSpec 的 change id、spec id 和目录名默认使用英文短名或 kebab-case，例如 `baseline-existing-teamtools`、`fpa-workflow`、`platform-architecture`。
- OpenSpec 模板中的固定结构关键字保留英文，例如 `Requirement`、`Scenario`、`ADDED`、`MODIFIED`、`REMOVED`。
- Comet、OpenSpec 相关文档中的 tag、id、目录名、状态值、模板关键字和机器可读字段，按对应工具或模板要求选择合适语言，不为了中文化破坏工具兼容性。
- 不使用中文目录名作为 OpenSpec change/spec 标识，避免 CLI、脚本、Git、CI 或跨平台路径兼容问题。
- 现有 `docs/` 中文文档保留原路径，不为了接入 OpenSpec 强制改名或搬迁。
- OpenSpec 只做结构化索引、能力规格、验收标准提炼和变更归档。
