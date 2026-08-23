"""
ocr.py — Receipt OCR service.
- Validates file type (JPEG, PNG, PDF, TIFF, BMP, WEBP).
- Primary: Tesseract OCR for local text extraction.
- Raises HTTPException with clear messages for invalid/unsupported files.
"""
import re
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional
from fastapi import HTTPException


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".webp", ".bmp", ".tiff", ".tif"}
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "image/bmp", "image/tiff", "application/pdf",
}


def validate_file(filename: str, content_type: str):
    """Raise HTTPException if file is not a supported image or PDF."""
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid file type '{ext}'. "
                "Please upload a valid receipt image (JPEG, PNG, PDF, TIFF, BMP, WEBP)."
            ),
        )
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported content type '{content_type}'. "
                "Please upload a valid receipt image or PDF."
            ),
        )


def _pdf_to_images(pdf_path: str, max_pages: int = 5):
    """Render up to five PDF pages to PIL images using PyMuPDF."""
    try:
        import fitz
        from PIL import Image
        import io
        document = fitz.open(pdf_path)
        if document.page_count < 1:
            raise HTTPException(status_code=400, detail="Could not read PDF. Make sure it contains at least one page.")
        images=[]
        for index in range(min(document.page_count, max_pages)):
            page=document.load_page(index)
            pix=page.get_pixmap(matrix=fitz.Matrix(2.5,2.5), alpha=False)
            image=Image.open(io.BytesIO(pix.tobytes("png")))
            image.load(); images.append(image)
        document.close(); return images
    except HTTPException: raise
    except ImportError:
        raise HTTPException(status_code=503, detail="PDF support is not installed. Run 'pip install PyMuPDF' in the backend environment.")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {str(exc)[:180]}")

def _extract_pdf_text(file_path: str) -> Optional[str]:
    """Extract text directly from a text-based PDF before falling back to OCR."""
    try:
        import fitz
        document = fitz.open(file_path)
        chunks = []
        for index in range(min(document.page_count, 10)):
            text = document.load_page(index).get_text("text")
            if text and text.strip():
                chunks.append(text.strip())
        document.close()
        result = "\n\n".join(chunks).strip()
        return result if len(result) >= 10 else None
    except Exception:
        return None


def _is_tesseract_available() -> bool:
    """Check if Tesseract OCR is installed and accessible."""
    try:
        import pytesseract
        from app.core.config import get_settings
        settings = get_settings()
        tesseract_cmd = settings.TESSERACT_CMD
        if not tesseract_cmd:
            candidates = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
            for c in candidates:
                if os.path.isfile(c):
                    tesseract_cmd = c
                    break
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _run_tesseract(image) -> str:
    """Run Tesseract OCR on a PIL Image. Returns raw text."""
    import pytesseract
    from app.core.config import get_settings
    settings = get_settings()

    tesseract_cmd = settings.TESSERACT_CMD
    if not tesseract_cmd:
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                tesseract_cmd = c
                break

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    pytesseract.get_tesseract_version()

    from PIL import ImageEnhance, ImageFilter
    image = image.convert("L")
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = image.filter(ImageFilter.SHARPEN)
    text = pytesseract.image_to_string(image, config="--psm 6")
    return text.strip()


def _extract_with_tesseract(file_path: str) -> Optional[str]:
    """OCR images and up to five pages of a scanned PDF."""
    from PIL import Image
    ext=os.path.splitext(file_path.lower())[1]
    try:
        images=_pdf_to_images(file_path) if ext==".pdf" else [Image.open(file_path)]
    except Exception:
        return None
    chunks=[]
    for image in images:
        try:
            text=_run_tesseract(image)
            if text.strip(): chunks.append(text.strip())
        except Exception:
            continue
    result="\n\n--- PAGE BREAK ---\n\n".join(chunks).strip()
    return result if len(result)>=10 else None

def extract_text(file_path: str) -> str:
    """
    Load file, convert if needed, run local OCR, and return raw text.
    Uses PyMuPDF for PDF text extraction and Tesseract for scanned PDFs/images.
    """
    # Validate the file is actually an image before processing
    ext = os.path.splitext(file_path.lower())[1]
    try:
        if ext != ".pdf":
            from PIL import Image
            image = Image.open(file_path)
            image.verify()
            # Re-open after verify
            image = Image.open(file_path)
            # Check it has actual content (not a 1x1 pixel or blank)
            if image.size[0] < 50 or image.size[1] < 50:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "The image is too small or appears to be empty. "
                        "Please upload a clear receipt photo."
                    ),
                )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded file is corrupted or not a valid image. "
                "Please upload a clear receipt photo (JPEG, PNG, PDF, TIFF, BMP, WEBP)."
            ),
        )

    # Text-based PDFs do not need OCR at all. This also makes ordinary
    # invoices/statements work even when Tesseract is not installed.
    if ext == ".pdf":
        pdf_text = _extract_pdf_text(file_path)
        if pdf_text:
            return pdf_text

    # Use local Tesseract OCR for receipt images and scanned PDFs.
    if not _is_tesseract_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "OCR is not available. Please install Tesseract OCR and make sure "
                "TESSERACT_CMD in the backend .env points to tesseract.exe."
            ),
        )

    raw_text = _extract_with_tesseract(file_path)
    if raw_text and len(raw_text.strip()) >= 10:
        return raw_text

    raise HTTPException(
        status_code=422,
        detail=(
            "Could not extract enough text from this receipt. Please upload a "
            "clear, well-lit image or a PDF with readable text."
        ),
    )


