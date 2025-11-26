"""
Main PDF processing pipeline integrating all modules with batch processing support
"""
import os
import sys
import glob
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from modules.extractor import extract_pages_text
from modules.page_numbers import detect_page_number, detect_missing_pages
from modules.headings import extract_title, classify_section, extract_section_number
from modules.embeddings import generate_embeddings
from modules.duplicates import (
    find_exact_duplicates, find_near_duplicates, 
    generate_duplicate_report, mark_duplicates
)
from modules.ordering import order_pages_hybrid, generate_ordering_explanation
from modules.llm_ordering import order_pages_with_gemini, GEMINI_AVAILABLE
from modules.export_pdf import export_all


def process_pdf_complete(pdf_path, output_dir="outputs", use_gemini=False, gemini_api_key=None):
    """
    Complete PDF processing pipeline.
    
    Steps:
    1. Extract text (with OCR fallback)
    2. Detect page numbers and titles
    3. Classify sections
    4. Generate embeddings
    5. Detect duplicates
    6. Detect missing pages
    7. Reorder pages using hybrid algorithm OR Gemini AI
    8. Export reordered PDF with TOC and reports
    
    Args:
        pdf_path: Path to input PDF
        output_dir: Directory for outputs
        use_gemini: Whether to use Gemini AI for ordering (default: False)
        gemini_api_key: Google API key for Gemini (required if use_gemini=True)
        
    Returns:
        Dictionary with processing results and output paths
    """
    print(f"Processing: {os.path.basename(pdf_path)}")
    print("=" * 70)
    
    # Step 1: Extract text from pages
    print(f"\nStep 1: Extracting text from pages...")
    pages = extract_pages_text(pdf_path)
    ocr_count = sum(1 for p in pages if p.get("ocr_used", False))
    print(f"   Extracted {len(pages)} pages ({ocr_count} used OCR)")
    
    # Step 2: Detect page numbers and titles
    print(f"\nStep 2: Detecting page numbers and titles...")
    
    # First pass: quick detection
    for page in pages:
        text = page["text"]
        header = page.get("header", "")
        footer = page.get("footer", "")
        
        # Detect page number with confidence
        page_num, confidence = detect_page_number(text, header, footer)
        page["page_number_detected"] = (page_num, confidence)
        
        # Quick title extraction
        title = extract_title(text, deep_analysis=False)
        page["title"] = title
    
    # Check if we need deep analysis (low page number coverage)
    pages_with_numbers = sum(1 for p in pages if p["page_number_detected"][0] is not None)
    page_num_coverage = pages_with_numbers / len(pages) if pages else 0
    
    # Second pass: deep analysis if needed
    if page_num_coverage < 0.7:
        print(f"   WARNING: Low page number coverage ({page_num_coverage*100:.0f}%), using deep title analysis...")
        for page in pages:
            if not page["page_number_detected"][0]:
                # Re-extract title with deep analysis
                title = extract_title(page["text"], deep_analysis=True)
                page["title"] = title
    
    # Extract section numbers from titles
    for page in pages:
        section_num, numeric_val = extract_section_number(page["title"])
        page["section_number"] = section_num
        page["section_numeric_value"] = numeric_val
    
    # Debug: show section numbers detected
    pages_with_sections = [p for p in pages if p["section_number"]]
    if pages_with_sections and page_num_coverage < 0.7:
        print(f"\n   📋 Section numbers detected:")
        for p in sorted(pages_with_sections, key=lambda x: (x["section_numeric_value"] or 999999, x["page_index"]))[:10]:
            print(f"      Page {p['page_index']}: {p['section_number']} - {p['title'][:50]}")
    
    blank_pages = sum(1 for p in pages if p.get("title") == "[BLANK PAGE]")
    print(f"   Detected page numbers on {pages_with_numbers}/{len(pages)} pages")
    print(f"   Extracted titles from {sum(1 for p in pages if p['title'] and p['title'] != '[BLANK PAGE]')} pages")
    print(f"   Section numbers on {len(pages_with_sections)} pages")
    if blank_pages > 0:
        print(f"   WARNING: Found {blank_pages} blank page(s)")
    
    # Step 3: Classify sections
    print(f"\nStep 3: Classifying sections...")
    for page in pages:
        section_type, priority, position_hint = classify_section(page["text"], page["title"])
        page["section_type"] = section_type
        page["section_priority"] = priority
        page["position_hint"] = position_hint
    
    classified = sum(1 for p in pages if p["section_type"] != "unknown")
    print(f"   Classified {classified} sections with keywords")
    
    # Step 4: Generate embeddings
    print(f"\nStep 4: Generating semantic embeddings...")
    texts = [p["text"] for p in pages]
    embeddings = generate_embeddings(texts)
    print(f"   Generated embeddings for {len(embeddings)} pages")
    
    # Step 5: Detect duplicates
    print("\nStep 5: Detecting duplicate pages...")
    exact_duplicates = find_exact_duplicates(pages)
    near_duplicates = find_near_duplicates(pages, embeddings, threshold=0.95)
    duplicate_report = generate_duplicate_report(pages, exact_duplicates, near_duplicates)
    mark_duplicates(pages, exact_duplicates, near_duplicates)
    
    print(f"   Found {len(exact_duplicates)} exact duplicate groups")
    print(f"   Found {len(near_duplicates)} near-duplicate pairs")
    
    # Step 6: Detect missing pages (only if we have page numbers OR using Gemini)
    missing_pages = []
    pages_with_numbers_list = [
        (p["page_index"], p["page_number_detected"][0])
        for p in pages
        if p["page_number_detected"][0] is not None
    ]
    
    # Only check for missing pages if we have meaningful page number coverage
    page_num_coverage = len(pages_with_numbers_list) / len(pages) if pages else 0
    
    if page_num_coverage >= 0.3 or (use_gemini and gemini_api_key):
        print("\nStep 6: Detecting missing pages...")
        missing_pages = detect_missing_pages(pages_with_numbers_list)
        
        if missing_pages:
            print(f"   ⚠ Missing pages detected: {missing_pages}")
        else:
            print(f"   No missing pages detected")
    else:
        print("\nStep 6: Skipping missing page detection (insufficient page numbers)...")
        print(f"   ℹ️  Only {len(pages_with_numbers_list)}/{len(pages)} pages have numbers")
    
    # Step 7: Reorder pages
    if use_gemini and GEMINI_AVAILABLE and gemini_api_key:
        print("\nStep 7: Reordering pages with Gemini AI...")
        gemini_result = order_pages_with_gemini(pages, gemini_api_key)
        
        if gemini_result[0] is not None:
            ordered_pages, ordering_metadata = gemini_result
            explanation = f"Gemini AI Analysis:\n{ordering_metadata.get('reasoning', '')}"
        else:
            print("   WARNING: Gemini ordering failed, falling back to hybrid algorithm...")
            ordered_pages, ordering_metadata = order_pages_hybrid(pages, embeddings)
            explanation = generate_ordering_explanation(ordered_pages, ordering_metadata)
    else:
        if use_gemini and not gemini_api_key:
            print("   WARNING: Gemini requested but no API key provided, using hybrid algorithm...")
        print("\nStep 7: Reordering pages with hybrid algorithm...")
        ordered_pages, ordering_metadata = order_pages_hybrid(pages, embeddings)
        explanation = generate_ordering_explanation(ordered_pages, ordering_metadata)
    
    reordered_count = sum(1 for p in ordered_pages if p["page_index"] != p["new_position"])
    print(f"   Reordered {reordered_count} pages")
    print(f"   Method: {ordering_metadata['ordering_method']}")
    
    # Step 8: Export all outputs
    print("\n💾 Step 8: Exporting results...")
    os.makedirs(output_dir, exist_ok=True)
    
    output_files = export_all(
        pdf_path, 
        ordered_pages, 
        ordering_metadata,
        duplicate_report,
        missing_pages,
        output_dir
    )
    
    # Save complete JSON report
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    json_path = os.path.join(output_dir, f"{base_name}_complete_report.json")
    
    complete_report = {
        "file": os.path.basename(pdf_path),
        "processing_summary": output_files.get("summary", {}),
        "ordering_explanation": explanation,
        "ordering_metadata": ordering_metadata,
        "duplicate_report": duplicate_report,
        "missing_pages": missing_pages,
        "pages": [
            {
                "original_index": p["page_index"],
                "new_position": p["new_position"],
                "page_number_detected": p["page_number_detected"][0],
                "page_number_confidence": p["page_number_detected"][1],
                "title": p["title"],
                "section_type": p["section_type"],
                "section_priority": p["section_priority"],
                "is_exact_duplicate": p.get("is_exact_duplicate", False),
                "is_near_duplicate": p.get("is_near_duplicate", False),
                "ocr_used": p.get("ocr_used", False),
                "text_preview": p["text"][:200]
            }
            for p in ordered_pages
        ]
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(complete_report, f, indent=2, ensure_ascii=False)
    
    output_files["complete_report_json"] = json_path
    
    print(f"   Reordered PDF: {output_files.get('reordered_pdf', 'N/A')}")
    print(f"   TOC PDF: {output_files.get('toc_pdf', 'N/A')}")
    print(f"   TOC Text: {output_files.get('toc_text', 'N/A')}")
    print(f"   Complete Report: {json_path}")
    
    print("\n" + "=" * 70)
    print("✅ Processing complete!")
    
    return {
        "success": True,
        "output_files": output_files,
        "summary": output_files.get("summary", {}),
        "complete_report": complete_report
    }


if __name__ == "__main__":
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python processor.py uploads/document.pdf    # Single file")
        print("  python processor.py uploads                 # All PDFs in folder")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    if not os.path.exists(input_path):
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)
    
    # Check if it's a directory or single file
    if os.path.isdir(input_path):
        # Batch process all PDFs in directory
        pdf_files = glob.glob(os.path.join(input_path, "*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in: {input_path}")
            sys.exit(1)
        
        print(f"📁 Found {len(pdf_files)} PDF file(s) in {input_path}")
        print("=" * 70)
        
        # Process each PDF
        for i, pdf_file in enumerate(pdf_files, 1):
            filename = os.path.basename(pdf_file)
            print(f"\nProcessing [{i}/{len(pdf_files)}]: {filename}")
            print("-" * 50)
            
            try:
                result = process_pdf_complete(pdf_file)
                
                if result["success"]:
                    print(f"✅ {filename}: Completed successfully")
                    summary = result["summary"]
                    print(f"   Pages: {summary['document_info']['total_pages']}")
                    print(f"   Reordered: {summary['document_info']['pages_reordered']}")
                    if summary['duplicates']['exact_duplicates'] > 0:
                        print(f"   Duplicates: {summary['duplicates']['exact_duplicates']} exact")
                else:
                    print(f"⚠️  {filename}: Processing completed with warnings")
                    
            except Exception as e:
                print(f"❌ {filename}: Error - {e}")
        
        print("\n" + "=" * 70)
        print("✅ Batch processing complete!")
        print(f"📁 All output files saved to: outputs/")
        
    elif input_path.endswith('.pdf'):
        # Process single file (original behavior)
        result = process_pdf_complete(input_path)
        
        if result["success"]:
            print("\n📊 Summary:")
            summary = result["summary"]
            print(f"   Total pages: {summary['document_info']['total_pages']}")
            print(f"   Pages reordered: {summary['document_info']['pages_reordered']}")
            print(f"   OCR pages: {summary['document_info']['ocr_pages']}")
            print(f"   Exact duplicates: {summary['duplicates']['exact_duplicates']}")
            print(f"   Near duplicates: {summary['duplicates']['near_duplicates']}")
            print(f"   Missing pages: {summary['missing_pages']['count']}")
    
    else:
        print(f"Error: Invalid input: {input_path}")
        print("Please provide a PDF file or folder containing PDFs")
        sys.exit(1)
