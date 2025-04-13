import os
import logging
from app.modules.baidu_ocr import BaiduOCR
from app.modules.paddle_ocr import PaddleOCR

logger = logging.getLogger(__name__)

class OCRManager:
    """OCR引擎管理器，处理引擎选择和切换"""
    
    def __init__(self):
        """初始化OCR管理器"""
        logger.info("Initializing OCR Manager")
        # 延迟初始化引擎实例，需要时才创建
        self._baidu_ocr = None
        self._paddle_ocr = None
        
        # 默认选择百度OCR作为主引擎
        self.primary_engine = 'baidu'
        self.fallback_enabled = True  # 是否启用备用引擎
    
    @property
    def baidu_ocr(self):
        """获取百度OCR实例，延迟初始化"""
        if self._baidu_ocr is None:
            logger.info("Lazy initializing Baidu OCR")
            self._baidu_ocr = BaiduOCR()
        return self._baidu_ocr
    
    @property
    def paddle_ocr(self):
        """获取PaddleOCR实例，延迟初始化"""
        if self._paddle_ocr is None:
            logger.info("Lazy initializing PaddleOCR")
            self._paddle_ocr = PaddleOCR()
        return self._paddle_ocr
    
    def set_engine(self, engine_name):
        """
        设置主OCR引擎
        
        Args:
            engine_name: 引擎名称，'baidu'或'paddle'
        """
        if engine_name in ['baidu', 'paddle']:
            logger.info(f"Setting primary OCR engine to: {engine_name}")
            self.primary_engine = engine_name
        else:
            logger.error(f"Unknown engine name: {engine_name}")
            raise ValueError(f"Unknown engine name: {engine_name}")
    
    def enable_fallback(self, enabled=True):
        """
        启用或禁用备用引擎
        
        Args:
            enabled: 是否启用备用引擎
        """
        logger.info(f"{'Enabling' if enabled else 'Disabling'} OCR engine fallback")
        self.fallback_enabled = enabled
    
    def process_image(self, image_path, invoice_type='Auto'):
        """
        处理图像，自动选择和切换引擎
        
        Args:
            image_path: 图像文件路径
            invoice_type: 发票类型
            
        Returns:
            OCR处理结果
        """
        logger.info(f"Processing image: {os.path.basename(image_path)}, type: {invoice_type}")
        
        # 首先使用主引擎
        if self.primary_engine == 'baidu':
            result = self.baidu_ocr.recognize(image_path, invoice_type)
            
            # 如果百度OCR失败且备用引擎启用，则切换到PaddleOCR
            if not result.get('success', False) and self.fallback_enabled:
                logger.warning(f"Baidu OCR failed, switching to PaddleOCR. Error: {result.get('error', 'Unknown error')}")
                result = self.paddle_ocr.recognize(image_path, invoice_type)
        else:
            result = self.paddle_ocr.recognize(image_path, invoice_type)
            
            # 如果PaddleOCR失败且备用引擎启用，则切换到百度OCR
            if not result.get('success', False) and self.fallback_enabled:
                logger.warning(f"PaddleOCR failed, switching to Baidu OCR. Error: {result.get('error', 'Unknown error')}")
                result = self.baidu_ocr.recognize(image_path, invoice_type)
        
        # 记录最终使用的引擎
        used_engine = result.get('engine', 'unknown')
        if result.get('success', False):
            logger.info(f"OCR processing successful using {used_engine} engine")
        else:
            logger.error(f"OCR processing failed with all engines. Last error: {result.get('error', 'Unknown error')}")
        
        return result
    
    def get_available_engines(self):
        """
        获取可用的OCR引擎列表
        
        Returns:
            引擎列表和当前主引擎
        """
        engines = [
            {'id': 'baidu', 'name': 'Baidu OCR', 'description': 'Cloud recognition'},
            {'id': 'paddle', 'name': 'PaddleOCR', 'description': 'Local processing'}
        ]
        
        return {
            'engines': engines,
            'primary': self.primary_engine,
            'fallback_enabled': self.fallback_enabled
        } 