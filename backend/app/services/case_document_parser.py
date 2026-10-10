"""Local document parsing for the Lawyer Case Documents workflow."""

import io

import fitz
from docx import Document as WordDocument


def _ocr_image_bytes(image_bytes: bytes) -> str:
    """Return OCR text using the locally installed RapidOCR engine."""
    from rapidocr_onnxruntime import RapidOCR

    result, _ = RapidOCR()(image_bytes)
    if not result:
        return ""
    return "\n".join(str(line[1]) for line in result if len(line) > 1 and line[1])


def _extract_entities(text: str) -> list[str]:
    """Entity extraction is deliberately deferred to the separate analysis workflow.

    This upload-and-parsing feature persists only text obtained from the
    document itself, so it does not infer or fabricate legal entities.
    """
    return []


def parse_case_document(content: bytes, file_type: str) -> dict:
    """Extract real text/pages. OCR is attempted only when local RapidOCR is available."""
    normalized_type = file_type.lower()
    text = ""
    page_count: int | None = None
    ocr_used = False

    if normalized_type == "pdf":
        with fitz.open(stream=content, filetype="pdf") as pdf:
            page_count = len(pdf)
            text = "\n".join(page.get_text("text") for page in pdf)
            if not text.strip():
                try:
                    ocr_used = True
                    text = "\n".join(
                        _ocr_image_bytes(page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png"))
                        for page in pdf
                    )
                except Exception as error:
                    raise RuntimeError("No extractable PDF text and local OCR is unavailable") from error
    elif normalized_type == "docx":
        document = WordDocument(io.BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        # DOCX files do not carry a dependable rendered page count.
        page_count = None
    elif normalized_type in {"jpg", "jpeg", "png"}:
        page_count = 1
        try:
            ocr_used = True
            text = _ocr_image_bytes(content)
        except Exception as error:
            raise RuntimeError("Local OCR is unavailable for image documents") from error
    else:
        raise ValueError("Unsupported document type")

    return {
        "text": text,
        "page_count": page_count,
        "ocr_used": ocr_used,
        "entities": _extract_entities(text),
    }
