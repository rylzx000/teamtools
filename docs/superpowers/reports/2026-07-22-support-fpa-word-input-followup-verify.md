# FPA Word 输入支持收尾修复验证报告

## 结论

- 验证结论：通过。
- Comet change：`support-fpa-word-input`。
- 本轮范围：仅修复上传框样式重叠、非法文件选择旧状态残留、Word 段落/表格顺序提取 3 个问题。
- 分支处理：按用户要求保留当前分支，不提交、不推送、不合并。

## 修复复核

- 上传框内部改为稳定 flex 布局：`MD/DOCX` 徽标固定宽高，文案区两行展示并允许小屏换行，`移除` 按钮不挤压主提示。
- `readFile` 遇到 `.doc`、非法扩展、超大 `.md` 或超大 `.docx` 时会调用 `clearFile()`，同步清空 `selectedFile`、`fileName`、`fileSize`、`fileText` 并重置文件 input key。
- `.docx` 归一化改为按 Word body 顺序遍历段落和表格，保留图片忽略、大小限制、空文本校验和损坏 Word 错误处理。
- 新增“段落 A -> 表格 -> 段落 B”的回归测试，验证表格保留在 A 与 B 之间。

## 验证命令

| 检查项 | 命令 | 结果 |
|---|---|---|
| OpenSpec 严格校验 | `openspec validate support-fpa-word-input --strict` | 通过 |
| 后端 FPA unittest | `cd backend; .\.venv\Scripts\python.exe -m unittest tests.test_fpa_mvp -v` | 通过，38 tests OK |
| 前端 TypeScript | `pnpm --dir frontend exec tsc --noEmit` | 通过 |
| 前端构建 | `pnpm --dir frontend build` | 通过 |
| 编码检查 | `.\scripts\check-encoding.ps1` | 通过 |
| Comet build guard | `COMET_SKIP_BUILD=1 node .codex/skills/comet/scripts/comet-guard.mjs support-fpa-word-input build --apply` | 通过，已重新推进到 verify |

## 说明

- `COMET_SKIP_BUILD=1` 仅用于 Comet guard：guard 只在仓库根目录自动探测单一构建命令，本项目实际构建和测试命令位于 `backend/` 与 `frontend/` 子目录，已按本报告命令手动运行并通过。
- 本轮未提交、未推送、未新建 change。
- 当前实现仍满足 `.docx` 上传、`.md` 上传和粘贴文本共存；不支持 `.doc`、PDF、图片和 OCR；AI 请求包仍只消费归一化正文。