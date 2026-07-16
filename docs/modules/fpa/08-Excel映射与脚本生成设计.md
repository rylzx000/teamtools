# FPA Excel 映射与脚本生成设计

## 1. 设计目标

本文档定义 FPA Excel 生成链路中结构化 JSON、模板、脚本 payload、映射配置和生成过程产物之间的契约。

目标：

- 给定后端生成的 Excel 脚本输入 payload，稳定生成 FPA 工作量评估 Excel。
- Excel 生成使用既有模板和脚本能力，不从零创建工作簿。
- 模板位置变化优先通过 `excel_mapping.yaml` 或等价映射配置调整。
- 计算口径变化必须同步更新脚本和计算规则。
- 清楚区分当前旧脚本限制与目标契约，避免后续开发误解。

本文档只处理 Excel 生成契约，不讨论 AI 提示词、模型调用、系统资料组织、前端页面实现或后端接口实现。

## 2. 三类 JSON 与职责边界

| JSON | 生成方 | 主要内容 | 不应包含 |
|---|---|---|---|
| `AI结构化结果.json` | AI | 功能点明细、项目特征建议、评估上下文、审计说明、不确定点 | `template_path`、`output_path`、`target_work_days`、Excel 单元格、脚本计算结果 |
| Excel 脚本输入 payload | 后端 | 后端合并后的 `requirement_name`、`items`、`project_features`、`target_work_days`、模板路径、输出路径 | 不作为 AI 输出契约 |
| `FPA生成过程.json` | 脚本 | 标准化明细、计算结果、目标命中、质量提示、输出路径、模板路径 | 不由 AI 直接生成 |

处理链路：

```text
用户输入/任务配置
  + AI结构化结果.json
  + 模板与输出配置
  + target_person_days
  ↓ 后端合并
Excel 脚本输入 payload
  ↓ Excel 脚本
FPA生成过程.json + FPA工作量评估.xlsx
```

关键规则：

- 不要求 AI 直接输出 `template_path`、`output_path`、`target_work_days`。
- 平台/接口/任务表统一使用 `target_person_days`。
- 现有脚本可暂时兼容 `target_work_days`。
- 后端在调用 Excel 脚本前，把 `target_person_days` 映射为 payload 的 `target_work_days`。
- 用户页面可以不强制填写需求名称；脚本 payload 必须有 `requirement_name`。
- 当用户未填需求名称时，后端用上传文件名、需求文本摘要或任务编号生成兜底名称。

## 3. 现有资源

当前基准资源：

| 类型 | 路径 |
|---|---|
| Excel 模板 | `D:\project\fpa功能点法工作量评估\fpa-skill\assets\fpa工作量评估模版.xlsx` |
| 生成脚本 | `D:\project\fpa功能点法工作量评估\fpa-skill\scripts\fill_fpa_workbook.py` |
| 模板契约 | `D:\project\fpa功能点法工作量评估\fpa-skill\references\excel-template-contract.md` |
| 过程样例 | 历史目录中的 `*-FPA生成过程.json` |
| Excel 样例 | 历史目录中的 `*-FPA工作量评估.xlsx` |

当前 TeamTools 内置实现：

| 类型 | 路径/命令 |
|---|---|
| Excel 模板 | `data/modules/fpa/profile/templates/fpa_template.xlsx` |
| 映射文件 | `data/modules/fpa/profile/mapping/excel_mapping.yaml` |
| 生成脚本 | `scripts/fpa/fill_fpa_workbook.py` |
| 输入 payload 样例 | `data/modules/fpa/examples/excel/Excel脚本输入payload.sample.json` |
| 权威 Excel 样例 | `data/modules/fpa/examples/excel/FPA工作量评估.sample.xlsx` |
| 权威过程 JSON 样例 | `data/modules/fpa/examples/excel/FPA生成过程.sample.json` |

脚本入口保持稳定：

```powershell
python scripts\fpa\fill_fpa_workbook.py `
  --payload data/modules/fpa/examples/excel/Excel脚本输入payload.sample.json `
  --output <xlsx> `
  --process-output <json>
