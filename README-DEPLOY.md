# 百度OCR应用部署指南

本文档提供了部署百度OCR应用的三种方法：直接运行、Systemd服务部署和Docker容器部署。

## 1. 直接运行

### 步骤：

1. 确保已安装Python 3.8+和所有依赖项：
   ```bash
   cd /opt/BaiduOCR
   python -m venv venv_py38
   source venv_py38/bin/activate
   pip install -r requirements.txt
   ```

2. 使用启动脚本运行应用：
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

## 2. Systemd服务部署（推荐方式）

### 步骤：

1. 将服务文件复制到系统服务目录：
   ```bash
   sudo cp /opt/BaiduOCR/baidu-ocr.service /etc/systemd/system/
   ```

2. 重新加载systemd配置：
   ```bash
   sudo systemctl daemon-reload
   ```

3. 启用并启动服务：
   ```bash
   sudo systemctl enable baidu-ocr
   sudo systemctl start baidu-ocr
   ```

4. 检查服务状态：
   ```bash
   sudo systemctl status baidu-ocr
   ```

5. 查看日志：
   ```bash
   sudo journalctl -u baidu-ocr -f
   ```

## 3. Docker容器部署

### 步骤：

1. 确保已安装Docker和Docker Compose：
   ```bash
   # 安装Docker（如果尚未安装）
   curl -fsSL https://get.docker.com | sh
   
   # 安装Docker Compose（如果尚未安装）
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. 构建并启动容器：
   ```bash
   cd /opt/BaiduOCR
   docker-compose up -d
   ```

3. 检查容器状态：
   ```bash
   docker-compose ps
   ```

4. 查看日志：
   ```bash
   docker-compose logs -f
   ```

## 资源要求

- **内存**: 至少2GB RAM
- **CPU**: 至少2核心
- **存储**: 至少1GB可用空间用于应用和临时文件

## 环境变量配置

您可以通过以下环境变量来配置应用：

- `PORT`: 应用监听端口（默认5001）
- `BAIDU_OCR_API_KEY`: 百度OCR API密钥
- `BAIDU_OCR_SECRET_KEY`: 百度OCR密钥

## 故障排除

### 服务无法启动

检查日志：
```bash
# 对于systemd服务
sudo journalctl -u baidu-ocr -f

# 对于直接运行
cat app/logs/app.log

# 对于Docker部署
docker-compose logs
```

### API请求超时或错误

确保API密钥配置正确：
```bash
# 检查环境变量
echo $BAIDU_OCR_API_KEY
echo $BAIDU_OCR_SECRET_KEY
```

### 数据目录权限问题

确保数据目录存在且具有正确的权限：
```bash
sudo mkdir -p /opt/BaiduOCR/app/data/uploads /opt/BaiduOCR/app/data/results
sudo chown -R $USER:$USER /opt/BaiduOCR/app/data
```
