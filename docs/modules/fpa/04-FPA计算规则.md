# FPA 计算规则

## 1. 文档目的

本文档记录 FPA Excel 生成链路中必须由脚本同步计算的关键口径，确保：

- 给定标准化脚本 payload 后，脚本计算结果、`FPA生成过程.json` 和 Excel 模板公式口径一致。
- 页面展示结果不读取 `.xlsx` 公式缓存。
- Excel 文件仍保留模板公式，用户下载后可用 Excel/WPS 打开并自动重算。

本文档只覆盖 Excel 生成契约相关计算，不讨论 AI 提示词、模型调用、系统资料组织、前端页面实现或后端接口实现。

## 2. 三类 JSON 边界

FPA 链路中必须区分三类 JSON，不能混用。

| JSON | 生成方 | 用途 | 是否包含路径/目标人天 |
|---|---|---|---|
| `AI结构化结果.json` | AI | 只保存业务判断，如功能点明细、项目特征建议、审计说明、不确定点 | 不要求 AI 输出 `template_path`、`output_path`、`target_work_days` |
| Excel 脚本输入 payload | 后端 | 后端合并 AI 结构化结果、任务配置、模板路径、输出路径、目标人天后传给脚本 | 可以包含 `template_path`、`output_path`、`target_work_days` |
| `FPA生成过程.json` | Excel 脚本 | 保存标准化明细、计算结果、目标命中、质量提示、输出路径等 | 由脚本生成，不由 AI 直接生成 |

字段来源规则：

- AI 只负责输出业务判断，不负责输出模板路径、输出路径、脚本控制参数或最终计算结果。
- 平台/接口/任务表统一使用 `target_person_days` 表示目标人天。
- `target_person_days` 可以在 AI 请求包中作为参考目标，辅助 AI 做 FPA 明细校准。
- 现有脚本可暂时兼容 `target_work_days`。
- 后端调用 Excel 脚本前，必须把 `target_person_days` 映射为脚本 payload 的 `target_work_days`。
- 目标命中计算只以脚本 payload 中的 `target_work_days` 为准，不以 AI 输出为准。
- 用户页面可以不强制填写需求名称；后端生成脚本 payload 时必须保证 `requirement_name` 有值。
- 如果用户未填需求名称，后端用上传文件名、需求文本摘要或任务编号生成兜底名称。

## 3. 当前模板范围

当前基准模板：

```text
D:\project\fpa功能点法工作量评估\fpa-skill\assets\fpa工作量评估模版.xlsx
```

必要工作表：

| 工作表 | 用途 |
|---|---|
| `项目特征` | 写入项目特征输入值，模板在 `D` 列计算调整因子 |
| `规模估算` | 写入功能点明细，模板计算 UFP、US 和合计 |
| `开发费用估算` | 模板展示规模、人天、报价等结果 |
| `模板使用说明&基础参数` | 存放权重、调整系数、允许值和基础参数 |

当前旧脚本：

```text
D:\project\fpa功能点法工作量评估\fpa-skill\scripts\fill_fpa_workbook.py
```

旧脚本可作为实现基础，但其 1-9 条明细限制属于当前实现现状，不是最终产品契约。

## 4. Excel 脚本输入 payload

脚本 payload 是后端合并后的输入，不是 AI 直接输出。

| 字段 | 脚本 payload 必填 | 类型 | 说明 |
|---|---:|---|---|
| `requirement_name` | 是 | string | 后端保证有值；用于输出文件名和结果摘要 |
| `items` | 是 | array | 功能点明细，来源于 AI 结构化结果并经后端校验 |
| `project_features` | 否 | object | 后端合并页面选择、平台默认值、模板默认值和 AI 建议后生成 |
| `target_work_days` | 否 | number | 由任务字段 `target_person_days` 映射而来 |
| `template_path` | 否 | string | 后端根据资源配置填入，不要求 AI 输出 |
| `output_path` | 否 | string | 后端根据任务目录生成，不要求 AI 输出 |
| `keep_intermediate_artifacts` | 否 | boolean | 是否保留 `FPA生成过程.json`，默认保留 |
| `assessment_context` | 否 | object | 质量提示上下文，主要来源于 AI 业务判断和任务配置 |