```

运行依赖：脚本使用 `openpyxl` 读取模板、复制样式、扩展明细行和保存 `.xlsx`，后端部署环境必须通过 `backend/pyproject.toml` 声明并安装 `openpyxl>=3.1`，不能依赖开发机全局 Python 已安装。

样例口径：`data/modules/fpa/examples/excel` 目录只保留中文命名的 Excel 和过程 JSON 作为权威样例；英文命名文件仅可作为临时调试输出，不纳入长期维护样例。

公式缓存边界：脚本不读取 `.xlsx` 公式缓存；页面、接口摘要和任务结果展示以脚本计算并写入的 `FPA生成过程.json` 为准。Excel 文件保留模板公式，用户用 Excel/WPS 打开后由办公软件自动重算。

模板必要 sheet：

| sheet | 用途 |
|---|---|
| `项目特征` | 项目特征输入与调整因子 |
| `规模估算` | 功能点明细、UFP、US、合计 |
| `开发费用估算` | 规模、人天、报价结果 |
| `模板使用说明&基础参数` | 允许值、权重、调整系数 |

### 3.1 模板保真硬约束

Excel 输出文件必须以 `fpa_template.xlsx` 为母版生成，不能从零创建 workbook，也不能用简化表格替代模板。

硬约束：

- sheet 名称和顺序必须与模板一致。
- 不得删除、新增或重命名模板 sheet。
- 模板固定区域的公式、合并单元格、数据验证、列宽、行高、样式和隐藏属性必须保留。
- 脚本只允许写入本文档明确列出的输入单元格和明细字段列。
- 未被明确允许写入的单元格必须保持模板原值。
- 生成结果用于上传外部系统识别时，必须优先保证模板结构和下拉原文一致，而不是只保证 Excel 能打开。
- 结构校验失败时应按技术失败处理，不应生成 `completed` 状态下的可下载正式 Excel。

当前 MVP 上传识别保真边界：

| 区域 | MVP 处理 |
|---|---|
| `项目特征!C1` | 可由页面/任务参数覆盖，取值必须是模板下拉原文 |
| `项目特征!C2:C10` | 默认保持模板原值，不用内部枚举、简称或“中等/3GL”等替换 |
| `规模估算` 明细输入列 | 允许写入 `B:I`、`K:L`、`N` |
| `规模估算` 公式列 | `A/J/M` 只允许保留、复制或公式平移，不写业务值 |
| 合计行与结果引用 | 仅在动态扩展明细行时按模板规则平移和更新公式 |
| `开发费用估算` | 默认不写业务值，只保留模板公式；必要时只更新对动态合计行的引用 |
| `模板使用说明&基础参数` | 只读，不写入 |

## 4. Excel 脚本输入 payload 契约

脚本 payload 是后端合并后的顶层 JSON object。

```json
{
  "requirement_name": "后端兜底后的需求名称",
  "target_work_days": 12,
  "template_path": "模板路径",
  "output_path": "输出 Excel 路径",
  "keep_intermediate_artifacts": true,
  "assessment_context": {
    "system_type": "核心系统",
    "requirement_level": "D2",
    "estimation_mode": "核心复杂改造模式",
    "source_level": "L2"
  },
  "project_features": {
    "规模计数时机": "估算早期",
    "应用类型": "业务处理",
    "分布式处理": "通过网络进行客户端/服务器及网络基础计算机系统分布处理和传输",
    "性能": "为满足性能需求事项，要求设计阶段进行性能分析，或在设计、开发阶段使用分析工具",
    "可靠性": "发生故障时可轻易修复，带来一定不便或经济损失",
    "多重站点": "在用途类似的硬件或软件环境下运行",
    "完整性级别": "完整性级别为A同时为达成完整性级别要求在软件开发全生命周期均采取了特定、明确的措施",
    "开发语言": "JAVA、C++、C#及其他同级别语言/平台",
    "开发团队背景": "为本行业开发过类似的项目"
  },
  "items": [
    {
      "system": "系统名称",
      "level1_module": "一级模块",
      "level2_module": "二级模块",
      "level3_module": "",
      "level4_module": "",
      "function_description": "功能项描述",
      "count_item_name": "功能点计数项名称",
      "category": "EI",
      "reuse": "中",
      "change_type": "新增",
      "remark": "类型依据：...；重用依据：...；修改类型：..."
    }
  ]
}
```

必填规则：

| 字段 | 脚本 payload 必填 | 说明 |
|---|---:|---|
| `requirement_name` | 是 | 后端必须兜底生成；不是用户前端必填 |
| `items` | 是 | 来源于 `AI结构化结果.json`，后端校验后传入 |
| `items[].system` | 是 | 写入 `规模估算!B` |
| `items[].level1_module` | 是 | 写入 `规模估算!C` |
| `items[].function_description` | 是 | 写入 `规模估算!G` |
| `items[].count_item_name` | 是 | 写入 `规模估算!H` |
| `items[].category` | 是 | `ILF`、`EIF`、`EI`、`EO`、`EQ` |
| `items[].reuse` | 是 | `高`、`中`、`低` |
| `items[].change_type` | 是 | `新增`、`修改`、`删除` |
| `items[].remark` | 是 | 审计说明 |

可选字段规则：

- `project_features` 未提供时，脚本读取模板默认值。
- MVP 阶段只允许 `project_features.规模计数时机` 覆盖 `项目特征!C1`。
- `项目特征!C2:C10` 默认保持模板原值；如果后续页面支持调整，传入值必须等于模板下拉项原文，不能使用内部枚举、简称或等级描述。
- `target_work_days` 来源于任务字段 `target_person_days`。
- `template_path` 和 `output_path` 由后端根据资源配置与任务目录生成。
- `assessor`、`assessment_date` 可保留在 payload 中，但新版模板没有写入位置。

## 5. JSON 到 Excel 映射

### 5.1 项目特征映射

| payload 字段 | Excel 单元格 | 公式/结果列 |
|---|---|---|
| `project_features.规模计数时机` | `项目特征!C1` | `项目特征!D1` |
| `project_features.应用类型` | `项目特征!C2` | `项目特征!D2` |
| `project_features.分布式处理` | `项目特征!C3` | `项目特征!D3` |
| `project_features.性能` | `项目特征!C4` | `项目特征!D4` |
| `project_features.可靠性` | `项目特征!C5` | `项目特征!D5` |
| `project_features.多重站点` | `项目特征!C6` | `项目特征!D6` |
| `project_features.完整性级别` | `项目特征!C7` | `项目特征!D7` |
| `project_features.开发语言` | `项目特征!C8` | `项目特征!D8` |
| `project_features.开发团队背景` | `项目特征!C9` | `项目特征!D9` |

MVP 写入边界：

- `项目特征!C1` 是首版唯一允许覆盖的项目特征单元格。
- `项目特征!C2:C10` 必须保持模板原值。
- 脚本可以读取 `C2:C10` 及其 `D` 列公式结果参与计算，但不得把内部标准值写回 Excel。
- 例如 `分布式处理` 不得写成 `中等`，`开发语言` 不得写成 `3GL`；如果未来允许页面调整，必须写入模板下拉项原文。
- `C10` 为模板默认“开发平台”，公式结果在 `D10`，脚本只读取其调整因子参与中值计算。

### 5.2 明细行映射

| payload 字段 | Excel 列 | 表头 |
|---|---|---|
| `items[].system` | `B` | 子系统 |
| `items[].level1_module` | `C` | 一级模块 |
| `items[].level2_module` | `D` | 二级模块 |
| `items[].level3_module` | `E` | 三级模块 |
| `items[].level4_module` | `F` | 四级模块 |
| `items[].function_description` | `G` | 功能项描述 |
| `items[].count_item_name` | `H` | 功能点计数项名称 |
| `items[].category` | `I` | 类别 |
| `items[].reuse` | `K` | 重用程度 |
| `items[].change_type` | `L` | 修改类型 |
| `items[].remark` | `N` | 备注 |

### 5.3 备注列生成契约

`规模估算!N` 备注列是人工复核和系统上传后的审计依据，不能只照搬 AI 输出的一句笼统说明。

Excel 备注必须采用三段式：

```text
类别原因：{category}，{为什么属于该功能点类型}；复用原因：{reuse}，{为什么是该复用程度}；修改类型原因：{change_type}，{为什么是该修改类型}。
```

示例：

```text
类别原因：EI，用户上传现场环境照片并保存元数据，属于外部输入并维护业务数据；复用原因：中，复用现有查勘照片上传框架，但需新增照片类型和关联规则；修改类型原因：新增，本次新增现场环境照片采集能力。
```

生成规则：

- 若 AI 输出已经包含完整三段式，脚本可规范化后写入 Excel。
- 若 AI 只输出普通 `remark`，脚本必须兜底拼装三段式备注。
- 兜底备注至少要明确包含 `category`、`reuse`、`change_type` 三个取值。
- 兜底备注要结合 `function_description`、`count_item_name` 和原始 `remark` 解释原因，不能只拼接“类别原因：EI；复用原因：中；修改类型原因：新增”。
- 后续可扩展 AI schema，增加 `category_reason`、`reuse_reason`、`change_type_reason` 三个字段；在扩展前，Excel 脚本仍需保证三段式输出。

脚本不得写入：

- `A` 列编号公式。
- `J` 列 UFP 公式。
- `M` 列 US 公式。
- 合计行非输入公式区。
- 结果区公式。

## 6. 明细区、公式列、合计行、结果单元格

### 6.1 当前旧模板结构

| 区域 | 范围 |
|---|---|
| 表头行 | `规模估算!5:5` |
| 旧脚本可靠可写明细行 | `规模估算!6:14` |
| 残留公式行 | `规模估算!15:15` |
| 原始合计行 | `规模估算!16:16` |

当前旧脚本常量：

```text
FIRST_ITEM_ROW = 6
LAST_ITEM_ROW = 14
MAX_ITEMS = 9
ORIGINAL_SUMMARY_ROW = 16
```

这些常量是当前实现现状，不是目标契约。

### 6.2 目标条目数量口径

目标契约：

- 平台设计不设置 29 条硬上限。
- 最终目标是同一个 Excel 内支持超过模板默认明细行数。
- 当 `items.length` 超过模板默认明细行数时，脚本必须动态插行。

动态插行要求：

| 动作 | 要求 |
|---|---|
| 插入明细行 | 在合计行前插入新增行 |
| 复制样式 | 复制模板明细行样式、边框、行高、列宽、对齐方式和换行设置 |
| 复制公式 | 翻译复制 `A/J/M` 公式到新增行 |
| 扩展数据验证 | 扩展 `I/K/L` 列下拉验证到新增行 |
| 保留固定区 | 不改变表头、说明行、非明细区域和基础参数区域 |
| 更新合计行 | 合计行随明细下移 |
| 更新合计公式 | `SUM(J{first}:J{last})`、`SUM(M{first}:M{last})` 覆盖全部明细 |
| 更新引用公式 | `规模估算!C2/C3`、`开发费用估算!C1` 指向新的合计行 |

未完成动态增行改造前，超过 9 条会触发旧脚本限制。这只能写在“当前实现现状/待改造项”，不得作为目标方案，也不得写成“超过 9 条拆多个 Excel”的产品契约。

动态扩展允许改变的结构仅限：

- `规模估算` 明细区行数。
- 合计行行号。
- 合计行相关合并区域行号。
- `I/K/L` 数据验证范围。
- `规模估算!C2/C3` 和 `开发费用估算!C1` 对动态合计行的引用。

动态扩展不允许改变：

- sheet 名称和顺序。
- 固定说明区和表头区。
- `项目特征`、`开发费用估算`、`模板使用说明&基础参数` 的固定结构。
- 非明细区域样式、公式、合并单元格和数据验证。

### 6.3 公式列

| 列 | 含义 | 模板公式口径 |
|---|---|---|
| `A` | 编号 | `=ROW()-5` |
| `J` | UFP | 根据 `I` 列类别和 `规模估算!C1` 方法读取基础参数权重 |
| `M` | US | `J * 重用程度系数 * 修改类型系数` |

### 6.4 动态合计行

设：

```text
R = last_detail_row
S = summary_row = R + 1
```

脚本必须写入或维护：

| 单元格 | 公式 |
|---|---|
| `规模估算!C2` | `=J{S}` |
| `规模估算!C3` | `=M{S}` |
| `规模估算!J{S}` | `=SUM(J6:J{R})` |
| `规模估算!M{S}` | `=SUM(M6:M{R})` |
| `开发费用估算!C1` | `=规模估算!M{S}` |

### 6.5 结果单元格

| 单元格 | 含义 | 公式/来源 |
|---|---|---|
| `规模估算!C2` | 功能点合计 | 引用动态合计行 `J{S}` |
| `规模估算!C3` | 调整后功能点 | 引用动态合计行 `M{S}` |
| `开发费用估算!C1` | 规模估算结果 | 引用 `规模估算!M{S}` |
| `开发费用估算!C3` | 调整后规模 | `=C1*C2` |
| `开发费用估算!C7` | 未调整工作量下限 | `=C3*C4/8` |
| `开发费用估算!C8` | 未调整工作量中值 | `=C3*C5/8` |
| `开发费用估算!C9` | 未调整工作量上限 | `=C3*C6/8` |
| `开发费用估算!C16` | 调整后工作量下限 | `=C7*C10*C11*C12*C13*C14*C15` |
| `开发费用估算!C17` | 调整后工作量中值 | `=C8*C10*C11*C12*C13*C14*C15` |
| `开发费用估算!C18` | 调整后工作量上限 | `=C9*C10*C11*C12*C13*C14*C15` |
| `开发费用估算!C20` | 基准报价下限 | `=C16*C19/21.75` |
| `开发费用估算!C21` | 基准报价中值 | `=C17*C19/21.75` |
| `开发费用估算!C22` | 基准报价上限 | `=C18*C19/21.75` |

脚本当前同步计算 `开发费用估算!C17` 对应的中值口径。若页面展示下限、上限或报价，也必须由脚本同步计算并写入 `FPA生成过程.json`。

## 7. 核心计算边界

脚本必须按以下口径同步计算，不能从 Excel 公式缓存读取：

```text
UFP = category 对应权重
US = UFP * reuse 系数 * change_type 系数
adjusted_fp_total = SUM(US)
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

