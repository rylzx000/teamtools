# fpa-excel-output Specification

## Purpose
定义 FPA Excel 生成链路中的三类 JSON 边界、脚本 payload、模板保真、功能点计算、目标命中、质量提示和结果展示口径。

## Source Documents

- `docs/modules/fpa/04-FPA计算规则.md`
- `docs/modules/fpa/06-资源包与生成契约设计.md`
- `docs/modules/fpa/08-Excel映射与脚本生成设计.md`
- `scripts/fpa/fill_fpa_workbook.py`
- `scripts/fpa/validate_ai_result.py`
- `data/modules/fpa/profile/mapping/excel_mapping.yaml`
- `data/modules/fpa/examples/excel/`
## Requirements
### Requirement: 三类 JSON 边界

系统 MUST 区分 `AI结构化结果.json`、Excel 脚本输入 payload 和 `FPA生成过程.json`，不得要求 AI 直接输出模板路径、输出路径、目标命中、人天结果或 Excel 单元格信息。

#### Scenario: 后端生成脚本 payload
- **WHEN** AI 结构化结果通过校验
- **THEN** 后端从冻结功能点清单映射生成脚本字段 `items`，并合并任务配置、模板配置、输出路径、目标人天、`规模计数时机` 和 `完整性级别` 生成一次性脚本 payload
- **AND** 将平台字段 `target_person_days` 映射为脚本 payload 的 `target_work_days`
- **AND** 脚本 payload 不作为普通用户可见或可下载产物
- **AND** `items` 只是冻结功能点清单进入脚本的字段名转换，不得代表重新生成、重新排序或重新判断功能点

#### Scenario: 项目特征默认值
- **WHEN** 后端生成 Excel 脚本 payload
- **THEN** `规模计数时机` 默认使用 `估算中期`，对应系数 `1.21`
- **AND** `完整性级别` 默认使用 `完整性级别为A/B同时为达成完整性级别要求采取了特殊的设计及实现方式`，对应系数 `1.10`
- **AND** 其他项目特征使用模板默认值，除非后续 change 明确开放给用户选择

#### Scenario: 脚本生成过程 JSON
- **WHEN** Excel 脚本运行成功
- **THEN** 脚本输出 `FPA生成过程.json`
- **AND** 过程 JSON 包含标准化明细、`stable_id`、计算结果、目标命中、结构提醒、校验门禁和脱敏输出摘要
- **AND** 过程 JSON 作为后台排查产物，不作为普通用户下载文件

#### Scenario: 脚本 payload 调试保留
- **WHEN** 平台为管理员排查保留脚本 payload
- **THEN** 该文件必须标记为 admin-only/internal debug/runtime temp
- **AND** 普通用户不得通过结果文件列表或下载接口获取
- **AND** 该文件不得作为下次评估输入或正式审计产物

#### Scenario: 脚本 payload 运行时保留
- **WHEN** 平台在 MVP 阶段为脚本执行保留 payload
- **THEN** 脚本 payload 只能作为 `runtime` 内部文件存在
- **AND** 脚本执行完成后不得登记为任务正式产物或普通用户文件
- **AND** 后续可优化为内存传递或执行后删除

### Requirement: Excel 模板保真

系统 SHALL 以既有 `fpa_template.xlsx` 为母版生成 Excel，保留模板工作表、公式、样式、参数区、数据验证、列宽、行高和固定结构。

#### Scenario: 生成正式 Excel
- **WHEN** 脚本生成 `FPA工作量评估.xlsx`
- **THEN** 输出文件必须基于模板复制和填充
- **AND** 不得从零创建简化 workbook 或删除、重命名模板 sheet

#### Scenario: 写入范围受限
- **WHEN** 脚本填充明细和项目特征
- **THEN** 只允许写入明确约定的输入单元格和明细字段列
- **AND** 未被允许写入的公式区、参数区和结果区必须保持模板逻辑

### Requirement: 功能点明细与备注规范

系统 MUST 将冻结功能点清单写入模板约定列，并保证备注具备可审计的类型、复用和修改依据。

#### Scenario: 明细写入
- **WHEN** payload 包含一组 `items`
- **THEN** 脚本将系统、模块层级、功能描述、计数项、类别、复用程度、修改类型和备注写入对应明细列
- **AND** `items` 的数量、顺序、名称、类型和模块必须与冻结功能点清单一致
- **AND** 公式列只允许保留、复制或平移公式，不写业务值

#### Scenario: 系统场景字典映射
- **WHEN** 冻结清单条目命中系统场景字典
- **THEN** Excel 一级模块、二级模块和功能点计数项名称必须使用系统字典映射值
- **AND** 脚本不得按需求文档章节或临时判断重新归类

#### Scenario: 备注兜底
- **WHEN** AI 输出备注缺少三段式依据
- **THEN** 脚本根据 `category`、`reuse`、`change_type`、功能描述和原始备注生成兜底三段式备注
- **AND** 备注必须包含类型依据、复用依据和修改类型依据，或包含兼容旧口径的“类别原因”“复用原因”和“修改类型原因”

