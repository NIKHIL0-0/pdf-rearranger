"""
Command-line interface for PDF reordering with batch processing support
"""
import sys
import os
import glob
from dotenv import load_dotenv
from processor import process_pdf_complete

# Load environment variables
load_dotenv()

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python cli.py uploads/document.pdf           # Single file")
        print("  python cli.py uploads                        # All PDFs in folder")
        print("  python cli.py uploads --gemini               # All PDFs with Gemini AI")
        print("  python cli.py uploads/document.pdf --gemini  # Single file with Gemini")
        print("  python cli.py uploads --gemini --api-key YOUR_KEY  # Override API key")
        print("\n💡 Add GEMINI_API_KEY to .env file or get key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    if not os.path.exists(input_path):
        print(f"❌ Error: Path not found: {input_path}")
        sys.exit(1)
    
    # Parse arguments
    use_gemini = '--gemini' in sys.argv
    # Get API key from environment variable
    gemini_api_key = os.getenv('GEMINI_API_KEY') if use_gemini else None
    
    # Validate API key if Gemini is requested
    if use_gemini and (not gemini_api_key or gemini_api_key == 'your_api_key_here'):
        print("❌ Error: Gemini API key not found!")
        print("   Add GEMINI_API_KEY to your .env file or use --api-key option")
        print("   Get API key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    
    # Override with command line API key if provided
    if '--api-key' in sys.argv:
        try:
            key_index = sys.argv.index('--api-key') + 1
            gemini_api_key = sys.argv[key_index]
        except (IndexError, ValueError):
            print("❌ Error: --api-key requires a value")
            sys.exit(1)
    
    # Determine if processing single file or folder
    if os.path.isdir(input_path):
        # Process all PDFs in folder
        pdf_files = glob.glob(os.path.join(input_path, "*.pdf"))
        
        if not pdf_files:
            print(f"❌ No PDF files found in: {input_path}")
            sys.exit(1)
        
        print(f"📁 Found {len(pdf_files)} PDF file(s) in {input_path}")
        print("=" * 70)
        
        if use_gemini:
            print("🤖 Gemini AI ordering enabled for all files")
            print("   Using: gemini-2.5-flash-lite model")
            print("   Mode: Intelligent document analysis and reordering")
        
        # Process each PDF
        for i, pdf_file in enumerate(pdf_files, 1):
            filename = os.path.basename(pdf_file)
            print(f"\n🔍 Processing [{i}/{len(pdf_files)}]: {filename}")
            print("-" * 50)
            
            try:
                result = process_pdf_complete(
                    pdf_file,
                    output_dir="outputs",
                    use_gemini=use_gemini,
                    gemini_api_key=gemini_api_key
                )
                
                if result and result.get("success"):
                    print(f"✅ {filename}: Completed successfully")
                    if use_gemini:
                        metadata = result.get("complete_report", {}).get("ordering_metadata", {})
                        if metadata.get("ordering_method") in ["gemini_ai", "gemini_ai_full_content"]:
                            doc_type = metadata.get("document_type", "unknown")
                            confidence = metadata.get("confidence", 0.0) * 100
                            sections = len(metadata.get("detected_sections", []))
                            print(f"   🧠 AI Analysis: {doc_type} ({confidence:.0f}% confidence)")
                            if sections > 0:
                                print(f"   📑 Detected sections: {sections}")
                else:
                    print(f"⚠️  {filename}: Processing completed with warnings")
                    
            except Exception as e:
                print(f"❌ {filename}: Error - {e}")
        
        print("\n" + "=" * 70)
        print("✅ Batch processing complete!")
        print(f"📁 All output files saved to: outputs/")
        
    elif input_path.endswith('.pdf'):
        # Process single file
        filename = os.path.basename(input_path)
        
        if use_gemini:
            print("🤖 Gemini AI ordering enabled")
            print("   Using: gemini-2.5-flash-lite model")
            print("   Mode: Intelligent document analysis and reordering")
        
        print(f"🔍 Processing: {filename}")
        print("=" * 70 + "\n")
        
        result = process_pdf_complete(
            input_path,
            output_dir="outputs",
            use_gemini=use_gemini,
            gemini_api_key=gemini_api_key
        )
    
    if result and result.get("success"):
        output_files = result.get("output_files", {})
        complete_report = result.get("complete_report", {})
        
        print("\n" + "=" * 70)
        print("✅ Processing Complete!")
        print("=" * 70)
        print(f"\n📄 Output PDF: {output_files.get('reordered_pdf', 'N/A')}")
        
        # Show missing pages if detected
        missing_pages = complete_report.get("missing_pages", [])
        if missing_pages:
            print(f"\n⚠️  Missing Pages: {missing_pages}")
        
            # Show ordering details
            ordering_metadata = complete_report.get("ordering_metadata", {})
            method = ordering_metadata.get('ordering_method', 'unknown')
            print(f"\n📊 Ordering Details:")
            print(f"   Method: {method}")
            
            if method in ['gemini_ai', 'gemini_ai_full_content', 'gemini_ai_structured']:
                print(f"   🤖 AI Document Type: {ordering_metadata.get('document_type', 'unknown')}")
                print(f"   🎯 AI Confidence: {ordering_metadata.get('confidence', 0)*100:.0f}%")
                print(f"   🧠 AI Analysis: {ordering_metadata.get('reasoning', 'N/A')[:100]}...")
                sections = len(ordering_metadata.get('detected_sections', []))
                if sections > 0:
                    print(f"   📑 Detected Sections: {sections}")
                chars = ordering_metadata.get('total_characters', 0)
                if chars > 0:
                    print(f"   📄 Document Size: {chars:,} characters")
                if 'structured' in method:
                    print(f"   ⚡ Optimized processing: Using structured summaries")
            else:
                print(f"   📄 Total Pages: {ordering_metadata.get('total_pages', 0)}")
                print(f"   📋 Page Number Coverage: {ordering_metadata.get('page_number_coverage', 0)*100:.0f}%")        # Show duplicate report if any
        duplicate_summary = complete_report.get("duplicate_summary", {})
        exact_dupes = duplicate_summary.get("exact_duplicate_count", 0)
        near_dupes = duplicate_summary.get("near_duplicate_count", 0)
        
        if exact_dupes > 0 or near_dupes > 0:
            print(f"\n🔍 Duplicates Found:")
            print(f"   Exact: {exact_dupes}")
            print(f"   Near: {near_dupes}")
    else:
        print("\n❌ Processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