页面展示边界：

- MVP 页面至少展示中值人天、功能点合计、调整后功能点合计、质量提示。
- 页面结果必须来自脚本计算结果和 `FPA生成过程.json`。
- 如果页面展示下限人天、上限人天、报价，脚本必须同步计算并写入 `FPA生成过程.json`。
- Excel 文件仍作为最终下载产物，保留公式供人工调整参数后重算。

## 8. 允许值与基础参数映射

当前脚本从模板读取允许值和系数。

| 字段 | 读取区域 | 说明 |
|---|---|---|
| `规模计数时机` | `模板使用说明&基础参数!H50:I53` | `估算早期=1.39`、`估算中期=1.21`、`估算晚期=1.1`、`项目交付后及运维阶段=1` |
| `应用类型` | `模板使用说明&基础参数!G10:I16` | 取 `G` 列标签、`I` 列因子 |
| `分布式处理` | `模板使用说明&基础参数!H19:I21` | 非功能特征 |
| `性能` | `模板使用说明&基础参数!H22:I24` | 非功能特征 |
| `可靠性` | `模板使用说明&基础参数!H25:I27` | 非功能特征 |
| `多重站点` | `模板使用说明&基础参数!H28:I30` | 非功能特征 |
| `开发语言` | `模板使用说明&基础参数!H34:I36` | 开发语言因子 |
| `开发团队背景` | `模板使用说明&基础参数!H40:I42` | 团队背景因子 |
| `完整性级别` | `模板使用说明&基础参数!H45:I47` | 完整性因子 |
| `开发平台` | `模板使用说明&基础参数!H56:I57` | 当前脚本读取模板 `项目特征!C10` 对应因子 |
| `重用程度` | `模板使用说明&基础参数!D5:E7` | 明细 US 计算 |
| `修改类型` | `模板使用说明&基础参数!D10:E12` | 明细 US 计算 |
| `预估功能点权重` | `模板使用说明&基础参数!D15:E19` | 由 `规模估算!C1` 决定是否使用 |
| `估算功能点权重` | `模板使用说明&基础参数!D22:E26` | 当前默认使用 |

