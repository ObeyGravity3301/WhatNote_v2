#!/bin/bash
set -e

echo "=== GPT-SoVITS 自动部署脚本 (Arch Linux / RTX 4050) ==="
TARGET_DIR="../GPT-SoVITS"

# 1. 检查必要工具
echo "🔍 检查环境工具..."
missing_tools=()
for cmd in git python ffmpeg wget; do
    if ! command -v $cmd &> /dev/null; then
        missing_tools+=($cmd)
    fi
done

if [ ${#missing_tools[@]} -ne 0 ]; then
    echo "❌ 缺少以下工具，请先通过 'sudo pacman -S ${missing_tools[*]}' 安装："
    echo "   ${missing_tools[*]}"
    exit 1
fi
echo "✅ 环境工具检查通过"

# 2. 克隆仓库
if [ -d "$TARGET_DIR" ]; then
    echo "⚠️  目录 $TARGET_DIR 已存在"
else
    echo "📦 正在克隆 GPT-SoVITS..."
    git clone https://github.com/RVC-Boss/GPT-SoVITS.git "$TARGET_DIR"
fi

cd "$TARGET_DIR"

# 3. 虚拟环境
if [ ! -d "venv" ]; then
    echo "🐍 创建虚拟环境..."
    python -m venv venv
fi

echo "🔌 激活虚拟环境..."
source venv/bin/activate

# 4. 安装依赖
echo "📦 安装/更新依赖..."
pip install --upgrade pip

# 自动修复：Arch Linux GCC 15 编译 opencc 失败的问题
# 使用纯 Python 实现版本替代 C++ 版本
echo "🔧 修正 opencc 依赖 (使用 pure-python 版本以修复编译错误)..."
pip install opencc-python-reimplemented
if [ -f requirements.txt ]; then
    sed -i 's/^opencc$/opencc-python-reimplemented/' requirements.txt
    # 有些 requirements 可能写着 opencc==x.x.x
    sed -i 's/^opencc[=>].*/opencc-python-reimplemented/' requirements.txt
fi

# 自动修复：尝试处理 mecab 问题 (韩语支持)
# 如果没有 mecab-config，python-mecab-ko 会编译失败
if ! command -v mecab-config &> /dev/null; then
    echo "⚠️  未检测到 mecab-config，python_mecab_ko 可能安装失败。"
    echo "   如果您需要韩语TTS，请先执行: sudo pacman -S mecab"
    echo "   这里我们将尝试从 requirements 中暂时移除它以确保主程序安装..."
    sed -i '/python-mecab-ko/d' requirements.txt
    sed -i '/python_mecab_ko/d' requirements.txt
fi

# 检查 torch 是否已安装
if ! python -c "import torch; print(torch.__version__)" &> /dev/null; then
    echo "   安装 PyTorch (尝试官方源，通常包含 CUDA 支持)..."
    # Python 3.13 较新，特定 index 可能缺失包，改用官方源
    pip install torch torchvision torchaudio
else
    echo "   PyTorch 已安装"
fi

echo "   安装项目依赖..."
pip install -r requirements.txt
pip install huggingface_hub modelscope

# 5. 下载模型
echo "⬇️  准备下载预训练模型..."
cat > download_models_script.py << 'EOF'
import os
from huggingface_hub import snapshot_download
from modelscope import snapshot_download as ms_download

# 确保目录存在
base_dir = "GPT_SoVITS/pretrained_models"
os.makedirs(base_dir, exist_ok=True)

print("正在下载预训练模型 (s1bert, s2G)...")
try:
    # 尝试从 HuggingFace 下载
    snapshot_download(repo_id="lj1995/GPT-SoVITS", local_dir=base_dir)
except Exception as e:
    print(f"HuggingFace 下载失败: {e}，尝试 ModelScope...")
    try:
        # 尝试从 ModelScope 下载 (国内镜像)
        ms_download("bubbliiiing/GPT-SoVITS-Pretrained-Models", local_dir=base_dir)
    except Exception as e2:
        print(f"ModelScope 下载也失败: {e2}")

print("正在下载中文 RoBERTa 模型...")
roberta_dir = os.path.join(base_dir, "chinese-roberta-wwm-ext-large")
os.makedirs(roberta_dir, exist_ok=True)
try:
    snapshot_download(repo_id="hfl/chinese-roberta-wwm-ext-large", local_dir=roberta_dir)
except Exception as e:
    print(f"RoBERTa 下载失败: {e}")

print("✅ 模型下载尝试完成，请检查 GPT_SoVITS/pretrained_models 目录")
EOF

python download_models_script.py
rm download_models_script.py

echo "=== 部署完成 ==="
echo "🚀 启动方式："
echo "cd $TARGET_DIR"
echo "source venv/bin/activate"
echo "python api.py"
