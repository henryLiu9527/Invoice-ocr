#!/usr/bin/env python3
"""
清理脚本 - 删除超过24小时的上传和结果文件
可通过cron作业定期运行: 0 * * * * cd /path/to/app && python cleanup.py >> app/logs/cleanup.log 2>&1
"""

import os
import time
import logging
import sys
from config import UPLOAD_FOLDER, RESULTS_FOLDER

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [cleanup] - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("cleanup")

def cleanup_old_files(max_age_seconds=86400):  # 默认为24小时
    """清理超过指定时间的文件"""
    logger.info("Starting cleanup of old files")
    now = time.time()
    expiry_time = now - max_age_seconds
    
    # 清理上传目录
    upload_count = cleanup_directory(UPLOAD_FOLDER, expiry_time)
    # 清理结果目录
    results_count = cleanup_directory(RESULTS_FOLDER, expiry_time)
    
    logger.info(f"Cleanup completed. Removed {upload_count} upload files and {results_count} result files.")
    
    return upload_count + results_count

def cleanup_directory(directory, expiry_time):
    """清理指定目录中的过期文件"""
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return 0
    
    count = 0
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path) and os.path.getmtime(file_path) < expiry_time:
            try:
                os.remove(file_path)
                count += 1
                logger.info(f"Removed old file: {filename}")
            except Exception as e:
                logger.error(f"Failed to remove file {filename}: {str(e)}")
    
    if count > 0:
        logger.info(f"Cleaned up {count} files from {directory}")
    else:
        logger.info(f"No files to clean up in {directory}")
    
    return count

if __name__ == "__main__":
    # 默认清理24小时前的文件
    cleanup_old_files()
    
    # 可以通过命令行参数指定不同的时间范围（秒）
    # 例如: python cleanup.py 3600 - 清理1小时前的文件
    if len(sys.argv) > 1:
        try:
            age_seconds = int(sys.argv[1])
            logger.info(f"Using custom age threshold: {age_seconds} seconds")
            cleanup_old_files(age_seconds)
        except ValueError:
            logger.error(f"Invalid age parameter: {sys.argv[1]}, must be integer seconds") 