明细允许值：

| 字段 | 允许值 |
|---|---|
| `category` | `ILF`、`EIF`、`EI`、`EO`、`EQ` |
| `reuse` | `高`、`中`、`低` |
| `change_type` | `新增`、`修改`、`删除` |

## 9. 结果 JSON 输出契约

`FPA生成过程.json` 至少包含：

| 字段 | 说明 |
|---|---|
| `requirement_name` | 后端兜底后的需求名称 |
| `output_path` | 输出 Excel 路径 |
| `template_path` | 使用的模板路径 |
| `item_count` | 功能点条目数 |
| `assessment_context` | 标准化后的上下文 |
| `project_features` | 合并模板默认值后的项目特征 |
| `features` | 与 `project_features` 同值，历史兼容字段 |
| `items` | 标准化后的明细 |
| `estimated` | 脚本计算结果 |
| `target_check` | 目标命中结果；无目标时为 `null` |
| `quality_warnings` | 风险提示数组 |
| `quality_gate` | 质量门禁 |
| `deliverable_valid` | 是否建议作为正式交付候选 |
| `formula_cache_notice` | 公式缓存提醒 |
| `intermediate_artifact_path` | 过程 JSON 路径 |

`estimated` 结构：

| 字段 | 对应模板口径 |
|---|---|
| `ufp_total` | `规模估算!C2` |
| `adjusted_fp_total` | `规模估算!C3` / `开发费用估算!C1` |
| `scale_factor` | `项目特征!D1` / `开发费用估算!C2` |
| `adjusted_size` | `开发费用估算!C3` |
| `adjusted_work_days_middle` | `开发费用估算!C17` |

