import os
import uuid
import logging
import werkzeug
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
                if 'result' in result and 'words_result' in result['result']:
                    for item in result['result']['words_result']:
                        if isinstance(item, dict) and 'words' in item:
                            words.append(item['words'])
                file_result['preview'] = words[:10]  # 仅显示前10行作为预览
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

@app.teardown_appcontext
def cleanup(exception=None):
    """清理资源"""
    # 可以在这里添加清理临时文件等逻辑
    pass

if __name__ == '__main__':
    logger.info(f"Starting Flask application on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG) 