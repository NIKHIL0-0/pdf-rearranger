"""
Hybrid page ordering algorithm using multiple signals:
- Page numbers (highest confidence)
- Section headings/keywords
- Semantic similarity (continuity)
"""
import re
import numpy as np
from modules.embeddings import compute_similarity

# Weighting factors for scoring
WEIGHTS = {
    "page_number": 0.4,      # Page numbers important but not dominant
    "section_priority": 0.3,  # Section keywords & titles guide structure
    "semantic_continuity": 0.3 # Semantic flow prevents jumps
}

# Alternative weights when page numbers are unreliable
WEIGHTS_NO_PAGE_NUMS = {
    "page_number": 0.1,
    "section_priority": 0.4,
    "semantic_continuity": 0.5
}


def compute_page_scores(pages, embeddings, use_page_numbers=True):
    """
    Compute ordering scores for each page based on multiple signals.
    
    Args:
        pages: List of page dictionaries with metadata
        embeddings: Array of page embeddings
        use_page_numbers: Whether page numbers are reliable
        
    Returns:
        List of page dictionaries with added 'ordering_score' field
    """
    n = len(pages)
    weights = WEIGHTS if use_page_numbers else WEIGHTS_NO_PAGE_NUMS
    
    for i, page in enumerate(pages):
        score_components = {
            "page_number_score": 0.0,
            "section_score": 0.0,
            "continuity_score": 0.0,
            "title_score": 0.0
        }
        
        # 1. Page number confidence score
        page_num, confidence = page.get("page_number_detected", (None, 0.0))
        if page_num is not None and use_page_numbers:
            # Use page number directly as position indicator
            score_components["page_number_score"] = page_num * confidence
        
        # 2. Section priority score with title quality bonus
        section_score = page.get("section_priority", 0) / 10.0  # Normalize to 0-1
        title = page.get("title", "")
        
        # Boost for section numbers
        section_numeric = page.get("section_numeric_value")
        if section_numeric is not None:
            # Use section number as position indicator (normalized)
            section_score += (section_numeric / 100.0) * 0.5  # Moderate boost
        
        # Boost for clear titles (ALL CAPS, numbered sections)
        if title and title != "[BLANK PAGE]":
            if title.isupper():
                section_score += 0.2
            if re.match(r'^(\d+\.\d*|Article|Section|ANNEXURE|SCHEDULE)', title, re.IGNORECASE):
                section_score += 0.3
        
        # Penalty for blank pages
        if title == "[BLANK PAGE]":
            section_score = -1.0
        
        score_components["section_score"] = min(section_score, 1.0)
        
        # 3. Semantic continuity (average similarity to neighbors)
        if i > 0:
            prev_similarity = compute_similarity(embeddings[i-1], embeddings[i])
            score_components["continuity_score"] += prev_similarity
        if i < n - 1:
            next_similarity = compute_similarity(embeddings[i], embeddings[i+1])
            score_components["continuity_score"] += next_similarity
        
        # Average the continuity scores
        neighbor_count = min(i, 1) + min(n - i - 1, 1)
        if neighbor_count > 0:
            score_components["continuity_score"] /= neighbor_count
        
        # Compute weighted total score
        total_score = (
            weights["page_number"] * score_components["page_number_score"] +
            weights["section_priority"] * score_components["section_score"] +
            weights["semantic_continuity"] * score_components["continuity_score"]
        )
        
        page["score_components"] = score_components
        page["ordering_score"] = total_score
    
    return pages


def order_pages_by_page_numbers(pages):
    """
    Order pages primarily by detected page numbers.
    Pages without numbers are ordered by section numbers if available,
    otherwise placed at end in original order.
    
    Args:
        pages: List of page dictionaries
        
    Returns:
        Reordered list of pages with 'new_position' field
    """
    pages_with_numbers = []
    pages_without_numbers = []
    
    for page in pages:
        page_num, confidence = page.get("page_number_detected", (None, 0.0))
        if page_num is not None and confidence > 0.5:  # High confidence threshold
            pages_with_numbers.append(page)
        else:
            pages_without_numbers.append(page)
    
    # Sort pages with numbers by page number
    pages_with_numbers.sort(key=lambda p: p["page_number_detected"][0])
    
    # Sort pages without page numbers by section number if available
    def section_sort_key(p):
        # Use numeric section value if available
        section_val = p.get("section_numeric_value")
        if section_val is not None:
            return (0, section_val)  # Priority group 0
        # Fall back to original index
        return (1, p["page_index"])  # Priority group 1
    
    pages_without_numbers.sort(key=section_sort_key)
    
    # Combine: numbered pages first, then pages sorted by section
    ordered = pages_with_numbers + pages_without_numbers
    
    # Add new position index
    for new_idx, page in enumerate(ordered):
        page["new_position"] = new_idx
    
    return ordered


