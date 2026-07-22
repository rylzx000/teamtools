## 1. OpenSpec 与契约确认

- [x] 1.1 用户确认本 change 的 proposal、design、tasks 和 delta spec 范围后，再进入实现阶段
- [x] 1.2 确认 `fpa-workflow`、`fpa-interface-ui`、`fpa-ai-contract` 的 delta spec 与需求边界一致
- [x] 1.3 运行 `openspec validate support-fpa-word-input --strict`

## 2. 后端输入归一化

- [x] 2.1 在后端项目依赖中新增 `python-docx`，仅写入项目依赖文件和必要锁文件，不做全局安装
- [x] 2.2 设计并实现 FPA 输入归一化结构，包含 `source_file_name`、`source_file_type`、`normalized_markdown` 或 `normalized_text`、`text_length`、`parse_warnings`
- [x] 2.3 保持 `.md` 上传和粘贴文本现有行为可用，并继续生成 `input/merged_input.md`
- [x] 2.4 实现 `.docx` 正文段落、标题、列表和表格文字提取，保持大致顺序
- [x] 2.5 对 Word 图片、截图和嵌入对象记录解析警告，不解析图片文字，不发送图片给 AI
- [x] 2.6 拒绝 `.doc`、PDF、图片、非法扩展、空文件、超大文件、损坏 Word、无法解析 Word 和无有效文字 Word
- [x] 2.7 确保错误提示面向普通用户可理解，不暴露服务器路径、堆栈或内部临时文件名

## 3. AI 请求包与任务详情

- [x] 3.1 确保 `scripts/fpa/build_ai_request_package.py` 继续只读取归一化后的 `input/merged_input.md`
- [x] 3.2 确保 AI 请求包不包含原始 Word 二进制、图片、嵌入对象或服务器临时路径
- [x] 3.3 保存或返回解析警告，任务详情可展示 Word 图片忽略提示
- [x] 3.4 确认 Excel 脚本输入 payload 和 Excel 生成主流程不因输入来源为 Word 而改变

## 4. 前端提交页

- [x] 4.1 上传控件从仅支持 `.md` 调整为支持 `.md / .docx`
- [x] 4.2 保留拖拽上传能力，更新上传提示为支持 Markdown / Word 文档
- [x] 4.3 前端增加 `.docx` 10MB 和 `.md` 256KB 的快速校验提示，后端仍作为最终校验来源
- [x] 4.4 将提交请求从 URL 编码文本改为 `FormData`，确保 `.docx` 二进制文件由后端解析
- [x] 4.5 在任务详情或提交结果中展示后端返回的 Word 图片忽略警告
- [x] 4.6 不大改现有提交页 UI 和模型调用区

## 5. 测试与验证

- [x] 5.1 验证 `.md` 上传仍然可用
- [x] 5.2 验证 `.docx` 正常提取段落、标题和列表文字
- [x] 5.3 验证 `.docx` 正常提取表格文字
- [x] 5.4 验证 `.docx` 包含图片时任务可继续，并返回图片忽略警告
- [x] 5.5 验证只有图片没有有效文字的 `.docx` 失败
- [x] 5.6 验证 `.doc`、非法扩展名、超大文件和损坏 Word 被拒绝
- [x] 5.7 验证 AI 请求包使用归一化正文，不依赖原始 Word 文件
- [x] 5.8 运行后端相关测试
- [x] 5.9 运行前端构建或相关检查
- [x] 5.10 运行 `.\scripts\check-encoding.ps1`
- [x] 5.11 如任一检查无法运行，在最终汇总中说明原因和可手动执行命令

