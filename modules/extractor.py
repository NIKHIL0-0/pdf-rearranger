import fitz  # PyMuPDF
import os
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
    # Allow custom tesseract path from environment
    if 'TESSERACT_CMD' in os.environ:
        pytesseract.pytesseract.tesseract_cmd = os.environ['TESSERACT_CMD']
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: OCR functionality not available. Install pytesseract and Tesseract for OCR support.")
import io

def extract_pages_text(pdf_path):
    """
    Extract text from all pages in a PDF.
    Falls back to OCR if no selectable text is found.
    
    Returns list of page dictionaries with:
        - page_index: 0-based page index
        - text: extracted text content
        - header: top 3 lines of text
        - footer: bottom 3 lines of text
        - ocr_used: boolean indicating if OCR was used
    """
    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Try direct text extraction
        text = page.get_text().strip()
        ocr_used = False

        # Fallback to OCR if very little text extracted
        if len(text) < 15 and OCR_AVAILABLE:
            try:
                pix = page.get_pixmap(dpi=300)  # Higher DPI for better OCR
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))
                
                # Use pytesseract with optimized config for documents
                text = pytesseract.image_to_string(img, config='--psm 6')
                ocr_used = True
            except Exception as e:
                if page_num == 0:  # Only show warning once
                    print(f"⚠️  OCR unavailable: {e}")
                    print(f"⚠️  Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
                text = f"[OCR unavailable - page {page_num}]"
        elif len(text) < 15:
            text = f"[No text extracted from page {page_num}]"

        # Extract header and footer regions
        lines = text.strip().split("\n")
        header = "\n".join(lines[:3]) if len(lines) >= 3 else text
        footer = "\n".join(lines[-3:]) if len(lines) >= 3 else text

        pages.append({
            "page_index": page_num,
            "text": text.strip(),
            "header": header,
            "footer": footer,
            "ocr_used": ocr_used
        })

    doc.close()
    return pages
