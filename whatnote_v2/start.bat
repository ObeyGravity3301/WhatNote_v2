@echo off
chcp 65001 >nul
title WhatNote V2 - Windows启动器

echo.
echo ╔══════════════════════════════════════╗
echo ║            WhatNote V2               ║
echo ║        Windows 启动脚本              ║
echo ╚══════════════════════════════════════╝
echo.

echo 🔍 检查运行环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
) else (
    echo ✓ Python 已安装
)

node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Node.js，请先安装 Node.js
    pause
    exit /b 1
) else (
    echo ✓ Node.js 已安装
)

echo.
echo 🚀 启动 WhatNote V2...
python start_universal.py

pause