### Requirement: 动态明细行与公式引用

系统 SHALL 支持超过模板默认明细行数的条目在同一个 Excel 文件内生成，并在插行时维护样式、公式、数据验证、合计行和引用公式。

#### Scenario: 条目超过默认行数
- **WHEN** `items.length` 超过模板默认明细行数量
- **THEN** 脚本在合计行前插入新增明细行并复制样式、公式和数据验证
- **AND** 合计公式和相关引用覆盖全部明细

#### Scenario: 动态扩展失败
- **WHEN** 插行、公式平移、数据验证扩展或模板结构校验失败
- **THEN** 任务按技术失败处理
- **AND** 不得生成 `completed` 状态下的可下载正式 Excel

### Requirement: 计算结果与页面展示

系统 MUST 由脚本按模板公式口径同步计算页面需要展示的关键结果，并写入 `FPA生成过程.json`；页面不得读取 `.xlsx` 公式缓存。

#### Scenario: 计算中值人天
- **WHEN** 脚本处理功能点明细
- **THEN** 输出 UFP 合计、调整后功能点合计、规模计数因子、调整后规模和调整后工作量中值
- **AND** Excel 文件保留模板公式，供用户打开后由办公软件重算

#### Scenario: 目标命中
- **WHEN** payload 包含 `target_work_days`
- **THEN** 脚本按结果中值是否落在目标 ±10% 范围内生成 `target_check`
- **AND** 页面展示的目标命中来自过程 JSON 或后端保存的脚本结果

#### Scenario: 结构质量提示
- **WHEN** 备注缺失、目标偏差、模板结构异常、允许值异常、公式保护异常或无资料模式存在复核风险
- **THEN** 脚本或后端生成结构质量提示
- **AND** 质量提示用于风险提醒，不默认阻止已成功生成的 Excel 下载

#### Scenario: 普通用户不查看过程 JSON
- **WHEN** 普通用户查看已完成任务
- **THEN** 页面展示来自后端汇总的结果摘要和 `AI评估.md`
- **AND** 不直接展示或下载完整 `FPA生成过程.json`
- **AND** 不得返回服务器绝对路径、payload 路径、内部文件角色、原始模型错误、环境变量或模型 Key

#### Scenario: 管理员查看完整过程信息
- **WHEN** 管理员排查任务生成结果
- **THEN** 后端可以展示完整过程 JSON 或内部路径摘要
- **AND** 展示内容仍不得包含模型 Key、环境变量或其他敏感凭据

#### Scenario: 禁止脚本业务补点
- **WHEN** 脚本生成 Excel
- **THEN** 脚本不得根据核心系统、需求等级、关键词、目标人天、条目数量、类型分布或复用比例新增、删除、拆分、合并或改变功能点
- **AND** 功能点拆分是否充分由 AI 结构化结果中的事实、路由和拆分/合并决策负责

### Requirement: 资源和依赖声明

系统 SHALL 通过模块资源目录维护模板、映射、schema、提示词和样例，并在后端依赖中声明 Excel 生成所需库。

#### Scenario: 运行 Excel 脚本
- **WHEN** 后端调用 `scripts/fpa/fill_fpa_workbook.py`
- **THEN** 运行环境必须具备 `openpyxl>=3.1`
- **AND** 不依赖开发机全局 Python 的隐式安装状态

#### Scenario: 样例验收
- **WHEN** 验证 FPA Excel 生成链路
- **THEN** 可以使用 `data/modules/fpa/examples/excel/` 下的样例 payload、过程 JSON 和 Excel 输出作为验收参考
- **AND** 样例只作为验证资源，不作为前端页面内容

### Requirement: 结构校验门禁

系统 SHALL 使用 `quality_warnings`、`quality_gate` 和 `deliverable_valid` 表达 Excel 生成后的结构校验结论。

#### Scenario: 结构校验通过
- **WHEN** 模板结构、允许值、备注、公式保护和目标检查均无阻断问题
- **THEN** `quality_gate.status` 为 `passed`
- **AND** `deliverable_valid` 为 `true`

#### Scenario: 需要人工复核
- **WHEN** 存在备注不完整、目标偏离或其他不阻断交付的结构提醒
- **THEN** `quality_gate.status` 为 `review_required`
- **AND** `deliverable_valid` 仍可为 `true`
- **AND** 页面摘要和 `AI评估.md` 必须展示对应提醒

#### Scenario: 结构校验失败
- **WHEN** 存在模板结构异常、允许值非法、公式保护异常或其他阻断交付的问题
- **THEN** `quality_gate.status` 为 `failed`
- **AND** `deliverable_valid` 为 `false`
- **AND** 任务不得把该 Excel 作为普通用户可下载的成功交付件

## Known Limits / 待确认点

- 旧外部 FPA 脚本的固定行数限制只属于历史实现现状，不得作为 TeamTools 目标契约。
- 下限人天、上限人天和报价若要上页面，需要先补充脚本计算和过程 JSON 字段。