若需要展示下限、上限或报价，建议扩展：

| 字段 | 对应模板口径 |
|---|---|
| `adjusted_work_days_low` | `开发费用估算!C16` |
| `adjusted_work_days_high` | `开发费用估算!C18` |
| `quote_low` | `开发费用估算!C20` |
| `quote_middle` | `开发费用估算!C21` |
| `quote_high` | `开发费用估算!C22` |

## 10. 质量门禁与下载行为

`quality_warnings` 是风险提示，`quality_gate.failed` 表示强风险/不建议不复核直接交付。

默认行为：

- 业务质量提示不阻断 Excel 生成。
- `quality_gate.failed` 默认不阻断下载。
- 页面应突出展示 failed 状态和 required_action。
- 只有结构错误、模板错误、脚本错误、JSON 校验失败等技术失败才阻断成功产物生成。

技术失败示例：

- payload JSON 非法。
- 必填字段缺失或枚举值非法。
- 模板文件缺失或无法读取。
- 必要 sheet 缺失。
- `excel_mapping.yaml` 缺失、解析失败或与模板不一致。
- 动态增行后合计公式或引用公式无法校验。
- 脚本运行异常。

## 11. 现有脚本可复用逻辑

`fill_fpa_workbook.py` 可以继续复用：

| 逻辑 | 现状 |
|---|---|
| 模板路径解析 | 支持 CLI `--template` 和 payload `template_path` |
| 输出路径解析 | 支持 CLI `--output` 和 payload `output_path` |
| 必要 sheet 校验 | 校验 4 个必要 sheet |
| 模板公式校验 | 校验 `规模估算!C2/C3`、合计行 `J/M`、`开发费用估算!C1` |
| 项目特征默认值读取 | 从 `项目特征!C1:C9` 读取 |
| 项目特征允许值校验 | 从基础参数页读取并校验 |
| 明细标准化 | 校验必填字段和枚举值 |
| 明细写入 | 写入 `B:I`、`K:L`、`N` |
| 公式保留与补齐 | 保留并补齐 `A/J/M` 公式 |
| 中值计算 | 同步计算 `estimated.adjusted_work_days_middle` |
| 目标命中 | 读取 `target_work_days`，由后端从 `target_person_days` 转换 |
| 质量提示 | 生成 `quality_warnings`、`quality_gate`、`deliverable_valid` |
| 公式重算设置 | 设置打开时重算 |
| 过程 JSON | 输出 `FPA生成过程.json` |