def parse_receipt(raw_text: str) -> dict:
    """
    Parse OCR text into structured fields.
    Uses multiple regex patterns to handle varied receipt formats.
    """
    merchant: Optional[str] = None
    total_amount: Optional[Decimal] = None
    receipt_date: Optional[date] = None
    tax_amount: Optional[Decimal] = None

    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    # ── Merchant: prefer explicit merchant/store labels, otherwise choose a
    # meaningful header line while skipping greetings/OCR noise.
    generic = {"dear all", "dear sir", "dear madam", "invoice", "receipt", "tax invoice", "bill", "thank you"}
    for line in lines[:12]:
        if re.search(r"(?:merchant|store|seller|vendor|restaurant)\s*[:#-]", line, re.I):
            merchant = re.split(r"[:#-]", line, maxsplit=1)[-1].strip(); break
    if not merchant:
        for line in lines[:10]:
            clean=re.sub(r"[^a-zA-Z0-9 &.'-]", "", line).strip()
            if len(clean)>=3 and clean.lower() not in generic and not re.fullmatch(r"[0-9 .-]+", clean):
                merchant=clean; break

    # ── Total amount: try multiple patterns in priority order
    total_patterns = [
        r"(?:grand\s*total|total\s*amount|amount\s*due|amount\s*paid|net\s*total|total|payable)[:\s*]+(?:rs\.?|inr|₹)?\s*([\d,]+\.?\d*)",
        r"(?:rs\.?|inr|₹)\s*([\d,]+\.\d{2})\s*$",
        r"(?:total)[:\s]+([\d,]+\.?\d*)",
        r"([\d,]+\.\d{2})\s*(?:rs|inr|₹)?$",
    ]
    for pattern in total_patterns:
        for line in reversed(lines):  # totals usually near bottom
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                try:
                    total_amount = Decimal(m.group(1).replace(",", ""))
                    if total_amount > 0:
                        break
                except InvalidOperation:
                    pass
        if total_amount:
            break

    # ── Tax amount
    tax_patterns = [
        r"(?:gst|cgst|sgst|igst|tax|vat)[:\s]+(?:rs\.?|inr|₹)?\s*([\d,]+\.?\d*)",
        r"(?:tax\s*amount)[:\s]+([\d,]+\.?\d*)",
    ]
    for pattern in tax_patterns:
        for line in lines:
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                try:
                    tax_amount = Decimal(m.group(1).replace(",", ""))
                    break
                except InvalidOperation:
                    pass
        if tax_amount:
            break

    # ── Date: try multiple formats
    date_patterns = [
        (r"(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})", "dmy"),   # DD/MM/YYYY
        (r"(\d{4})[/\-\.](\d{2})[/\-\.](\d{2})", "ymd"),   # YYYY-MM-DD
        (r"(\d{1,2})\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})", "dmy_text"),
    ]
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    for line in lines:
        for pattern, fmt in date_patterns:
            m = re.search(pattern, line, re.IGNORECASE)
            if m:
                try:
                    if fmt == "dmy":
                        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    elif fmt == "ymd":
                        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    elif fmt == "dmy_text":
                        d = int(m.group(1))
                        mo_str = re.search(r"[a-z]+", m.group(0), re.IGNORECASE).group(0)[:3].lower()
                        mo = month_map.get(mo_str, 0)
                        y = int(m.group(2))
                    if 1 <= mo <= 12 and 1 <= d <= 31 and 2000 <= y <= 2100:
                        receipt_date = date(y, mo, d)
                        break
                except (ValueError, AttributeError):
                    pass
        if receipt_date:
            break

    return {
        "merchant": merchant,
        "total_amount": total_amount,
        "receipt_date": receipt_date,
        "tax_amount": tax_amount,
        "raw_text": raw_text,
    }


def process_receipt(file_path: str) -> dict:
    """Full pipeline: extract text -> parse -> return structured data."""
    raw = extract_text(file_path)
    return parse_receipt(raw)
