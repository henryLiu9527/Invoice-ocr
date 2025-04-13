import os
import time
import base64
import requests
import logging
from config import BAIDU_OCR_API_KEY, BAIDU_OCR_SECRET_KEY, BAIDU_OCR_MAX_RETRIES

logger = logging.getLogger(__name__)

class BaiduOCR:
    """百度OCR服务集成类"""
    
    # 百度OCR API接口URL
    TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'
    OCR_URL_PREFIX = 'https://aip.baidubce.com/rest/2.0/ocr/v1'
    
    # 发票类型映射
    INVOICE_TYPES = {
        'VAT': 'vat_invoice',              # 增值税发票
        'General': 'invoice',               # 通用发票
        'Receipt': 'receipt',               # 收据
        'Form': 'form',                     # 表单
        'Auto': 'accurate_basic'            # 自动（通用高精度）
    }
    
    def __init__(self):
        """初始化百度OCR客户端"""
        self.access_token = None
        self.token_expiry = 0
        logger.info("Initializing Baidu OCR client")
    
    def get_access_token(self):
        """获取百度API访问令牌，如果已过期则重新获取"""
        current_time = time.time()
        
        # 如果令牌尚未获取或已过期，则获取新令牌
        if self.access_token is None or current_time >= self.token_expiry:
            logger.info("Getting new Baidu OCR access token")
            params = {
                'grant_type': 'client_credentials',
                'client_id': BAIDU_OCR_API_KEY,
                'client_secret': BAIDU_OCR_SECRET_KEY
            }
            
            try:
                response = requests.post(self.TOKEN_URL, params=params)
                response.raise_for_status()
                result = response.json()
                
                self.access_token = result.get('access_token')
                # 令牌有效期通常为30天，但设置为提前1小时过期以确保安全
                expires_in = result.get('expires_in', 2592000) - 3600
                self.token_expiry = current_time + expires_in
                
                logger.info("Successfully obtained Baidu OCR access token")
                return self.access_token
            except Exception as e:
                logger.error(f"Failed to get Baidu OCR access token: {str(e)}")
                raise
        
        return self.access_token
    
    def _encode_image(self, image_path):
        """将图像编码为base64格式"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def recognize(self, image_path, invoice_type='Auto'):
        """
        使用百度OCR识别图像
        
        Args:
            image_path: 图像文件路径
            invoice_type: 发票类型，可选值包括Auto、VAT、General、Receipt、Form
            
        Returns:
            识别结果的JSON对象
        """
        logger.info(f"Processing image with Baidu OCR: {os.path.basename(image_path)}, type: {invoice_type}")
        
        # 确定OCR API类型
        ocr_type = self.INVOICE_TYPES.get(invoice_type, 'accurate_basic')
        request_url = f"{self.OCR_URL_PREFIX}/{ocr_type}"
        
        # 获取访问令牌
        access_token = self.get_access_token()
        
        # 准备请求参数
        params = {'access_token': access_token}
        
        # 图像编码
        image_base64 = self._encode_image(image_path)
        data = {'image': image_base64}
        
        # 添加特定参数
        if ocr_type == 'accurate_basic':
            data['detect_direction'] = 'true'
            data['probability'] = 'true'
        
        # 尝试请求，最多重试BAIDU_OCR_MAX_RETRIES次
        for attempt in range(BAIDU_OCR_MAX_RETRIES):
            try:
                response = requests.post(request_url, params=params, data=data)
                response.raise_for_status()
                result = response.json()
                
                # 检查是否有错误
                if 'error_code' in result:
                    error_code = result.get('error_code')
                    error_msg = result.get('error_msg', 'Unknown error')
                    logger.warning(f"Baidu OCR API error (attempt {attempt+1}/{BAIDU_OCR_MAX_RETRIES}): {error_code} - {error_msg}")
                    
                    # 如果是令牌过期错误，尝试刷新令牌
                    if error_code == 110 or error_code == 111:
                        self.access_token = None
                        continue
                    
                    # 如果是QPS限制，等待后重试
                    if error_code == 17 or error_code == 18:
                        wait_time = (attempt + 1) * 2
                        logger.info(f"QPS limit reached, waiting {wait_time} seconds before retry")
                        time.sleep(wait_time)
                        continue
                    
                    # 其他错误，返回失败结果
                    return {'success': False, 'error': error_msg, 'error_code': error_code}
                
                # 成功处理，返回结果
                logger.info(f"Successfully processed image with Baidu OCR: {os.path.basename(image_path)}")
                return {'success': True, 'result': result, 'engine': 'baidu'}
                
            except Exception as e:
                logger.error(f"Baidu OCR request failed (attempt {attempt+1}/{BAIDU_OCR_MAX_RETRIES}): {str(e)}")
                if attempt < BAIDU_OCR_MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 2
                    time.sleep(wait_time)
                else:
                    return {'success': False, 'error': str(e), 'engine': 'baidu'}
        
        return {'success': False, 'error': 'Maximum retry attempts reached', 'engine': 'baidu'} 