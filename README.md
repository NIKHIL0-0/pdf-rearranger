# PDF Rearranger

Intelligent PDF reordering system with OCR support, semantic analysis, and duplicate detection.

## Features

### 🔍 Text Extraction
- **Direct text extraction** attempted first using PyMuPDF
- **OCR fallback** for scanned/image-only pages using Tesseract
- Automatic header and footer detection

### 🔢 Page Number Detection
- Multiple pattern recognition (e.g., "Page 5", "5/24", "-5-")
- Confidence scoring for reliability
- Missing page detection when sequences have gaps

### 📑 Section Classification
- Keyword-based section detection
- Priority scoring for structural elements
- Common document sections: Definitions, Annexures, Repayment Schedule, etc.

### 🧠 Semantic Analysis
- Sentence embeddings using `sentence-transformers`
- Cosine similarity for page continuity
- Near-duplicate detection (>95% similarity)

### 🔄 Hybrid Ordering Algorithm
Pages are reordered using a weighted scoring system:
- **Page numbers (60%)** - Highest confidence signal
- **Section keywords (20%)** - Structural guidance
- **Semantic continuity (20%)** - Topic flow

### 🔍 Duplicate Detection
- **Exact duplicates**: SHA-256 content hashing
- **Near duplicates**: Embedding similarity (>95% threshold)
- Comprehensive duplicate report

### 📄 Export & Reports
- Reordered PDF with embedded bookmarks
- Table of Contents (PDF + text formats)
- Complete JSON report with all metadata
- Missing pages report
- Duplicate detection report

## Installation

### Prerequisites
1. **Python 3.8+**
2. **Tesseract OCR** (for scanned documents)
   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt-get install tesseract-ocr`
   - Mac: `brew install tesseract`

### Setup

1. Clone or download this repository

2. Create virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:
```powershell
pip install -r requirments.txt
```

4. **Configure API Key** (for Gemini AI features):
   - Copy `.env.example` to `.env`
   - Add your Gemini API key:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```
   - Get API key from: https://aistudio.google.com/app/apikey

5. (Optional) Set Tesseract path if not in PATH:
```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Usage

### Option 1: Flask API

Start the server:
```powershell
python app.py
```

Server runs at `http://127.0.0.1:5000`

#### API Endpoints

**Upload and Process:**
```bash
POST /upload
Content-Type: multipart/form-data
Body: pdf=<file>
```

**Process Existing File:**
```bash
POST /process/<filename>
```

**List Files:**
```bash
GET /files
```

**View Results:**
```bash
GET /view/<filename>
```

**Download Output:**
```bash
GET /download/<filename>
```

### Option 2: Command Line

Process a single PDF:
```powershell
python processor.py uploads/document.pdf
```

Process all PDFs in uploads folder:
```powershell
python process_uploads.py
```

## Output Files

After processing `document.pdf`, you'll find in `outputs/`:

- `document_reordered.pdf` - Reordered PDF with bookmarks
- `document_toc.pdf` - Table of Contents (standalone)
- `document_toc.txt` - Table of Contents (text format)
- `document_complete_report.json` - Full processing report

## Project Structure

```
pdf-rearranger/
├── app.py                      # Flask API server
├── processor.py                # Main processing pipeline
├── process_uploads.py          # Batch processor
├── requirments.txt             # Dependencies
├── modules/
│   ├── extractor.py           # Text extraction + OCR
│   ├── page_numbers.py        # Page number detection
│   ├── headings.py            # Title & section classification
│   ├── embeddings.py          # Semantic similarity
│   ├── duplicates.py          # Duplicate detection
│   ├── ordering.py            # Hybrid ordering algorithm
│   └── export_pdf.py          # PDF export & TOC generation
├── uploads/                    # Input PDFs
└── outputs/                    # Processed results
```

## Configuration

### Tesseract Path
Set environment variable if Tesseract is not in PATH:
```powershell
$env:TESSERACT_CMD = "C:\Path\To\tesseract.exe"
```

### Ordering Weights
Modify in `modules/ordering.py`:
```python
WEIGHTS = {
    "page_number": 0.6,
    "section_priority": 0.2,
    "semantic_continuity": 0.2
}
```

### Duplicate Threshold
Adjust in `modules/duplicates.py`:
```python
near_duplicates = find_near_duplicates(pages, embeddings, threshold=0.95)
```

## Examples

### Example 1: Scanned Loan Agreement

Input: Shuffled scanned loan document
- OCR automatically triggered
- Pages reordered by detected numbers
- Annexures identified and grouped
- Duplicate signature pages detected

Output:
- Reordered PDF with proper sequence
- TOC with sections: Agreement → Schedule → Annexures
- Report showing 3 duplicate pages removed

### Example 2: Unnumbered Contract

Input: Contract without page numbers
- Ordering by section keywords
- Semantic continuity maintained
- Definitions → Terms → Schedules → Signatures

## Troubleshooting

**OCR not working:**
- Install Tesseract OCR
- Set TESSERACT_CMD environment variable
- Verify: `tesseract --version`

**Import errors:**
- Activate virtual environment
- Reinstall: `pip install -r requirments.txt`

**Model download slow:**
- First run downloads sentence-transformers model (~90MB)
- Subsequent runs use cached model

**Memory issues with large PDFs:**
- Process in batches
- Reduce DPI in extractor.py (default: 300)

## Technical Details

### Embedding Model
Uses `all-MiniLM-L6-v2`:
- Size: 80MB
- Speed: ~2000 sentences/sec
- Embedding dim: 384

### Page Ordering Logic

1. **High page number coverage (>70%)**
   - Sort by detected page numbers
   - Place unnumbered pages at end

2. **Low page number coverage (<70%)**
   - Compute weighted scores
   - Sort by combined score
   - Apply continuity optimization

### Performance

- ~1-2 pages/second (text extraction)
- OCR: ~5-10 seconds/page (300 DPI)
- Embeddings: ~50-100 pages/second
- Total: ~2-3 minutes for 50-page document

## License

MIT License - Feel free to use and modify

## Credits

Built with:
- PyMuPDF (fitz)
- Tesseract OCR
- sentence-transformers
- scikit-learn
- Flask
