"""
Extract titles and classify sections using keywords
"""
import re

# Section keywords with priority scores AND position hints
# position_hint: 0=very early, 500=middle, 1000=very late
SECTION_KEYWORDS = {
    # Front matter (position 0-200)
    "table of contents": {"priority": 10, "position": 10},
    "index": {"priority": 10, "position": 20},
    "abstract": {"priority": 9, "position": 30},
    "executive summary": {"priority": 10, "position": 40},
    "summary": {"priority": 9, "position": 50},
    "introduction": {"priority": 8, "position": 100},
    "background": {"priority": 7, "position": 110},
    "overview": {"priority": 7, "position": 120},
    "scope": {"priority": 7, "position": 130},
    
    # Main content - Legal/Contract (position 200-500)
    "definitions": {"priority": 10, "position": 200},
    "whereas": {"priority": 8, "position": 210},
    "witnesseth": {"priority": 8, "position": 220},
    "recitals": {"priority": 8, "position": 230},
    "parties": {"priority": 7, "position": 240},
    "agreement": {"priority": 7, "position": 300},
    "terms and conditions": {"priority": 8, "position": 350},
    "representations and warranties": {"priority": 7, "position": 400},
    "covenants": {"priority": 7, "position": 410},
    "indemnification": {"priority": 7, "position": 420},
    "termination": {"priority": 7, "position": 430},
    "dispute resolution": {"priority": 7, "position": 440},
    "governing law": {"priority": 7, "position": 450},
    
    # Financial (position 500-700)
    "loan amount": {"priority": 8, "position": 500},
    "principal amount": {"priority": 7, "position": 510},
    "interest rate": {"priority": 7, "position": 520},
    "payment terms": {"priority": 8, "position": 530},
    "disbursement": {"priority": 7, "position": 540},
    "repayment schedule": {"priority": 9, "position": 550},
    "collateral": {"priority": 7, "position": 600},
    "security": {"priority": 7, "position": 610},
    
    # Annexures and schedules (position 800-900)
    "annexure": {"priority": 9, "position": 800},
    "annex": {"priority": 9, "position": 800},
    "appendix": {"priority": 9, "position": 850},
    "exhibit": {"priority": 9, "position": 850},
    "schedule": {"priority": 8, "position": 800},
    "attachment": {"priority": 8, "position": 850},
    
    # Miscellaneous (position 700-750)
    "miscellaneous": {"priority": 6, "position": 700},
    
    # End matter (position 900-1000)
    "signatures": {"priority": 9, "position": 900},
    "witness": {"priority": 8, "position": 910},
    "executed": {"priority": 7, "position": 920},
    "conclusion": {"priority": 7, "position": 950},
    "references": {"priority": 7, "position": 960},
    "bibliography": {"priority": 7, "position": 970},
    "glossary": {"priority": 8, "position": 980},
    "abbreviations": {"priority": 7, "position": 990},
}


def is_blank_page(text):
    """
    Detect if a page is essentially blank (very little meaningful content).
    
    Args:
        text: Page text content
        
    Returns:
        Boolean indicating if page is blank
    """
    if not text:
        return True
    
    # Remove whitespace and count meaningful characters
    clean_text = text.strip()
    meaningful_chars = len(re.sub(r'[\s\n\r\t]+', '', clean_text))
    
    # Less than 20 meaningful characters = blank page
    return meaningful_chars < 20