def order_pages_hybrid(pages, embeddings):
    """
    Main hybrid ordering algorithm.
    
    Strategy:
    1. Separate blank pages (always go to end)
    2. Check page number reliability (coverage + sequential consistency)
    3. If reliable page numbers (>70%) -> use page number ordering
    4. If some/no page numbers -> sort by section numbers, then position hints, then semantics
    5. Apply semantic continuity optimization
    6. Append blank pages at the end
    
    Args:
        pages: List of page dictionaries with all metadata
        embeddings: Array of page embeddings
        
    Returns:
        Tuple: (reordered_pages, ordering_metadata)
    """
    n = len(pages)
    
    # Separate blank pages - they always go to the end
    blank_pages = [p for p in pages if p.get("title") == "[BLANK PAGE]"]
    content_pages = [p for p in pages if p.get("title") != "[BLANK PAGE]"]
    
    if not content_pages:
        return blank_pages, {"total_pages": n, "ordering_method": "blank_only"}
    
    # Check how many pages have reliable page numbers
    pages_with_numbers = sum(
        1 for p in content_pages
        if p.get("page_number_detected", (None, 0.0))[0] is not None
    )
    page_number_coverage = pages_with_numbers / len(content_pages) if content_pages else 0
    
    # Check sequential consistency of page numbers
    numbered_pages = sorted(
        [p for p in content_pages if p.get("page_number_detected", (None, 0.0))[0] is not None],
        key=lambda p: p["page_number_detected"][0]
    )
    
    sequential_score = 1.0
    if len(numbered_pages) > 2:
        gaps = []
        for i in range(len(numbered_pages) - 1):
            curr_num = numbered_pages[i]["page_number_detected"][0]
            next_num = numbered_pages[i+1]["page_number_detected"][0]
            gaps.append(abs(next_num - curr_num))
        avg_gap = sum(gaps) / len(gaps)
        if avg_gap > 1.5:
            sequential_score = 0.5
    
    use_page_numbers = page_number_coverage >= 0.7 and sequential_score > 0.7
    
    ordering_metadata = {
        "total_pages": n,
        "content_pages": len(content_pages),
        "blank_pages": len(blank_pages),
        "pages_with_numbers": pages_with_numbers,
        "page_number_coverage": round(page_number_coverage, 2),
        "sequential_score": round(sequential_score, 2),
        "ordering_method": ""
    }
    
    # Strategy 1: High page number coverage
    if use_page_numbers:
        ordered = order_pages_by_page_numbers(content_pages)
        ordering_metadata["ordering_method"] = "page_numbers_primary"
        
    # Strategy 2: Sort by section numbers, position hints, and semantics
    else:
        # Debug: Show what we're sorting by
        print(f"\n   🔍 Using section_numbers_primary ordering:")
        pages_with_section_nums = [p for p in content_pages if p.get("section_numeric_value")]
        print(f"      Found {len(pages_with_section_nums)}/{len(content_pages)} pages with section numbers")
        
        # If NO section numbers found, warn and use alternative methods
        if len(pages_with_section_nums) == 0:
            print(f"      ⚠️  No section numbers detected!")
            print(f"      Using keyword-based positioning + semantic similarity")
            keyword_pages = sum(1 for p in content_pages if p.get("section_type") != "unknown")
            print(f"      Detected {keyword_pages} pages with keywords (Introduction, Conclusion, etc.)")
        elif len(content_pages) <= 20:
            # Only show detailed list for smaller documents
            for p in sorted(pages_with_section_nums, key=lambda x: x.get("section_numeric_value", 999999))[:10]:
                print(f"         {p.get('section_number')}: {p.get('title', '')[:50]}")
        
        # Create sort key: (section_numeric_value, position_hint, page_index)
        def content_sort_key(p):
            section_val = p.get("section_numeric_value")
            position_hint = p.get("position_hint", 500)
            page_idx = p["page_index"]
            
            # If section number exists, use it as primary sort
            if section_val is not None:
                return (0, section_val, 0, page_idx)  # Group 0: has section number
            
            # Otherwise use position hint from keywords
            return (1, 0, position_hint, page_idx)  # Group 1: use position hint
        
        content_pages_sorted = sorted(content_pages, key=content_sort_key)
        
        # Add new positions
        for new_idx, page in enumerate(content_pages_sorted):
            page["new_position"] = new_idx
        
        ordered = content_pages_sorted
        ordering_metadata["ordering_method"] = "section_numbers_primary"
        
        # Optional: Apply continuity optimization if we have good embeddings
        if len(content_pages) > 3:
            content_embeddings_ordered = [embeddings[p["page_index"]] for p in ordered]
            ordered = optimize_continuity(ordered, content_embeddings_ordered)
    
    # Append blank pages at the end
    final_ordered = ordered + blank_pages
    
    # Final position update
    for new_idx, page in enumerate(final_ordered):
        page["new_position"] = new_idx
    
    return final_ordered, ordering_metadata


