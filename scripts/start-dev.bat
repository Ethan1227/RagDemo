@echo off
chcp 65001 >nul
rem 本地开发一键启动：基础设施(Docker) + 后端(uvicorn) + 前端(vite)
cd /d "%~dp0.."

echo [1/3] 启动基础设施（MySQL/Milvus/MinIO）...
docker compose up -d
if errorlevel 1 (
    echo 基础设施启动失败，请检查 Docker Desktop 是否运行。
    pause
    exit /b 1
)

echo [2/3] 启动后端 http://127.0.0.1:8000 ...
start "legal-rag-backend" cmd /k "cd /d %cd% && uv run uvicorn backend.app.main:app --reload --port 8000"

echo [3/3] 启动前端 http://localhost:5173 ...
start "legal-rag-frontend" cmd /k "cd /d %cd%\frontend && npm run dev"

echo.
echo 启动完成：前端 http://localhost:5173  ^|  接口文档 http://127.0.0.1:8000/docs
echo 关闭：运行 scripts\stop-dev.bat（或直接关闭两个命令行窗口）
pause
