# shared-frontend-model-key-quota 验证报告

## 验证结论

- 结论：通过。
- 分支处理：按用户要求不提交、不 push，当前分支保持现状。
- 范围：管理员公用模型 Key 配置、用户额度管理、公用 Key 领取、FPA 成功后扣减、失败不扣减、前端模型配置页和额度展示。

## 已运行检查

| 检查 | 命令 | 结果 |
|---|---|---|
| 后端 FPA 测试 | `cd backend; uv run python -m unittest tests.test_fpa_mvp -v` | 通过，22 个测试全部 OK |
| 前端构建 | `cd frontend; npm run build` | 通过 |
| Python 编译 | `cd backend; uv run python -m py_compile app\config.py app\db.py app\main.py app\modules\fpa\service.py app\modules\model_keys\service.py app\worker.py` | 通过 |
| 当前 change 校验 | `openspec validate shared-frontend-model-key-quota --strict` | 通过 |
| OpenSpec 全量严格校验 | `openspec validate --all --strict` | 通过，7 项全部通过 |
| 编码检查 | `.\scripts\check-encoding.ps1` | 通过 |
| Comet Build 守卫 | `COMET_SKIP_BUILD=1 node .codex/skills/comet/scripts/comet-guard.mjs shared-frontend-model-key-quota build --apply` | 通过，已进入 verify |

## 说明

- Comet Build 守卫的自动 build 探测只检查仓库根目录的 `package.json`、`pom.xml` 或 `Cargo.toml`；本项目实际前端 build 位于 `frontend/`，后端验证位于 `backend/`，因此已先手动运行对应验证命令，再用 `COMET_SKIP_BUILD=1` 跳过根目录自动推断。
- 自动代码审查子任务调用时，当前工具参数校验多次拒绝调用；本轮用完整后端测试、前端构建、OpenSpec 校验、编码检查和安全断言覆盖关键风险。

## 风险复核

- 公用 API Key 仅在 `POST /api/fpa/tasks/{id}/shared-model-key` 校验通过后返回给浏览器。
- 普通任务详情、调用事件、AI 原始响应、任务文件索引和前端静态代码不保存或返回公用 Key 明文。
- 个人 Key 调用不扣减公用额度。
- 公用 Key 调用只在任务成功生成 Excel 并进入 `completed` 后扣减 1 次。
- 模型调用失败、JSON 校验失败、Excel 生成失败和取消任务不扣减。
- 同一任务重复触发扣减时由 `shared_quota_deducted_at` 防重复。
