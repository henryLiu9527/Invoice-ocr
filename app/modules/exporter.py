import os
import json
import logging
import pandas as pd
from docx import Document
from config import RESULTS_FOLDER

logger = logging.getLogger(__name__)

class ResultExporter:
    """OCR结果导出器，支持多种格式导出"""
    
    def __init__(self):
        """初始化导出器"""
        logger.info("Initializing ResultExporter")
        
        # 确保结果目录存在
        os.makedirs(RESULTS_FOLDER, exist_ok=True)
    
    def _get_output_path(self, original_filename, format_name):
        """
        生成输出文件路径
        
        Args:
            original_filename: 原始文件名
            format_name: 输出格式名称
            
        Returns:
            输出文件的完整路径
        """
        # 获取不带扩展名的原始文件名
        basename = os.path.splitext(os.path.basename(original_filename))[0]
        # 文件名安全处理
        safe_name = "".join([c for c in basename if c.isalnum() or c in (' ', '_', '-')]).rstrip()
        
        # 生成输出文件名
        timestamp = pd.Timestamp.now().strftime('%Y%m%d%H%M%S')
        output_filename = f"{safe_name}_{timestamp}.{format_name.lower()}"
        
        return os.path.join(RESULTS_FOLDER, output_filename)
    
    def _extract_text_from_result(self, ocr_result):
        """
        从OCR结果中提取文本内容
        
        Args:
            ocr_result: OCR引擎返回的结果
            
        Returns:
            提取的文本列表
        """
        lines = []
        
        # 检查结果格式
        if not ocr_result.get('success', False):
            logger.warning("Cannot extract text: OCR result indicates failure")
            return ["OCR Processing Failed"]
        
        result = ocr_result.get('result', {})
        invoice_type = ocr_result.get('invoice_type', 'Auto')
        
        # 处理智能财务票据识别结果
        if 'multiple_invoice' in result:
            multi_data = result.get('multiple_invoice', {})
            lines.append("== 智能财务票据识别结果 ==")
            
            # 获取票据类型
            invoice_type_detected = multi_data.get('invoice_type', {}).get('text', 'Unknown')
            lines.append(f"检测到的票据类型: {invoice_type_detected}")
            lines.append("------------------------------")
            
            # 处理票据详细信息
            invoice_detail = multi_data.get('details', [])
            if isinstance(invoice_detail, list):
                for item in invoice_detail:
                    if isinstance(item, dict):
                        key = item.get('key', '')
                        value = item.get('value', '')
                        lines.append(f"{key}: {value}")
            
            # 处理票据金额
            if 'money' in multi_data:
                lines.append(f"金额: {multi_data['money']}")
            
            # 处理票据其他字段
            for field in ['tax', 'date', 'publisher', 'buyer', 'seller']:
                if field in multi_data:
                    lines.append(f"{field.capitalize()}: {multi_data[field]}")
        
        # 处理通用高精度接口返回结果 (accurate)
        elif invoice_type == 'Accurate' and 'words_result' in result:
            lines.append("== 通用高精度识别结果 ==")
            words_result = result.get('words_result', [])
            
            for item in words_result:
                if isinstance(item, dict):
                    words = item.get('words', '')
                    probability = item.get('probability', {}).get('average', 0)
                    probability_str = f" (置信度: {probability:.2f})" if probability else ""
                    lines.append(f"{words}{probability_str}")
                    
                    # 如果有位置信息，也可以添加
                    location = item.get('location', {})
                    if location:
                        loc_str = f"位置: 左={location.get('left', 0)}, 上={location.get('top', 0)}, 宽={location.get('width', 0)}, 高={location.get('height', 0)}"
                        lines.append(f"  {loc_str}")
        
        # 处理标准的words_result格式
        elif 'words_result' in result:
            words_result = result.get('words_result', [])
            
            for item in words_result:
                if isinstance(item, dict) and 'words' in item:
                    lines.append(item['words'])
                elif isinstance(item, str):
                    lines.append(item)
        
        # 处理特殊格式（增值税发票等）
        if 'vat_invoice' in result:
            vat_data = result['vat_invoice']
            if not lines:  # 如果之前没有内容，添加标题
                lines.append("== 增值税发票识别结果 ==")
            for key, value in vat_data.items():
                if isinstance(value, dict) and 'word' in value:
                    lines.append(f"{key}: {value['word']}")
                elif isinstance(value, str):
                    lines.append(f"{key}: {value}")
        
        # 如果没有提取到任何文本
        if not lines:
            lines.append("No text detected or unsupported result format")
        
        return lines
    
    def export_to_xlsx(self, ocr_result, original_filename):
        """
        将OCR结果导出为Excel格式
        
        Args:
            ocr_result: OCR引擎返回的结果
            original_filename: 原始文件名
            
        Returns:
            输出文件路径
        """
        logger.info(f"Exporting OCR result to XLSX for: {os.path.basename(original_filename)}")
        
        try:
            output_path = self._get_output_path(original_filename, 'xlsx')
            
            # 提取文本
            lines = self._extract_text_from_result(ocr_result)
            
            # 创建DataFrame
            df = pd.DataFrame(lines, columns=['Text'])
            
            # 添加元数据
            metadata = {
                'Original File': os.path.basename(original_filename),
                'OCR Engine': ocr_result.get('engine', 'unknown'),
                'Invoice Type': ocr_result.get('invoice_type', 'unknown'),
                'Export Time': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 创建一个Excel写入器
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 写入OCR结果
                df.to_excel(writer, sheet_name='OCR Results', index=False)
                
                # 写入元数据
                pd.DataFrame([metadata]).T.to_excel(writer, sheet_name='Metadata')
            
            logger.info(f"XLSX export successful: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export to XLSX: {str(e)}")
            raise
    
    def export_to_docx(self, ocr_result, original_filename):
        """
        将OCR结果导出为Word文档格式
        
        Args:
            ocr_result: OCR引擎返回的结果
            original_filename: 原始文件名
            
        Returns:
            输出文件路径
        """
        logger.info(f"Exporting OCR result to DOCX for: {os.path.basename(original_filename)}")
        
        try:
            output_path = self._get_output_path(original_filename, 'docx')
            
            # 提取文本
            lines = self._extract_text_from_result(ocr_result)
            
            # 创建Word文档
            doc = Document()
            
            # 添加标题
            doc.add_heading('OCR Recognition Results', level=1)
            
            # 添加元数据
            doc.add_heading('Metadata', level=2)
            doc.add_paragraph(f"Original File: {os.path.basename(original_filename)}")
            doc.add_paragraph(f"OCR Engine: {ocr_result.get('engine', 'unknown')}")
            doc.add_paragraph(f"Invoice Type: {ocr_result.get('invoice_type', 'unknown')}")
            doc.add_paragraph(f"Export Time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 添加OCR结果
            doc.add_heading('Recognized Text', level=2)
            for line in lines:
                doc.add_paragraph(line)
            
            # 保存文档
            doc.save(output_path)
            
            logger.info(f"DOCX export successful: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export to DOCX: {str(e)}")
            raise
    
    def export_to_txt(self, ocr_result, original_filename):
        """
        将OCR结果导出为文本格式
        
        Args:
            ocr_result: OCR引擎返回的结果
            original_filename: 原始文件名
            
        Returns:
            输出文件路径
        """
        logger.info(f"Exporting OCR result to TXT for: {os.path.basename(original_filename)}")
        
        try:
            output_path = self._get_output_path(original_filename, 'txt')
            
            # 提取文本
            lines = self._extract_text_from_result(ocr_result)
            
            # 写入文本文件
            with open(output_path, 'w', encoding='utf-8') as f:
                # 写入元数据
                f.write(f"# OCR Recognition Results\n")
                f.write(f"# Original File: {os.path.basename(original_filename)}\n")
                f.write(f"# OCR Engine: {ocr_result.get('engine', 'unknown')}\n")
                f.write(f"# Invoice Type: {ocr_result.get('invoice_type', 'unknown')}\n")
                f.write(f"# Export Time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("#" + "-" * 50 + "\n\n")
                
                # 写入OCR结果
                for line in lines:
                    f.write(f"{line}\n")
            
            logger.info(f"TXT export successful: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export to TXT: {str(e)}")
            raise
    
    def export(self, ocr_result, original_filename, format_name):
        """
        将OCR结果导出为指定格式
        
        Args:
            ocr_result: OCR引擎返回的结果
            original_filename: 原始文件名
            format_name: 导出格式（xlsx, docx, txt）
            
        Returns:
            输出文件路径
        """
        logger.info(f"Exporting OCR result to {format_name} for: {os.path.basename(original_filename)}")
        
        format_name = format_name.lower()
        
        if format_name == 'xlsx':
            return self.export_to_xlsx(ocr_result, original_filename)
        elif format_name == 'docx':
            return self.export_to_docx(ocr_result, original_filename)
        elif format_name == 'txt':
            return self.export_to_txt(ocr_result, original_filename)
        else:
            logger.error(f"Unsupported export format: {format_name}")
            raise ValueError(f"Unsupported export format: {format_name}") 