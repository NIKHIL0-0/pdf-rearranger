"""
Export reordered PDF with Table of Contents and reports
"""
import fitz  # PyMuPDF
import os
from datetime import datetime

def create_toc(pages):
    """
    Generate Table of Contents from page titles with hierarchical levels.
    
    Args:
        pages: List of ordered page dictionaries
        
    Returns:
        List of TOC entries: [(level, title, page_number), ...]
    """
    toc = []
    
    for idx, page in enumerate(pages):
        title = page.get("title") or f"Page {idx + 1}"
        page_number = idx + 1  # 1-based page numbering
        
        # Skip blank pages in TOC
        if title == "[BLANK PAGE]":
            continue
        
        # Determine hierarchy level based on section number first
        section_num = page.get("section_number")
        if section_num:
            # Calculate level from section number depth
            # "3" -> level 1, "3.1" -> level 2, "3.1.2" -> level 3
            level = min(section_num.count('.') + 1, 4)  # Max level 4
            
            # Prepend section number to title if not already there
            if not title.startswith(section_num):
                title = f"{section_num} {title}"
        else:
            # Fallback to section type for level
            section_type = page.get("section_type", "unknown")
            
            # Level 1: Major sections
            level_1_types = ["definitions", "table of contents", "summary", "executive summary",
                            "introduction", "conclusion", "signatures", "annexure", "annex"]
            
            # Level 2: Sub-sections  
            level_2_types = ["appendix", "schedule", "repayment schedule", "terms and conditions"]
            
            if section_type in level_1_types:
                level = 1
            elif section_type in level_2_types:
                level = 2
            else:
                level = 1  # Default to level 1 for visibility
        
        toc.append((level, title, page_number))
    
    return toc


def format_toc_text(toc):
    """
    Format TOC as text for display or export.
    
    Args:
        toc: List of TOC entries
        
    Returns:
        Formatted string
    """
    lines = ["TABLE OF CONTENTS", "=" * 60, ""]
    
    for level, title, page_num in toc:
        # Handle None or blank titles
        if not title or title == "[BLANK PAGE]":
            title = "(Untitled Page)"
        
        indent = "  " * (level - 1)
        # Truncate long titles
        display_title = title[:70] + "..." if len(title) > 70 else title
        lines.append(f"{indent}{display_title} ... Page {page_num}")
    
    return "\n".join(lines)


def create_missing_pages_report(missing_pages):
    """
    Generate missing pages report.
    
    Args:
        missing_pages: List of missing page numbers
        
    Returns:
        Dictionary report
    """
    if not missing_pages:
        return {
            "status": "No missing pages detected",
            "missing_count": 0,
            "missing_pages": []
        }
    
    return {
        "status": "Missing pages detected",
        "missing_count": len(missing_pages),
        "missing_pages": sorted(missing_pages),
        "ranges": _format_page_ranges(missing_pages)
    }


def _format_page_ranges(pages):
    """
    Format list of pages into ranges (e.g., [1,2,3,5,6] -> "1-3, 5-6")
    
    Args:
        pages: List of page numbers
        
    Returns:
        String of formatted ranges
    """
    if not pages:
        return ""
    
    sorted_pages = sorted(pages)
    ranges = []
    start = sorted_pages[0]
    end = sorted_pages[0]
    
    for i in range(1, len(sorted_pages)):
        if sorted_pages[i] == end + 1:
            end = sorted_pages[i]
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = sorted_pages[i]
            end = sorted_pages[i]
    
    # Add last range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    return ", ".join(ranges)


def export_reordered_pdf(original_pdf_path, ordered_pages, output_path):
    """
    Create new PDF with pages in the correct order.
    
    Args:
        original_pdf_path: Path to original PDF
        ordered_pages: List of page dictionaries in new order
        output_path: Path for output PDF
        
    Returns:
        True if successful
    """
    try:
        src_doc = fitz.open(original_pdf_path)
        dest_doc = fitz.open()  # New empty PDF
        
        # Copy pages in new order
        for page_info in ordered_pages:
            original_index = page_info["page_index"]
            dest_doc.insert_pdf(src_doc, from_page=original_index, to_page=original_index)
        
        # Add metadata
        now_str = datetime.now().strftime("D:%Y%m%d%H%M%S")
        metadata = {
            "title": "Reordered Document",
            "author": "PDF Rearranger",
            "subject": "Automatically reordered PDF",
            "creator": "PDF Rearranger System",
            "producer": "PyMuPDF",
            "creationDate": now_str,
            "modDate": now_str
        }
        dest_doc.set_metadata(metadata)
        
        # Save
        dest_doc.save(output_path)
        dest_doc.close()
        src_doc.close()
        
        return True
    
    except Exception as e:
        print(f"Error exporting PDF: {e}")
        return False


