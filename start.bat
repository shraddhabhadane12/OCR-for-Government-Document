@echo off
echo OCR Document Extractor - Starting Server
echo ==========================================
echo.
echo Installing requirements...
pip install -r backend\requirements.txt
echo.
echo Starting server on http://localhost:7000
echo Press Ctrl+C to stop
echo ==========================================
echo.
cd backend
python app.py
pause