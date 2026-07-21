# TeamTools

内网工具平台的技术底座。

当前阶段已具备 FPA 模块 MVP，可用于内网 Docker 单机部署验证。

## 当前范围

- 前端：React + TypeScript + Vite
- 后端：FastAPI
- 数据库：SQLite
- 模型调用：用户浏览器直连外部模型，后端不保存 API Key
- 部署方式：Docker Compose 单机部署、无 Nginx

## 目录

- `frontend/`：前端工程
- `backend/`：后端工程
- `docs/architecture/`：平台架构文档
- `docs/deployment/`：部署文档
- `docs/modules/`：业务模块文档
- `docs/ui/`：页面设计文档
- `scripts/`：本地启动和初始化脚本
- `data/`：运行数据和服务器配置，默认不进入版本管理

## 运行数据目录

运行数据默认放在工程根目录下：

```text
D:\project\teamtools\data
```

服务器部署时保持同样结构，例如：

```text
/data/teamtools/data
```

`TEAMTOOLS_DATA_DIR` 默认等于 `项目根目录/data`。如确有需要，也可以通过环境变量覆盖。

## 本阶段目标

- `http://127.0.0.1:8000` 可访问
- `GET /api/health` 可返回健康状态
- 前端页面可被后端托管
- SQLite 可初始化

## Docker 部署

复制环境变量样例：

```bash
cp .env.example .env
```

启动：

```bash
mkdir -p data logs
docker compose build
docker compose up -d
```

创建管理员账号：

```bash
docker compose exec teamtools python scripts/create-user.py --username admin --display-name 管理员 --role admin
```

更多步骤见 `docs/deployment/02-服务器部署.md`。

## 编码检查

项目文本文件统一使用 UTF-8。提交或交付前运行：

```powershell
.\scripts\check-encoding.ps1
```