`items[]` 结构：

| 字段 | 必填 | 允许值/说明 |
|---|---:|---|
| `system` | 是 | 子系统/系统名称 |
| `level1_module` | 是 | 一级模块 |
| `level2_module` | 否 | 二级模块 |
| `level3_module` | 否 | 三级模块 |
| `level4_module` | 否 | 四级模块 |
| `function_description` | 是 | 功能项描述 |
| `count_item_name` | 是 | 功能点计数项名称 |
| `category` | 是 | `ILF`、`EIF`、`EI`、`EO`、`EQ` |
| `reuse` | 是 | `高`、`中`、`低` |
| `change_type` | 是 | `新增`、`修改`、`删除` |
| `remark` | 是 | 审计说明；建议包含“类型依据”“重用依据”“修改类型” |

`project_features` 可覆盖字段：

| 字段 | 写入单元格 | 说明 |
|---|---|---|
| `规模计数时机` | `项目特征!C1` | 默认 `估算早期` |
| `应用类型` | `项目特征!C2` | 默认 `业务处理` |
| `分布式处理` | `项目特征!C3` | 非功能特征之一 |
| `性能` | `项目特征!C4` | 非功能特征之一 |
| `可靠性` | `项目特征!C5` | 非功能特征之一 |
| `多重站点` | `项目特征!C6` | 非功能特征之一 |
| `完整性级别` | `项目特征!C7` | 完整性调整因子 |
| `开发语言` | `项目特征!C8` | 开发语言调整因子 |
| `开发团队背景` | `项目特征!C9` | 团队背景调整因子 |

MVP 模板保真规则：

- 首版只允许覆盖 `项目特征!C1`。
- `项目特征!C2:C10` 默认保持模板原值。
- 脚本可以读取 `C2:C10` 及其公式结果参与计算，但不得把内部枚举、简称或等级描述写回 Excel。
- 不得把 `分布式处理`、`性能`、`可靠性`、`多重站点`、`完整性级别`、`开发语言`、`开发团队背景` 写成 `中等`、`3GL` 等非模板下拉原文。
- 如果后续页面支持调整 `C2:C10`，传入值必须等于模板下拉项原文，并通过模板允许值校验。

`项目特征!C10` 为模板内“开发平台”默认值。当前脚本不通过 `project_features` 覆盖该值，但会读取其调整因子参与工作量中值计算。

## 4.1 明细备注口径

`items[].remark` 最终写入 `规模估算!N`，必须满足人工复核和上传后审计需要。

Excel 备注统一采用三段式：

```text
类别原因：{category}，{为什么属于该功能点类型}；复用原因：{reuse}，{为什么是该复用程度}；修改类型原因：{change_type}，{为什么是该修改类型}。
```

规则：

- 备注必须包含“类别原因：”“复用原因：”“修改类型原因：”。
- 备注必须明确包含对应的 `category`、`reuse`、`change_type` 取值。
- 不能只写笼统说明，例如“已有功能，流程归属调整，字段逻辑不变”。
- 若 AI 未输出完整三段式原因，脚本必须根据明细字段和原始 `remark` 生成兜底三段式备注。
- 后续可扩展 AI 输出 `category_reason`、`reuse_reason`、`change_type_reason`；未扩展前，脚本仍承担标准化备注职责。

## 5. 功能点与规模计算

### 5.1 功能点权重

模板 `规模估算!C1` 决定权重口径：

