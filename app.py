from flask import Flask, request, jsonify, send_file
import os
import json
from processor import process_pdf_complete

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return jsonify({
        "message": "PDF Rearranger API",
        "version": "2.0",
        "description": "Intelligent PDF reordering with OCR, duplicate detection, and semantic analysis",
        "endpoints": {
            "upload": {
                "url": "/upload",
                "method": "POST",
                "description": "Upload and process a PDF with complete analysis",
                "parameters": {
                    "pdf": "PDF file (form-data)"
                }
            },
            "process": {
                "url": "/process/<filename>",
                "method": "POST",
                "description": "Process an already uploaded PDF"
            },
            "files": {
                "url": "/files",
                "method": "GET",
                "description": "List all uploaded and processed files"
            },
            "view": {
                "url": "/view/<filename>",
                "method": "GET",
                "description": "View processing results for a file"
            },
            "download": {
                "url": "/download/<filename>",
                "method": "GET",
                "description": "Download reordered PDF or TOC"
            }
        }
    })

@app.route("/files")
def list_files():
    """List all processed files and their outputs"""
    result = {
        "uploaded_files": [],
        "processed_outputs": []
    }
    
    # List uploaded files
    if os.path.exists(UPLOAD_FOLDER):
        pdf_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith('.pdf')]
        result["uploaded_files"] = pdf_files
    
    # List processed outputs
    if os.path.exists(OUTPUT_FOLDER):
        output_files = os.listdir(OUTPUT_FOLDER)
        result["processed_outputs"] = output_files
    
    return jsonify(result)

@app.route("/view/<filename>")
def view_processed_file(filename):
    """View the processed results of a specific file"""
    base_name = filename.replace('.pdf', '')
    json_filename = f"{base_name}_complete_report.json"
    json_path = os.path.join(OUTPUT_FOLDER, json_filename)
    
    if not os.path.exists(json_path):
        return jsonify({"error": f"Processed file {json_filename} not found"}), 404
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Failed to read processed file: {str(e)}"}), 500

@app.route("/download/<filename>")
def download_file(filename):
    """Download a processed file (reordered PDF, TOC, etc.)"""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": f"File {filename} not found"}), 404
    
    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Failed to send file: {str(e)}"}), 500

@app.route("/upload", methods=["POST"])
def upload_pdf():
    """Upload and immediately process a PDF"""
    if "pdf" not in request.files:
        return jsonify({"error": "PDF file required"}), 400

    file = request.files["pdf"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    filename = file.filename
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    # Process the PDF with complete pipeline
    try:
        result = process_pdf_complete(save_path, OUTPUT_FOLDER)
        
        return jsonify({
            "message": "Upload and processing successful",
            "file": filename,
            "success": result["success"],
            "output_files": result["output_files"],
            "summary": result["summary"]
        })
    
    except Exception as e:
        return jsonify({
            "error": f"Processing failed: {str(e)}"
        }), 500

@app.route("/process/<filename>", methods=["POST"])
def process_existing_pdf(filename):
    """Process an already uploaded PDF"""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": f"File {filename} not found in uploads"}), 404
    
    try:
        result = process_pdf_complete(file_path, OUTPUT_FOLDER)
        
        return jsonify({
            "message": "Processing successful",
            "file": filename,
            "success": result["success"],
            "output_files": result["output_files"],
            "summary": result["summary"]
        })
    
    except Exception as e:
        return jsonify({
            "error": f"Processing failed: {str(e)}"
        }), 500


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 PDF Rearranger API v2.0")
    print("=" * 70)
    print("\nFeatures:")
    print("  ✓ OCR fallback for scanned documents")
    print("  ✓ Page number detection")
    print("  ✓ Section classification with keywords")
    print("  ✓ Semantic similarity analysis")
    print("  ✓ Hybrid page ordering algorithm")
    print("  ✓ Duplicate detection (exact & near)")
    print("  ✓ Missing page detection")
    print("  ✓ PDF export with Table of Contents")
    print("\nServer starting at: http://127.0.0.1:5000")
    print("Upload endpoint: POST http://127.0.0.1:5000/upload")
    print("=" * 70)
    
    app.run(debug=True, host='127.0.0.1', port=5000)
