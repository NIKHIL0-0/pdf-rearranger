#**PDF Page Rearranger with AI**

An intelligent PDF page reordering system that restores shuffled / out-of-order PDFs back to their correct reading sequence.

Instead of relying only on page numbers (which are often missing or wrong), this system mimics human reasoning using a hybrid decision model:

Detect structural clues (page numbers, section numbering, headings)

Understand document type (legal, academic, business report, etc.)

Use semantic continuity + AI reasoning when structure fails

#**Why I Built It**

Manually reordering PDFs — especially scanned or mis-merged files — is slow and error-prone.
AI tools alone are not reliable for every case, so I built a multi-layer logic system that combines rules + AI:

#**Method	Advantage**
Page number recognition	Fast & accurate when pages are labeled
Section hierarchy (1 → 1.1 → 1.1.1)	Works for academic & technical docs
Keyword ordering (Intro → Methods → Results…)	Useful when numbering missing
Semantic similarity	Maintains content continuity
Gemini AI analysis	Solves complex, ambiguous cases

This gives speed when possible and intelligence when required.

#**How It Works (Architecture)**
PDF → Text Extraction (OCR + PyMuPDF)
        ↓
Multi-Signal Detection
   → Page numbers
   → Section hierarchy
   → Keyword flow
   → Semantic embeddings
   → Document type classifier
        ↓
Hybrid Ordering Engine
   → Rule-based (fast path)
   → Gemini AI (fallback path)
        ↓
Reordered PDF + TOC + Analysis Report

#**Assumptions & Limitations**
Category	Notes
Assumptions	Document has some logical flow (not 100% random)
Required	English text; Tesseract for OCR if scanned
Dependency	Gemini API enables deep AI ordering
Limitation	Visual-only pages (charts/maps) may reduce accuracy
Trade-off	AI mode is slower but handles difficult cases better

#**What I Would Improve With More Time**

Multi-language support (regex + AI multilingual models)

Visual layout understanding (detect headers/footers via computer vision)

Learning loop that improves accuracy using user feedback

Confidence score per page + uncertainty heatmap

#**What Makes This Unique**

✔ Hybrid human-style reasoning, not just full AI or full rule-based
✔ Automatic fallback hierarchy ensures graceful degradation
✔ Multiple interfaces — CLI, API, and Streamlit UI
✔ Transparency — system generates a detailed analysis report explaining why each page was placed

#**Quick Start**
pip install -r requirements.txt
python processor.py uploads/document.pdf
# or
python cli.py uploads/document.pdf --gemini


Outputs include:

document_reordered.pdf

document_toc.pdf

document_complete_report.json

Built with curiosity around:

📌 document structure → 📌 intelligence systems → 📌 practical AI
video explanation: [text](https://drive.google.com/file/d/1p-0HesNHoI4nx2i6xMIuAghEkHuF05SH/view?usp=sharing)