def extract_title(text, deep_analysis=False):
    """
    Extract the first meaningful line that looks like a title or heading.
    Prioritizes lines with section numbers and isolated lines (surrounded by whitespace).
    
    For PDFs with scrambled text extraction, also searches for section patterns
    anywhere in the text.
    
    Args:
        text: Page text content
        deep_analysis: If True, analyze more lines and use heuristics
        
    Returns:
        Cleaned title string or None
    """
    if is_blank_page(text):
        return "[BLANK PAGE]"
    
    lines = text.split("\n")
    
    # Pre-scan: Look for section number patterns ANYWHERE in text
    # Patterns like "6 Results", "6.1 MachineTranslation", "5 Training"
    # Balanced constraints to work across different document types
    section_pattern = r'(?:^|\n)(\d{1,2}(?:\.\d+)*)\s+([A-Z][A-Za-z]{2,50})'
    section_matches = re.findall(section_pattern, text, re.MULTILINE)
    
    if section_matches:
        # Filter out unlikely section numbers (years, extreme values, table data)
        valid_matches = []
        for num_str, title_part in section_matches:
            # Parse the section number parts
            parts = [int(p) for p in num_str.split('.')]
            main_num = parts[0]
            
            # Accept section numbers 1-50 (works for papers, reports, books)
            if not (1 <= main_num <= 50):
                continue
            
            # Check subsection numbers are reasonable (≤20)
            if len(parts) > 1 and parts[1] > 20:
                continue
            
            # Skip if title looks like data (all caps short words, numbers)
            if len(title_part) < 4 or title_part.isupper():
                continue
            
            valid_matches.append((num_str, title_part))
        
        if valid_matches:
            # Found valid section numbers - use the first one
            num, title_part = valid_matches[0]
            return f"{num} {title_part}"
    
    # First pass: Look for isolated headings (surrounded by blank lines)
    # These are likely section headings like "6 Results", "6.1 MachineTranslation"
    for i in range(min(20, len(lines))):
        clean = lines[i].strip()
        
        # Check if line is short and has section number pattern
        if 5 <= len(clean) <= 100 and re.match(r'^\d+(?:\.\d+)*\s+[A-Z]', clean):
            # Check if surrounded by blank/short lines (isolated heading)
            prev_blank = (i == 0) or (len(lines[i-1].strip()) < 10)
            next_blank = (i >= len(lines)-1) or (len(lines[i+1].strip()) < 10)
            
            if prev_blank or next_blank:
                return clean
    
    # Second pass: Score candidate lines
    candidate_lines = []
    for i, line in enumerate(lines[:15]):
        clean = line.strip()
        
        # Skip very short or very long lines
        if not (5 <= len(clean) <= 200):
            continue
        
        # Skip purely numeric or date patterns
        if clean.isnumeric():
            continue
        if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', clean):
            continue
        if re.match(r'^page\s+\d+', clean, re.IGNORECASE):
            continue
        
        # Check isolation (surrounded by whitespace)
        prev_blank = (i == 0) or (len(lines[i-1].strip()) < 10)
        next_blank = (i >= len(lines)-1) or (len(lines[i+1].strip()) < 10)
        is_isolated = prev_blank or next_blank
        
        # Scoring
        is_caps = clean.isupper() and len(clean.split()) <= 8
        is_title_case = clean.istitle()
        has_section_num = bool(re.match(r'^(\d+\.?\d*|\(\w+\)|Article|Section)', clean, re.IGNORECASE))
        is_short = len(clean) < 50  # Headings are usually concise
        
        score = 0
        if has_section_num:
            score += 5
        if is_isolated:
            score += 4  # Strong signal for headings
        if is_caps:
            score += 3
        if is_short and is_isolated:
            score += 2
        if is_title_case:
            score += 2
        if i < 3:
            score += 1
        
        candidate_lines.append((clean, score, i))
    
    if not candidate_lines:
        return None
    
    # Return highest scoring line
    candidate_lines.sort(key=lambda x: (-x[1], x[2]))
    return candidate_lines[0][0] if candidate_lines else None


def classify_section(text, title=None):
    """
    Classify the section type based on keywords in text or title.
    
    Args:
        text: Full page text
        title: Detected title (optional)
        
    Returns:
        Tuple of (section_type, priority_score, position_hint)
        section_type: matched keyword or "unknown"
        priority_score: numeric score (0-10)
        position_hint: suggested position (0-1000)
    """
    # Prioritize title, then first 500 chars of text
    search_text = (title or "").lower() + " " + text[:500].lower()
    
    best_match = None
    best_score = 0
    best_position = 500  # Default middle position
    
    for keyword, info in SECTION_KEYWORDS.items():
        if keyword in search_text:
            # Boost score if keyword appears in title
            title_boost = 2 if title and keyword in title.lower() else 1
            weighted_score = info["priority"] * title_boost
            
            if weighted_score > best_score:
                best_match = keyword
                best_score = info["priority"]  # Store original score
                best_position = info["position"]
    
    # Special handling for blank pages
    if title == "[BLANK PAGE]":
        return ("blank", 0, 9999)  # Put at very end
    
    return (best_match or "unknown", best_score, best_position)


