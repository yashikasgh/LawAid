"""Text extraction for Lawyer case documents with page-level OCR fallbacks."""

import io
import os
import subprocess

import fitz
from docx import Document as WordDocument

OCR_LANGUAGE = os.getenv("TESSERACT_LANGUAGES", "eng+hin")
OCR_DPI = int(os.getenv("DOCUMENT_OCR_DPI", "300"))
MIN_USABLE_TEXT = 12


class OCRUnavailableError(RuntimeError):
    pass


def _usable_text(text: str) -> bool:
    return len("".join(text.split())) >= MIN_USABLE_TEXT


def _ocr_image_bytes(image_bytes: bytes) -> str:
    """Run the Docker-installed Tesseract engine with English and Hindi packs."""
    try:
        result = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", OCR_LANGUAGE, "--psm", "6"],
            input=image_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=120,
        )
    except FileNotFoundError as error:
        raise OCRUnavailableError(
            "OCR is unavailable: Tesseract is not installed. Install tesseract-ocr with English and Hindi language data."
        ) from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("OCR timed out while reading the document page") from error
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise OCRUnavailableError(f"OCR failed: {detail or 'Tesseract could not process the page'}")
    return result.stdout.decode("utf-8", errors="replace").strip()


def _pdf_page_ocr(page: fitz.Page) -> str:
    # get_pixmap uses the page's displayed rotation, preserving readable OCR orientation.
    scale = OCR_DPI / 72
    image = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).tobytes("png")
    return _ocr_image_bytes(image)


def _extract_pdf(content: bytes) -> tuple[str, int, bool, list[dict], list[dict]]:
    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except (fitz.FileDataError, RuntimeError) as error:
        raise RuntimeError("PDF is corrupt, encrypted, or unreadable") from error
    with pdf:
        if pdf.needs_pass:
            raise RuntimeError("Encrypted PDFs are not supported. Upload an unlocked copy.")
        pages: list[dict] = []
        page_texts: list[dict] = []
        chunks: list[str] = []
        used_ocr = False
        for number, page in enumerate(pdf, start=1):
            native = page.get_text("text").strip()
            has_images = len(page.get_images()) > 0
            
            if _usable_text(native) and (not has_images or len(native) > 1000):
                chunks.append(native)
                pages.append({"page": number, "method": "native", "status": "parsed", "characters": len(native)})
                page_texts.append({"page": number, "method": "native", "text": native})
                continue
                
            ocr_text = _pdf_page_ocr(page)
            
            if _usable_text(ocr_text) and len(ocr_text) > len(native):
                chunks.append(ocr_text)
                used_ocr = True
                pages.append({"page": number, "method": "ocr", "status": "parsed", "characters": len(ocr_text)})
                page_texts.append({"page": number, "method": "ocr", "text": ocr_text})
            elif _usable_text(native):
                chunks.append(native)
                pages.append({"page": number, "method": "native", "status": "parsed", "characters": len(native)})
                page_texts.append({"page": number, "method": "native", "text": native})
            else:
                raise RuntimeError(f"Page {number} has no usable native text and OCR could not read it")
                
        return "\n\n".join(chunks), len(pdf), used_ocr, pages, page_texts


def _extract_entities(text: str) -> list[str]:
    """Entity extraction remains deferred to the lawyer analysis workflow."""
    return []


def parse_case_document(content: bytes, file_type: str) -> dict:
    """Extract text without claiming success when pages cannot actually be read."""
    normalized_type = file_type.lower()
    if normalized_type == "pdf":
        text, page_count, ocr_used, extraction_details, page_texts = _extract_pdf(content)
    elif normalized_type == "docx":
        document = WordDocument(io.BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs).strip()
        if not text:
            raise RuntimeError("DOCX contains no extractable paragraph text")
        page_count, ocr_used = None, False
        extraction_details = [{"page": None, "method": "native", "status": "parsed", "characters": len(text)}]
        page_texts = [{"page": None, "method": "native", "text": text}]
    elif normalized_type in {"jpg", "jpeg", "png"}:
        text = _ocr_image_bytes(content)
        if not _usable_text(text):
            raise RuntimeError("OCR could not read usable text from the image")
        page_count, ocr_used = 1, True
        extraction_details = [{"page": 1, "method": "ocr", "status": "parsed", "characters": len(text)}]
        page_texts = [{"page": 1, "method": "ocr", "text": text}]
    else:
        raise ValueError("Unsupported document type")
    return {"text": text, "page_count": page_count, "ocr_used": ocr_used,
            "extraction_details": extraction_details, "page_texts": page_texts,
            "entities": _extract_entities(text)}