| 估算方法 | 权重来源 | ILF | EIF | EI | EO | EQ |
|---|---|---:|---:|---:|---:|---:|
| `预估功能点` | `模板使用说明&基础参数!D15:E19` | 35 | 15 | 当前模板为空 | 当前模板为空 | 当前模板为空 |
| `估算功能点` | `模板使用说明&基础参数!D22:E26` | 10 | 7 | 4 | 5 | 4 |

当前模板默认 `规模估算!C1 = 估算功能点`。若所选方法下某个类别无权重，脚本必须按技术失败处理，不生成成功状态。

### 5.2 重用与修改类型系数

重用程度系数来自 `模板使用说明&基础参数!D5:E7`：

| 重用程度 | 系数 |
|---|---:|
| 高 | 0.333333333333333 |
| 中 | 0.666666666666667 |
| 低 | 1 |

修改类型系数来自 `模板使用说明&基础参数!D10:E12`：

| 修改类型 | 系数 |
|---|---:|
| 新增 | 1 |
| 修改 | 0.8 |
| 删除 | 0.2 |

### 5.3 核心公式

每条功能点：

```text
UFP = category 对应权重
US = UFP * reuse 系数 * change_type 系数
```

合计：

```text
adjusted_fp_total = SUM(US)
```

规模与工作量中值：

```text
adjusted_size = adjusted_fp_total * 规模计数时机因子
unadjusted_mid = adjusted_size * productivity_mid / 8
quality_factor = 1 + 0.025 * SUM(分布式处理、性能、可靠性、多重站点因子)

adjusted_work_days_middle =
  unadjusted_mid
  * 应用类型因子
  * quality_factor
  * 完整性级别因子
  * 开发语言因子
  * 开发团队背景因子
  * 开发平台因子
```

当前模板中 `productivity_mid = 开发费用估算!C5 = 7.88`。

脚本输出字段：

| 字段 | 说明 |
|---|---|
| `estimated.ufp_total` | UFP 合计，保留 4 位小数 |
| `estimated.adjusted_fp_total` | US 合计，保留 4 位小数 |
| `estimated.scale_factor` | 规模计数时机调整因子，保留 4 位小数 |
| `estimated.adjusted_size` | 调整后规模，保留 4 位小数 |
| `estimated.adjusted_work_days_middle` | 调整后工作量中值，保留 2 位小数 |

## 6. 目标命中口径

平台统一字段是 `target_person_days`。后端调用脚本前映射为：

```json
{
  "target_work_days": "{target_person_days}"
}
```

脚本生成 `target_check`：

```text
target_lower_bound = target_work_days * 0.9
target_upper_bound = target_work_days * 1.1
within_target_10_percent =
  target_lower_bound <= adjusted_work_days_middle <= target_upper_bound
```

输出字段：

| 字段 | 说明 |
|---|---|
| `target_check.target_work_days` | 脚本 payload 中的目标人天，来源于平台 `target_person_days` |
| `target_check.within_target_10_percent` | 是否命中目标 ±10% |
| `target_check.target_lower_bound` | 目标下界，保留 2 位小数 |
| `target_check.target_upper_bound` | 目标上界，保留 2 位小数 |

若平台任务未提供 `target_person_days`，脚本 payload 可不传 `target_work_days`，`target_check = null`。

## 7. 页面展示计算边界

MVP 页面至少展示：

- 中值人天：来自 `FPA生成过程.json` 的 `estimated.adjusted_work_days_middle`。
- 功能点合计：来自 `FPA生成过程.json` 的 `estimated.ufp_total`。
- 调整后功能点合计：来自 `FPA生成过程.json` 的 `estimated.adjusted_fp_total`。
- 质量提示：来自 `FPA生成过程.json` 的 `quality_warnings` 和 `quality_gate`。

边界规则：

- 页面结果不能读取 Excel 公式缓存。
- 页面展示必须以脚本计算结果和 `FPA生成过程.json` 为准。
- 如果页面要展示下限人天、上限人天、报价，脚本也必须同步计算并写入 `FPA生成过程.json`。
- 下限人天、上限人天、报价不能从 `.xlsx` 公式缓存读取。
- Excel 仍作为最终下载产物，保留公式，供用户人工调整参数后重算。

