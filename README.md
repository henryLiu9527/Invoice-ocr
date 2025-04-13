# Invoice OCR Processing System

A web application for automatic invoice recognition and data extraction using OCR technology.

## Features

- **Multiple File Upload**: Process up to 10 invoice files at once
- **Dual OCR Engines**:
  - Baidu OCR (cloud-based, primary)
  - PaddleOCR (local processing, backup)
- **Automatic Engine Failover**: If the primary engine fails, the system automatically switches to the backup
- **Multiple Invoice Types**: Supports VAT, General, Receipt, Form, and Auto detection formats
- **Export Options**: Export results as XLSX, DOCX, or TXT
- **Responsive UI**: Single-page user interface with real-time feedback

## System Requirements

- Python 3.8+
- Flask web framework
- PaddlePaddle and PaddleOCR for local processing
- Docker (optional, for containerized deployment)

## Installation

### Direct Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd invoice-ocr
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set environment variables for Baidu OCR:
   ```
   export BAIDU_OCR_API_KEY="your_api_key"
   export BAIDU_OCR_SECRET_KEY="your_secret_key"
   ```

4. Run the application:
   ```
   python app.py
   ```

5. Access the web interface at `http://localhost:5001`

### Docker Installation

1. Build the Docker image:
   ```
   docker build -t invoice-ocr .
   ```

2. Run the container:
   ```
   docker run -d -p 5001:5001 \
     -e BAIDU_OCR_API_KEY="your_api_key" \
     -e BAIDU_OCR_SECRET_KEY="your_secret_key" \
     -v ./app/data:/app/app/data \
     -v ./app/logs:/app/app/logs \
     --name invoice-ocr invoice-ocr
   ```

3. Access the web interface at `http://localhost:5001`

## Configuration

Configuration options can be set through environment variables:

- `PORT`: Web server port (default: 5001)
- `DEBUG`: Enable debug mode (default: False)
- `BAIDU_OCR_API_KEY`: Baidu OCR API key
- `BAIDU_OCR_SECRET_KEY`: Baidu OCR Secret key
- `LOG_LEVEL`: Logging level (default: INFO)

## Usage

1. Upload invoice files (PNG, JPG, JPEG, PDF, TIF, TIFF formats)
2. Select the OCR engine (Baidu OCR or PaddleOCR)
3. Choose the invoice type
4. Click "Start Processing"
5. View the extracted text results
6. Export the results in your preferred format

## Project Structure

```
invoice-ocr/
├── app/
│   ├── data/
│   │   ├── uploads/    # Temporary storage for uploaded files
│   │   └── results/    # Exported result files
│   ├── logs/           # Application logs
│   ├── modules/        # Core functionality modules
│   │   ├── baidu_ocr.py
│   │   ├── paddle_ocr.py
│   │   ├── ocr_manager.py
│   │   └── exporter.py
│   ├── static/         # Static web assets
│   │   ├── css/
│   │   └── js/
│   └── templates/      # HTML templates
├── app.py              # Main application entry point
├── config.py           # Application configuration
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
└── README.md
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 