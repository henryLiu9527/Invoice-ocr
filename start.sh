#!/bin/bash

# Set environment variables for Baidu OCR (if not already set)
export BAIDU_OCR_API_KEY="${BAIDU_OCR_API_KEY:-Io2AFs0q1pPmzlxxYn44dMmR}"
export BAIDU_OCR_SECRET_KEY="${BAIDU_OCR_SECRET_KEY:-09cMxoWTA7UG7ekNIjs8AYJIJWvuXRUW}"
export PORT="${PORT:-5001}"

# Make sure required directories exist
mkdir -p app/data/uploads app/data/results app/logs

echo "Starting Invoice OCR application..."
echo "API Key: ${BAIDU_OCR_API_KEY}"
echo "Port: ${PORT}"

# Start the application
python app.py 