#!/usr/bin/env python3
"""
Simple startup script for OCR Document Extractor
"""
import os
import sys
import subprocess
import time

def check_tesseract():
    """Check if Tesseract is installed"""
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ Tesseract OCR is installed")
            return True
    except:
        pass
    
    print("❌ Tesseract OCR not found!")
    print("Please install Tesseract OCR:")
    print("Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
    print("Or install via: winget install UB-Mannheim.TesseractOCR")
    return False

def install_requirements():
    """Install Python requirements"""
    try:
        print("Installing Python requirements...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'backend/requirements.txt'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Requirements installed successfully")
            return True
        else:
            print(f"❌ Failed to install requirements: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing requirements: {e}")
        return False

def start_server():
    """Start the Flask server"""
    try:
        print("\n" + "="*50)
        print("🚀 Starting OCR Document Extractor Server")
        print("="*50)
        print("Server will be available at: http://localhost:7000")
        print("Press Ctrl+C to stop the server")
        print("="*50 + "\n")
        
        # Change to backend directory and start server
        os.chdir('backend')
        subprocess.run([sys.executable, 'app.py'])
        
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    print("OCR Document Extractor - Startup Script")
    print("=" * 40)
    
    # Check Tesseract
    if not check_tesseract():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        print("Continuing anyway... (requirements might already be installed)")
    
    # Start server
    start_server()