## 12. 现有脚本必须改造逻辑

### 12.1 MVP 发布前必须明确的改造

| 改造点 | 原因 |
|---|---|
| 引入 `excel_mapping.yaml` | 当前 sheet、行列、结果单元格和允许值区域硬编码，模板变更风险高 |
| 映射驱动结构校验 | 发现模板位置变化时应明确失败 |
| 将 `FEATURE_CELL_MAP` 外置 | 项目特征单元格属于模板位置契约 |
| 将明细列映射外置 | `B:I/K:L/N` 属于模板位置契约 |
| 将公式列和合计行配置外置 | 公式列、合计公式和联动单元格应由映射描述 |
| 将结果单元格外置 | 页面展示和脚本校验需要明确对应模板位置 |
| 将允许值区域外置 | 模板允许值范围调整时无需改脚本 |
| 支持动态增行 | 目标契约要求同一个 Excel 支持超过模板默认明细行数 |
| 固化目标字段转换 | 后端把 `target_person_days` 映射为 `target_work_days` |
| 项目特征保真 | MVP 只允许覆盖 `项目特征!C1`，其余 `C2:C10` 保持模板原值 |
| 备注三段式 | `规模估算!N` 必须写入“类别原因/复用原因/修改类型原因” |
| 模板保真校验 | 生成后对比模板固定区域，发现非允许差异时失败 |

### 12.2 动态增行未完成时的风险

如果不改造动态增行：

- 超过 9 条可能被旧脚本拒绝。
- 若绕过旧脚本限制直接写入更多行，合计公式可能遗漏新增行。
- 数据验证可能未覆盖新增行。
- `开发费用估算!C1` 可能仍引用旧合计行，导致结果不完整。

因此，超过模板默认明细行数前必须先完成脚本改造，不能只改文档或只放宽数量校验。

## 13. 是否需要 excel_mapping.yaml

结论：需要。`excel_mapping.yaml` 应作为模板位置契约，不承载业务计算规则。

应放入 mapping：

- sheet 名称。
- 项目特征输入单元格。
- 明细起始行、模板默认结束行、合计行定位策略。
- JSON 字段到 Excel 列的映射。
- 公式列位置。
- 合计公式模板和联动单元格。
- 结果单元格。
- 允许值区域。
- 系数和权重读取区域。

不应放入 mapping：

- 功能点拆分规则。
- 质量提示业务判断。
- 目标命中阈值。
- 提示词或页面文案。
- 是否阻断下载的业务策略。

## 14. excel_mapping.yaml 建议结构

```yaml
version: 1

template:
  required_sheets:
    feature: 项目特征
    size: 规模估算
    cost: 开发费用估算
    base: 模板使用说明&基础参数

feature_inputs:
  sheet: 项目特征
  fields:
    规模计数时机: C1
    应用类型: C2
    分布式处理: C3
    性能: C4
    可靠性: C5
    多重站点: C6
    完整性级别: C7
    开发语言: C8
    开发团队背景: C9
  read_only_defaults:
    开发平台: C10

detail_table:
  sheet: 规模估算
  header_row: 5
  first_row: 6
  template_last_row: 14
  residual_formula_row: 15
  original_summary_row: 16
  overflow_policy: insert_rows
  columns:
    system: B
    level1_module: C
    level2_module: D
    level3_module: E
    level4_module: F
    function_description: G
    count_item_name: H
    category: I
    reuse: K
    change_type: L
    remark: N
  formula_columns:
    index: A
    ufp: J
    us: M
  validation_columns:
    category: I
    reuse: K
    change_type: L

summary:
  row: after_last_detail
  merged_ranges:
    - A{summary_row}:I{summary_row}
    - K{summary_row}:L{summary_row}
  formulas:
    ufp_total: J{summary_row}=SUM(J{first_detail_row}:J{last_detail_row})
    us_total: M{summary_row}=SUM(M{first_detail_row}:M{last_detail_row})
  linked_cells:
    规模估算!C2: J{summary_row}
    规模估算!C3: M{summary_row}
    开发费用估算!C1: 规模估算!M{summary_row}

result_cells:
  ufp_total: 规模估算!C2
  adjusted_fp_total: 规模估算!C3
  adjusted_size: 开发费用估算!C3
  unadjusted_work_days_low: 开发费用估算!C7
  unadjusted_work_days_middle: 开发费用估算!C8
  unadjusted_work_days_high: 开发费用估算!C9
  adjusted_work_days_low: 开发费用估算!C16
  adjusted_work_days_middle: 开发费用估算!C17
  adjusted_work_days_high: 开发费用估算!C18
  quote_low: 开发费用估算!C20
  quote_middle: 开发费用估算!C21
  quote_high: 开发费用估算!C22

allowed_values:
  sheet: 模板使用说明&基础参数
  fields:
    规模计数时机:
      label_column: H
      value_column: I
      start_row: 50
      end_row: 53
    应用类型:
      label_column: G
      value_column: I
      start_row: 10
      end_row: 16
    分布式处理:
      label_column: H
      value_column: I
      start_row: 19
      end_row: 21
    性能:
      label_column: H
      value_column: I
      start_row: 22
      end_row: 24
    可靠性:
      label_column: H
      value_column: I
      start_row: 25
      end_row: 27
    多重站点:
      label_column: H
      value_column: I
      start_row: 28
      end_row: 30
    开发语言:
      label_column: H
      value_column: I
      start_row: 34
      end_row: 36
    开发团队背景:
      label_column: H
      value_column: I
      start_row: 40
      end_row: 42
    完整性级别:
      label_column: H
      value_column: I
      start_row: 45
      end_row: 47
    开发平台:
      label_column: H
      value_column: I
      start_row: 56
      end_row: 57

coefficients:
  reuse:
    sheet: 模板使用说明&基础参数
    label_column: D
    value_column: E
    start_row: 5
    end_row: 7
  change_type:
    sheet: 模板使用说明&基础参数
    label_column: D
    value_column: E
    start_row: 10
    end_row: 12
  fp_weights:
    method_cell: 规模估算!C1
    methods:
      预估功能点:
        sheet: 模板使用说明&基础参数
        label_column: D
        value_column: E
        start_row: 15
        end_row: 19
      估算功能点:
        sheet: 模板使用说明&基础参数
        label_column: D
        value_column: E
        start_row: 22
        end_row: 26

calculation_inputs:
  productivity_middle: 开发费用估算!C5
  platform_default: 项目特征!C10
```

