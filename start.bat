@echo off
chcp 65001 >nul 2>&1
echo ==============================================
echo   区域电商智能数据分析助手 - 一键启动
echo ==============================================
echo.

:: 切换到项目目录
cd /d "%~dp0"

:: 检查Node.js
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] 未检测到Node.js，请先安装Node.js（https://nodejs.org）
    pause
    exit /b 1
)

:: 检查前端依赖
if not exist "node_modules" (
    echo [1/4] 正在安装前端依赖...
    call npm install
    if %ERRORLEVEL% neq 0 (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
    echo 前端依赖安装完成！
) else (
    echo [1/4] 前端依赖已存在，跳过安装
)

:: 检查Python依赖
echo [2/4] 正在检查Python依赖...
pip install flask flask-cors pymysql pandas langchain-community langchain-core langchain-text-splitters sentence-transformers chromadb pydantic 2>nul
echo Python依赖检查完成！

:: 启动Ollama服务
echo [3/4] 正在启动Ollama服务...
start "Ollama Service" "C:\Users\86175\AppData\Local\Programs\Ollama\ollama.exe" serve 2>nul
timeout /t 5 /nobreak >nul
echo Ollama服务已启动！

:: 启动后端服务
echo [4/4] 正在启动后端服务...
start "Backend Server" cmd /k "cd /d "%~dp0backend" && python server.py"
timeout /t 3 /nobreak >nul

:: 启动前端开发服务器
echo 正在启动前端开发服务器...
echo.
echo ==============================================
echo   启动完成！
echo   前端地址: http://localhost:5173
echo   后端API:  http://localhost:5000
echo ==============================================
echo.
start http://localhost:5173

call npm run dev

pause