def add_toc_to_pdf(pdf_path, toc):
    """
    Add PDF outline/bookmarks based on TOC.
    
    Args:
        pdf_path: Path to PDF file
        toc: List of TOC entries
    """
    try:
        doc = fitz.open(pdf_path)
        
        # Convert our TOC format to PyMuPDF format
        # PyMuPDF expects: [level, title, page_num]
        outline = []
        prev_level = 1
        
        for level, title, page_num in toc:
            # Handle None or blank titles
            if not title or title == "[BLANK PAGE]":
                title = "(Untitled Page)"
            
            # Ensure level doesn't jump more than 1 from previous
            if level > prev_level + 1:
                level = prev_level + 1
            
            # Ensure level is at least 1
            level = max(1, level)
            
            # page_num is 1-based, PyMuPDF uses 0-based
            outline.append([level, title, page_num - 1])
            prev_level = level
        
        if outline:
            doc.set_toc(outline)
            doc.save(pdf_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        doc.close()
        
        return True
    
    except Exception as e:
        print(f"Error adding TOC to PDF: {e}")
        return False


def create_toc_page(toc, output_path):
    """
    Create a standalone PDF page with the Table of Contents.
    
    Args:
        toc: List of TOC entries
        output_path: Path for TOC PDF
        
    Returns:
        True if successful
    """
    try:
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4 size
        
        # Set up text
        text = format_toc_text(toc)
        
        # Insert text with formatting
        text_rect = fitz.Rect(50, 50, 545, 792)
        page.insert_textbox(
            text_rect,
            text,
            fontsize=10,
            fontname="helv",
            color=(0, 0, 0)
        )
        
        doc.save(output_path)
        doc.close()
        
        return True
    
    except Exception as e:
        print(f"Error creating TOC page: {e}")
        return False


def generate_summary_report(pages, ordering_metadata, duplicate_report, missing_pages):
    """
    Generate comprehensive summary report of all processing.
    
    Args:
        pages: Processed pages
        ordering_metadata: Metadata from ordering
        duplicate_report: Duplicate detection report
        missing_pages: List of missing page numbers
        
    Returns:
        Dictionary with complete summary
    """
    report = {
        "processing_date": datetime.now().isoformat(),
        "document_info": {
            "total_pages": len(pages),
            "pages_reordered": sum(1 for p in pages if p["page_index"] != p["new_position"]),
            "ocr_pages": sum(1 for p in pages if p.get("ocr_used", False))
        },
        "ordering": ordering_metadata,
        "duplicates": {
            "exact_duplicates": duplicate_report["summary"]["exact_duplicate_count"],
            "near_duplicates": duplicate_report["summary"]["near_duplicate_count"]
        },
        "missing_pages": {
            "count": len(missing_pages),
            "pages": missing_pages
        },
        "quality_metrics": {
            "page_number_coverage": ordering_metadata.get("page_number_coverage", 0),
            "titles_extracted": sum(1 for p in pages if p.get("title")),
            "sections_classified": sum(1 for p in pages if p.get("section_type") != "unknown")
        }
    }
    
    return report


def export_all(original_pdf_path, pages, ordering_metadata, duplicate_report, 
               missing_pages, output_dir="outputs"):
    """
    Export all outputs: reordered PDF, TOC, and reports.
    
    Args:
        original_pdf_path: Path to original PDF
        pages: Ordered pages with metadata
        ordering_metadata: Ordering information
        duplicate_report: Duplicate detection results
        missing_pages: List of missing page numbers
        output_dir: Output directory path
        
    Returns:
        Dictionary with paths to all generated files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base filename
    base_name = os.path.splitext(os.path.basename(original_pdf_path))[0]
    
    outputs = {}
    
    # 1. Export reordered PDF
    reordered_pdf_path = os.path.join(output_dir, f"{base_name}_reordered.pdf")
    if export_reordered_pdf(original_pdf_path, pages, reordered_pdf_path):
        outputs["reordered_pdf"] = reordered_pdf_path
        
        # 2. Add TOC to the reordered PDF
        toc = create_toc(pages)
        add_toc_to_pdf(reordered_pdf_path, toc)
    
    # 3. Export standalone TOC
    toc_pdf_path = os.path.join(output_dir, f"{base_name}_toc.pdf")
    toc = create_toc(pages)
    if create_toc_page(toc, toc_pdf_path):
        outputs["toc_pdf"] = toc_pdf_path
    
    # 4. Export TOC as text
    toc_text_path = os.path.join(output_dir, f"{base_name}_toc.txt")
    with open(toc_text_path, 'w', encoding='utf-8') as f:
        f.write(format_toc_text(toc))
    outputs["toc_text"] = toc_text_path
    
    # 5. Export duplicate report (already in JSON format via main process)
    
    # 6. Export missing pages report
    missing_report = create_missing_pages_report(missing_pages)
    
    # 7. Export summary report
    summary = generate_summary_report(pages, ordering_metadata, duplicate_report, missing_pages)
    outputs["summary"] = summary
    
    return outputs
