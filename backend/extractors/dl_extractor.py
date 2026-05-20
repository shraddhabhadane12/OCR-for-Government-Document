import re
from collections import Counter

class DrivingLicenseExtractor:
    def extract(self, text):
        """Enhanced Driving License extraction focusing ONLY on Name, DL Number, DOB, and Blood Group"""
        result = {
            'document_type': 'DRIVING_LICENSE',
            'name': None,
            'dob': None,
            'blood_group': None,
            'dl_number': None
        }
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text_clean = ' '.join(lines)
        
        # Clean text for better extraction
        cleaned_text = self._clean_text(text_clean)
        
        # Extract ONLY the required fields with maximum accuracy
        # 1. Extract DL number (highest priority)
        result['dl_number'] = self._extract_dl_number(cleaned_text, lines)
        
        # 2. Extract DOB
        result['dob'] = self._extract_dob(cleaned_text, lines)
        
        # 3. Extract Blood Group
        result['blood_group'] = self._extract_blood_group(cleaned_text, lines)
        
        # 4. Extract Name (use all available context)
        result['name'] = self._extract_name(text, lines, result['dl_number'], result['dob'], result['blood_group'])
        
        return result
    
    def _clean_text(self, text):
        """Clean OCR text for better extraction"""
        # Fix common OCR errors
        corrections = {
            'DRIVINC': 'DRIVING',
            'LICEHCE': 'LICENCE',
            'LICEHSE': 'LICENSE',
            'TRANSPORI': 'TRANSPORT',
            'DEPARTNENT': 'DEPARTMENT',
            '0': 'O',
            '5': 'S',
            '1': 'I',
            '8': 'B',
            '6': 'G',
            '|': 'I',
        }
        
        cleaned = text
        for wrong, correct in corrections.items():
            cleaned = cleaned.replace(wrong, correct)
        
        return cleaned
    
    def _extract_dl_number(self, text, lines):
        """Ultra-precise DL number extraction with maximum accuracy"""
        candidates = []
        
        # Valid Indian state codes for DL
        valid_state_codes = [
            'AP', 'AR', 'AS', 'BR', 'CG', 'GA', 'GJ', 'HR', 'HP', 'JH', 'JK',
            'KA', 'KL', 'MP', 'MH', 'MN', 'ML', 'MZ', 'NL', 'OR', 'PB', 'RJ',
            'SK', 'TN', 'TS', 'TR', 'UP', 'UK', 'WB', 'AN', 'CH', 'DN', 'DD',
            'DL', 'LD', 'PY'
        ]
        
        # Strategy 1: Labeled patterns (highest priority)
        labeled_patterns = [
            r'(?:DL|Licence|License)\s*(?:No|Number)\s*:?\s*([A-Z]{2}[\s\-]?\d{2}[\s\-]?\d{11})',
            r'Driving\s+(?:Licence|License)\s*(?:No|Number)\s*:?\s*([A-Z]{2}[\s\-]?\d{2}[\s\-]?\d{11})',
        ]
        
        for pattern in labeled_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = self._normalize_dl_number(match)
                if normalized and self._validate_dl_format(normalized):
                    candidates.append((normalized, 25))  # Highest priority
        
        # Strategy 2: State-code based search with context validation
        for i, line in enumerate(lines):
            line_upper = line.upper()
            
            # Look for valid state codes followed by numbers
            for state_code in valid_state_codes:
                state_patterns = [
                    rf'{state_code}[\s\-]?\d{{2}}[\s\-]?\d{{11}}',  # With separators
                    rf'{state_code}\d{{13}}',  # Continuous format
                ]
                
                for pattern in state_patterns:
                    matches = re.findall(pattern, line_upper)
                    for match in matches:
                        normalized = self._normalize_dl_number(match)
                        if normalized and self._validate_dl_format(normalized):
                            # Check surrounding context
                            context_score = 10
                            context_lines = lines[max(0, i-2):i+3]
                            context_text = ' '.join(context_lines).lower()
                            
                            # Boost for DL indicators
                            if any(indicator in context_text for indicator in 
                                   ['driving', 'licence', 'license', 'dl', 'transport', 'motor']):
                                context_score = 20
                            
                            # Reduce if near other document indicators
                            if any(other in context_text for other in 
                                   ['pan', 'aadhar', 'aadhaar']):
                                context_score = max(5, context_score - 10)
                            
                            candidates.append((normalized, context_score))
        
        # Strategy 3: Enhanced OCR error correction
        ocr_corrections = {
            '0': ['O', 'Q'], '1': ['I', 'l', '|'], '5': ['S'], 
            '8': ['B'], '6': ['G'], 'O': ['0'], 'I': ['1'], 
            'S': ['5'], 'B': ['8'], 'G': ['6']
        }
        
        # Find potential DL patterns with OCR errors
        for state_code in valid_state_codes:
            # Look for patterns with potential OCR errors
            error_patterns = [
                rf'{state_code}[0-9OIlSBG]{{13}}',  # State + 13 chars with OCR errors
                rf'{state_code}[\s\-]?[0-9OIlSBG]{{2}}[\s\-]?[0-9OIlSBG]{{11}}',  # With separators
            ]
            
            for pattern in error_patterns:
                matches = re.findall(pattern, text.upper())
                for match in matches:
                    # Apply OCR corrections
                    corrected = match
                    for wrong, corrections_list in ocr_corrections.items():
                        for correct in corrections_list:
                            if wrong != correct:
                                corrected = corrected.replace(wrong, correct)
                    
                    normalized = self._normalize_dl_number(corrected)
                    if normalized and self._validate_dl_format(normalized):
                        candidates.append((normalized, 12))
        
        # Strategy 4: Position-based scoring (DL numbers often appear in specific areas)
        for i, line in enumerate(lines):
            # DL numbers often appear in the middle or bottom section
            if len(lines) // 3 <= i <= 2 * len(lines) // 3:
                # Look for 15-character alphanumeric sequences
                potential_dls = re.findall(r'[A-Z]{2}\d{13}', line.upper())
                for dl in potential_dls:
                    normalized = self._normalize_dl_number(dl)
                    if normalized and self._validate_dl_format(normalized):
                        candidates.append((normalized, 8))
        
        if candidates:
            # Calculate final scores
            dl_scores = {}
            for dl_number, score in candidates:
                if dl_number in dl_scores:
                    dl_scores[dl_number] += score
                else:
                    dl_scores[dl_number] = score
            
            # Get highest scoring DL number
            best_dl = max(dl_scores.items(), key=lambda x: x[1])[0]
            return best_dl
        
        return None
    
    def _normalize_dl_number(self, dl_text):
        """Normalize DL number format"""
        if not dl_text:
            return None
        
        # Remove spaces and hyphens
        normalized = re.sub(r'[\s-]', '', dl_text.upper())
        
        # Expected format: AA99999999999999 (2 letters + 13 digits)
        if len(normalized) == 15 and normalized[:2].isalpha() and normalized[2:].isdigit():
            return f"{normalized[:4]} {normalized[4:]}"
        
        return None
    
    def _validate_dl_format(self, dl):
        """Validate DL format"""
        if not dl:
            return False
        
        # Remove spaces for validation
        dl_clean = dl.replace(' ', '')
        
        # Should be 15 characters: 2 letters + 2 digits + 11 digits
        if len(dl_clean) != 15:
            return False
        
        # First 2: State code (letters)
        if not dl_clean[:2].isalpha():
            return False
        
        # Next 2: RTO code (digits)
        if not dl_clean[2:4].isdigit():
            return False
        
        # Last 11: License number (digits)
        if not dl_clean[4:].isdigit():
            return False
        
        return True
    
    def _extract_dob(self, text, lines):
        """Enhanced DOB extraction specifically optimized for driving licenses"""
        candidates = []
        
        # Strategy 1: Labeled patterns with enhanced DL-specific labels (highest priority)
        labeled_patterns = [
            r'Date\s+of\s+Birth\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'DOB\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'Birth\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'D\.O\.B\.\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'जन्म\s+दिनांक\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        ]
        
        for pattern in labeled_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized_date = self._normalize_date(match)
                if normalized_date and self._validate_date(normalized_date):
                    candidates.append((normalized_date, 25))
        
        # Strategy 2: Context-aware date search (look near other DL fields)
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # If line contains DOB indicators
            if any(indicator in line_lower for indicator in ['dob', 'birth', 'born', 'जन्म']):
                # Search in current and surrounding lines
                search_lines = lines[max(0, i-1):i+3]
                
                for search_line in search_lines:
                    # Look for date patterns
                    date_patterns = [
                        r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
                        r'(\d{1,2}\.\d{1,2}\.\d{4})',
                        r'(\d{1,2}\s+\d{1,2}\s+\d{4})',
                    ]
                    
                    for pattern in date_patterns:
                        matches = re.findall(pattern, search_line)
                        for match in matches:
                            normalized_date = self._normalize_date(match)
                            if normalized_date and self._validate_date(normalized_date):
                                candidates.append((normalized_date, 20))
        
        # Strategy 3: Year-only patterns (when only birth year is available)
        year_patterns = [
            r'Date\s+of\s+Birth\s*:?\s*(\d{4})',
            r'DOB\s*:?\s*(\d{4})',
            r'Birth\s*:?\s*(\d{4})',
            r'Born\s*:?\s*(\d{4})',
            r'जन्म\s*:?\s*(\d{4})',
        ]
        
        if not candidates:  # Only look for year if no full date found
            for pattern in year_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if self._validate_year(match):
                        candidates.append((match, 15))
            
            # Look for standalone years near birth indicators
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['birth', 'born', 'dob', 'जन्म']):
                    search_lines = lines[i:i+2] if i+1 < len(lines) else [line]
                    for search_line in search_lines:
                        year_matches = re.findall(r'\b(19[5-9]\d|20[0-2]\d)\b', search_line)
                        for year in year_matches:
                            if self._validate_year(year):
                                candidates.append((year, 12))
        
        # Strategy 4: Position-based search (DOB often appears in specific areas of DL)
        if not candidates:
            # Look in middle and bottom sections of the license
            middle_start = len(lines) // 3
            for i in range(middle_start, len(lines)):
                line = lines[i]
                # Look for any date-like patterns
                date_matches = re.findall(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', line)
                for match in date_matches:
                    normalized_date = self._normalize_date(match)
                    if normalized_date and self._validate_date(normalized_date):
                        candidates.append((normalized_date, 8))
        
        if candidates:
            # Sort by priority and return best candidate
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    def _normalize_date(self, date_str):
        """Normalize date format to DD/MM/YYYY"""
        if not date_str:
            return None
        
        # Replace various separators with /
        normalized = re.sub(r'[-.\s]+', '/', date_str.strip())
        
        # Ensure DD/MM/YYYY format
        parts = normalized.split('/')
        if len(parts) == 3:
            day, month, year = parts[0].zfill(2), parts[1].zfill(2), parts[2]
            return f"{day}/{month}/{year}"
        
        return normalized
    
    def _extract_blood_group(self, text, lines):
        """Ultra-precise blood group extraction with maximum accuracy"""
        candidates = []
        
        # Strategy 1: Labeled patterns (highest priority)
        labeled_patterns = [
            r'Blood\s+Group\s*:?\s*([ABO]+[+-]?)',
            r'BG\s*:?\s*([ABO]+[+-]?)',
            r'B\.G\.\s*:?\s*([ABO]+[+-]?)',
            r'Blood\s*:?\s*([ABO]+[+-]?)',
        ]
        
        for pattern in labeled_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = self._normalize_blood_group(match)
                if normalized:
                    candidates.append((normalized, 25))  # Highest priority
        
        # Strategy 2: Context-aware line search
        for i, line in enumerate(lines):
            line_upper = line.upper()
            
            # If line contains blood group indicators
            if any(indicator in line_upper for indicator in ['BLOOD', 'BG', 'B.G']):
                # Search in current and surrounding lines
                search_lines = lines[max(0, i-1):i+3]
                
                for j, search_line in enumerate(search_lines):
                    # Look for valid blood group patterns
                    bg_patterns = [
                        r'\b([ABO]+[+-])\b',
                        r'([ABO]+\s*[+-])',
                        r'([ABO]\s*[+-])',
                    ]
                    
                    for pattern in bg_patterns:
                        bg_matches = re.findall(pattern, search_line.upper())
                        for match in bg_matches:
                            normalized = self._normalize_blood_group(match)
                            if normalized:
                                # Higher score for same line as indicator
                                context_score = 20 if j == 1 else 15
                                candidates.append((normalized, context_score))
        
        # Strategy 3: Standalone blood group search with strict validation
        standalone_patterns = [
            r'\b(A\+|A-|B\+|B-|AB\+|AB-|O\+|O-)\b',  # Exact matches
            r'\b(A\s*\+|A\s*-|B\s*\+|B\s*-|AB\s*\+|AB\s*-|O\s*\+|O\s*-)\b',  # With spaces
        ]
        
        for pattern in standalone_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = self._normalize_blood_group(match)
                if normalized:
                    candidates.append((normalized, 12))
        
        # Strategy 4: Enhanced OCR error correction
        ocr_corrections = {
            'A*': 'A+', 'A#': 'A+', 'A_': 'A-',
            'B*': 'B+', 'B#': 'B+', 'B_': 'B-', '8+': 'B+', '8-': 'B-',
            'AB*': 'AB+', 'AB#': 'AB+', 'AB_': 'AB-', 'A8+': 'AB+', 'A8-': 'AB-',
            'O*': 'O+', 'O#': 'O+', 'O_': 'O-', '0+': 'O+', '0-': 'O-',
        }
        
        # Search for OCR error patterns
        for error_pattern, correct_bg in ocr_corrections.items():
            if error_pattern in text.upper():
                candidates.append((correct_bg, 10))
        
        # Strategy 5: Character-by-character reconstruction
        char_patterns = [
            r'([ABO8])\s*([+\-*#_])',  # Letter/8 followed by sign/symbol
            r'([ABO8]{1,2})\s*([+\-*#_])',  # 1-2 letters followed by sign
        ]
        
        for pattern in char_patterns:
            matches = re.findall(pattern, text.upper())
            for letter_part, sign_part in matches:
                # Convert OCR errors
                if letter_part == '8':
                    letter_part = 'B'
                
                # Convert sign errors
                if sign_part in ['*', '#']:
                    sign_part = '+'
                elif sign_part == '_':
                    sign_part = '-'
                
                combined = letter_part + sign_part
                normalized = self._normalize_blood_group(combined)
                if normalized:
                    candidates.append((normalized, 8))
        
        # Strategy 6: Position-based search (blood group often appears in specific areas)
        for i, line in enumerate(lines):
            # Blood group often appears in the middle or bottom section of DL
            if len(lines) // 2 <= i <= len(lines):
                # Look for isolated blood group patterns
                isolated_patterns = [
                    r'\b([ABO]+[+-])\b',
                    r'([ABO8][+\-*#_])',
                ]
                
                for pattern in isolated_patterns:
                    matches = re.findall(pattern, line.upper())
                    for match in matches:
                        normalized = self._normalize_blood_group(match)
                        if normalized:
                            candidates.append((normalized, 6))
        
        if candidates:
            # Calculate final scores
            bg_scores = {}
            for bg, score in candidates:
                if bg in bg_scores:
                    bg_scores[bg] += score
                else:
                    bg_scores[bg] = score
            
            # Get highest scoring blood group
            best_bg = max(bg_scores.items(), key=lambda x: x[1])[0]
            return best_bg
        
        return None
    
    def _normalize_blood_group(self, bg_text):
        """Normalize blood group format with enhanced validation"""
        if not bg_text:
            return None
        
        # Clean the input
        bg_clean = bg_text.upper().strip().replace(' ', '')
        
        # Valid blood groups
        valid_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        
        # Direct match
        if bg_clean in valid_groups:
            return bg_clean
        
        # Handle common OCR errors and variations
        corrections = {
            'A*': 'A+', 'A#': 'A+', 'A_': 'A-',
            'B*': 'B+', 'B#': 'B+', 'B_': 'B-', '8+': 'B+', '8-': 'B-',
            'AB*': 'AB+', 'AB#': 'AB+', 'AB_': 'AB-', 'A8+': 'AB+', 'A8-': 'AB-',
            'O*': 'O+', 'O#': 'O+', 'O_': 'O-', '0+': 'O+', '0-': 'O-',
        }
        
        if bg_clean in corrections:
            return corrections[bg_clean]
        
        # Try to construct valid blood group from components
        if len(bg_clean) >= 1:
            letter_part = ''
            sign_part = ''
            
            # Extract letter part
            if bg_clean.startswith('AB'):
                letter_part = 'AB'
                remaining = bg_clean[2:]
            elif bg_clean.startswith('A'):
                letter_part = 'A'
                remaining = bg_clean[1:]
            elif bg_clean.startswith('B') or bg_clean.startswith('8'):
                letter_part = 'B'
                remaining = bg_clean[1:]
            elif bg_clean.startswith('O') or bg_clean.startswith('0'):
                letter_part = 'O'
                remaining = bg_clean[1:]
            
            # Extract sign part
            if remaining:
                if '+' in remaining or '*' in remaining or '#' in remaining:
                    sign_part = '+'
                elif '-' in remaining or '_' in remaining:
                    sign_part = '-'
            
            # Construct blood group
            if letter_part and sign_part:
                constructed = letter_part + sign_part
                if constructed in valid_groups:
                    return constructed
            
            # If no sign found, assume positive for valid letters
            if letter_part in ['A', 'B', 'AB', 'O'] and not sign_part:
                return letter_part + '+'
        
        return None
    
    def _validate_date(self, date_str):
        """Simple date validation"""
        try:
            parts = date_str.split('/')
            if len(parts) != 3:
                return False
            
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            
            # Basic range validation
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1920 <= year <= 2050):
                return False
            
            # Month-specific validation
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
    
    def _extract_name(self, text, lines, dl_number, dob, blood_group):
        """Enhanced name extraction for Driving License - look for 'Name:' label"""
        candidates = []
        
        # Strategy 1: Look for explicit "Name:" label (highest priority for DL)
        name_label_patterns = [
            r'Name\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'Name\s*:?\s*([A-Z]{2,}(?:\s+[A-Z]{2,})*)',
            r'नाम\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in name_label_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._validate_name(match):
                    candidates.append((match, 30))  # Highest priority for labeled names
        
        # Strategy 2: Line-by-line search for "Name:" followed by name
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if 'name' in line_lower and ':' in line:
                # Extract text after "Name:"
                name_match = re.search(r'name\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', line, re.IGNORECASE)
                if name_match:
                    potential_name = name_match.group(1).strip()
                    if self._validate_name(potential_name):
                        candidates.append((potential_name, 25))
                
                # Also check next line in case name is on separate line
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if self._validate_name(next_line) and not re.search(r'\d', next_line):
                        candidates.append((next_line, 22))
        
        # Strategy 3: Position-based extraction with DL-specific positioning
        for i, line in enumerate(lines[:25]):  # Check more lines for DL
            if self._is_header_line(line):
                continue
            
            # Skip lines with numbers, dates, or technical info
            if (re.search(r'\d', line) or 
                any(tech in line.lower() for tech in ['class', 'category', 'cov', 'issue', 'valid', 'blood', 'group'])):
                continue
                
            words = line.split()
            if 2 <= len(words) <= 5:  # Names can be 2-5 words in DL
                if self._validate_name(line):
                    # Higher score for positions 3-15 (typical name area in DL)
                    if 3 <= i <= 15:
                        position_score = 15
                    elif i <= 25:
                        position_score = max(5, 25 - i)
                    else:
                        position_score = 5
                    candidates.append((line.strip(), position_score))
        
        # Strategy 2: Enhanced context-based extraction
        context_boost_lines = []
        
        # Find lines near DL number (names usually appear well before DL number)
        if dl_number:
            dl_clean = dl_number.replace(' ', '')
            for i, line in enumerate(lines):
                if dl_clean in line.replace(' ', ''):
                    # Names usually appear 5-15 lines before DL number in DL cards
                    context_boost_lines.extend(range(max(0, i-15), max(0, i-5)))
        
        # Find lines near DOB (names usually appear before DOB)
        if dob:
            dob_parts = dob.split('/') if '/' in dob else [dob]
            for i, line in enumerate(lines):
                if any(part in line for part in dob_parts):
                    # Names usually appear 2-10 lines before DOB
                    context_boost_lines.extend(range(max(0, i-10), i))
        
        # Find lines near blood group (names appear well before blood group)
        if blood_group:
            for i, line in enumerate(lines):
                if blood_group in line.upper():
                    # Names usually appear 3-12 lines before blood group
                    context_boost_lines.extend(range(max(0, i-12), max(0, i-3)))
        
        # Apply context boost with enhanced validation
        for line_idx in set(context_boost_lines):
            if line_idx < len(lines):
                potential = lines[line_idx].strip()
                if (self._validate_dl_name(potential) and 
                    not re.search(r'\d', potential) and
                    not any(tech in potential.lower() for tech in ['class', 'category', 'blood', 'group', 'dob'])):
                    candidates.append((potential, 22))
        
        # Strategy 3: Pattern-based extraction with DL-specific patterns
        name_patterns = [
            r'([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?(?:\s+[A-Z][a-z]{2,})?)',  # Title case 2-4 words
            r'([A-Z]{3,}\s+[A-Z]{3,}(?:\s+[A-Z]{3,})?(?:\s+[A-Z]{3,})?)',  # All caps 2-4 words
            r'([A-Z][A-Z\s]{10,40})',  # All caps name patterns common in DL
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if (self._validate_dl_name(match) and 
                    not re.search(r'\d', match) and
                    not any(tech in match.lower() for tech in ['driving', 'licence', 'license', 'transport'])):
                    candidates.append((match, 15))
        
        # Strategy 4: Look for names in DL-specific "sweet spots"
        # Names in DL typically appear in lines 3-18
        for i in range(3, min(18, len(lines))):
            line = lines[i].strip()
            if (self._validate_dl_name(line) and 
                not self._is_header_line(line) and
                not re.search(r'\d', line) and
                not any(tech in line.lower() for tech in ['class', 'category', 'blood', 'group', 'dob', 'issue', 'valid'])):
                candidates.append((line, 18))
        
        # Strategy 5: Enhanced exclusion of non-name lines
        exclude_keywords = [
            'driving', 'licence', 'license', 'transport', 'department', 'motor', 'vehicle',
            'blood', 'group', 'dob', 'birth', 'date', 'issue', 'valid', 'class', 'category',
            'cov', 'mcwg', 'mcwog', 'lmv', 'hmv', 'psv', 'government', 'india', 'state'
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            # Skip lines containing exclude keywords
            if any(keyword in line_lower for keyword in exclude_keywords):
                continue
            
            # Check lines that appear before demographic/technical info
            if i > 0 and i < len(lines) - 1:
                next_line = lines[i + 1].lower()
                if any(keyword in next_line for keyword in ['dob', 'birth', 'blood', 'class']):
                    if (self._validate_dl_name(line) and 
                        not re.search(r'\d', line)):
                        candidates.append((line.strip(), 16))
        
        if candidates:
            # Calculate final scores with enhanced DL-specific scoring
            name_scores = {}
            for name, score in candidates:
                cleaned_name = name.strip().title()
                if cleaned_name in name_scores:
                    name_scores[cleaned_name] += score
                else:
                    name_scores[cleaned_name] = score
                
                # Add DL-specific quality bonus
                name_scores[cleaned_name] += self._score_dl_name_quality(cleaned_name)
            
            # Get highest scoring name
            best_name = max(name_scores.items(), key=lambda x: x[1])[0]
            return best_name
        
        return None
    
    def _validate_dl_name(self, name):
        """Enhanced name validation specifically for driving licenses"""
        if not name or len(name) < 3 or len(name) > 80:  # DL names can be longer
            return False
        
        # Exclude DL-specific false positives
        exclude_words = [
            'driving', 'licence', 'license', 'transport', 'department', 'motor', 'vehicle',
            'blood', 'group', 'date', 'birth', 'issue', 'validity', 'class', 'category',
            'cov', 'mcwg', 'mcwog', 'lmv', 'hmv', 'psv', 'government', 'india', 'state',
            'rto', 'office', 'authority', 'endorsement', 'restriction'
        ]
        
        name_lower = name.lower()
        if any(word in name_lower for word in exclude_words):
            return False
        
        # Must have at least 2 words for full names
        words = name.split()
        if len(words) < 2:
            return False
        
        # Each word validation with DL-specific rules
        for word in words:
            if len(word) < 2:
                return False
            # Allow some numbers in names (like Jr., Sr., II, etc.) but not too many
            if not re.match(r'^[A-Za-z][A-Za-z\s]*[A-Za-z]$', word) and word not in ['Jr', 'Sr', 'II', 'III']:
                return False
        
        # Check for DL number patterns
        if re.search(r'[A-Z]{2}\d{2}\s?\d{11}', name):
            return False
        
        # Check for blood group patterns
        if re.search(r'\b[ABO]+[+-]\b', name.upper()):
            return False
        
        return True
    
    def _score_dl_name_quality(self, name):
        """Enhanced name quality scoring for driving licenses"""
        score = 0
        words = name.split()
        
        # Prefer 2-4 words (common in Indian names on DL)
        if 2 <= len(words) <= 4:
            score += 20
        elif len(words) == 5:
            score += 10  # Some names can be 5 words
        
        # Prefer title case (most common in DL)
        if all(w.istitle() for w in words):
            score += 25
        elif all(w.isupper() for w in words):
            score += 15  # All caps also common in DL
        
        # Prefer reasonable word lengths
        avg_length = sum(len(w) for w in words) / len(words)
        if 3 <= avg_length <= 10:
            score += 15
        
        # Prefer names without numbers or special chars
        if name.replace(' ', '').isalpha():
            score += 10
        
        # Bonus for common Indian name patterns
        indian_indicators = ['kumar', 'singh', 'sharma', 'patel', 'gupta', 'agarwal', 'jain', 'shah', 'reddy', 'rao', 'das', 'devi', 'kumari']
        if any(indicator in name.lower() for indicator in indian_indicators):
            score += 8
        
        # Penalty for very long names (might be address or other info)
        if len(name) > 50:
            score -= 10
        
        return score
    

    
    def _validate_name(self, name):
        """Validate name quality"""
        if not name or len(name) < 3 or len(name) > 60:
            return False
        
        # Exclude common false positives
        exclude_words = [
            'driving', 'licence', 'license', 'transport', 'department', 'motor',
            'vehicle', 'blood', 'group', 'date', 'birth', 'issue', 'validity'
        ]
        
        name_lower = name.lower()
        if any(word in name_lower for word in exclude_words):
            return False
        
        # Must have at least 2 words
        words = name.split()
        if len(words) < 2:
            return False
        
        # Each word validation
        for word in words:
            if len(word) < 2 or not word.replace(' ', '').isalpha():
                return False
        
        return True
    
    def _score_name_quality(self, name):
        """Score name quality for ranking"""
        score = 0
        words = name.split()
        
        # Prefer 2-4 words
        if 2 <= len(words) <= 4:
            score += 15
        
        # Prefer title case
        if all(w.istitle() for w in words):
            score += 20
        elif all(w.isupper() for w in words):
            score += 10
        
        # Prefer reasonable word lengths
        avg_length = sum(len(w) for w in words) / len(words)
        if 3 <= avg_length <= 10:
            score += 10
        
        # Prefer names without numbers or special chars
        if name.replace(' ', '').isalpha():
            score += 10
        
        return score
    

    
    def _is_header_line(self, line):
        """Check if line is a header/label"""
        header_keywords = [
            'driving', 'licence', 'license', 'transport', 'department', 'motor',
            'vehicle', 'government', 'india', 'state'
        ]
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in header_keywords)