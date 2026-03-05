#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$APP_ROOT/models"

echo -e "${BLUE}=== Bilibili 视频转写工具启动脚本 ===${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python3${NC}"
    echo "请先安装 Python 3.8 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓ Python 版本: $PYTHON_VERSION${NC}"

# Check if running in virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    # Try to activate virtual environment if it exists
    if [[ -d "$APP_ROOT/venv" ]]; then
        echo -e "${YELLOW}检测到虚拟环境，正在激活...${NC}"
        source "$APP_ROOT/venv/bin/activate"
    else
        echo -e "${YELLOW}警告: 未检测到虚拟环境${NC}"
        echo "建议创建虚拟环境: python3 -m venv venv"
    fi
fi

# Check required Python packages
echo ""
echo -e "${BLUE}检查 Python 依赖...${NC}"

REQUIRED_PACKAGES=("fastapi" "uvicorn" "pydantic" "httpx" "aiofiles")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [[ ${#MISSING_PACKAGES[@]} -gt 0 ]]; then
    echo -e "${RED}错误: 缺少以下 Python 包:${NC}"
    printf '  - %s\n' "${MISSING_PACKAGES[@]}"
    echo ""
    echo "请安装依赖: pip install -r backend/requirements.txt"
    exit 1
fi

echo -e "${GREEN}✓ Python 依赖检查通过${NC}"

# Check external tools
echo ""
echo -e "${BLUE}检查外部工具...${NC}"

# Check yt-dlp
if ! command -v yt-dlp &> /dev/null; then
    echo -e "${RED}错误: 未找到 yt-dlp${NC}"
    echo "请安装 yt-dlp:"
    echo "  pip install yt-dlp"
    exit 1
fi
echo -e "${GREEN}✓ yt-dlp 已安装${NC}"

# Check ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}错误: 未找到 ffmpeg${NC}"
    echo "请安装 ffmpeg:"
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    exit 1
fi
echo -e "${GREEN}✓ ffmpeg 已安装${NC}"

# Check whisper.cpp binary
WHISPER_BIN="$APP_ROOT/bin/whisper-cli"
if [[ ! -f "$WHISPER_BIN" ]]; then
    # Try to find in PATH
    if command -v whisper-cli &> /dev/null; then
        echo -e "${GREEN}✓ whisper-cli 在 PATH 中找到${NC}"
    else
        echo -e "${YELLOW}警告: 未找到 whisper-cli${NC}"
        echo "请在 $APP_ROOT/bin/ 目录下放置 whisper-cli 二进制文件"
        echo "或确保 whisper-cli 在系统 PATH 中"
    fi
else
    echo -e "${GREEN}✓ whisper-cli 已找到${NC}"
fi

# Check Whisper models
echo ""
echo -e "${BLUE}检查 Whisper 模型...${NC}"

AVAILABLE_MODELS=()
MODEL_NAMES=("ggml-tiny.bin" "ggml-base.bin" "ggml-small.bin" "ggml-medium.bin" "ggml-large-v3.bin")
MODEL_DISPLAY=("tiny (最快，最不准)" "base" "small" "medium (推荐)" "large-v3 (最慢，最准)")
MODEL_URLS=(
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin"
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin"
)

mkdir -p "$MODELS_DIR"

for i in "${!MODEL_NAMES[@]}"; do
    model="${MODEL_NAMES[$i]}"
    if [[ -f "$MODELS_DIR/$model" ]]; then
        AVAILABLE_MODELS+=("$model")
        echo -e "${GREEN}  ✓ $model${NC}"
    fi
done

if [[ ${#AVAILABLE_MODELS[@]} -eq 0 ]]; then
    echo -e "${YELLOW}警告: 未找到任何 Whisper 模型${NC}"
    echo ""
    echo "请选择一个模型下载："
    echo ""

    for i in "${!MODEL_DISPLAY[@]}"; do
        echo "  $((i+1)). ${MODEL_DISPLAY[$i]}"
    done
    echo "  0. 跳过（稍后手动下载）"
    echo ""

    # Check if running in interactive mode
    if [[ -t 0 ]]; then
        read -p "请输入选项编号 [0-5]: " choice

        if [[ "$choice" =~ ^[1-5]$ ]]; then
            idx=$((choice-1))
            model_name="${MODEL_NAMES[$idx]}"
            model_url="${MODEL_URLS[$idx]}"
            model_display="${MODEL_DISPLAY[$idx]}"

            echo ""
            echo -e "${BLUE}正在下载 $model_display...${NC}"

            if command -v curl &> /dev/null; then
                curl -L --progress-bar "$model_url" -o "$MODELS_DIR/$model_name"
            elif command -v wget &> /dev/null; then
                wget --progress=bar:force "$model_url" -O "$MODELS_DIR/$model_name"
            else
                echo -e "${RED}错误: 未找到 curl 或 wget${NC}"
                echo "请手动下载: $model_url"
                echo "保存到: $MODELS_DIR/$model_name"
                exit 1
            fi

            if [[ -f "$MODELS_DIR/$model_name" ]]; then
                echo -e "${GREEN}✓ 模型下载完成: $model_name${NC}"
            else
                echo -e "${RED}错误: 模型下载失败${NC}"
                exit 1
            fi
        elif [[ "$choice" == "0" ]]; then
            echo "跳过模型下载"
            echo "注意: 没有模型将无法进行转写"
        else
            echo -e "${YELLOW}无效选项，跳过模型下载${NC}"
        fi
    else
        echo "非交互式模式，跳过模型下载提示"
        echo "请手动下载模型到 $MODELS_DIR/ 目录"
        echo "下载地址: https://huggingface.co/ggerganov/whisper.cpp/tree/main"
    fi
else
    echo -e "${GREEN}✓ 已找到 ${#AVAILABLE_MODELS[@]} 个模型${NC}"
fi

echo ""
echo -e "${BLUE}启动服务...${NC}"
echo ""

# Start the server
uvicorn backend.app:app --reload --port 8000