def optimize_continuity(pages, embeddings):
    """
    Fine-tune ordering to maximize semantic continuity.
    Uses a sliding window to detect and fix local discontinuities.
    
    Args:
        pages: Ordered list of pages
        embeddings: Array of embeddings in the SAME ORDER as pages
        
    Returns:
        Optimized page ordering
    """
    # Embeddings should already be in the correct order
    if len(embeddings) != len(pages):
        return pages  # Safety check
    
    # Compute continuity scores
    continuity_scores = []
    for i in range(len(embeddings) - 1):
        sim = compute_similarity(embeddings[i], embeddings[i+1])
        continuity_scores.append(sim)
    
    # Find discontinuities (similarity < threshold)
    threshold = 0.3
    for i in range(len(continuity_scores)):
        if continuity_scores[i] < threshold and i + 2 < len(pages):
            # Check if swapping next two pages improves continuity
            if i + 3 < len(pages):
                # Calculate alternative similarity
                alt_sim = compute_similarity(
                    embeddings[i],
                    embeddings[i+2]
                )
                if alt_sim > continuity_scores[i] + 0.2:  # Significant improvement
                    # Swap pages i+1 and i+2
                    pages[i+1], pages[i+2] = pages[i+2], pages[i+1]
                    embeddings[i+1], embeddings[i+2] = embeddings[i+2], embeddings[i+1]
    
    # Update positions after optimization
    for new_idx, page in enumerate(pages):
        page["new_position"] = new_idx
    
    return pages


def generate_ordering_explanation(pages, ordering_metadata):
    """
    Generate human-readable explanation of ordering decisions.
    
    Args:
        pages: Ordered list of pages
        ordering_metadata: Metadata from ordering process
        
    Returns:
        String explanation
    """
    explanation_parts = []
    
    method = ordering_metadata.get('ordering_method', 'unknown')
    
    # Gemini AI has different metadata structure
    if method == 'gemini_ai':
        explanation_parts.append(f"Ordering Method: Gemini AI")
        explanation_parts.append(f"Document Type: {ordering_metadata.get('document_type', 'unknown')}")
        explanation_parts.append(f"Confidence: {ordering_metadata.get('confidence', 0)*100:.0f}%")
        explanation_parts.append(f"\nReasoning: {ordering_metadata.get('reasoning', 'N/A')}")
    else:
        explanation_parts.append(f"Ordering Method: {ordering_metadata['ordering_method']}")
        explanation_parts.append(f"Total Pages: {ordering_metadata['total_pages']}")
        explanation_parts.append(
            f"Page Number Coverage: {ordering_metadata.get('page_number_coverage', 0)*100:.0f}%"
        )
    
    if ordering_metadata['ordering_method'] == 'page_numbers_primary':
        explanation_parts.append(
            "\nPages were ordered primarily by detected page numbers. "
            "Pages without numbers were placed at the end."
        )
    else:
        explanation_parts.append(
            "\nPages were ordered using hybrid scoring combining:\n"
            f"- Page numbers ({WEIGHTS['page_number']*100:.0f}% weight)\n"
            f"- Section keywords ({WEIGHTS['section_priority']*100:.0f}% weight)\n"
            f"- Semantic continuity ({WEIGHTS['semantic_continuity']*100:.0f}% weight)"
        )
    
    # Show major reorderings
    major_moves = []
    for page in pages:
        original_pos = page["page_index"]
        new_pos = page["new_position"]
        if abs(new_pos - original_pos) > 3:  # Moved more than 3 positions
            major_moves.append((original_pos, new_pos, page.get("title", "Untitled")))
    
    if major_moves:
        explanation_parts.append(f"\nMajor reorderings ({len(major_moves)} pages):")
        for orig, new, title in major_moves[:5]:  # Show first 5
            explanation_parts.append(f"  Page {orig+1} → Position {new+1}: {title[:50]}")
    
    return "\n".join(explanation_parts)
