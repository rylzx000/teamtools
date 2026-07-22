## Why

当前 FPA 提交评估只支持粘贴文本或上传 `.md` 文件，许多需求材料实际以 Word `.docx` 流转，用户需要先手工转 Markdown 才能提交，增加了操作成本和格式丢失风险。

本 change 让后端在任务创建阶段把 `.md` 和 `.docx` 统一归一化为需求正文，继续复用既有 AI 请求包、结构化校验和 Excel 生成链路，避免让 AI 直接处理 Word 二进制文件。

`Markdown`、`Word`、`AI`、`Excel`、`API`、`.md`、`.docx` 保留英文，是文件格式、办公软件名称和既有技术/接口专有名词。

## What Changes

- FPA 提交输入从“粘贴文本或单个 `.md` 文件”扩展为“粘贴文本、单个 `.md` 文件或单个 `.docx` 文件”。
- 后端新增输入归一化边界：`.md` 直接按文本读取，`.docx` 提取正文段落、标题、列表和表格文字后生成统一 Markdown/文本内容。
- `.docx` 图片、截图和嵌入对象首版不解析、不 OCR、不发送给 AI；存在此类内容时记录解析警告并向用户提示已忽略图片内容。
- 后续 AI 请求包生成只读取归一化后的正文输入，不在提示词脚本中直接解析 Word。
- 后端只允许 `.md` / `.docx`，拒绝 `.doc`、PDF、图片和其他非法扩展；新增 `.docx` 大小上限建议为 10MB。
- 前端提交页上传控件支持 `.md / .docx`，保留拖拽上传能力，并展示 Markdown / Word 文档支持提示。
- 任务详情或提交结果展示后端返回的 Word 解析警告，尤其是图片内容被忽略的提示。
- 不改变 AI 输出契约、FPA Excel 脚本 payload、Excel 生成模板和结果下载主流程。

## Capabilities

### New Capabilities

- 无。本次是既有 FPA 提交与评估能力的输入格式扩展，不新增同义 capability。

### Modified Capabilities

- `fpa-workflow`：修改 FPA 任务输入、文件校验、输入归一化、Word 图片忽略告警和任务主链路前置处理要求。
- `fpa-interface-ui`：修改提交页上传控件、格式提示、前端校验和任务详情解析警告展示要求。
- `fpa-ai-contract`：明确 AI 请求包只消费归一化正文，`.docx` 解析不进入提示词脚本，AI 不接收 Word 二进制、图片或嵌入对象。

## Impact

- 影响后端接口与任务创建链路：`backend/app/main.py` 的上传解析、`backend/app/modules/fpa/service.py` 的任务输入保存、归一化元数据和任务详情返回。
- 影响后端依赖：建议在项目后端依赖文件中新增 `python-docx`，不做全局安装，不引入 Windows COM、LibreOffice 或外部转换服务。
- 影响前端提交页：`frontend/src/App.tsx` 的文件选择、拖拽校验、大小限制提示和解析警告展示；样式尽量复用现有上传控件。
- 影响 AI 请求包生成边界：`scripts/fpa/build_ai_request_package.py` 继续只读取 `input/merged_input.md`，必要时只读取归一化元数据摘要，不解析原始 Word 文件。
- 影响测试：补充 `.md` 保持可用、`.docx` 段落/表格提取、图片忽略警告、纯图片 Word 失败、`.doc`/非法扩展/超大/损坏 Word 拒绝、AI 请求包使用归一化正文等用例。
- 非目标：不支持 `.doc`、PDF、图片 OCR、多模态图片理解、页眉页脚强解析、多个文件上传、Excel 生成主流程调整或 AI 直接处理二进制文件。
