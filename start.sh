#!/bin/bash

# 激活虚拟环境
VENV_DIR="venv_py38"
if [ -d "$VENV_DIR" ]; then
    echo "Activating virtual environment: $VENV_DIR"
    source $VENV_DIR/bin/activate
else
    echo "Virtual environment $VENV_DIR not found!"
    exit 1
fi

# 设置环境变量
export BAIDU_OCR_API_KEY="${BAIDU_OCR_API_KEY:-Io2AFs0q1pPmzlxxYn44dMmR}"
export BAIDU_OCR_SECRET_KEY="${BAIDU_OCR_SECRET_KEY:-09cMxoWTA7UG7ekNIjs8AYJIJWvuXRUW}"
export PORT="${PORT:-5001}"

# 确保所需目录存在
mkdir -p app/data/uploads app/data/results app/logs

echo "Starting Invoice OCR application..."
echo "Running on port: ${PORT}"

# 直接使用Python运行应用
python app.py
