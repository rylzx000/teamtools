# Tasks: baseline-existing-teamtools

## 1. Comet 与协作规则

- [x] 1.1 迁移 `.comet/` 项目配置。
- [x] 1.2 迁移 `.codex/` Comet / OpenSpec 技能、阶段守卫和 hook 配置。
- [x] 1.3 将 hook 中的项目路径从 `D:/project/selfCam` 改为 `D:/project/teamtools`。
- [x] 1.4 在 `AGENTS.md` 增加 OpenSpec / Comet 使用规则、命名语言规则和最终工具使用汇总格式。

## 2. OpenSpec 配置

- [x] 2.1 新增 `openspec/config.yaml`，写入 TeamTools 项目上下文、事实来源和规则。
- [x] 2.2 建立 `openspec/changes/archive/2026-07-15-baseline-existing-teamtools/` 基线索引。

## 3. 正式能力规格

- [x] 3.1 新增 `platform-architecture` 规格。
- [x] 3.2 新增 `task-processing` 规格。
- [x] 3.3 新增 `fpa-workflow` 规格。
- [x] 3.4 新增 `fpa-interface-ui` 规格。
- [x] 3.5 新增 `fpa-ai-contract` 规格。
- [x] 3.6 新增 `fpa-excel-output` 规格。

## 4. 验证

- [x] 4.1 运行 OpenSpec strict validation。
- [x] 4.2 运行编码检查。
- [x] 4.3 检查是否存在 selfCam 绝对路径或业务描述残留。