当前旧脚本只同步计算中值、功能点合计和调整后功能点合计；下限、上限和报价若要上页面，需要补充脚本计算与过程 JSON 字段。

## 8. 质量提示与门禁口径

质量提示基于标准化后的 `items`、`assessment_context` 和 `target_check` 计算，不读取 Excel 公式缓存。

### 8.1 quality_warnings

`quality_warnings` 是风险提示，用于提醒人工复核。它本身不是技术失败，也不默认阻断 Excel 生成和下载。

主要 warning：

| code | 触发口径 | 默认影响 |
|---|---|---|
| `CORE_D1_ITEM_COUNT_LOW` | 核心系统 D1 且条目数偏少 | 复核风险；可参与强风险组合 |
| `CORE_D2_ITEM_COUNT_LOW` | 核心系统 D2 且条目数偏少 | 复核风险；可参与强风险组合 |
| `CORE_D3_COMPLEX_SIGNALS` | 核心系统 D3 命中多个复杂信号 | 复核风险；可参与强风险组合 |
| `CORE_D3_COMPLEX_SPLIT_THIN` | 核心 D3 复杂但拆分偏薄 | 复核风险；可参与强风险组合 |
| `MERGED_BASIC_PROCESS_RISK` | 单条功能点合并多个基本过程信号 | 复核风险；可参与强风险组合 |
| `CORE_NO_ILF` | 核心 D1/D2 无 ILF | 复核风险；可参与强风险组合 |
| `CORE_NO_EO` | 核心 D1/D2 无 EO | 复核提示 |
| `ONLY_EI_EQ_NO_DATA_OUTPUT` | 只有 EI/EQ，缺少 ILF/EO | 复核风险；可参与强风险组合 |
| `DATA_SIGNAL_WITHOUT_ILF` | 有结果存储信号但无 ILF | 复核风险；可参与强风险组合 |
| `OUTPUT_SIGNAL_WITHOUT_EO` | 有派生输出或风险处理信号但无 EO | 复核风险；可参与强风险组合 |
| `QUERY_DISPLAY_SIGNAL_WITHOUT_EQ_OR_EO` | 有查询展示信号但无 EQ/EO | 复核提示 |
| `CORE_HIGH_REUSE_RATIO` | 核心 D1/D2 高/中复用占比过高 | 复核提示 |
| `CORE_CHANGE_RATIO_HIGH` | 核心 D1/D2 修改占比过高 | 复核提示 |
| `NEW_ILF_WITHOUT_EI` | 有新增 ILF 但无 EI | 强风险 |
| `NEW_ILF_WITHOUT_EQ_OR_EO` | 有新增 ILF 但无 EQ/EO | 复核提示 |
| `REMARK_INCOMPLETE` | 备注缺少类型、复用或修改依据 | 复核提示 |
| `TARGET_OUT_OF_RANGE` | 中值未命中目标 ±10% | 复核提示 |
| `CRUD_OVERCOUNT_RISK` | 按物理表 CRUD 机械拆分风险 | 复核提示 |

### 8.2 quality_gate

`quality_gate.status` 取值：

| 状态 | 含义 | 下载行为 |
|---|---|---|
| `passed` | 无明显质量提示 | 可下载 |
| `review_required` | 存在风险提示，建议复核 | 可下载 |
| `failed` | 强风险/不建议不复核直接交付 | 默认仍可下载，但页面应突出提示 |

`quality_gate.failed` 表示业务质量强风险，不等同于技术失败。除非出现结构错误、模板错误、脚本错误、JSON 校验失败等技术失败，否则不因为业务质量提示阻断 Excel 生成和下载。

技术失败示例：

