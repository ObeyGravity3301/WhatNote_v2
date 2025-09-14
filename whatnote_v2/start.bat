@echo off
chcp 65001 >nul
title WhatNote V2 启动器

echo.
echo ╔══════════════════════════════════════╗
echo ║            WhatNote V2               ║
echo ║      Windows 快速启动脚本            ║
echo ╚══════════════════════════════════════╝
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 检查Node.js是否安装
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Node.js，请先安装 Node.js
    pause
    exit /b 1
)

echo ✓ 环境检查通过
echo.
echo 🚀 启动 WhatNote V2...
echo.

REM 运行Python启动脚本
python start.py

pause


