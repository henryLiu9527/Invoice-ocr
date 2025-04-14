#!/bin/bash

# 激活虚拟环境
VENV_DIR="venv_py38"
if [ -d "$VENV_DIR" ]; then
    echo "Activating virtual environment: $VENV_DIR"
    source $VENV_DIR/bin/activate  # Linux/macOS
    # 如果是Windows，使用以下命令（注释掉Linux/macOS的命令）
    # source $VENV_DIR/Scripts/activate
else
    echo "Virtual environment $VENV_DIR not found!"
    exit 1
fi

# 设置百度OCR的环境变量（如果未设置）
export BAIDU_OCR_API_KEY="${BAIDU_OCR_API_KEY:-Io2AFs0q1pPmzlxxYn44dMmR}"
export BAIDU_OCR_SECRET_KEY="${BAIDU_OCR_SECRET_KEY:-09cMxoWTA7UG7ekNIjs8AYJIJWvuXRUW}"
export PORT="${PORT:-5001}"

# 确保所需目录存在
mkdir -p app/data/uploads app/data/results app/logs

echo "Starting Invoice OCR application..."
echo "API Key: ${BAIDU_OCR_API_KEY}"
echo "Port: ${PORT}"

# 启动应用
python app.py
