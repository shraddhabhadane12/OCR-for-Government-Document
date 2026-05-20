#!/bin/bash

# Install system dependencies
apt-get update
apt-get install -y tesseract-ocr tesseract-ocr-hin libgl1-mesa-glx libglib2.0-0

# Install Python dependencies
pip install -r requirements.txt

echo "Build completed successfully!"