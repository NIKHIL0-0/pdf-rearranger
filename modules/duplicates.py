"""
Duplicate page detection using content hashing and semantic similarity
"""
import hashlib
from modules.embeddings import compute_similarity

def compute_page_hash(text):
    """
    Compute SHA-256 hash of page text content.
    
    Args:
        text: Page text content
        
    Returns:
        Hexadecimal hash string
    """
    # Normalize text: strip whitespace, lowercase
    normalized = text.strip().lower()
    
    # Compute SHA-256 hash
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    return hash_obj.hexdigest()


def find_exact_duplicates(pages):
    """
    Find exact duplicate pages using content hashing.
    
    Args:
        pages: List of page dictionaries with 'text' field
        
    Returns:
        List of duplicate groups: [[page_idx1, page_idx2], ...]
    """
    hash_map = {}  # hash -> list of page indices
    
    for idx, page in enumerate(pages):
        text = page.get("text", "")
        page_hash = compute_page_hash(text)
        
        if page_hash not in hash_map:
            hash_map[page_hash] = []
        hash_map[page_hash].append(idx)
    
    # Find groups with more than one page (duplicates)
    duplicates = [indices for indices in hash_map.values() if len(indices) > 1]
    
    return duplicates


def find_near_duplicates(pages, embeddings, threshold=0.95):
    """
    Find near-duplicate pages using embedding similarity.
    
    Args:
        pages: List of page dictionaries
        embeddings: Array of page embeddings
        threshold: Similarity threshold (default 0.95)
        
    Returns:
        List of near-duplicate pairs: [(idx1, idx2, similarity), ...]
    """
    near_duplicates = []
    n = len(embeddings)
    
    # Compare each pair of pages
    for i in range(n):
        for j in range(i + 1, n):
            similarity = compute_similarity(embeddings[i], embeddings[j])
            
            if similarity >= threshold:
                near_duplicates.append((i, j, similarity))
    
    return near_duplicates


def generate_duplicate_report(pages, exact_duplicates, near_duplicates):
    """
    Generate a human-readable duplicate detection report.
    
    Args:
        pages: List of page dictionaries
        exact_duplicates: List of exact duplicate groups
        near_duplicates: List of near-duplicate pairs
        
    Returns:
        Dictionary with duplicate report
    """
    report = {
        "total_pages": len(pages),
        "exact_duplicates": [],
        "near_duplicates": [],
        "summary": {
            "exact_duplicate_count": sum(len(group) - 1 for group in exact_duplicates),
            "near_duplicate_count": len(near_duplicates)
        }
    }
    
    # Format exact duplicates
    for group in exact_duplicates:
        # Get title from first page in group
        first_page = pages[group[0]]
        title = first_page.get("title", "Untitled")
        
        report["exact_duplicates"].append({
            "page_indices": group,
            "page_numbers": [i + 1 for i in group],  # 1-based for display
            "title": title,
            "text_preview": first_page.get("text", "")[:100]
        })
    
    # Format near duplicates
    for idx1, idx2, similarity in near_duplicates:
        page1 = pages[idx1]
        page2 = pages[idx2]
        
        report["near_duplicates"].append({
            "page_1_index": idx1,
            "page_2_index": idx2,
            "page_1_number": idx1 + 1,
            "page_2_number": idx2 + 1,
            "similarity": round(similarity, 3),
            "page_1_title": page1.get("title", "Untitled"),
            "page_2_title": page2.get("title", "Untitled"),
            "page_1_preview": page1.get("text", "")[:100],
            "page_2_preview": page2.get("text", "")[:100]
        })
    
    return report


def mark_duplicates(pages, exact_duplicates, near_duplicates):
    """
    Add duplicate flags to page dictionaries.
    
    Args:
        pages: List of page dictionaries (modified in-place)
        exact_duplicates: List of exact duplicate groups
        near_duplicates: List of near-duplicate pairs
    """
    # Initialize flags
    for page in pages:
        page["is_exact_duplicate"] = False
        page["is_near_duplicate"] = False
        page["duplicate_of"] = []
    
    # Mark exact duplicates (keep first occurrence, flag others)
    for group in exact_duplicates:
        if len(group) > 1:
            original_idx = group[0]
            for dup_idx in group[1:]:
                pages[dup_idx]["is_exact_duplicate"] = True
                pages[dup_idx]["duplicate_of"].append(original_idx)
    
    # Mark near duplicates
    for idx1, idx2, similarity in near_duplicates:
        pages[idx2]["is_near_duplicate"] = True
        pages[idx2]["duplicate_of"].append(idx1)
        pages[idx2]["duplicate_similarity"] = similarity
