import os
import logging
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)

class PaddleOCR:
    """PaddleOCR本地OCR引擎实现"""
    
    def __init__(self):
        """初始化PaddleOCR引擎"""
        logger.info("Initializing PaddleOCR engine")
        self.ocr = None
        self._load_model()
    
    def _load_model(self):
        """延迟加载PaddleOCR模型"""
        try:
            # 仅在第一次使用时导入PaddleOCR，减少启动时间和资源占用
            from paddleocr import PaddleOCR as POCR
            
            # 使用中英文通用OCR模型
            self.ocr = POCR(use_angle_cls=True, lang="ch", use_gpu=False)
            logger.info("PaddleOCR model loaded successfully")
        except ImportError:
            logger.error("PaddleOCR package not installed. Please install with: pip install paddleocr")
            raise
        except Exception as e:
            logger.error(f"Failed to load PaddleOCR model: {str(e)}")
            raise
    
    def _ensure_model_loaded(self):
        """确保模型已加载"""
        if self.ocr is None:
            self._load_model()
    
    def _preprocess_image(self, image_path):
        """预处理图像以提高OCR质量"""
        try:
            # 读取图像
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Cannot read image: {image_path}")
            
            # 将图像转换为灰度
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 应用阈值处理增强对比度
            _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            
            # 应用高斯模糊去除噪点
            processed = cv2.GaussianBlur(binary, (5, 5), 0)
            
            return processed
        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            # 如果预处理失败，返回原始图像路径
            return image_path
    
    def recognize(self, image_path, invoice_type=None):
        """
        使用PaddleOCR识别图像
        
        Args:
            image_path: 图像文件路径
            invoice_type: 发票类型（对PaddleOCR不影响处理逻辑，仅用于日志记录）
            
        Returns:
            识别结果的JSON对象
        """
        logger.info(f"Processing image with PaddleOCR: {os.path.basename(image_path)}")
        
        try:
            # 确保模型已加载
            self._ensure_model_loaded()
            
            # 预处理图像
            processed_image = self._preprocess_image(image_path)
            
            # 如果预处理返回的是字符串路径，则直接使用原始图像
            if isinstance(processed_image, str):
                result = self.ocr.ocr(image_path, cls=True)
            else:
                # 保存预处理后的图像
                temp_path = f"{image_path}_processed.jpg"
                cv2.imwrite(temp_path, processed_image)
                result = self.ocr.ocr(temp_path, cls=True)
                
                # 删除临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
            # 转换PaddleOCR结果为标准格式
            standardized_result = self._standardize_result(result)
            
            logger.info(f"Successfully processed image with PaddleOCR: {os.path.basename(image_path)}")
            return {'success': True, 'result': standardized_result, 'engine': 'paddle'}
            
        except Exception as e:
            logger.error(f"PaddleOCR processing failed: {str(e)}")
            return {'success': False, 'error': str(e), 'engine': 'paddle'}
    
    def _standardize_result(self, paddle_result):
        """
        将PaddleOCR的结果转换为与百度OCR一致的格式
        
        Args:
            paddle_result: PaddleOCR返回的结果
            
        Returns:
            标准化后的结果字典
        """
        if not paddle_result or len(paddle_result) == 0:
            return {'words_result': []}
        
        # PaddleOCR返回格式: [[(x1,y1),(x2,y1),(x2,y2),(x1,y2)], (text, confidence)]
        # 转换为百度格式: {'words_result': [{'words': text, 'location': {...}}]}
        words_result = []
        
        for line in paddle_result:
            for item in line:
                text = item[1][0]  # 文本内容
                confidence = item[1][1]  # 置信度
                box = item[0]  # 文本框坐标
                
                # 计算文本框位置
                left = min(point[0] for point in box)
                top = min(point[1] for point in box)
                width = max(point[0] for point in box) - left
                height = max(point[1] for point in box) - top
                
                words_result.append({
                    'words': text,
                    'probability': {'average': confidence},
                    'location': {
                        'top': int(top),
                        'left': int(left),
                        'width': int(width),
                        'height': int(height)
                    }
                })
        
        return {'words_result': words_result, 'words_result_num': len(words_result)} 