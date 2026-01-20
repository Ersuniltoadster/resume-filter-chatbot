from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


def _extract_with_pypdf(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes), strict=False)

    parts: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            # page-level failure (broken font descriptors, etc.)
            continue

        text = text.strip()
        if text:
            parts.append(text)

    return "\n\n".join(parts).strip()


def _extract_with_pdfminer(pdf_bytes: bytes) -> str:
    # Import inside function so your app can still run even if dependency missing
    from pdfminer.high_level import extract_text

    text = extract_text(BytesIO(pdf_bytes)) or ""
    return text.strip()


def _extract_with_ocr(pdf_bytes: bytes) -> str:
    # OCR fallback: convert PDF pages -> images -> run Tesseract OCR
    # Requires system packages: poppler-utils, tesseract-ocr
    from pdf2image import convert_from_bytes
    import pytesseract

    images = convert_from_bytes(pdf_bytes, dpi=200)

    parts: list[str] = []
    for img in images:
        t = pytesseract.image_to_string(img) or ""
        t = t.strip()
        if t:
            parts.append(t)

    return "\n\n".join(parts).strip()


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    # 1) Try pypdf
    text = _extract_with_pypdf(pdf_bytes)
    if len(text) >= 50:
        return text

    # 2) Try pdfminer.six
    try:
        text = _extract_with_pdfminer(pdf_bytes)
        if len(text) >= 50:
            return text
    except Exception:
        pass

    # 3) OCR fallback (slow but most robust)
    try:
        text = _extract_with_ocr(pdf_bytes)
        return text
    except Exception:
        # Last resort: return whatever we got (even if small)
        return text