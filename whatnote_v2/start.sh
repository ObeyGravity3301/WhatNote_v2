#!/bin/bash

# WhatNote V2 快速启动脚本 (Linux/Mac)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印横幅
echo -e "${BLUE}"
echo "╔══════════════════════════════════════╗"
echo "║            WhatNote V2               ║"
echo "║     Unix/Linux 快速启动脚本          ║"
echo "╚══════════════════════════════════════╝"
echo -e "${NC}"

# 检查Python
echo -e "${YELLOW}🔍 检查运行环境...${NC}"
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo -e "${RED}❌ 未找到 Python，请先安装 Python 3.8+${NC}"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 未找到 Node.js，请先安装 Node.js${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 环境检查通过${NC}"
echo ""
echo -e "${BLUE}🚀 启动 WhatNote V2...${NC}"
echo ""

# 运行Python启动脚本
$PYTHON_CMD start.py


