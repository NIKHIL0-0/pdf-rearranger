"""
PDF Rearranger - Streamlit Interface
Intelligent PDF reordering with AI-powered analysis
"""

import streamlit as st
import os
from processor import process_pdf_complete
import json
from pathlib import Path

# Page config
st.set_page_config(
    page_title="PDF Rearranger",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []

# Create directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# Title and description
st.title("PDF Rearranger")
st.markdown("""
**Intelligent PDF page reordering system**

• Automatic page number detection
• Section heading recognition
• AI-powered document analysis
• Duplicate detection and removal
• Table of contents generation
""")

# Check OCR availability
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False

if not OCR_AVAILABLE:
    st.warning("OCR not available. Install Tesseract OCR for scanned PDFs. Text-based PDFs will work normally.")

# Check embeddings availability
from modules.embeddings import EMBEDDINGS_AVAILABLE
if not EMBEDDINGS_AVAILABLE:
    st.info("ℹ️ Semantic similarity features disabled (torch DLL issue). Core ordering features still work.")

# Sidebar
with st.sidebar:
    st.header("Settings")
    
    # LLM Option
    st.subheader("AI Ordering")
    use_gemini = st.checkbox(
        "Use Gemini AI",
        value=os.getenv('USE_GEMINI_BY_DEFAULT', 'false').lower() == 'true',
        help="Use AI for intelligent document analysis"
    )
    
    gemini_api_key = None
    if use_gemini:
        # Try to get API key from environment first
        default_api_key = os.getenv('GEMINI_API_KEY', '')
        if default_api_key and default_api_key != 'your_api_key_here':
            gemini_api_key = default_api_key
            st.success("API key loaded from environment")
        else:
            gemini_api_key = st.text_input(
                "Gemini API Key", 
                type="password",
                help="Get your API key from Google AI Studio or add to .env file"
            )
            if not gemini_api_key:
                st.warning("Please enter your Gemini API key or add GEMINI_API_KEY to .env file")
            else:
                st.success("API key provided")
    
    st.markdown("---")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=['pdf'],
        help="Upload a shuffled PDF to reorder"
    )
    
    st.markdown("---")
    
    # Processing options
    st.subheader("Processing Options")
    ocr_fallback = st.checkbox("Enable OCR fallback", value=os.getenv('ENABLE_OCR_FALLBACK', 'true').lower() == 'true', help="Use OCR for scanned pages")
    detect_duplicates = st.checkbox("Detect duplicates", value=os.getenv('DETECT_DUPLICATES', 'true').lower() == 'true')
    generate_toc = st.checkbox("Generate TOC", value=os.getenv('GENERATE_TOC', 'true').lower() == 'true')
    
    st.markdown("---")
    
    # Previous results
    st.subheader("Processed Files")
    output_dir = Path("outputs")
    if output_dir.exists():
        pdf_files = list(output_dir.glob("*_reordered.pdf"))
        if pdf_files:
            for pdf_file in pdf_files[:5]:
                base_name = pdf_file.stem.replace("_reordered", "")
                if st.button(f"{base_name[:30]}...", key=pdf_file.name):
                    st.session_state.selected_result = base_name
        else:
            st.info("No processed files yet")
    
    st.markdown("---")
    st.caption("PDF Rearranger v1.0")

