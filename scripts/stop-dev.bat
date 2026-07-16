@echo off
chcp 65001 >nul
rem 停止本地开发环境：结束后端/前端进程，基础设施容器保留（数据不丢）
cd /d "%~dp0.."

echo 停止后端(8000)与前端(5173)进程...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1

echo 如需一并停止基础设施容器，请执行：docker compose stop
echo 完成。
pause
