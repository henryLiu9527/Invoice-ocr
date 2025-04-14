import os
import uuid
import logging
import werkzeug
import threading
import time
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# 导入配置和模块
from config import (
    SECRET_KEY, DEBUG, PORT, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, 
    MAX_CONTENT_LENGTH, MAX_FILES_COUNT, RESULTS_FOLDER, logger
)
from app.modules.ocr_manager import OCRManager
from app.modules.exporter import ResultExporter

# 创建Flask应用
app = Flask(__name__, 
            static_folder='app/static',
            template_folder='app/templates')

# 应用配置
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

# 初始化OCR管理器和导出器
ocr_manager = OCRManager()
exporter = ResultExporter()

# 维护上传文件和OCR结果的会话数据
session_data = {}

def allowed_file(filename):
    """检查文件是否为允许的扩展名"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """主页路由"""
    logger.info("Accessing index page")
    
    # 获取可用的OCR引擎
    engines = ocr_manager.get_available_engines()
    
    return render_template('index.html', engines=engines)

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    # 检查是否有文件
    if 'files[]' not in request.files:
        logger.warning("No files part in the request")
        return jsonify({'success': False, 'error': 'No files submitted'})
    
    files = request.files.getlist('files[]')
    
    # 检查文件数量限制
    if len(files) > MAX_FILES_COUNT:
        logger.warning(f"Too many files submitted: {len(files)}, max allowed: {MAX_FILES_COUNT}")
        return jsonify({'success': False, 'error': f'Maximum {MAX_FILES_COUNT} files allowed'})
    
    # 生成会话ID
    session_id = str(uuid.uuid4())
    session_data[session_id] = {'files': [], 'results': {}}
    
    uploaded_files = []
    for file in files:
        if file and allowed_file(file.filename):
            try:
                # 安全地保存文件
                filename = secure_filename(file.filename)
                # 添加会话ID前缀，避免文件名冲突
                temp_filename = f"{session_id}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
                file.save(file_path)
                
                # 记录文件信息
                uploaded_files.append({
                    'original_name': filename,
                    'temp_path': file_path
                })
                session_data[session_id]['files'].append({
                    'original_name': filename,
                    'temp_path': file_path
                })
                
                logger.info(f"File uploaded: {filename}")
            except Exception as e:
                logger.error(f"Error saving file {file.filename}: {str(e)}")
                return jsonify({'success': False, 'error': f'Error saving file: {str(e)}'})
        else:
            logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({'success': False, 'error': f'Invalid file type for {file.filename}'})
    
    return jsonify({
        'success': True, 
        'message': f'{len(uploaded_files)} files uploaded successfully',
        'session_id': session_id
    })

@app.route('/process', methods=['POST'])
def process_files():
    """处理上传的文件"""
    data = request.json
    session_id = data.get('session_id')
    engine = data.get('engine', 'baidu')
    invoice_type = data.get('invoice_type', 'Auto')
    
    # 验证会话ID
    if not session_id or session_id not in session_data:
        logger.warning(f"Invalid session ID: {session_id}")
        return jsonify({'success': False, 'error': 'Invalid session ID'})
    
    # 设置OCR引擎
    ocr_manager.set_engine(engine)
    
    files = session_data[session_id]['files']
    if not files:
        logger.warning("No files to process")
        return jsonify({'success': False, 'error': 'No files to process'})
    
    results = []
    for file_info in files:
        try:
            # 处理图像
            original_name = file_info['original_name']
            temp_path = file_info['temp_path']
            
            logger.info(f"Processing file: {original_name}, type: {invoice_type}")
            result = ocr_manager.process_image(temp_path, invoice_type)
            
            # 立即保存原始JSON响应
            if result.get('success', True):
                try:
                    # 保存原始JSON响应
                    json_path = exporter.export_to_json(result, temp_path)
                    logger.info(f"Saved original JSON response to: {json_path}")
                except Exception as e:
                    logger.error(f"Failed to save original JSON response: {str(e)}")
            
            # 保存结果
            session_data[session_id]['results'][original_name] = result
            
            # 准备响应数据
            file_result = {
                'filename': original_name,
                'success': result.get('success', False),
                'engine': result.get('engine', 'unknown')
            }
            
            if result.get('success', False):
                # 提取部分文本作为预览
                words = []
                
                # 处理不同类型的OCR结果
                if invoice_type == 'MultipleInvoice' and 'result' in result:
                    # 检查是否有增值税发票数据
                    if 'words_result' in result['result'] and len(result['result']['words_result']) > 0:
                        # 检查是否是vat_invoice类型
                        for word_item in result['result']['words_result']:
                            if isinstance(word_item, dict) and (
                                (word_item.get('type') == 'vat_invoice') or
                                ('result' in word_item and 'vat_invoice' in word_item.get('result', {}))
                            ):
                                # 这是增值税发票数据
                                logger.info("Found VAT invoice data in MultipleInvoice result")
                                
                                # 提取关键字段
                                if 'result' in word_item and 'vat_invoice' in word_item['result']:
                                    vat_data = word_item['result']
                                    # 添加发票类型
                                    if 'InvoiceType' in vat_data and vat_data['InvoiceType'] and isinstance(vat_data['InvoiceType'], list):
                                        invoice_type_text = vat_data['InvoiceType'][0].get('word', '') if isinstance(vat_data['InvoiceType'][0], dict) else str(vat_data['InvoiceType'][0])
                                        words.append(f"发票类型: {invoice_type_text}")
                                    
                                    # 添加发票号码和代码
                                    if 'InvoiceNum' in vat_data and vat_data['InvoiceNum'] and isinstance(vat_data['InvoiceNum'], list):
                                        invoice_num = vat_data['InvoiceNum'][0].get('word', '') if isinstance(vat_data['InvoiceNum'][0], dict) else str(vat_data['InvoiceNum'][0])
                                        words.append(f"发票号码: {invoice_num}")
                                    
                                    if 'InvoiceCode' in vat_data and vat_data['InvoiceCode'] and isinstance(vat_data['InvoiceCode'], list):
                                        invoice_code = vat_data['InvoiceCode'][0].get('word', '') if isinstance(vat_data['InvoiceCode'][0], dict) else str(vat_data['InvoiceCode'][0])
                                        words.append(f"发票代码: {invoice_code}")
                                    
                                    # 添加销售方和购买方
                                    if 'SellerName' in vat_data and vat_data['SellerName'] and isinstance(vat_data['SellerName'], list):
                                        seller_name = vat_data['SellerName'][0].get('word', '') if isinstance(vat_data['SellerName'][0], dict) else str(vat_data['SellerName'][0])
                                        words.append(f"销售方: {seller_name}")
                                    
                                    if 'PurchaserName' in vat_data and vat_data['PurchaserName'] and isinstance(vat_data['PurchaserName'], list):
                                        purchaser_name = vat_data['PurchaserName'][0].get('word', '') if isinstance(vat_data['PurchaserName'][0], dict) else str(vat_data['PurchaserName'][0])
                                        words.append(f"购买方: {purchaser_name}")
                                    
                                    # 添加金额
                                    if 'AmountInFiguers' in vat_data and vat_data['AmountInFiguers'] and isinstance(vat_data['AmountInFiguers'], list):
                                        amount = vat_data['AmountInFiguers'][0].get('word', '') if isinstance(vat_data['AmountInFiguers'][0], dict) else str(vat_data['AmountInFiguers'][0])
                                        words.append(f"金额: {amount}")
                                    
                                    # 添加商品信息
                                    if 'CommodityName' in vat_data and vat_data['CommodityName'] and isinstance(vat_data['CommodityName'], list):
                                        for i, item in enumerate(vat_data['CommodityName']):
                                            commodity_name = item.get('word', '') if isinstance(item, dict) else str(item)
                                            words.append(f"商品{i+1}: {commodity_name}")
                                            if i >= 2:  # 只显示前3个商品
                                                break
                                else:
                                    # 直接处理word_item
                                    words.append(f"发票类型: {word_item.get('type', 'vat_invoice')}")
                                    for key, value in word_item.items():
                                        if key not in ['type', 'probability', 'left', 'top', 'width', 'height'] and len(words) < 10:
                                            words.append(f"{key}: {value}")
                                
                                break
                    
                    # 如果没有找到增值税发票数据，尝试multiple_invoice字段
                    if not words and 'multiple_invoice' in result['result']:
                        multi_data = result['result']['multiple_invoice']
                        if isinstance(multi_data, dict):
                            # 获取票据类型
                            if 'invoice_type' in multi_data and isinstance(multi_data['invoice_type'], dict):
                                invoice_type_text = multi_data['invoice_type'].get('text', '')
                                if invoice_type_text:
                                    words.append(f"检测到的票据类型: {invoice_type_text}")
                            
                            # 获取详细信息
                            if 'details' in multi_data and isinstance(multi_data['details'], list):
                                for item in multi_data['details']:
                                    if isinstance(item, dict):
                                        key = item.get('key', '')
                                        value = item.get('value', '')
                                        if key and value:
                                            words.append(f"{key}: {value}")
                                            if len(words) >= 10:  # 最多显示10行
                                                break
                    
                    # 如果words仍为空，检查是否有常规words_result
                    if not words and 'words_result' in result['result']:
                        words_result = result['result']['words_result']
                        if isinstance(words_result, list) and words_result:
                            for item in words_result:
                                if isinstance(item, dict) and 'words' in item:
                                    words.append(item['words'])
                                    if len(words) >= 10:  # 最多显示10行
                                        break
                
                elif 'result' in result and 'words_result' in result['result']:
                    # 处理标准OCR结果
                    for item in result['result']['words_result']:
                        if isinstance(item, dict) and 'words' in item:
                            words.append(item['words'])
                            if len(words) >= 10:  # 最多显示10行
                                break
                
                # 如果没有提取到文本，添加默认信息
                if not words:
                    words.append("No text detected")
                
                file_result['preview'] = words[:10]  # 确保最多只有10行预览
            else:
                file_result['error'] = result.get('error', 'Unknown error')
            
            results.append(file_result)
            
        except Exception as e:
            logger.error(f"Error processing file {file_info['original_name']}: {str(e)}")
            results.append({
                'filename': file_info['original_name'],
                'success': False,
                'error': str(e)
            })
    
    return jsonify({
        'success': True,
        'results': results
    })

@app.route('/export', methods=['POST'])
def export_results():
    """将OCR结果导出为指定格式"""
    data = request.json
    session_id = data.get('session_id')
    filename = data.get('filename')
    format_name = data.get('format', 'xlsx')
    
    # 验证会话ID和文件名
    if not session_id or session_id not in session_data:
        logger.warning(f"Invalid session ID: {session_id}")
        return jsonify({'success': False, 'error': 'Invalid session ID'})
    
    if not filename or filename not in session_data[session_id]['results']:
        logger.warning(f"Invalid filename: {filename}")
        return jsonify({'success': False, 'error': 'Invalid filename'})
    
    # 获取结果和文件路径
    result = session_data[session_id]['results'][filename]
    
    # 查找对应的临时文件路径
    temp_path = None
    for file_info in session_data[session_id]['files']:
        if file_info['original_name'] == filename:
            temp_path = file_info['temp_path']
            break
    
    if not temp_path:
        logger.error(f"File path not found for: {filename}")
        return jsonify({'success': False, 'error': 'File path not found'})
    
    try:
        # 导出结果
        export_path = exporter.export(result, temp_path, format_name)
        
        # 获取导出文件的基本名称（不含路径）
        export_filename = os.path.basename(export_path)
        
        logger.info(f"Result exported to {format_name}: {export_path}")
        return jsonify({
            'success': True,
            'message': f'Result exported to {format_name} successfully',
            'download_url': url_for('download_file', filename=export_filename),
            'filename': export_filename
        })
        
    except Exception as e:
        logger.error(f"Error exporting result: {str(e)}")
        return jsonify({'success': False, 'error': f'Export failed: {str(e)}'})

@app.route('/download/<filename>')
def download_file(filename):
    """下载导出的文件"""
    logger.info(f"Downloading file: {filename}")
    return send_from_directory(app.config['RESULTS_FOLDER'], filename, as_attachment=True)

@app.route('/view_json/<filename>')
def view_json(filename):
    """直接查看JSON文件内容"""
    logger.info(f"Viewing JSON file: {filename}")
    json_folder = os.path.join(app.config['RESULTS_FOLDER'], 'json')
    try:
        with open(os.path.join(json_folder, filename), 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        return jsonify(json_data)
    except FileNotFoundError:
        return jsonify({'error': 'JSON file not found'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON file'}), 400
    except Exception as e:
        logger.error(f"Error viewing JSON file {filename}: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/json_files')
def list_json_files():
    """列出所有可用的JSON文件"""
    logger.info("Listing available JSON files")
    json_folder = os.path.join(app.config['RESULTS_FOLDER'], 'json')
    try:
        files = []
        if os.path.exists(json_folder):
            for filename in os.listdir(json_folder):
                if filename.endswith('.json'):
                    files.append({
                        'filename': filename,
                        'url': url_for('view_json', filename=filename)
                    })
        return jsonify({'json_files': files})
    except Exception as e:
        logger.error(f"Error listing JSON files: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/engines')
def get_engines():
    """获取可用的OCR引擎"""
    engines = ocr_manager.get_available_engines()
    return jsonify(engines)

@app.errorhandler(werkzeug.exceptions.RequestEntityTooLarge)
def handle_request_too_large(e):
    """处理请求体过大的错误"""
    logger.error("File too large")
    return jsonify(success=False, error=f"File too large. Maximum file size is {MAX_CONTENT_LENGTH/(1024*1024)}MB")

@app.errorhandler(Exception)
def handle_exception(e):
    """处理未捕获的异常"""
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify(success=False, error=f"Server error: {str(e)}")

def cleanup_old_files():
    """定期清理超过24小时的临时文件"""
    while True:
        try:
            logger.info("Running scheduled cleanup of old files")
            now = time.time()
            # 清理上传目录
            cleanup_directory(UPLOAD_FOLDER, now - 86400)  # 24小时
            # 清理结果目录
            cleanup_directory(RESULTS_FOLDER, now - 86400)  # 24小时
            # 每小时检查一次
            time.sleep(3600)
        except Exception as e:
            logger.error(f"Error during file cleanup: {str(e)}")
            time.sleep(3600)  # 出错时仍然继续下一轮清理

def cleanup_directory(directory, expiry_time):
    """清理指定目录中的过期文件"""
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return
    
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

@app.teardown_appcontext
def cleanup(exception=None):
    """清理资源"""
    # 可以在这里添加清理临时文件等逻辑
    pass

# 启动自动清理线程
# cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
# cleanup_thread.start()

if __name__ == '__main__':
    logger.info(f"Starting Flask application on port {PORT}")
    # 运行前先清理一次旧文件
    now = time.time()
    #cleanup_directory(UPLOAD_FOLDER, now - 86400)
    #cleanup_directory(RESULTS_FOLDER, now - 86400)
    # 启动应用
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG) 