# Main content
if uploaded_file is not None:
    # Save uploaded file
    upload_path = os.path.join("uploads", uploaded_file.name)
    with open(upload_path, "wb") as f:
        f.write(uploaded_file.read())
    
    st.success(f"Uploaded: {uploaded_file.name}")
    
    # Process button
    if st.button("Process PDF", type="primary"):
        # Validate Gemini settings
        if use_gemini and not gemini_api_key:
            st.error("Please enter your Gemini API key or disable Gemini AI")
        else:
            with st.spinner("Processing PDF... This may take a minute."):
                try:
                    # Process the PDF
                    result = process_pdf_complete(
                        upload_path, 
                        use_gemini=use_gemini,
                        gemini_api_key=gemini_api_key if use_gemini else None
                    )
                    
                    if result["success"]:
                        st.session_state.processed_files.append(uploaded_file.name)
                        st.session_state.current_result = result
                        st.success("Processing complete!")
                        st.rerun()
                    else:
                        st.error("Processing failed!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.exception(e)

# Display results
if 'current_result' in st.session_state and st.session_state.current_result:
    result = st.session_state.current_result
    summary = result['summary']
    
    st.markdown("---")
    st.header("Processing Results")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Pages",
            summary['document_info']['total_pages']
        )
    
    with col2:
        st.metric(
            "Pages Reordered",
            summary['document_info']['pages_reordered']
        )
    
    with col3:
        st.metric(
            "OCR Pages",
            summary['document_info']['ocr_pages']
        )
    
    with col4:
        duplicates = summary['duplicates']['exact_duplicates'] + summary['duplicates']['near_duplicates']
        st.metric(
            "Duplicates Found",
            duplicates
        )
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Table of Contents", "Details", "Downloads", "Advanced"])
    
    with tab1:
        st.subheader("Table of Contents")
        
        # Read TOC file
        base_name = Path(result['output_files']['reordered_pdf']).stem.replace("_reordered", "")
        toc_path = result['output_files'].get('toc_text')
        
        if toc_path and os.path.exists(toc_path):
            with open(toc_path, 'r', encoding='utf-8') as f:
                toc_content = f.read()
            st.text(toc_content)
        else:
            st.info("TOC not generated")
    
    with tab2:
        st.subheader("Processing Details")
        
        # Ordering method
        ordering = summary['ordering']
        st.markdown(f"**Ordering Method:** `{ordering['ordering_method']}`")
        st.markdown(f"**Page Number Coverage:** {ordering['page_number_coverage']*100:.1f}%")
        st.markdown(f"**Pages with Numbers:** {ordering['pages_with_numbers']}/{ordering['total_pages']}")
        
        # Missing pages
        if summary['missing_pages']['count'] > 0:
            st.warning(f"Misplaced pages detected: {summary['missing_pages']['pages']}")
        
        # Duplicates
        if duplicates > 0:
            st.warning(f"Found {summary['duplicates']['exact_duplicates']} exact duplicates and {summary['duplicates']['near_duplicates']} near-duplicates")
        
        # Page details
        with st.expander("View Page Details"):
            complete_report = result.get('complete_report', {})
            if complete_report and 'pages' in complete_report:
                for page in complete_report['pages'][:20]:  # Show first 20
                    st.markdown(f"""
                    **Page {page['original_index']} → Position {page['new_position']}**
                    - Title: {page['title']}
                    - Page Number: {page['page_number_detected']} (confidence: {page['page_number_confidence']:.2f})
                    - Section: {page.get('section_type', 'unknown')}
                    """)
                    st.markdown("---")
    
    with tab3:
        st.subheader("Download Results")
        
        # Reordered PDF
        reordered_path = result['output_files']['reordered_pdf']
        if os.path.exists(reordered_path):
            with open(reordered_path, 'rb') as f:
                st.download_button(
                    "Download Reordered PDF",
                    f,
                    file_name=os.path.basename(reordered_path),
                    mime="application/pdf"
                )
        
        # TOC PDF
        toc_pdf_path = result['output_files'].get('toc_pdf')
        if toc_pdf_path and os.path.exists(toc_pdf_path):
            with open(toc_pdf_path, 'rb') as f:
                st.download_button(
                    "Download TOC PDF",
                    f,
                    file_name=os.path.basename(toc_pdf_path),
                    mime="application/pdf"
                )
        
        # JSON Report
        json_path = result['output_files'].get('complete_report_json')
        if json_path and os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                st.download_button(
                    "Download JSON Report",
                    f,
                    file_name=os.path.basename(json_path),
                    mime="application/json"
                )
    
    with tab4:
        st.subheader("Advanced Information")
        
        # Full JSON report
        with st.expander("View Complete JSON Report"):
            complete_report = result.get('complete_report', {})
            st.json(complete_report)
        
        # Processing summary
        st.markdown("### Quality Metrics")
        quality = summary.get('quality_metrics', {})
        st.write(f"- Page Number Coverage: {quality.get('page_number_coverage', 0)*100:.1f}%")
        st.write(f"- Titles Extracted: {quality.get('titles_extracted', 0)}")
        st.write(f"- Sections Classified: {quality.get('sections_classified', 0)}")

else:
    # Welcome message
    st.info("👆 Upload a PDF file to get started")
    
    # Example/Demo section
    st.markdown("---")
    st.header("🎯 How It Works")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Step 1: Upload
        Upload your shuffled or disorganized PDF
        
        ### Step 2: Analysis
        The system analyzes:
        - Page numbers (multiple patterns)
        - Section headings (hierarchical)
        - Content similarity (AI embeddings)
        - Duplicates and missing pages
        """)
    
    with col2:
        st.markdown("""
        ### Step 3: Reordering
        Hybrid algorithm combines:
        - Page number sequences
        - Section numbering
        - Semantic continuity
        - Document structure
        
        ### Step 4: Export
        Get your reordered PDF with:
        - Proper page order
        - Table of contents
        - Detailed reports
        """)