## 15. mapping 与脚本边界

| 类型 | 归属 | 说明 |
|---|---|---|
| sheet 名称 | mapping | 模板位置契约 |
| 明细起止行 | mapping | 模板位置契约 |
| 字段列 | mapping | payload 到 Excel 的直接映射 |
| 公式列 | mapping | 标识公式列，脚本只补齐不手写业务值 |
| 合计公式模板 | mapping | 描述公式形态 |
| 联动单元格 | mapping | 描述动态引用关系 |
| 结果单元格 | mapping | 用于校验和对账 |
| 允许值区域 | mapping | 用于读取模板支持值 |
| 输入 payload 校验 | 脚本 | 校验字段、类型、枚举 |
| 写入 Excel | 脚本 | 按 mapping 执行 |
| 动态插行 | 脚本 | 按 mapping 定位模板行、公式列和数据验证 |
| 人天中值计算 | 脚本 | 计算规则，不放入 mapping |
| 目标命中 | 脚本 | 使用 `target_work_days`，由后端从 `target_person_days` 转换 |
| 质量提示 | 脚本 | 业务质量规则，不放入 mapping |

## 16. 模板结构校验

生成前必须校验：

- 模板文件存在且可读。
- mapping 文件存在且 YAML 可解析。
- 必要 sheet 存在。
- sheet 名称和顺序与模板一致。
- `feature_inputs.fields` 单元格存在。
- `detail_table.header_row`、`first_row`、`template_last_row`、`original_summary_row` 存在。
- `detail_table.columns`、`formula_columns` 和 `validation_columns` 指向有效列。
- 合计行公式可渲染。
- `summary.linked_cells` 指向有效单元格。
- `result_cells` 指向有效单元格。
- `allowed_values` 每个区域能读取到非空标签和数值。
- `coefficients` 每个区域能读取到完整系数。
- 动态插行后的公式范围覆盖全部明细行。

生成后必须校验：

- `项目特征!C2:C10` 与模板原值一致，除非后续需求明确开放并使用模板下拉原文。
- `项目特征`、`开发费用估算`、`模板使用说明&基础参数` 的合并单元格与模板一致。
- `规模估算` 除动态明细扩展允许变化外，表头、说明区、公式区和样式不发生非预期变化。
- `规模估算!C2/C3` 指向动态合计行。
- `开发费用估算!C1` 指向动态合计行的调整后功能点。
- `I/K/L` 数据验证覆盖全部明细行，不覆盖合计行。
- 每条明细的 `N` 列备注包含“类别原因：”“复用原因：”“修改类型原因：”。
- 每条备注明确包含对应的 `category`、`reuse`、`change_type` 取值。

失败处理：

| 场景 | 处理 |
|---|---|
| mapping 缺失 | 技术失败，不生成成功状态 |
| YAML 解析失败 | 技术失败，不生成成功状态 |
| 必填配置缺失 | 技术失败，不生成成功状态 |
| 模板结构不一致 | 技术失败，不生成成功状态 |
| 输入值不在允许值中 | 技术失败，不生成成功状态 |
| 动态增行公式校验失败 | 技术失败，不生成成功状态 |
| 模板固定区域被误改 | 技术失败，不生成成功状态 |
| 备注未满足三段式 | 技术失败，不生成成功状态 |