def compare_section_numbers(num1, num2):
    """
    Compare two section numbers hierarchically.
    Returns: -1 if num1 < num2, 0 if equal, 1 if num1 > num2
    
    Examples:
        "3" < "3.1" < "3.2" < "4"
    """
    if not num1 and not num2:
        return 0
    if not num1:
        return 1
    if not num2:
        return -1
    
    # Parse numbers
    parts1 = [int(x) for x in num1.split('.')]
    parts2 = [int(x) for x in num2.split('.')]
    
    # Compare part by part
    for i in range(min(len(parts1), len(parts2))):
        if parts1[i] < parts2[i]:
            return -1
        elif parts1[i] > parts2[i]:
            return 1
    
    # If all compared parts are equal, shorter is less
    if len(parts1) < len(parts2):
        return -1
    elif len(parts1) > len(parts2):
        return 1
    
    return 0


def parse_roman_numeral(s):
    """
    Parse Roman numerals to integers.
    Returns None if not a valid Roman numeral.
    """
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    s = s.upper().strip()
    
    if not s or not all(c in roman_map for c in s):
        return None
    
    result = 0
    prev_value = 0
    
    for char in reversed(s):
        value = roman_map[char]
        if value < prev_value:
            result -= value
        else:
            result += value
        prev_value = value
    
    return result if result > 0 else None


def extract_section_number(title):
    """
    Extract section numbering from title (e.g., "1.2.3 Introduction" -> "1.2.3")
    Handles hierarchical numbering like 3, 3.1, 3.2, 3.2.1, Roman numerals, etc.
    
    Args:
        title: Title string
        
    Returns:
        Tuple of (section_number_string, numeric_value) or (None, None)
    """
    if not title or title == "[BLANK PAGE]":
        return None, None
    
    title_clean = title.strip()
    
    # Pattern 1: Numbers followed by space and capital letter
    # "5 Training", "3.2 Attention", "1 Introduction"
    match = re.match(r'^(\d+(?:\.\d+){0,3})\s+[A-Z]', title_clean)
    if match:
        section_num = match.group(1)
        # Create hierarchical numeric value: 3.2.1 = 3.002001
        # This ensures: 3 < 3.1 < 3.2 < 3.2.1 < 3.2.2 < 3.3 < 4
        parts = [int(x) for x in section_num.split('.')]
        numeric_val = parts[0]  # Start with main section number
        for i, part in enumerate(parts[1:], 1):
            # Add fractional part: .1 = 0.001, .2 = 0.002, etc.
            numeric_val += part / (1000 ** i)
        return section_num, numeric_val
    
    # Pattern 2: Numbers at start with letter immediately after (no space)
    match = re.match(r'^(\d+(?:\.\d+){0,3})[A-Z]', title_clean)
    if match:
        section_num = match.group(1)
        parts = [int(x) for x in section_num.split('.')]
        numeric_val = parts[0]
        for i, part in enumerate(parts[1:], 1):
            numeric_val += part / (1000 ** i)
        return section_num, numeric_val
    
    # Pattern 3: Roman numerals (I, II, III, IV, V, etc.)
    match = re.match(r'^([IVXLCDM]+)[\s.)]', title_clean, re.IGNORECASE)
    if match:
        roman = match.group(1)
        numeric_val = parse_roman_numeral(roman)
        if numeric_val:
            return roman.upper(), numeric_val
    
    # Pattern 4: Article/Section with number
    match = re.match(r'^(?:article|section|chapter|part)\s+([IVXLCDM\d]+)', title_clean, re.IGNORECASE)
    if match:
        num_str = match.group(1)
        # Try Roman first
        numeric_val = parse_roman_numeral(num_str)
        if numeric_val:
            return num_str.upper(), numeric_val
        # Try regular number
        if num_str.isdigit():
            return num_str, int(num_str)
    
    # Pattern 5: Parenthetical numbers/letters ((a), (1), (i))
    match = re.match(r'^\(([a-z0-9]+)\)', title_clean, re.IGNORECASE)
    if match:
        sub_num = match.group(1)
        if sub_num.isdigit():
            return f"({sub_num})", int(sub_num)
        elif len(sub_num) == 1 and sub_num.isalpha():
            return f"({sub_num})", ord(sub_num.lower()) - ord('a') + 1
    
    # Pattern 6: Schedule/Annexure with Roman/numeric
    match = re.match(r'^(?:schedule|annexure|annex|appendix)\s+([IVXLCDM\d]+)', title_clean, re.IGNORECASE)
    if match:
        num_str = match.group(1)
        numeric_val = parse_roman_numeral(num_str)
        if numeric_val:
            return num_str.upper(), numeric_val + 1000  # Offset to place after main sections
        if num_str.isdigit():
            return num_str, int(num_str) + 1000
    
    return None, None
