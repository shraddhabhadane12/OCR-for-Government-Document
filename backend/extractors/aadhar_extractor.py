import re
from datetime import datetime
from collections import Counter

class AadharExtractor:
    def extract(self, text):
        """Enhanced Aadhaar extraction focusing ONLY on Name, Gender, Aadhaar Number, and DOB"""
        result = {
            'document_type': 'AADHAR',
            'name': None,
            'dob': None,
            'gender': None,
            'aadhar_number': None
        }
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text_clean = ' '.join(lines)
        
        # Clean text for better extraction
        cleaned_text = self._clean_text(text_clean)
        
        # Extract ONLY the required fields with maximum accuracy
        # 1. Extract Aadhaar number (highest priority)
        result['aadhar_number'] = self._extract_aadhar_number(cleaned_text, lines)
        
        # 2. Extract DOB
        result['dob'] = self._extract_dob(cleaned_text, lines)
        
        # 3. Extract Gender
        result['gender'] = self._extract_gender(cleaned_text, lines)
        
        # 4. Extract Name (use all available context)
        result['name'] = self._extract_name(text, lines, result['aadhar_number'], result['gender'], result['dob'])
        
        return result
    
    def _clean_text(self, text):
        """Clean OCR text for better extraction"""
        # Fix common OCR errors
        corrections = {
            'Femala': 'Female',
            'Femal': 'Female',
            'Fernale': 'Female',
            'Femaie': 'Female',
            'Mala': 'Male',
            'Maie': 'Male',
            'Wale': 'Male',
            'Govemment': 'Government',
            'lndia': 'India',
            '|': 'I',
            '0': 'O',
            '5': 'S',
        }
        
        cleaned = text
        for wrong, correct in corrections.items():
            cleaned = cleaned.replace(wrong, correct)
        
        return cleaned
    
    def _extract_aadhar_number(self, text, lines):
        """Ultra-precise Aadhaar number extraction with maximum accuracy"""
        candidates = []
        
        # Strategy 1: Labeled patterns (highest priority)
        labeled_patterns = [
            r'Aadhaar\s*(?:No|Number|संख्या|नंबर)\s*:?\s*(\d{4}[\s\-\.]*\d{4}[\s\-\.]*\d{4})',
            r'आधार\s*(?:संख्या|नंबर)\s*:?\s*(\d{4}[\s\-\.]*\d{4}[\s\-\.]*\d{4})',
            r'UID\s*(?:No|Number)\s*:?\s*(\d{4}[\s\-\.]*\d{4}[\s\-\.]*\d{4})',
        ]
        
        for pattern in labeled_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                digits = re.sub(r'\D', '', match)
                if self._validate_aadhar_number(digits):
                    candidates.append((digits, 20))  # Highest priority
        
        # Strategy 2: Context-aware line search
        for i, line in enumerate(lines):
            # Look for 12-digit sequences in lines with Aadhaar context
            digit_sequences = re.findall(r'\d{4}[\s\-\.]*\d{4}[\s\-\.]*\d{4}|\d{12}', line)
            for seq in digit_sequences:
                digits = re.sub(r'\D', '', seq)
                if len(digits) == 12 and self._validate_aadhar_number(digits):
                    # Check surrounding context
                    context_score = 5
                    context_lines = lines[max(0, i-3):i+4]
                    context_text = ' '.join(context_lines).lower()
                    
                    # Boost score for Aadhaar indicators
                    if any(indicator in context_text for indicator in 
                           ['aadhaar', 'aadhar', 'आधार', 'government', 'uidai', 'unique']):
                        context_score = 15
                    
                    # Reduce score if near other numbers (dates, phone numbers)
                    if any(pattern in context_text for pattern in 
                           ['mobile', 'phone', 'dob', 'birth', 'pin']):
                        context_score = max(1, context_score - 5)
                    
                    candidates.append((digits, context_score))
        
        # Strategy 3: OCR error correction with validation
        ocr_corrections = {
            'O': '0', 'o': '0', 'Q': '0',
            'l': '1', 'I': '1', '|': '1',
            'S': '5', 's': '5',
            'G': '6', 'g': '6',
            'B': '8', 'b': '8'
        }
        
        # Find potential Aadhaar patterns with OCR errors
        ocr_patterns = [
            r'([0-9OolILSGBgb]{4}[\s\-\.]*[0-9OolILSGBgb]{4}[\s\-\.]*[0-9OolILSGBgb]{4})',
            r'([0-9OolILSGBgb]{12})'
        ]
        
        for pattern in ocr_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Apply OCR corrections
                corrected = match
                for wrong, correct in ocr_corrections.items():
                    corrected = corrected.replace(wrong, correct)
                
                digits = re.sub(r'\D', '', corrected)
                if len(digits) == 12 and self._validate_aadhar_number(digits):
                    candidates.append((digits, 8))
        
        # Strategy 4: Position-based scoring (Aadhaar usually appears in specific areas)
        for i, line in enumerate(lines):
            # Aadhaar numbers often appear in the bottom half of the card
            if i > len(lines) // 2:
                digit_sequences = re.findall(r'\d{12}', line)
                for seq in digit_sequences:
                    if self._validate_aadhar_number(seq):
                        candidates.append((seq, 3))
        
        if candidates:
            # Calculate final scores and select best candidate
            number_scores = {}
            for number, score in candidates:
                if number in number_scores:
                    number_scores[number] += score
                else:
                    number_scores[number] = score
            
            # Get highest scoring Aadhaar number
            best_number = max(number_scores.items(), key=lambda x: x[1])[0]
            return f"{best_number[0:4]} {best_number[4:8]} {best_number[8:12]}"
        
        return None
    
    def _validate_aadhar_number(self, number):
        """Simple Aadhaar validation"""
        if len(number) != 12:
            return False
        
        if not number.isdigit():
            return False
        
        # Cannot start with 0 or 1
        if number[0] in ['0', '1']:
            return False
        
        # Check for obvious invalid patterns
        if number == '000000000000' or number == '111111111111':
            return False
        
        # Must have at least 3 unique digits
        if len(set(number)) < 3:
            return False
        
        return True
    
    def _extract_dob(self, text, lines):
        """Extract DOB with multiple patterns including year-only cases"""
        # Full date patterns (highest priority) - XX/XX/XXXX format
        full_date_patterns = [
            r'जन्म\s+तिथि\s*/\s*DOB\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'Date\s+of\s+Birth\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'DOB\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'Birth\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})'
        ]
        
        # Year-only patterns (when only birth year is available)
        year_only_patterns = [
            r'जन्म\s+तिथि\s*/\s*DOB\s*:?\s*(\d{4})',
            r'Date\s+of\s+Birth\s*:?\s*(\d{4})',
            r'DOB\s*:?\s*(\d{4})',
            r'Birth\s*:?\s*(\d{4})',
            r'Year\s+of\s+Birth\s*:?\s*(\d{4})',
            r'Born\s*:?\s*(\d{4})',
        ]
        
        candidates = []
        
        # First try to find full dates with enhanced Aadhaar-specific patterns
        for pattern in full_date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized_date = self._normalize_date_format(match.replace('-', '/'))
                if self._validate_date(normalized_date):
                    candidates.append((normalized_date, 25))  # High priority for full dates
        
        # Enhanced strategy for Aadhaar cards - look for complete dates in various formats
        aadhaar_date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # Any DD/MM/YYYY or D/M/YYYY format
            r'(\d{1,2}\.\d{1,2}\.\d{4})',      # DD.MM.YYYY format
            r'(\d{1,2}\s+\d{1,2}\s+\d{4})',   # DD MM YYYY format
        ]
        
        # Search for complete dates in context of birth-related keywords
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['dob', 'birth', 'जन्म', 'तिथि']):
                # Check current and next 2 lines for date patterns
                search_lines = lines[i:i+3] if i+2 < len(lines) else lines[i:]
                for search_line in search_lines:
                    for pattern in aadhaar_date_patterns:
                        date_matches = re.findall(pattern, search_line)
                        for date_match in date_matches:
                            normalized_date = self._normalize_date_format(date_match.replace('-', '/').replace('.', '/').replace(' ', '/'))
                            if self._validate_date(normalized_date):
                                candidates.append((normalized_date, 30))  # Highest priority for contextual dates
        
        # Search for standalone complete dates (without labels) - higher priority than years
        if not candidates:
            standalone_date_patterns = [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',  # Complete dates
                r'\b(\d{1,2}\.\d{1,2}\.\d{4})\b',      # Dot separated dates
            ]
            
            for pattern in standalone_date_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    normalized_date = self._normalize_date_format(match.replace('-', '/').replace('.', '/'))
                    if self._validate_date(normalized_date):
                        candidates.append((normalized_date, 18))  # High priority for standalone complete dates
        
        # Only if no complete dates found, look for year-only as fallback
        if not candidates:
            for pattern in year_only_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if self._validate_year(match):
                        candidates.append((match, 10))  # Medium priority for year-only
            
            # Also look for standalone 4-digit years in context (lowest priority)
            if not candidates:  # Only if no labeled years found
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ['birth', 'born', 'dob', 'जन्म']):
                        # Look for 4-digit years in current and next lines
                        search_lines = lines[i:i+2] if i+1 < len(lines) else [line]
                        for search_line in search_lines:
                            year_matches = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', search_line)
                            for year in year_matches:
                                if self._validate_year(year):
                                    candidates.append((year, 5))  # Lowest priority
        
        if candidates:
            # Sort by priority and return best candidate
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    def _validate_date(self, date_str):
        """Simple date validation"""
        try:
            parts = date_str.split('/')
            if len(parts) != 3:
                return False
            
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            
            # Basic range validation
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1920 <= year <= 2025):
                return False
            
            # Month-specific day validation
            days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            if day > days_in_month[month - 1]:
                return False
            
            return True
        except:
            return False
    
    def _validate_year(self, year_str):
        """Validate year for year-only DOB"""
        try:
            year = int(year_str)
            # Valid birth year range
            return 1920 <= year <= 2025
        except:
            return False
    
    def _normalize_date_format(self, date_str):
        """Normalize date to XX/XX/XXXX format"""
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = parts
                # Ensure day and month are 2 digits
                day = day.zfill(2)
                month = month.zfill(2)
                return f"{day}/{month}/{year}"
            return date_str
        except:
            return date_str
    
    def _extract_gender(self, text, lines):
        """Ultra-precise gender extraction with maximum accuracy"""
        candidates = []
        
        # Strategy 1: Labeled patterns (highest priority)
        labeled_patterns = [
            r'लिंग\s*/\s*Gender\s*:?\s*(Male|Female|MALE|FEMALE|पुरुष|महिला)',
            r'Gender\s*:?\s*(Male|Female|MALE|FEMALE)',
            r'Sex\s*:?\s*(Male|Female|MALE|FEMALE)',
            r'लिंग\s*:?\s*(पुरुष|महिला|Male|Female)',
        ]
        
        for pattern in labeled_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                gender = self._normalize_gender(match.group(1))
                if gender:
                    candidates.append((gender, 25))  # Highest priority
        
        # Strategy 2: Context-aware line search
        for i, line in enumerate(lines):
            line_upper = line.upper()
            
            # Look for gender words in lines with demographic context
            if any(keyword in line_upper for keyword in ['DOB', 'BIRTH', 'जन्म', 'DATE']):
                # Check current and surrounding lines
                search_lines = lines[max(0, i-2):i+3]
                for search_line in search_lines:
                    for gender_word in ['MALE', 'FEMALE', 'पुरुष', 'महिला']:
                        if gender_word in search_line.upper():
                            normalized = self._normalize_gender(gender_word)
                            if normalized:
                                candidates.append((normalized, 20))
        
        # Strategy 3: Standalone gender words with validation
        standalone_patterns = [
            r'\b(MALE|FEMALE|Male|Female)\b',
            r'\b(पुरुष|महिला)\b',
        ]
        
        for pattern in standalone_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = self._normalize_gender(match)
                if normalized:
                    candidates.append((normalized, 15))
        
        # Strategy 4: OCR error correction for gender
        ocr_gender_corrections = {
            'FEMALA': 'FEMALE', 'FEMAL': 'FEMALE', 'FERNALE': 'FEMALE',
            'FEMAIE': 'FEMALE', 'WEMALE': 'FEMALE', 'PEMALE': 'FEMALE',
            'MALA': 'MALE', 'MAIE': 'MALE', 'WALE': 'MALE', 'NALE': 'MALE'
        }
        
        for wrong, correct in ocr_gender_corrections.items():
            if wrong in text.upper():
                normalized = self._normalize_gender(correct)
                if normalized:
                    candidates.append((normalized, 12))
        
        # Strategy 5: Single letter gender indicators (with strict context)
        single_letter_patterns = [
            r'\b(M|F)\b(?=\s|$)',  # Single letter followed by space or end
        ]
        
        for pattern in single_letter_patterns:
            matches = re.findall(pattern, text.upper())
            for match in matches:
                # Only accept single letters if they appear near other demographic info
                context_found = False
                for line in lines:
                    if (match in line.upper() and 
                        any(keyword in line.upper() for keyword in ['DOB', 'BIRTH', 'DATE', 'GENDER', 'लिंग'])):
                        context_found = True
                        break
                
                if context_found:
                    normalized = self._normalize_gender(match)
                    if normalized:
                        candidates.append((normalized, 8))
        
        if candidates:
            # Calculate final scores
            gender_scores = {}
            for gender, score in candidates:
                if gender in gender_scores:
                    gender_scores[gender] += score
                else:
                    gender_scores[gender] = score
            
            # Get highest scoring gender
            best_gender = max(gender_scores.items(), key=lambda x: x[1])[0]
            return best_gender
        
        return None
    
    def _normalize_gender(self, gender_text):
        """Normalize gender text to standard format"""
        if not gender_text:
            return None
        
        gender_upper = gender_text.upper().strip()
        
        # Female indicators
        if any(indicator in gender_upper for indicator in ['FEMALE', 'महिला', 'F']):
            # Make sure it's not part of another word
            if gender_upper in ['FEMALE', 'महिला', 'F']:
                return 'Female'
        
        # Male indicators  
        if any(indicator in gender_upper for indicator in ['MALE', 'पुरुष', 'M']):
            # Make sure it's not FEMALE
            if 'FEMALE' not in gender_upper and gender_upper in ['MALE', 'पुरुष', 'M']:
                return 'Male'
        
        return None
    
    def _extract_name(self, text, lines, aadhar_number, gender, dob):
        """Ultra-precise name extraction using all available context"""
        candidates = []
        
        # Strategy 1: Position-based extraction with enhanced filtering
        for i, line in enumerate(lines[:25]):  # Check first 25 lines
            if self._is_header_line(line) or self._is_demographic_line(line):
                continue
            
            # Skip lines with numbers (likely not names)
            if re.search(r'\d', line):
                continue
                
            words = line.split()
            if 2 <= len(words) <= 4:  # Names typically 2-4 words
                if self._validate_name(line):
                    # Higher score for earlier positions (names appear early)
                    position_score = max(5, 25 - i)
                    candidates.append((line.strip(), position_score))
        
        # Strategy 2: Context-based extraction near known fields
        context_boost_lines = []
        
        # Find lines near Aadhaar number
        if aadhar_number:
            aadhar_digits = aadhar_number.replace(' ', '')
            for i, line in enumerate(lines):
                if aadhar_digits in line.replace(' ', ''):
                    # Names usually appear 3-15 lines before Aadhaar number
                    context_boost_lines.extend(range(max(0, i-15), i))
        
        # Find lines near gender
        if gender:
            for i, line in enumerate(lines):
                if gender.lower() in line.lower():
                    # Names usually appear 1-8 lines before gender
                    context_boost_lines.extend(range(max(0, i-8), i))
        
        # Find lines near DOB
        if dob:
            for i, line in enumerate(lines):
                if any(date_part in line for date_part in dob.split('/')):
                    # Names usually appear 1-10 lines before DOB
                    context_boost_lines.extend(range(max(0, i-10), i))
        
        # Apply context boost
        for line_idx in set(context_boost_lines):
            if line_idx < len(lines):
                potential = lines[line_idx].strip()
                if self._validate_name(potential):
                    candidates.append((potential, 18))  # High context score
        
        # Strategy 3: Pattern-based extraction with strict validation
        name_patterns = [
            r'([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)',  # Title case
            r'([A-Z]{3,}\s+[A-Z]{3,}(?:\s+[A-Z]{3,})?)',  # All caps
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if self._validate_name(match) and not re.search(r'\d', match):
                    candidates.append((match, 12))
        
        # Strategy 4: Exclude lines with demographic info but keep nearby names
        demographic_keywords = ['male', 'female', 'dob', 'birth', 'gender', 'लिंग', 'जन्म']
        for i, line in enumerate(lines):
            line_lower = line.lower()
            # Skip lines containing demographic keywords
            if any(keyword in line_lower for keyword in demographic_keywords):
                continue
            
            # But check lines just before demographic info
            if i > 0 and i < len(lines) - 1:
                next_line = lines[i + 1].lower()
                if any(keyword in next_line for keyword in demographic_keywords):
                    if self._validate_name(line):
                        candidates.append((line.strip(), 15))
        
        # Strategy 5: Look for names in the "sweet spot" (lines 2-12, avoiding headers)
        for i in range(2, min(12, len(lines))):
            line = lines[i].strip()
            if (self._validate_name(line) and 
                not self._is_header_line(line) and 
                not self._is_demographic_line(line) and
                not re.search(r'\d', line)):
                candidates.append((line, 14))
        
        if candidates:
            # Calculate final scores with enhanced quality metrics
            name_scores = {}
            for name, score in candidates:
                cleaned_name = name.strip().title()
                if cleaned_name in name_scores:
                    name_scores[cleaned_name] += score
                else:
                    name_scores[cleaned_name] = score
                
                # Add comprehensive quality bonus
                quality_score = self._score_name_quality(cleaned_name)
                name_scores[cleaned_name] += quality_score
                
                # Bonus for common Indian name patterns
                if self._is_indian_name_pattern(cleaned_name):
                    name_scores[cleaned_name] += 5
            
            # Get highest scoring name
            best_name = max(name_scores.items(), key=lambda x: x[1])[0]
            return best_name
        
        return None
    
    def _validate_name(self, name):
        """Validate name quality"""
        if not name or len(name) < 5 or len(name) > 50:
            return False
        
        # Exclude common false positives
        exclude_words = [
            'government', 'india', 'aadhaar', 'aadhar', 'male', 'female',
            'date', 'birth', 'issue', 'dob', 'year', 'address', 'permanent',
            'resident', 'card', 'number', 'unique', 'identification'
        ]
        
        name_lower = name.lower()
        if any(word in name_lower for word in exclude_words):
            return False
        
        # Must have at least 2 words
        words = name.split()
        if len(words) < 2:
            return False
        
        # Each word should be mostly alphabetic
        for word in words:
            if not word.replace(' ', '').isalpha():
                return False
            if len(word) < 2:
                return False
        
        # Check for Aadhaar number pattern
        if re.search(r'\d{4}\s*\d{4}\s*\d{4}', name):
            return False
        
        return True
    
    def _score_name_quality(self, name):
        """Score name quality for ranking"""
        score = 0
        words = name.split()
        
        # Prefer 2-4 words
        if 2 <= len(words) <= 4:
            score += 10
        
        # Prefer title case
        if all(w.istitle() for w in words):
            score += 15
        elif all(w.isupper() for w in words):
            score += 10
        
        # Prefer reasonable word lengths
        avg_length = sum(len(w) for w in words) / len(words)
        if 3 <= avg_length <= 8:
            score += 10
        
        # Prefer names without numbers or special chars
        if name.replace(' ', '').isalpha():
            score += 5
        
        return score
    
    def _is_indian_name_pattern(self, name):
        """Check if name follows common Indian naming patterns"""
        words = name.split()
        if len(words) < 2:
            return False
        
        # Common Indian name endings and patterns
        indian_endings = ['kumar', 'singh', 'sharma', 'gupta', 'agarwal', 'jain', 'shah', 'patel', 'reddy', 'rao', 'das', 'devi', 'kumari']
        
        for word in words:
            if word.lower() in indian_endings:
                return True
        
        # Check for balanced word lengths (typical of Indian names)
        avg_length = sum(len(w) for w in words) / len(words)
        return 3 <= avg_length <= 8
    
    def _is_header_line(self, line):
        """Check if line is a header/label"""
        header_keywords = [
            'government', 'india', 'aadhaar', 'aadhar', 'issue', 'date',
            'unique', 'identification', 'authority', 'भारत', 'सरकार',
            'uidai', 'enrollment', 'update'
        ]
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in header_keywords)
    
    def _is_demographic_line(self, line):
        """Check if line contains demographic information"""
        demographic_keywords = [
            'male', 'female', 'dob', 'birth', 'gender', 'लिंग', 'जन्म',
            'year', 'age', 'address', 'pin', 'mobile', 'email'
        ]
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in demographic_keywords)