import io
from pathlib import Path

import fitz
import pytest
from docx import Document as WordDocument

from app.services import case_document_parser as parser


def pdf_with_pages(*texts: str) -> bytes:
    document = fitz.open()
    for text in texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    return document.tobytes()


def test_native_text_pdf_records_each_page_without_ocr(monkeypatch):
    monkeypatch.setattr(parser, "_pdf_page_ocr", lambda _page: pytest.fail("OCR should not run"))
    parsed = parser.parse_case_document(pdf_with_pages("First native page contains enough extractable text", "Second native page contains enough extractable text"), "pdf")
    assert parsed["page_count"] == 2
    assert parsed["ocr_used"] is False
    assert [page["method"] for page in parsed["extraction_details"]] == ["native", "native"]
    assert "Second native" in parsed["text"]


def test_mixed_pdf_uses_ocr_only_for_unusable_page(monkeypatch):
    calls = []
    def ocr(_page):
        calls.append(True)
        return "हिंदी FIR narrative with English PS Jahangir Puri"
    monkeypatch.setattr(parser, "_pdf_page_ocr", ocr)
    parsed = parser.parse_case_document(pdf_with_pages("Native FIR field District North West", ""), "pdf")
    assert len(calls) == 1
    assert [page["method"] for page in parsed["extraction_details"]] == ["native", "ocr"]
    assert "District North West" in parsed["text"]
    assert "हिंदी FIR narrative" in parsed["text"]


def test_image_ocr_and_docx_text_are_persistable(monkeypatch):
    monkeypatch.setattr(parser, "_ocr_image_bytes", lambda _bytes: "हिंदी English mixed statement readable")
    image = parser.parse_case_document(b"fake-image", "png")
    assert image["ocr_used"] is True and image["extraction_details"][0]["method"] == "ocr"
    word = WordDocument(); word.add_paragraph("Witness statement from Asha Kumar")
    stream = io.BytesIO(); word.save(stream)
    docx = parser.parse_case_document(stream.getvalue(), "docx")
    assert "Asha Kumar" in docx["text"] and docx["ocr_used"] is False


def test_scanned_fir_regression_uses_ocr_and_requires_meaningful_text(monkeypatch):
    fixture = Path(r"C:\Users\rajse\Downloads\757152326-FIR-sample-1-BNSS-only-for-academic-purpose.pdf")
    if not fixture.exists():
        pytest.skip("Provided FIR regression fixture is not available on this host")
    data = fixture.read_bytes()
    with fitz.open(stream=data, filetype="pdf") as document:
        assert all(not page.get_text("text").strip() for page in document)
    outputs = iter([
        "FIR Form District NORTH WEST P.S. JAHANGIR PURI",
        "Statements of Bhawna Rajput Delhi FIR No 0382 हिंदी बयान PS Jahangir Puri",
        "FIR read over to the complainant",
    ])
    monkeypatch.setattr(parser, "_pdf_page_ocr", lambda _page: next(outputs))
    parsed = parser.parse_case_document(data, "pdf")
    assert parsed["page_count"] == 3
    assert all(page["method"] == "ocr" for page in parsed["extraction_details"])
    assert "JAHANGIR PURI" in parsed["text"] and "Bhawna Rajput" in parsed["text"]


def test_ocr_unavailable_does_not_claim_pdf_parsed(monkeypatch):
    monkeypatch.setattr(parser, "_pdf_page_ocr", lambda _page: (_ for _ in ()).throw(parser.OCRUnavailableError("Tesseract missing")))
    with pytest.raises(parser.OCRUnavailableError, match="Tesseract missing"):
        parser.parse_case_document(pdf_with_pages(""), "pdf")
