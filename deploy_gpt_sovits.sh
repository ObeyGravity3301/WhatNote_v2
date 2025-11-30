#!/bin/bash

# GPT-SoVITS 部署脚本
# 目标：在 Arch Linux 上自动部署 GPT-SoVITS

set -e  # 遇到错误立即退出

echo "=== GPT-SoVITS 自动化部署脚本 ==="
echo "正在检查环境..."

# 1. 检查基本工具
command -v git >/dev/null 2>&1 || { echo "❌ 未找到 git，请先安装：sudo pacman -S git"; exit 1; }
command -v python >/dev/null 2>&1 || { echo "❌ 未找到 python，请先安装"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "❌ 未找到 ffmpeg，请先安装：sudo pacman -S ffmpeg"; exit 1; }

echo "✅ 基本工具检查通过"

# 2. 设置安装目录
INSTALL_DIR="gpt-sovits-deploy"
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️ 目录 $INSTALL_DIR 已存在"
    read -p "是否删除并重新部署？(y/n): " confirm
    if [ "$confirm" == "y" ]; then
        rm -rf "$INSTALL_DIR"
        echo "已删除旧目录"
    else
        echo "部署已取消"
        exit 0
    fi
fi

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# 3. 克隆仓库
echo "📦 正在克隆 GPT-SoVITS 仓库..."
git clone https://github.com/RVC-Boss/GPT-SoVITS.git .

# 4. 创建虚拟环境
echo "🐍 正在创建 Python 虚拟环境..."
python -m venv venv
source venv/bin/activate

# 5. 安装依赖
echo "📥 正在安装依赖 (这可能需要一段时间)..."
# 升级 pip
pip install --upgrade pip

# 安装 PyTorch (Arch Linux 通常推荐系统包，但在 venv 中我们需要 pip 包)
# 根据 CUDA 版本选择，这里假设有 CUDA，如果没有会自动回退到 CPU 版本或需手动指定
pip install torch torchvision torchaudio

# 安装项目依赖
pip install -r requirements.txt

echo "✅ 依赖安装完成"

echo "=== 部署阶段一完成 ==="
echo "接下来需要下载预训练模型。"
echo "请手动下载以下模型并放入 GPT_SoVITS/pretrained_models 目录："
echo "1. GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt"
echo "2. GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2G488k.pth"
echo "3. GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large/*"
echo ""
echo "或者您可以运行 python tools/download_models.py (如果项目提供了下载脚本)"