- 输入 JSON 不是合法 object。
- `items` 为空或字段/枚举校验失败。
- 模板文件缺失。
- 必要 sheet 缺失。
- 映射配置缺失或与模板结构不一致。
- 公式列、合计行、结果单元格无法定位。
- 脚本运行异常。

强风险组合命中时，`FPA生成过程.json` 应保留：

```json
{
  "quality_gate": {
    "status": "failed",
    "deliverable_valid": false,
    "reason_codes": ["..."],
    "required_action": "建议回到候选拆分阶段复核 ILF、EO、EQ、批量处理、风险提示、强排查和结果存储候选，重新生成 payload 并重跑脚本；不建议不复核直接交付。"
  },
  "deliverable_valid": false
}
```

## 9. 明细条目数量口径

目标契约：

- 平台设计不设置 29 条硬上限。
- 最终目标是同一个 Excel 内支持超过模板默认明细行数。
- 脚本应通过动态插行、复制样式、复制公式、扩展数据验证、更新合计公式和引用公式实现扩展。

当前实现现状：

- 旧脚本和旧模板可靠支持 1-9 条功能点，来自 `规模估算!6:14`。
- 旧脚本超过 9 条会失败，这是未改造前限制，不是最终产品方案。
- 开发前必须改造脚本支持动态增行，否则超过 9 条会导致合计公式遗漏或结果不完整。

文档和实现不得把“超过 9 条拆多个 Excel”作为目标方案。若上线前脚本尚未改造完成，应在当前实现限制中明确提示，而不是写入目标契约。

## 10. Excel 公式与脚本计算边界

脚本必须同步计算：

- `estimated.ufp_total`
- `estimated.adjusted_fp_total`
- `estimated.scale_factor`
- `estimated.adjusted_size`
- `estimated.adjusted_work_days_middle`
- `target_check`
- `quality_warnings`
- `quality_gate`
- `deliverable_valid`

模板继续负责：

- 明细行编号。
- 每行 UFP、US 公式。
- 合计行公式。
- 下限/中值/上限人天展示。
- 基准报价展示。
- 用户打开 Excel/WPS 后重算。

脚本不得依赖读取 Excel 公式缓存作为页面结果来源。`openpyxl` 保存后不会写入公式缓存值，因此页面与任务摘要以脚本 stdout 和 `FPA生成过程.json` 为准。

## 11. 当前实现现状与待改造项

当前旧脚本可复用：

- 模板路径和输出路径解析。
- 必要 sheet 校验。
- 项目特征默认值读取与允许值校验。
- 功能点明细标准化与写入。
- UFP、US、调整后规模、中值人天同步计算。
- `target_work_days` 目标命中判断。
- `quality_warnings`、`quality_gate`、`deliverable_valid` 生成。
- `FPA生成过程.json` 输出。

必须改造：

- 引入 `excel_mapping.yaml` 或等价映射配置。
- 将 sheet、行列、公式列、合计行、结果单元格、允许值区域从硬编码迁移到映射配置。
- 支持超过模板默认明细行数的动态增行。
- 将平台 `target_person_days` 到脚本 `target_work_days` 的转换固定在后端调用脚本前。
- 若页面展示下限、上限、报价，脚本必须同步计算并写入 `FPA生成过程.json`。

## 12. 变更维护要求

当模板或脚本变化时，按以下顺序维护：

1. 先更新本计算规则。
2. 再更新 Excel 映射契约文档。
3. 再修改脚本。
4. 用同一组 payload 对比脚本输出 JSON 与 Excel 打开重算后的关键单元格。

至少校验：

- `estimated.ufp_total` 对齐 `规模估算!C2`。
- `estimated.adjusted_fp_total` 对齐 `规模估算!C3`。
- `estimated.adjusted_work_days_middle` 对齐 `开发费用估算!C17`。
- `target_check.within_target_10_percent` 符合 `target_person_days` 映射后的 ±10% 规则。
- `quality_gate.status` 与 warning 组合一致。
