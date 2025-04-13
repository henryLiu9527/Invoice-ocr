# 使用多阶段构建来优化镜像大小
FROM python:3.8-slim AS builder

# 安装依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /build

# 复制依赖文件
COPY requirements.txt .

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 第二阶段：创建最终镜像
FROM python:3.8-slim

# 复制运行时所需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p /app/app/data/uploads /app/app/data/results /app/app/logs && \
    chown -R appuser:appuser /app

# 设置环境变量
ENV PORT=5001
ENV BAIDU_OCR_API_KEY="Io2AFs0q1pPmzlxxYn44dMmR"
ENV BAIDU_OCR_SECRET_KEY="09cMxoWTA7UG7ekNIjs8AYJIJWvuXRUW"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["python", "app.py"] 