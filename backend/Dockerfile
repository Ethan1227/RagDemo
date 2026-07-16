# 后端镜像：Python 3.12 + uv（依赖按 uv.lock 冻结安装）
# 构建（在项目根目录）：docker build -f backend/Dockerfile -t legal-rag-backend .
FROM python:3.12-slim

# 安装 uv（从官方静态镜像拷贝二进制）
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /usr/local/bin/

# 国内网络可取消注释使用清华镜像源加速
# ENV UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

# 先装依赖（利用 Docker 层缓存，代码变更不重装依赖）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 拷贝后端代码（配置文件运行时挂载，不打入镜像）
COPY backend ./backend

EXPOSE 8000

# RAGDEMO_CONFIG 由 compose 指定为容器内配置路径
CMD ["uv", "run", "--no-sync", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
