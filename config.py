import os
import logging
from datetime import datetime

# Flask应用配置
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_for_dev_environment')
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
PORT = int(os.environ.get('PORT', 5001))

# 文件上传配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app/data/uploads')
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app/data/results')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tif', 'tiff'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
MAX_FILES_COUNT = 10  # 最多上传10个文件

# 百度OCR API配置
BAIDU_OCR_API_KEY = os.environ.get('BAIDU_OCR_API_KEY', 'Io2AFs0q1pPmzlxxYn44dMmR')
BAIDU_OCR_SECRET_KEY = os.environ.get('BAIDU_OCR_SECRET_KEY', '09cMxoWTA7UG7ekNIjs8AYJIJWvuXRUW')
BAIDU_OCR_MAX_RETRIES = 3  # 百度OCR API最大重试次数

# 日志配置
LOG_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app/logs')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(LOG_FOLDER, f"ocr_app_{datetime.now().strftime('%Y%m%d')}.log")

# 确保必要的目录存在
for folder in [UPLOAD_FOLDER, RESULTS_FOLDER, LOG_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# 日志格式配置
log_format = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(module)s] - %(message)s'
)

# 配置根日志记录器
def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # 文件处理器
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    return logger

# 初始化日志记录器
logger = setup_logger() 