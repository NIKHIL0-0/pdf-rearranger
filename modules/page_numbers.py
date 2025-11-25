import re

def detect_page_number(text, header="", footer=""):
    """
    Detect page numbers from text, prioritizing header and footer regions.
    Returns tuple: (page_number, confidence_score)
    confidence: 1.0 = high (explicit format), 0.5 = medium (standalone number)
    """
    lines = text.strip().split("\n")
    
    # Search in header + footer regions (top 3 and bottom 3 lines)
    header_lines = header if header else "\n".join(lines[:3])
    footer_lines = footer if footer else "\n".join(lines[-3:])
    scope = header_lines + "\n" + footer_lines

    # Patterns with confidence scores (pattern, confidence)
    patterns = [
        (r"-\s*(\d+)\s*-", 1.0),                    # -20-
        (r"page\s+(\d+)\s+of\s+\d+", 1.0),         # Page 4 of 12
        (r"page\s+(\d+)", 0.9),                     # Page 4
        (r"(\d+)\s*/\s*\d+", 0.9),                 # 4 / 12
        (r"p\.\s*(\d+)", 0.8),                      # p. 4
        (r"^[\s\-]*(\d{1,3})[\s\-]*$", 0.5)        # Standalone "4" (lower confidence)
    ]

    for pattern, confidence in patterns:
        m = re.search(pattern, scope, re.IGNORECASE | re.MULTILINE)
        if m:
            page_num = int(m.group(1))
            # Sanity check: page numbers typically < 10000
            if 1 <= page_num <= 9999:
                return page_num, confidence

    return None, 0.0


def detect_missing_pages(pages_with_numbers):
    """
    Detect missing pages based on page number sequence.
    Returns list of missing page numbers.
    
    Args:
        pages_with_numbers: List of tuples [(page_index, page_number), ...]
    """
    if len(pages_with_numbers) < 2:
        return []
    
    # Sort by detected page number
    sorted_pages = sorted(pages_with_numbers, key=lambda x: x[1])
    page_numbers = [pn for _, pn in sorted_pages]
    
    missing = []
    for i in range(len(page_numbers) - 1):
        current = page_numbers[i]
        next_num = page_numbers[i + 1]
        
        # Check for gaps in sequence
        if next_num - current > 1:
            missing.extend(range(current + 1, next_num))
    
    return missing
