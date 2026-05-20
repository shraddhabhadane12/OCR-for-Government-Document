import re
from collections import Counter

class PANExtractor:
    def extract(self, text):
        """Enhanced PAN card extraction focusing ONLY on Name, Father's Name, DOB, and PAN Number"""
        result = {
            'document_type': 'PAN',
            'name': None,
            'fathers_name': None,
            'dob': None,
            'pan_number': None
        }
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text_clean = ' '.join(lines)
        
        # Clean text for better extraction
        cleaned_text = self._clean_text(text_clean)
        
        # Extract ONLY the required fields with maximum accuracy
        # 1. Extract PAN number (highest priority)
        result['pan_number'] = self._extract_pan_number(cleaned_text, lines)
        
        # 2. Extract DOB
        result['dob'] = self._extract_dob(cleaned_text, lines)
        
        # 3. Extract Name
        result['name'] = self._extract_name(text, lines, result['pan_number'], result['dob'])
        
        # 4. Extract Father's Name (use all available context)
        result['fathers_name'] = self._extract_fathers_name(text, lines, result['name'], result['pan_number'], result['dob'])
        
        return result
    
    def _clean_text(self, text):
        """Clean OCR text for better extraction"""
        # Fix common OCR errors
        corrections = {
            'PERNIANENT': 'PERMANENT',
            'ACCOUHT': 'ACCOUNT',
            'HUMBER': 'NUMBER',
            'INCONE': 'INCOME',
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
    
    def _extract_pan_number(self, text, lines):
        """Ultra-precise PAN number extraction with maximum accuracy"""
        candidates = []
        
        # Strategy 1: Labeled patterns (highest priority)
        labeled_patterns = [
            r'PAN\s*(?:No|Number)\s*:?\s*([A-Z]{5}\d{4}[A-Z])',
            r'Permanent\s+Account\s+Number\s*:?\s*([A-Z]{5}\d{4}[A-Z])',
            r'P\.A\.N\.\s*(?:No|Number)\s*:?\s*([A-Z]{5}\d{4}[A-Z])',
        ]
        
        for pattern in labeled_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cleaned = match.upper().strip()
                if self._validate_pan_format(cleaned):
                    candidates.append((cleaned, 25))  # Highest priority
        
        # Strategy 2: Context-aware line search
        for i, line in enumerate(lines):
            # Look for PAN patterns in lines with tax/income context
            potential_pans = re.findall(r'[A-Z]{5}\d{4}[A-Z]', line.upper())
            for pan in potential_pans:
                if self._validate_pan_format(pan):
                    # Check surrounding context
                    context_score = 8
                    context_lines = lines[max(0, i-2):i+3]
                    context_text = ' '.join(context_lines).lower()
                    
                    # Boost score for PAN indicators
                    if any(indicator in context_text for indicator in 
                           ['pan', 'permanent', 'account', 'income', 'tax', 'department']):
                        context_score = 18
                    
                    # Reduce score if near other patterns
                    if any(pattern in context_text for pattern in 
                           ['mobile', 'phone', 'aadhar', 'aadhaar']):
                        context_score = max(3, context_score - 8)
                    
                    candidates.append((pan, context_score))
        
        # Strategy 3: Enhanced OCR error correction
        ocr_corrections = {
            '0': ['O', 'Q'], '1': ['I', 'l', '|'], '5': ['S'], 
            '8': ['B'], '6': ['G'], 'O': ['0'], 'I': ['1'], 
            'S': ['5'], 'B': ['8'], 'G': ['6']
        }
        
        # Find potential PAN patterns with OCR errors
        potential_matches = re.findall(r'[A-Z0-9]{10}', text.upper())
        for match in potential_matches:
            # Generate corrected versions systematically
            corrected_versions = [match]
            
            # Apply corrections position by position
            for pos in range(len(match)):
                char = match[pos]
                if char in ocr_corrections:
                    for correction in ocr_corrections[char]:
                        variant = match[:pos] + correction + match[pos+1:]
                        corrected_versions.append(variant)
            
            # Validate all versions
            for variant in corrected_versions:
                if self._validate_pan_format(variant):
                    candidates.append((variant, 10))
        
        # Strategy 4: Position-based scoring (PAN usually appears in specific areas)
        for i, line in enumerate(lines):
            # PAN numbers often appear in the middle section of the card
            if len(lines) // 4 <= i <= 3 * len(lines) // 4:
                potential_pans = re.findall(r'[A-Z]{5}\d{4}[A-Z]', line.upper())
                for pan in potential_pans:
                    if self._validate_pan_format(pan):
                        candidates.append((pan, 5))
        
        if candidates:
            # Calculate final scores
            pan_scores = {}
            for pan, score in candidates:
                if pan in pan_scores:
                    pan_scores[pan] += score
                else:
                    pan_scores[pan] = score
            
            # Get highest scoring PAN
            best_pan = max(pan_scores.items(), key=lambda x: x[1])[0]
            return best_pan
        
        return None
    
    def _validate_pan_format(self, pan):
        """Validate PAN format"""
        if len(pan) != 10:
            return False
        
        # PAN format: AAAAA9999A
        if not (pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
            return False
        
        # Check for obviously invalid patterns
        if pan in ['AAAAA0000A', 'BBBBB1111B', 'CCCCC2222C']:
            return False
        
        return True
    
    def _extract_dob(self, text, lines):
        """Enhanced DOB extraction specifically for PAN cards - prioritize complete dates"""
        candidates = []
        
        print(f"DEBUG: PAN DOB extraction - Processing text with {len(lines)} lines")
        
        # Strategy 1: Look for ANY date pattern in DD/MM/YYYY or D/M/YYYY format first
        all_date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # Any DD/MM/YYYY format
            r'(\d{1,2}\.\d{1,2}\.\d{4})',      # DD.MM.YYYY format  
            r'(\d{1,2}\s+\d{1,2}\s+\d{4})',   # DD MM YYYY format
        ]
        
        # Search through all text for any valid date
        for pattern in all_date_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Normalize different separators to /
                normalized = match.replace('-', '/').replace('.', '/').replace(' ', '/')
                normalized_date = self._normalize_date_format(normalized)
                if self._validate_date(normalized_date):
                    print(f"DEBUG: Found date pattern: {match} -> {normalized_date}")
                    candidates.append((normalized_date, 20))
        
        # Strategy 2: Line-by-line search for DOB context
        for i, line in enumerate(lines):
            line_clean = line.strip()
            print(f"DEBUG: Line {i}: {line_clean}")
            
            # Look for DOB indicators
            if any(indicator in line_clean.upper() for indicator in ['DOB', 'BIRTH', 'DATE OF BIRTH']):
                print(f"DEBUG: Found DOB indicator in line {i}: {line_clean}")
                
                # Search current line and next 2 lines for dates
                search_lines = lines[i:i+3] if i+2 < len(lines) else lines[i:]
                for j, search_line in enumerate(search_lines):
                    for pattern in all_date_patterns:
                        date_matches = re.findall(pattern, search_line)
                        for date_match in date_matches:
                            normalized = date_match.replace('-', '/').replace('.', '/').replace(' ', '/')
                            normalized_date = self._normalize_date_format(normalized)
                            if self._validate_date(normalized_date):
                                print(f"DEBUG: Found contextual date: {date_match} -> {normalized_date}")
                                candidates.append((normalized_date, 25 + (3-j)))  # Higher score for closer lines
        
        # Strategy 3: Look for dates near names (PAN cards often have DOB near names)
        for i, line in enumerate(lines):
            words = line.split()
            # If line looks like a name (2-4 words, mostly alphabetic)
            if (2 <= len(words) <= 4 and 
                all(word.replace(' ', '').isalpha() for word in words if len(word) > 1)):
                
                # Check next 3 lines for dates
                search_lines = lines[i+1:i+4] if i+3 < len(lines) else lines[i+1:]
                for search_line in search_lines:
                    for pattern in all_date_patterns:
                        date_matches = re.findall(pattern, search_line)
                        for date_match in date_matches:
                            normalized = date_match.replace('-', '/').replace('.', '/').replace(' ', '/')
                            normalized_date = self._normalize_date_format(normalized)
                            if self._validate_date(normalized_date):
                                print(f"DEBUG: Found date near name: {date_match} -> {normalized_date}")
                                candidates.append((normalized_date, 15))
        
        # Strategy 4: Fallback - look for any 4-digit year only if no complete dates found
        if not candidates:
            print("DEBUG: No complete dates found, looking for years")
            year_patterns = [
                r'\b(19\d{2}|20[0-2]\d)\b'  # 4-digit years
            ]
            
            for pattern in year_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if self._validate_year(match):
                        print(f"DEBUG: Found year: {match}")
                        candidates.append((match, 5))
        
        if candidates:
            # Sort by priority and return best candidate
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_date = candidates[0][0]
            print(f"DEBUG: Selected best date: {best_date}")
            return best_date
        
        print("DEBUG: No valid dates found")
        return None
    
    def _validate_date(self, date_str):
        """Enhanced date validation for PAN cards"""
        try:
            if not date_str or '/' not in date_str:
                return False
                
            parts = date_str.split('/')
            if len(parts) != 3:
                return False
            
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            
            print(f"DEBUG: Validating date - Day: {day}, Month: {month}, Year: {year}")
            
            # Basic range validation - be more lenient
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1920 <= year <= 2025):
                print(f"DEBUG: Date failed basic range validation")
                return False
            
            # Month-specific validation - be more lenient for OCR errors
            days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            if day > days_in_month[month - 1]:
                print(f"DEBUG: Date failed month-specific validation")
                return False
            
            print(f"DEBUG: Date validation passed: {date_str}")
            return True
        except Exception as e:
            print(f"DEBUG: Date validation error: {e}")
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
        """Normalize date to DD/MM/YYYY format"""
        try:
            if not date_str:
                return date_str
                
            # Handle different separators
            normalized = date_str.replace('-', '/').replace('.', '/').replace(' ', '/')
            
            parts = normalized.split('/')
            if len(parts) == 3:
                day, month, year = parts.strip() if hasattr(parts, 'strip') else parts
                
                # Clean up parts
                day = str(day).strip()
                month = str(month).strip()
                year = str(year).strip()
                
                # Ensure day and month are 2 digits, year is 4 digits
                if len(day) == 1:
                    day = '0' + day
                if len(month) == 1:
                    month = '0' + month
                    
                result = f"{day}/{month}/{year}"
                print(f"DEBUG: Normalized {date_str} -> {result}")
                return result
            return date_str
        except Exception as e:
            print(f"DEBUG: Date normalization error: {e}")
            return date_str
    
    def _extract_name(self, text, lines, pan_number, dob):
        """Ultra-precise name extraction using all available context"""
        candidates = []
        
        # Strategy 1: Position-based extraction (names usually appear early in PAN cards)
        for i, line in enumerate(lines[:20]):
            if self._is_header_line(line):
                continue
            
            # Skip lines with numbers (likely not names)
            if re.search(r'\d', line):
                continue
                
            words = line.split()
            if 2 <= len(words) <= 4:  # Names typically 2-4 words
                if self._validate_name(line):
                    # Higher score for earlier positions
                    position_score = max(5, 20 - i)
                    candidates.append((line.strip(), position_score))
        
        # Strategy 2: Context-based extraction near known fields
        context_boost_lines = []
        
        # Find lines near PAN number
        if pan_number:
            for i, line in enumerate(lines):
                if pan_number in line:
                    # Names usually appear 2-8 lines before PAN number
                    context_boost_lines.extend(range(max(0, i-8), i))
        
        # Find lines near DOB
        if dob:
            for i, line in enumerate(lines):
                if any(date_part in line for date_part in dob.split('/')):
                    # Names usually appear 1-6 lines before DOB
                    context_boost_lines.extend(range(max(0, i-6), i))
        
        # Apply context boost
        for line_idx in set(context_boost_lines):
            if line_idx < len(lines):
                potential = lines[line_idx].strip()
                if self._validate_name(potential) and not re.search(r'\d', potential):
                    candidates.append((potential, 18))
        
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
        
        # Strategy 4: Look for names in the "sweet spot" (lines 2-10, avoiding headers)
        for i in range(2, min(10, len(lines))):
            line = lines[i].strip()
            if (self._validate_name(line) and 
                not self._is_header_line(line) and
                not re.search(r'\d', line)):
                candidates.append((line, 14))
        
        # Strategy 5: Sequential name detection (PAN holder is typically first)
        for i in range(len(lines) - 1):
            line1 = lines[i].strip()
            line2 = lines[i + 1].strip()
            
            if (self._validate_name(line1) and self._validate_name(line2) and
                line1 != line2 and 
                not re.search(r'\d', line1) and not re.search(r'\d', line2) and
                len(line1.split()) >= 2 and len(line2.split()) >= 2 and
                not self._is_header_line(line1) and not self._is_header_line(line2)):
                # In PAN cards, first name is usually the PAN holder
                candidates.append((line1, 16))  # Boost first name in sequence
        
        if candidates:
            # Calculate final scores
            name_scores = {}
            for name, score in candidates:
                cleaned_name = name.strip().title()
                if cleaned_name in name_scores:
                    name_scores[cleaned_name] += score
                else:
                    name_scores[cleaned_name] = score
                
                # Add quality bonus
                name_scores[cleaned_name] += self._score_name_quality(cleaned_name)
            
            # Get highest scoring name
            best_name = max(name_scores.items(), key=lambda x: x[1])[0]
            return best_name
        
        return None
    
    def _extract_fathers_name(self, text, lines, name, pan_number, dob):
        """Ultra-precise father's name extraction using all available context"""
        candidates = []
        
        # Strategy 1: Labeled patterns (highest priority)
        father_patterns = [
            r'(?:Father\'?s?\s+Name|Father)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'(?:पिता|श्री)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'(?:Mr\.?|Shri|Sri)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
        ]
        
        for pattern in father_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if (self._validate_name(match) and 
                    (not name or match.lower() != name.lower())):
                    candidates.append((match, 25))  # Highest priority
        
        # Strategy 2: Relationship patterns
        relationship_patterns = [
            r'S/O\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',  # Son of
            r'Son\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
            r'D/O\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',  # Daughter of
            r'Daughter\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
        ]
        
        for pattern in relationship_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if (self._validate_name(match) and 
                    (not name or match.lower() != name.lower())):
                    candidates.append((match, 20))
        
        # Strategy 3: Position-based extraction using all context
        context_boost_lines = []
        
        # Find lines near main name
        if name:
            for i, line in enumerate(lines):
                if any(word in line.lower() for word in name.lower().split()):
                    # Father's name usually appears 1-4 lines after main name
                    context_boost_lines.extend(range(i + 1, min(i + 5, len(lines))))
        
        # Find lines near PAN number
        if pan_number:
            for i, line in enumerate(lines):
                if pan_number in line:
                    # Father's name usually appears 2-6 lines before PAN
                    context_boost_lines.extend(range(max(0, i-6), i))
        
        # Find lines near DOB
        if dob:
            for i, line in enumerate(lines):
                if any(date_part in line for date_part in dob.split('/')):
                    # Father's name usually appears 1-5 lines before DOB
                    context_boost_lines.extend(range(max(0, i-5), i))
        
        # Apply context boost
        for line_idx in set(context_boost_lines):
            if line_idx < len(lines):
                potential = lines[line_idx].strip()
                if (self._validate_name(potential) and 
                    not re.search(r'\d', potential) and
                    (not name or potential.lower() != name.lower())):
                    candidates.append((potential, 15))
        
        # Strategy 4: Sequential name detection (PAN holder first, father's name second)
        consecutive_names = []
        for i in range(len(lines) - 1):
            line1 = lines[i].strip()
            line2 = lines[i + 1].strip()
            
            if (self._validate_name(line1) and self._validate_name(line2) and
                line1 != line2 and 
                not re.search(r'\d', line1) and not re.search(r'\d', line2) and
                len(line1.split()) >= 2 and len(line2.split()) >= 2 and
                not self._is_header_line(line1) and not self._is_header_line(line2)):
                consecutive_names.append((line1, line2, i))
        
        # In PAN cards, if we have the main name, father's name typically follows it
        if name and consecutive_names:
            for name1, name2, pos in consecutive_names:
                # Check if first name matches the PAN holder's name
                if any(word in name1.lower() for word in name.lower().split()):
                    # Second name is likely father's name
                    candidates.append((name2, 22))  # High priority for sequential pattern
                # Also check reverse case (though less common)
                elif any(word in name2.lower() for word in name.lower().split()):
                    candidates.append((name1, 18))
        
        # If no main name context, use first valid consecutive pair
        elif consecutive_names and not candidates:
            # In PAN cards, first name is usually PAN holder, second is father
            for name1, name2, pos in consecutive_names:
                # Prefer the second name as father's name in sequential pairs
                candidates.append((name2, 16))
        
        # Strategy 5: Father indicator context search
        father_indicators = ['father', 'fathers', "father's", 'पिता', 'श्री', 'shri', 'mr']
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(indicator in line_lower for indicator in father_indicators):
                # Search in current and next line
                for j in range(i, min(i + 2, len(lines))):
                    potential_line = lines[j]
                    
                    # Clean the line
                    cleaned_line = potential_line
                    for indicator in father_indicators:
                        cleaned_line = re.sub(rf'\b{indicator}\'?s?\b', '', cleaned_line, flags=re.IGNORECASE)
                    cleaned_line = re.sub(r'[:\-\.]', '', cleaned_line).strip()
                    
                    if (self._validate_name(cleaned_line) and 
                        not re.search(r'\d', cleaned_line) and
                        (not name or cleaned_line.lower() != name.lower())):
                        candidates.append((cleaned_line, 12))
        
        if candidates:
            # Calculate final scores
            name_scores = {}
            for candidate_name, score in candidates:
                cleaned_name = candidate_name.strip().title()
                if cleaned_name in name_scores:
                    name_scores[cleaned_name] += score
                else:
                    name_scores[cleaned_name] = score
                
                # Add quality bonus
                name_scores[cleaned_name] += self._score_name_quality(cleaned_name)
                
                # Bonus for common prefixes
                if any(prefix in cleaned_name.lower() for prefix in ['shri', 'mr', 'sri']):
                    name_scores[cleaned_name] += 5
            
            # Get highest scoring father's name
            best_name = max(name_scores.items(), key=lambda x: x[1])[0]
            return best_name
        
        return None
    
    def _validate_name(self, name):
        """Validate name quality"""
        if not name or len(name) < 3 or len(name) > 60:
            return False
        
        # Exclude common false positives
        exclude_words = [
            'government', 'india', 'income', 'tax', 'department', 'permanent',
            'account', 'number', 'pan', 'card', 'signature', 'date', 'issue'
        ]
        
        name_lower = name.lower()
        if any(word in name_lower for word in exclude_words):
            return False
        
        # Must have at least 2 words for full names
        words = name.split()
        if len(words) < 2:
            return False
        
        # Each word validation
        for word in words:
            if len(word) < 2 or not word.replace(' ', '').isalpha():
                return False
        
        # Check for PAN number pattern
        if re.search(r'[A-Z]{5}\d{4}[A-Z]', name):
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
            'government', 'india', 'income', 'tax', 'department', 'permanent',
            'account', 'number', 'pan', 'card', 'signature'
        ]
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in header_keywords)