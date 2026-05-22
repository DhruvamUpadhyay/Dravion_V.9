import os
import fitz  # PyMuPDF
from docx import Document
from core.logger import log

def read_document(path):
    """Reads the text content of a PDF or DOCX file."""
    if not os.path.exists(path):
        return f"File not found: {path}"
        
    ext = path.lower().split('.')[-1]
    
    if ext == 'pdf':
        try:
            doc = fitz.open(path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text if text.strip() else "(PDF seems to contain no extractable text, might be images)"
        except Exception as e:
            return f"Error reading PDF: {e}"
            
    elif ext == 'docx':
        try:
            doc = Document(path)
            text = "\n".join([p.text for p in doc.paragraphs])
            return text if text.strip() else "(DOCX seems to be empty)"
        except Exception as e:
            return f"Error reading DOCX: {e}"
            
    else:
        return f"Unsupported document format: {ext}. Only PDF and DOCX are supported."
