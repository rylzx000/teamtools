# FPA Word 输入支持验证报告

## 结论

- 验证结论：通过。
- Comet change：`support-fpa-word-input`。
- 验证模式：`full`。
- 分支处理：按用户本轮明确约束保留当前分支，不提交、不推送、不合并。

## 范围复核

- 已确认 `.docx` 上传由后端输入归一化层处理，并继续保留 `.md` 上传与粘贴文本。
- 已确认 Word 正文、标题、列表和表格文字进入 `input/merged_input.md`。
- 已确认 Word 图片、截图和嵌入对象不解析、不 OCR、不发送给 AI；有有效文字时任务继续并返回图片忽略警告。
- 已确认 `.doc`、PDF、图片、非法扩展、空文件、超大文件、损坏 Word、无法解析 Word 和无有效文字 Word 被拒绝。
- 已确认 AI 请求包脚本继续只读取归一化正文，不直接解析 `.docx`，不读取 Word 二进制、图片或服务器路径。
- 已确认前端上传控件支持 `.md / .docx`，使用 `FormData` 提交，并展示后端解析警告。

## 验证命令

| 检查项 | 命令 | 结果 |
|---|---|---|
| OpenSpec 严格校验 | `openspec validate support-fpa-word-input --strict` | 通过 |
| 后端 FPA unittest | `cd backend; uv run python -m unittest tests.test_fpa_mvp -v` | 通过，37 tests OK |
| 前端构建 | `cd frontend; npm run build` | 通过 |
| 编码检查 | `.\scripts\check-encoding.ps1` | 通过 |
| AI/Excel 脚本边界 | `rg -n "docx|python-docx|Document\(" scripts/fpa/build_ai_request_package.py scripts/fpa/fill_fpa_workbook.py` | 无匹配，符合预期 |
| Comet build guard | `COMET_SKIP_BUILD=1 node .codex/skills/comet/scripts/comet-guard.mjs support-fpa-word-input build --apply` | 通过，已推进到 verify |

## 说明

- `COMET_SKIP_BUILD=1` 仅用于 Comet guard：guard 只在仓库根目录自动探测单一构建命令，本项目实际构建命令位于 `backend/` 和 `frontend/` 子目录，相关命令已在本报告中手动运行并通过。
- 本轮未提交、未推送、未切换分支。
- 未发现 CRITICAL 或 IMPORTANT 级别问题。

