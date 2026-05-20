import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance
import re
from pdf2image import convert_from_path
import os

class OCRProcessor:
    def __init__(self):
        # Auto-detect Tesseract on Windows
        import platform
        if platform.system() == 'Windows':
            possible_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\Tesseract-OCR\tesseract.exe'
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"✓ Tesseract found at: {path}")
                    break
        print("✓ OCR Processor initialized")
    
    def preprocess_image(self, image):
        """Simple but effective preprocessing for better OCR accuracy"""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Resize if too small (aim for good resolution)
        height, width = gray.shape
        if height < 1000 or width < 1000:
            scale = max(1000 / height, 1000 / width)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Threshold
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def extract_text(self, image_path):
        """Enhanced text extraction optimized for Indian identity documents with maximum accuracy"""
        print(f"Processing image: {image_path}")
        
        # Load image
        if image_path.lower().endswith('.pdf'):
            images = convert_from_path(image_path, dpi=300)
            image = np.array(images[0])
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        else:
            image = cv2.imread(image_path)
        
        if image is None:
            raise ValueError("Could not load image")
        
        # Store original for preview
        original = image.copy()
        
        all_texts = []
        
        # 1. Original image with optimized config for Indian documents
        print("Running OCR on original image...")
        try:
            # Best config for Indian identity documents
            original_text = pytesseract.image_to_string(
                original, 
                config=r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz/-:., ',
                lang='eng'
            )
            if original_text.strip():
                all_texts.append(f"=== ORIGINAL_OPTIMIZED ===\n{original_text}")
        except Exception as e:
            print(f"Original OCR error: {e}")
        
        # 2. Multiple preprocessing strategies
        print("Running OCR on preprocessed images...")
        
        # Strategy A: Standard preprocessing
        try:
            processed = self.preprocess_image(original)
            processed_text = pytesseract.image_to_string(
                processed, 
                config=r'--oem 3 --psm 6',
                lang='eng'
            )
            if processed_text.strip():
                all_texts.append(f"=== PREPROCESSED_STANDARD ===\n{processed_text}")
        except Exception as e:
            print(f"Standard preprocessing error: {e}")
        
        # Strategy B: High contrast preprocessing
        try:
            high_contrast = self._high_contrast_preprocess(original)
            hc_text = pytesseract.image_to_string(
                high_contrast,
                config=r'--oem 3 --psm 6',
                lang='eng'
            )
            if hc_text.strip():
                all_texts.append(f"=== HIGH_CONTRAST ===\n{hc_text}")
        except Exception as e:
            print(f"High contrast preprocessing error: {e}")
        
        # Strategy C: Morphological preprocessing
        try:
            morph_processed = self._morphological_preprocess(original)
            morph_text = pytesseract.image_to_string(
                morph_processed,
                config=r'--oem 3 --psm 6',
                lang='eng'
            )
            if morph_text.strip():
                all_texts.append(f"=== MORPHOLOGICAL ===\n{morph_text}")
        except Exception as e:
            print(f"Morphological preprocessing error: {e}")
        
        # 3. Multiple PSM modes for different document layouts
        print("Running OCR with different PSM modes...")
        psm_configs = [
            (r'--oem 3 --psm 3', 'PSM_3_FULLY_AUTO'),
            (r'--oem 3 --psm 4', 'PSM_4_SINGLE_COLUMN'),
            (r'--oem 3 --psm 6', 'PSM_6_SINGLE_BLOCK'),
            (r'--oem 3 --psm 11', 'PSM_11_SPARSE_TEXT'),
            (r'--oem 3 --psm 12', 'PSM_12_SPARSE_OSD'),
        ]
        
        for config, name in psm_configs:
            try:
                text = pytesseract.image_to_string(original, config=config, lang='eng')
                if text.strip():
                    all_texts.append(f"=== {name} ===\n{text}")
            except Exception as e:
                print(f"{name} error: {e}")
        
        # 4. Enhanced PIL processing with multiple enhancement levels
        print("Running OCR on PIL enhanced images...")
        try:
            pil_image = Image.fromarray(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
            
            # Enhancement level 1: Moderate
            enhancer = ImageEnhance.Contrast(pil_image)
            enhanced_pil = enhancer.enhance(1.3)
            enhancer = ImageEnhance.Sharpness(enhanced_pil)
            sharp_pil = enhancer.enhance(1.5)
            enhanced_array = np.array(sharp_pil)
            
            enhanced_text = pytesseract.image_to_string(
                enhanced_array, 
                config=r'--oem 3 --psm 6',
                lang='eng'
            )
            if enhanced_text.strip():
                all_texts.append(f"=== PIL_ENHANCED_MODERATE ===\n{enhanced_text}")
            
            # Enhancement level 2: Aggressive
            enhancer = ImageEnhance.Contrast(pil_image)
            enhanced_pil2 = enhancer.enhance(2.0)
            enhancer = ImageEnhance.Sharpness(enhanced_pil2)
            sharp_pil2 = enhancer.enhance(2.5)
            enhanced_array2 = np.array(sharp_pil2)
            
            enhanced_text2 = pytesseract.image_to_string(
                enhanced_array2,
                config=r'--oem 3 --psm 6',
                lang='eng'
            )
            if enhanced_text2.strip():
                all_texts.append(f"=== PIL_ENHANCED_AGGRESSIVE ===\n{enhanced_text2}")
                
        except Exception as e:
            print(f"PIL enhancement error: {e}")
        
        # 5. Specialized config for numbers (Aadhaar, PAN, DL numbers)
        print("Running OCR optimized for numbers...")
        try:
            number_text = pytesseract.image_to_string(
                original,
                config=r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ ',
                lang='eng'
            )
            if number_text.strip():
                all_texts.append(f"=== NUMBER_OPTIMIZED ===\n{number_text}")
        except Exception as e:
            print(f"Number optimization error: {e}")
        
        # Combine all results
        combined_text = "\n".join(all_texts)
        print(f"OCR processing complete. Generated {len(all_texts)} text extractions.")
        
        return combined_text, original
    
    def _high_contrast_preprocess(self, image):
        """High contrast preprocessing for better text recognition"""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply CLAHE with higher clip limit
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Apply adaptive threshold
        adaptive = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        return adaptive
    
    def _morphological_preprocess(self, image):
        """Morphological preprocessing to clean up text"""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        
        # Remove noise
        opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Fill gaps
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        return closing
    
    def detect_document_type(self, text):
        """Detect document type from extracted text"""
        text_lower = text.lower()
        
        # Aadhaar indicators
        aadhar_indicators = [
            'aadhaar', 'aadhar', 'government of india', 'भारत सरकार',
            'unique identification', 'uidai', 'आधार'
        ]
        
        # PAN indicators
        pan_indicators = [
            'permanent account number', 'income tax department', 'आयकर विभाग',
            'pan card', 'govt. of india'
        ]
        
        # DL indicators
        dl_indicators = [
            'driving licence', 'driving license', 'transport department',
            'motor vehicle', 'dl no'
        ]
        
        # Count indicators
        aadhar_score = sum(1 for indicator in aadhar_indicators if indicator in text_lower)
        pan_score = sum(1 for indicator in pan_indicators if indicator in text_lower)
        dl_score = sum(1 for indicator in dl_indicators if indicator in text_lower)
        
        # Pattern-based detection
        if re.search(r'\d{4}\s*\d{4}\s*\d{4}', text):
            aadhar_score += 1
        if re.search(r'[A-Z]{5}\d{4}[A-Z]', text):
            pan_score += 1
        
        # Determine document type
        if aadhar_score > pan_score and aadhar_score > dl_score:
            return 'AADHAR'
        elif pan_score > aadhar_score and pan_score > dl_score:
            return 'PAN'
        elif dl_score > 0:
            return 'DRIVING_LICENSE'
        
        # Fallback
        if re.search(r'\d{4}\s*\d{4}\s*\d{4}', text):
            return 'AADHAR'
        if re.search(r'[A-Z]{5}\d{4}[A-Z]', text):
            return 'PAN'
        
        return 'UNKNOWN'