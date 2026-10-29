import os
import tempfile

import fitz   # PyMuPDF

MAX_PAGES = 10   # ignore PDFs longer than this (likely not a job posting)

def extract_text_from_pdf(file_path: str) -> dict:
    """
    Extracts text from a PDF file.
    Returns:
        success   (bool)
        text      (str)
        pages     (int)
        error     (str)  — only on failure
    """
    if not os.path.exists(file_path):
        return {"success": False, "error": "Uploaded file not found."}

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return {"success": False, "error": f"Could not open PDF: {str(e)}"}

    try:
        if len(doc) > MAX_PAGES:
            return {
                "success": False,
                "error": f"PDF has {len(doc)} pages — please upload a single job posting (max {MAX_PAGES} pages)."
            }

        full_text = []
        for page in doc:
            full_text.append(page.get_text("text"))
    except Exception:
        return {"success": False, "error": "Could not read PDF text. Please try another PDF."}
    finally:
        doc.close()

    combined = " ".join(full_text).strip()
    combined = " ".join(combined.split())   # collapse extra whitespace

    if len(combined) < 100:
        return {
            "success": False,
            "error": "PDF appears to be scanned/image-based with no extractable text. Please paste the text manually."
        }

    return {
        "success": True,
        "text": combined[:8000],
        "pages": len(full_text)
    }


def save_uploaded_pdf(file_storage, upload_folder: str) -> str:
    """
    Saves a Flask file upload to disk safely.
    Returns the saved file path.
    """
    os.makedirs(upload_folder, exist_ok=True)
    # Never derive paths from client filenames or share a path between requests.
    fd, save_path = tempfile.mkstemp(prefix="job_", suffix=".pdf", dir=upload_folder)
    try:
        with os.fdopen(fd, "wb") as destination:
            file_storage.save(destination)
    except Exception:
        os.remove(save_path)
        raise
    return save_path


def process_uploaded_pdf(file_storage, upload_folder: str) -> dict:
    """Extract an upload's text and remove its temporary file on every path."""
    save_path = save_uploaded_pdf(file_storage, upload_folder)
    try:
        return extract_text_from_pdf(save_path)
    finally:
        os.remove(save_path)
