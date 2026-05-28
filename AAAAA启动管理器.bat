@echo off
cd /d "%~dp0"
python launcher.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [错误] 启动失败，请确认已安装 Python 并配置了环境变量
    pause
)
