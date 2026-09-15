import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_text_pdf(text: str) -> bytes:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    bytes_out = doc.tobytes()
    doc.close()
    return bytes_out


def create_test_image_bytes(text: str = "FIR REPORT THEFT OF MOBILE PHONE BNS 303") -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (400, 100), color="white")
    d = ImageDraw.Draw(img)
    d.text((20, 30), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def mock_pipeline_success():
    with patch("app.routers.fir._run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = {
            "status": "success",
            "sanitized_incident": "Theft of mobile phone from shop",
            "privacy_metadata": {"detections": ["PHONE_NUMBER"], "replacement_map": {}},
            "analysis": [
                {
                    "section": "303(2)",
                    "title": "Theft",
                    "punishment": "Imprisonment up to 3 years",
                    "bailable": "Bailable",
                    "cognizable": "Cognizable",
                    "reasoning": "Accused took property without consent.",
                    "status": "Supported"
                }
            ],
            "disclaimer": "Legal analysis provided by LawAid AI is for informational purposes only."
        }
        yield mock_pipeline


def test_understand_text_pdf(mock_pipeline_success):
    pdf_bytes = create_text_pdf("FIRST INFORMATION REPORT: Theft of mobile device worth 20000 rupees from shop.")
    response = client.post(
        "/fir/understand",
        files={"file": ("sample_fir.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Theft" in data["summary"]
    assert len(data["charges"]) == 1
    assert data["charges"][0]["section"] == "303(2)"
    assert "disclaimer" in data


def test_understand_image_fir(mock_pipeline_success):
    img_bytes = create_test_image_bytes("FIR REPORT ACCUSED STOLE GOLD CHAIN NEAR MARKET")
    response = client.post(
        "/fir/understand",
        files={"file": ("fir_photo.png", io.BytesIO(img_bytes), "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "file_id" in data
    assert len(data["charges"]) > 0


def test_understand_scanned_pdf(mock_pipeline_success):
    # A PDF with an image containing text, but no native text stream
    img_bytes = create_test_image_bytes("SCANNED FIR COMPLAINT STOLEN VEHICLE BNS")
    from PIL import Image
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(page.rect, stream=img_bytes)
    scanned_pdf = doc.tobytes()
    doc.close()

    response = client.post(
        "/fir/understand",
        files={"file": ("scanned_fir.pdf", io.BytesIO(scanned_pdf), "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_understand_unsupported_file():
    response = client.post(
        "/fir/understand",
        files={"file": ("data.txt", io.BytesIO(b"Some text file content"), "text/plain")}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_understand_empty_file():
    response = client.post(
        "/fir/understand",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    )
    assert response.status_code == 400
    assert "Uploaded file is empty" in response.json()["detail"]


def test_understand_unreadable_image():
    # Blank image with no text
    from PIL import Image
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    response = client.post(
        "/fir/understand",
        files={"file": ("blank.png", io.BytesIO(buf.getvalue()), "image/png")}
    )
    assert response.status_code == 400
    assert "Could not extract readable text" in response.json()["detail"]


def test_understand_ai_pipeline_failure():
    pdf_bytes = create_text_pdf("FIRST INFORMATION REPORT: Theft of mobile device worth 20000 rupees from shop.")
    with patch("app.routers.fir._run_pipeline", side_effect=Exception("Groq API rate limit exceeded")):
        response = client.post(
            "/fir/understand",
            files={"file": ("sample_fir.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        )
        assert response.status_code == 500
        assert "AI Legal Analysis failed" in response.json()["detail"]


def test_case_a_ner_no_assault_overclassification_for_hit():
    """Case A: Verify 'An unknown car hit a pedestrian on a public road and caused injury' does not classify 'hit' as legal offence 'assault', and query generation functions."""
    from ai.rag.ner.ner_extractor import extract_entities
    from ai.rag.retrieval.query_generator import generate_queries

    text = "An unknown car hit a pedestrian on a public road and caused injury."
    ner_res = extract_entities(text)

    # 1. NER must NOT classify "hit" as legal offence_type="assault"
    assert "assault" not in ner_res.get("offence_types", []), (
        f"NER overclassified 'hit' as legal offence 'assault': {ner_res.get('offence_types')}"
    )

    # 2. Query generation functions cleanly when offence_types is empty
    queries_res = generate_queries(ner_res)
    queries = queries_res.get("queries", [])
    assert len(queries) > 0, "Query generation failed for incident with empty offence_types"
    assert any(q.get("query") for q in queries)


def test_case_b_fir_understand_applicability_mapping():
    """Case B: Candidate analysis containing supported + uncertain + not_supported provisions."""
    sample_text = "Road accident FIR text describing collision and hurt."
    pdf_bytes = create_text_pdf(sample_text)

    mock_analysis_payload = {
        "status": "success",
        "sanitized_incident": sample_text,
        "privacy_metadata": {"detections": [], "replacement_map": {}},
        "analysis": [
            {
                "section": "281",
                "title": "Rash driving or riding on a public way.",
                "applicability": "supported",
                "punishment": "6 months",
                "bailable": "Bailable",
                "cognizable": "Cognizable",
                "reasoning": "Driven in rash manner on public road."
            },
            {
                "section": "125(b)",
                "title": "Act endangering life or personal safety of others.",
                "applicability": "uncertain",
                "punishment": "3 years",
                "bailable": "Bailable",
                "cognizable": "Cognizable",
                "reasoning": "Requires medical report confirming grievous hurt."
            },
            {
                "section": "282",
                "title": "Rash navigation of vessel.",
                "applicability": "not_supported",
                "punishment": "6 months",
                "bailable": "Bailable",
                "cognizable": "Cognizable",
                "reasoning": "Inapplicable as incident involves motor car, not vessel."
            }
        ],
        "disclaimer": "Legal analysis provided by LawAid AI."
    }

    with patch("app.routers.fir._run_pipeline", return_value=mock_analysis_payload):
        response = client.post(
            "/fir/understand",
            files={"file": ("accident_fir.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        )
        assert response.status_code == 200
        data = response.json()

        # 1. charges contains ONLY supported items
        charge_sections = [c["section"] for c in data.get("charges", [])]
        assert "281" in charge_sections
        assert "125(b)" not in charge_sections
        assert "282" not in charge_sections

        # 2. uncertain_provisions contains ONLY uncertain items
        uncertain_sections = [c["section"] for c in data.get("uncertain_provisions", [])]
        assert "125(b)" in uncertain_sections
        assert "281" not in uncertain_sections
        assert "282" not in uncertain_sections

        # 3. full analysis contains ALL items (including not_supported for audit/debugging)
        all_analysis_sections = [a["section"] for a in data.get("analysis", [])]
        assert "281" in all_analysis_sections
        assert "125(b)" in all_analysis_sections
        assert "282" in all_analysis_sections


def test_case_c_genuine_assault_preserves_assault_entity():
    """Case C: Verify genuine physical assault input 'An unknown man punched the victim' retains assault offence classification."""
    from ai.rag.ner.ner_extractor import extract_entities

    text = "An unknown man punched the victim"
    ner_res = extract_entities(text)

    assert "assault" in ner_res.get("offence_types", []), (
        f"NER failed to extract 'assault' for genuine assault input 'punched': {ner_res.get('offence_types')}"
    )

