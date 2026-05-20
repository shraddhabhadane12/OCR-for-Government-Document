from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import base64
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
from ocr_processor import OCRProcessor
from extractors import AadharExtractor, PANExtractor, DrivingLicenseExtractor

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Serve frontend files
@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory('../frontend', path)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize processors
ocr_processor = OCRProcessor()
extractors = {
    'AADHAR': AadharExtractor(),
    'PAN': PANExtractor(),
    'DRIVING_LICENSE': DrivingLicenseExtractor()
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('../frontend', filename)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'OCR API is running'})

@app.route('/api/process', methods=['POST'])
def process_document():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, PDF'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract text using OCR
        extracted_text, original_image = ocr_processor.extract_text(filepath)
        
        # Detect document type
        doc_type = ocr_processor.detect_document_type(extracted_text)
        
        # Extract structured information
        if doc_type in extractors:
            extracted_data = extractors[doc_type].extract(extracted_text)
        else:
            extracted_data = {
                'document_type': 'UNKNOWN',
                'raw_text': extracted_text
            }
        
        # Convert image to base64 for preview
        import cv2
        _, buffer = cv2.imencode('.jpg', original_image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Save to CSV
        csv_filename = f"{timestamp}_extracted_data.csv"
        csv_path = os.path.join(OUTPUT_FOLDER, csv_filename)
        
        df = pd.DataFrame([extracted_data])
        df.to_csv(csv_path, index=False)
        
        # Clean up uploaded file
        try:
            os.remove(filepath)
        except:
            pass
        
        return jsonify({
            'success': True,
            'document_type': doc_type,
            'extracted_data': extracted_data,
            'image_preview': f"data:image/jpeg;base64,{image_base64}",
            'csv_file': csv_filename,
            'raw_text': extracted_text
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_csv(filename):
    try:
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        files = []
        for filename in os.listdir(OUTPUT_FOLDER):
            if filename.endswith('.csv'):
                filepath = os.path.join(OUTPUT_FOLDER, filename)
                files.append({
                    'filename': filename,
                    'created': datetime.fromtimestamp(os.path.getctime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
                })
        files.sort(key=lambda x: x['created'], reverse=True)
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting OCR Document Extractor API...")
    print("Make sure Tesseract OCR is installed on your system")
    
    # Get port from environment variable for deployment platforms
    port = int(os.environ.get('PORT', 7000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print(f"Server running on port {port}")
    app.run(debug=debug, host='0.0.0.0', port=port)
