"""
LLM-based PDF ordering using Google Gemini
"""
import os
import json

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("WARNING: Google Generative AI not installed. Run: pip install google-generativeai")


def configure_gemini(api_key):
    """
    Configure Gemini API with the provided key.
    
    Args:
        api_key: Google API key for Gemini
        
    Returns:
        Boolean indicating success
    """
    if not GEMINI_AVAILABLE:
        return False
    
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"WARNING: Error configuring Gemini: {e}")
        return False


def order_pages_with_gemini(pages, api_key=None):
    """
    Use Gemini 2.5 Flash-Lite to analyze COMPLETE page content and order pages.
    
    Args:
        pages: List of page dictionaries with COMPLETE extracted text
        api_key: Google API key (optional if already configured)
        
    Returns:
        Tuple: (reordered_pages, ordering_metadata)
    """
    if not GEMINI_AVAILABLE:
        print("WARNING: Gemini not available, falling back to rule-based ordering")
        return None, {"error": "gemini_not_available"}
    
    if api_key:
        if not configure_gemini(api_key):
            return None, {"error": "configuration_failed"}
    
    try:
        # Prepare structured page summaries for Gemini (more efficient than full text)
        page_summaries = []
        total_chars = sum(len(page.get("text", "")) for page in pages)
        
        for idx, page in enumerate(pages):
            # Extract key information from each page
            text = page.get("text", "")
            
            # Get first 3 and last 3 lines for context
            lines = text.split('\n')
            header_lines = lines[:3] if len(lines) >= 3 else lines
            footer_lines = lines[-3:] if len(lines) >= 3 else lines
            
            # Find potential titles (lines with fewer than 10 words, not empty)
            potential_titles = []
            for line in lines[:10]:  # Check first 10 lines
                cleaned = line.strip()
                if cleaned and len(cleaned.split()) <= 10 and len(cleaned) > 5:
                    potential_titles.append(cleaned)
            
            summary = {
                "page_index": idx,
                "text_length": len(text),
                "header_content": " ".join(header_lines).strip()[:200],
                "footer_content": " ".join(footer_lines).strip()[:200],
                "potential_titles": potential_titles[:3],  # Top 3 potential titles
                "text_preview": text.replace('\n', ' ').strip()[:400],  # 400 chars preview
                "detected_page_number": page.get("page_number_detected", [None, 0])[0],
                "detected_section": page.get("section_number", None),
                "detected_title": page.get("title", "").strip()[:100]
            }
            page_summaries.append(summary)
        
        # Create efficient prompt for Gemini
        prompt = f"""You are analyzing a shuffled PDF document with {len(pages)} pages (total: {total_chars:,} characters).

Here is structured information from each page:

{json.dumps(page_summaries, indent=2)}

Based on this analysis, please:
1. Determine document type and structure
2. Identify the logical reading order
3. Detect patterns in titles, headers, and content flow

Return ONLY a valid JSON object:
{{
  "document_type": "academic paper|legal document|book|report|manual|other",
  "confidence": 0.0-1.0,
  "reasoning": "explanation of ordering logic based on content patterns",
  "detected_sections": ["list of main section titles found"],
  "correct_order": [array of page indices in correct reading order]
}}"""

        # Use Gemini 2.5 Flash-Lite with structured summaries
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        print("🤖 Sending structured page summaries to Gemini for analysis...")
        print(f"   Document size: {total_chars:,} characters across {len(pages)} pages")
        print(f"   Using efficient summary approach for better processing...")
        
        response = model.generate_content(prompt)
        
        # Parse response
        response_text = response.text.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        result = json.loads(response_text)
        
        # Validate the response
        if "correct_order" not in result:
            raise ValueError("Response missing 'correct_order' field")
        
        order_indices = result["correct_order"]
        
        # Validate indices
        if len(order_indices) != len(pages):
            raise ValueError(f"Order has {len(order_indices)} pages but document has {len(pages)}")
        
        if set(order_indices) != set(range(len(pages))):
            raise ValueError("Invalid page indices in order")
        
        # Reorder pages
        reordered_pages = [pages[idx] for idx in order_indices]
        
        # Update positions
        for new_idx, page in enumerate(reordered_pages):
            page["new_position"] = new_idx
        
        metadata = {
            "ordering_method": "gemini_ai_structured",
            "document_type": result.get("document_type", "unknown"),
            "confidence": result.get("confidence", 0.0),
            "reasoning": result.get("reasoning", ""),
            "detected_sections": result.get("detected_sections", []),
            "total_pages": len(pages),
            "total_characters": total_chars,
            "page_number_coverage": 0.0,  # Gemini analyzes from structured data
            "content_pages": len(pages),
            "blank_pages": 0
        }
        
        print(f"✅ Gemini structured analysis complete!")
        print(f"   Document type: {metadata['document_type']}")
        print(f"   Confidence: {metadata['confidence']:.0%}")
        print(f"   Detected sections: {len(metadata.get('detected_sections', []))}")
        print(f"   Analysis: {metadata['reasoning'][:120]}...")
        
        return reordered_pages, metadata
        
    except json.JSONDecodeError as e:
        print(f"⚠️  Error parsing Gemini response: {e}")
        print(f"   Response: {response_text[:200]}...")
        return None, {"error": "invalid_json_response"}
    
    except Exception as e:
        print(f"⚠️  Error using Gemini: {e}")
        return None, {"error": str(e)}


def get_gemini_explanation(pages, ordering_metadata):
    """
    Get a natural language explanation of the ordering from Gemini.
    
    Args:
        pages: Ordered list of pages
        ordering_metadata: Metadata about the ordering
        
    Returns:
        String explanation
    """
    if not GEMINI_AVAILABLE:
        return "Gemini explanations not available (library not installed)"
    
    try:
        # Create summary
        summary = f"""Document was reordered using {ordering_metadata.get('ordering_method', 'unknown')} method.
Total pages: {ordering_metadata.get('total_pages', 0)}
Pages reordered: {sum(1 for p in pages if p.get('page_index') != p.get('new_position', 0))}

First 5 pages in new order:
"""
        for i, page in enumerate(pages[:5]):
            summary += f"\n{i+1}. {page.get('title', 'Untitled')[:60]}"
        
        return summary
        
    except Exception as e:
        return f"Error generating explanation: {e}"
