# FPA AI 请求包资源使用说明

本目录保存 FPA 模块生成 AI 请求包所需的受控资源。

## 文件职责

- `skill/prompt_template.md`：提示词模板，包含系统角色、输入材料、目标人天参考口径和 JSON 输出契约。
- `schema/result.schema.json`：AI 结构化结果 JSON Schema，约束顶层结构、`items` 必填字段和枚举值。
- `profile.yaml`：默认模型参数、请求格式和长度保护配置，不保存任何模型密钥。

## 生成请求包

```powershell
python scripts/fpa/build_ai_request_package.py `
  --task-dir data/modules/fpa/examples/demo-task `
  --data-dir data `
  --profile-dir data/modules/fpa/profile `
  --systems-config data/config/modules/fpa/systems.yaml `
  --system-code onlineclaim `
  --output-dir data/modules/fpa/examples/expected/ai
```

输出：

- `AI请求包.json`
- `AI请求摘要.json`

前端实际调用模型时，只能从 `messages` 或 `plain_prompt` 中二选一发送；不要把 `metadata`、摘要文件、任务路径或排查字段发送给模型。

## 校验 AI 结果

```powershell
python scripts/fpa/validate_ai_result.py `
  --result-file data/modules/fpa/examples/expected/AI结构化结果.sample.json `
  --schema-file data/modules/fpa/profile/schema/result.schema.json
```