业务质量提示不属于模板结构校验失败。

## 17. 生成流程

标准流程：

1. 后端读取 `AI结构化结果.json`。
2. 后端读取任务配置、模板配置、输出路径和 `target_person_days`。
3. 后端生成 `requirement_name` 兜底值。
4. 后端把 `target_person_days` 映射为 payload 的 `target_work_days`。
5. 后端生成 Excel 脚本输入 payload。
6. 脚本读取 payload。
7. 脚本读取模板和 `excel_mapping.yaml`。
8. 脚本校验模板结构。
9. 脚本合并并校验 `project_features`。
10. 脚本标准化并校验 `items`。
11. 脚本写入允许覆盖的项目特征；MVP 只写 `项目特征!C1`，保持 `C2:C10` 模板原值。
12. 脚本写入功能点明细。
13. 脚本按条目数量删除空白明细行或动态插入新增明细行。
14. 脚本更新合计公式、联动公式和结果引用。
15. 脚本同步计算页面展示所需结果。
16. 脚本生成三段式备注并写入 `规模估算!N`。
17. 脚本执行生成后模板保真校验。
18. 脚本生成 `FPA生成过程.json`。
19. 脚本保存 Excel，并设置打开时重算。

## 18. 当前现状与目标契约差异

| 项目 | 当前旧脚本 | 目标契约/MVP 发布要求 |
|---|---|---|
| AI JSON | 不作为脚本独立边界充分区分 | 明确区分 `AI结构化结果.json`、脚本 payload、`FPA生成过程.json` |
| 目标人天 | 脚本使用 `target_work_days` | 平台统一 `target_person_days`，后端映射到 `target_work_days` |
| requirement_name | 脚本需要 | 用户不必填，后端必须兜底 |
| mapping | 未读取 | 读取 `excel_mapping.yaml` 或等价映射配置 |
| sheet/行列 | 硬编码 | mapping 驱动 |
| 明细上限 | 旧脚本可靠支持 1-9 条 | 目标是同一个 Excel 动态增行，不设置 29 条硬上限 |
| 公式列 | 硬编码 `A/J/M` | mapping 标识 |
| 结果单元格 | 脚本隐含 | mapping 显式记录 |
| 项目特征写入 | 可能把内部值写入 `C2:C10` | MVP 只允许覆盖 `C1`，其余保持模板原值 |
| 明细备注 | 可能直接写 AI 一句话说明 | 统一三段式：类别原因、复用原因、修改类型原因 |
| 模板保真 | 主要验证能生成和能打开 | 必须验证固定区域与模板一致，便于上传系统识别 |
| 页面结果 | 当前仅同步中值等核心字段 | 页面展示字段必须来自脚本和 `FPA生成过程.json` |
| 质量门禁 | 可能被误解为阻断交付 | failed 表示强风险，不默认阻断下载 |

## 19. 验收检查

每次调整模板、mapping 或脚本后，至少用一个历史样例复跑，检查：

- 后端生成的脚本 payload 不要求 AI 输出路径或 `target_work_days`。
- `target_person_days` 已正确映射为 payload 的 `target_work_days`。
- `requirement_name` 在脚本 payload 中有兜底值。
- Excel 文件成功生成。
- sheet 名称和顺序与模板一致。
- `项目特征!C2:C10` 未被内部枚举或简称覆盖。
- `规模估算` 明细行数量、顺序、字段映射正确。
- 超过模板默认明细行数时，新增行样式、公式、数据验证完整。
- 动态扩展只改变允许变化的明细区、合计行、数据验证范围和结果引用。
- 模板固定区域合并单元格、公式、样式和数据验证无非预期变化。
- `规模估算!N` 每条备注均包含“类别原因：”“复用原因：”“修改类型原因：”。
- `规模估算!C2` 引用动态合计行 `J{S}`。
- `规模估算!C3` 引用动态合计行 `M{S}`。
- `开发费用估算!C1` 引用动态合计行 `M{S}`。
- `estimated.ufp_total` 与 Excel 打开重算后的 `规模估算!C2` 一致。
- `estimated.adjusted_fp_total` 与 Excel 打开重算后的 `规模估算!C3` 一致。
- `estimated.adjusted_work_days_middle` 与 Excel 打开重算后的 `开发费用估算!C17` 一致。
- `target_check` 符合目标 ±10%。
- `quality_gate.failed` 只作为强风险提示，不默认阻断下载。
- 输出过程 JSON 中 `deliverable_valid` 明确。

未经过 Excel/WPS 打开保存时，不要求 `.xlsx` 内公式缓存值可被外部系统直接读取；页面和任务摘要以脚本 stdout 和 `FPA生成过程.json` 为准。
