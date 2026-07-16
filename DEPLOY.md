# 部署指南

本项目提供两种启动方式：**本地开发模式**（日常开发调试）与 **Docker 一键部署**（演示/生产）。

## 前置条件

| 依赖 | 版本 | 说明 |
|------|------|------|
| Docker Desktop | 20+ (含 compose v2) | 基础设施与容器化部署 |
| uv | 0.11+ | 仅本地开发模式需要 |
| Node.js / npm | 20+ / 10+ | 仅本地开发模式需要 |
| DashScope API Key | - | [阿里云百炼](https://bailian.console.aliyun.com/) 开通，需可用 qwen-max、text-embedding-v3、gte-rerank-v2 |

## 端口一览

| 服务 | 端口 | 模式 |
|------|------|------|
| 前端(vite dev) | 5173 | 本地开发 |
| 前端(nginx) | 8080 | Docker 部署 |
| 后端 FastAPI | 8000 | 两种模式 |
| MySQL | 3307→3306 | 基础设施 |
| Milvus | 19530 / 9091 | 基础设施 |
| 应用 MinIO | 9200 / 9201(控制台) | 基础设施 |

---

## 方式一：本地开发模式

```bash
# 1. 配置（首次）：复制模板并填入 DashScope api_key
cp backend/config/config.example.yaml backend/config/config.yaml

# 2. 安装依赖（首次）
uv sync
cd frontend && npm install && cd ..

# 3. 一键启动（Windows）
scripts\start-dev.bat
```

或手动分步启动：

```bash
docker compose up -d                                          # 基础设施
uv run uvicorn backend.app.main:app --reload --port 8000     # 后端
cd frontend && npm run dev                                    # 前端
```

访问：前端 <http://localhost:5173>，接口文档 <http://127.0.0.1:8000/docs>。
停止：`scripts\stop-dev.bat`（容器保留数据，如需停容器执行 `docker compose stop`）。

---

## 方式二：Docker 一键部署（app profile）

后端/前端以容器运行，前端由 nginx 托管并同源代理 `/api`（含 SSE 流式支持）。

```bash
# 1. 配置（首次）：容器内通过服务名互联，使用专用配置模板
cp backend/config/config.docker.example.yaml backend/config/config.docker.yaml
# 编辑 config.docker.yaml，填入 dashscope.api_key

# 2. 构建并启动全部服务（基础设施 + 后端 + 前端）
docker compose --profile app up -d --build

# 3. 验证
docker compose --profile app ps          # 各容器应为 healthy / running
curl http://localhost:8000/health        # {"status":"ok",...}
```

访问：<http://localhost:8080>

常用运维命令：

```bash
docker compose --profile app logs -f backend   # 后端日志（也写入 ./logs/app.log）
docker compose --profile app restart backend   # 改配置后重启后端
docker compose --profile app down              # 停止应用+基础设施（数据卷保留）
docker compose up -d                           # 仅启动基础设施（回到开发模式）
```

> 国内网络构建慢时，取消 `backend/Dockerfile` 与 `frontend/Dockerfile` 中镜像源注释（清华 PyPI / npmmirror）。

---

## 配置文件说明

| 文件 | 用途 | 是否入库 |
|------|------|----------|
| `backend/config/config.example.yaml` | 本地开发配置模板 | ✅ |
| `backend/config/config.yaml` | 本地实际配置（含密钥） | ❌ gitignore |
| `backend/config/config.docker.example.yaml` | 容器部署配置模板 | ✅ |
| `backend/config/config.docker.yaml` | 容器实际配置（含密钥） | ❌ gitignore |

配置查找顺序：环境变量 `RAGDEMO_CONFIG` 指定路径 > `config.yaml` > `config.example.yaml`。
容器部署时 compose 已设置 `RAGDEMO_CONFIG=/app/backend/config/config.docker.yaml`。

## 数据与持久化

- MySQL / Milvus / MinIO 数据均落在 `./volumes/`（bind mount），`docker compose down` 不丢数据
- 后端日志：`./logs/app.log`（按天轮转，保留 14 天），容器模式已挂载同一目录
- 上传原件存 MinIO 桶 `legal-rag`，控制台 <http://localhost:9201>（minioadmin/minioadmin）

## 故障排查

| 现象 | 处理 |
|------|------|
| 后端启动即退出，日志提示数据库失败 | 先 `docker compose up -d` 并等待 mysql healthy |
| 问答返回"回答生成失败" | 检查 config 中 dashscope.api_key；日志 `./logs/app.log` 有具体错误 |
| rerank 告警 AccessDenied | 确认账号已开通 gte-rerank-v2 模型 |
| 端口冲突 | 3307/19530/9200/8000/8080 被占用时，修改 docker-compose.yml 对应映射 |
