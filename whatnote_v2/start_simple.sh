#!/bin/bash

# WhatNote V2 简化启动脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         WhatNote V2 启动器           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# 清理端口
echo -e "${YELLOW}🧹 清理端口...${NC}"
lsof -ti :8081 | xargs -r kill -9 2>/dev/null
lsof -ti :3000 | xargs -r kill -9 2>/dev/null
sleep 1
echo -e "${GREEN}✓ 端口清理完成${NC}"
echo ""

# 启动后端
echo -e "${BLUE}🚀 启动后端服务...${NC}"
cd backend
source ../venv/bin/activate
python run.py &
BACKEND_PID=$!
cd ..
echo -e "${GREEN}✓ 后端服务已启动 (PID: $BACKEND_PID)${NC}"
echo ""

# 等待后端启动
sleep 3

# 启动前端
echo -e "${BLUE}🚀 启动前端服务...${NC}"
cd frontend
BROWSER=none npm start &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}✓ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"
echo ""

# 等待服务就绪
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 5

# 检查服务状态
if curl -s http://localhost:8081/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 后端服务就绪${NC}"
else
    echo -e "${RED}✗ 后端服务未响应${NC}"
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 前端服务就绪${NC}"
else
    echo -e "${YELLOW}⚠ 前端服务仍在启动中...${NC}"
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 WhatNote V2 启动完成!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${BLUE}📱 前端: http://localhost:3000${NC}"
echo -e "${BLUE}🔧 后端: http://localhost:8081${NC}"
echo -e "${BLUE}📖 文档: http://localhost:8081/docs${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${YELLOW}💡 按 Ctrl+C 停止服务${NC}"
echo ""

# 等待用户中断
trap "echo -e '\n${YELLOW}🛑 停止服务...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

# 保持脚本运行
while true; do
    sleep 1
done
