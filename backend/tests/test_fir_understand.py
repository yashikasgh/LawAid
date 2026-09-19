import io
import uuid
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


def get_auth_headers(email_prefix: str = "user"):
    client.cookies.clear()
    client.headers.clear()
    uid = str(uuid.uuid4())[:8]
    email = f"{email_prefix}_{uid}@lawaid.com"
    pwd = "password123"

    # Register
    client.post(
        "/auth/register",
        json={"email": email, "password": pwd, "role": "citizen", "full_name": "Test User"}
    )
    # Login
    res = client.post(
        "/auth/login",
        json={"email": email, "password": pwd, "role": "citizen"}
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    client.cookies.clear()
    client.headers.clear()
    return {"Authorization": f"Bearer {token}"}


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
    assert len(data["charges"]) > 0


def test_understand_txt_fir(mock_pipeline_success):
    txt_content = b"FIRST INFORMATION REPORT: Mobile theft lodged under section 303 BNS."
    response = client.post(
        "/fir/understand",
        files={"file": ("fir_statement.txt", io.BytesIO(txt_content), "text/plain")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["charges"]) > 0


def test_understand_unsupported_file():
    response = client.post(
        "/fir/understand",
        files={"file": ("data.docx", io.BytesIO(b"Word document bytes"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 400
    assert "LawAid cannot currently extract FIR content" in response.json()["detail"]


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


def test_understand_does_not_persist_without_consent(mock_pipeline_success):
    headers = get_auth_headers("consent_user")
    pdf_bytes = create_text_pdf("FIRST INFORMATION REPORT: Theft of mobile device worth 20000 rupees from shop.")

    # 1. Call /fir/understand for temporary analysis
    response = client.post(
        "/fir/understand",
        files={"file": ("sample_fir.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data.get("file_id") is None  # No GridFS persistence before consent

    # 2. Check saved FIR list — must be empty before explicit save
    res_list = client.get("/fir/saved", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) == 0


def test_saved_fir_crud_and_user_isolation():
    headers_user_a = get_auth_headers("user_a")
    headers_user_b = get_auth_headers("user_b")

    # 1. User A saves an FIR analysis
    save_payload = {
        "filename": "my_fir_report.pdf",
        "file_type": "application/pdf",
        "file_size": 1024,
        "summary": "Alleged theft of mobile device.",
        "charges": [{"section": "303(2)", "title": "Theft", "bailable": "Bailable"}],
        "rights": ["Right to counsel."],
        "next_steps": ["Contact DLSA."],
        "disclaimer": "Informational purpose only."
    }

    res_save = client.post("/fir/saved", json=save_payload, headers=headers_user_a)
    assert res_save.status_code == 200
    saved_data = res_save.json()
    assert saved_data["status"] == "saved"
    saved_id = saved_data["saved_id"]

    # 2. User A retrieves saved FIR list
    res_list_a = client.get("/fir/saved", headers=headers_user_a)
    assert res_list_a.status_code == 200
    firs_a = res_list_a.json()
    assert any(f["id"] == saved_id for f in firs_a)

    # 3. User B retrieves saved FIR list (User B must NOT see User A's FIR)
    res_list_b = client.get("/fir/saved", headers=headers_user_b)
    assert res_list_b.status_code == 200
    firs_b = res_list_b.json()
    assert not any(f["id"] == saved_id for f in firs_b)

    # 4. User B attempts to view User A's saved FIR detail (must return 403)
    res_detail_b = client.get(f"/fir/saved/{saved_id}", headers=headers_user_b)
    assert res_detail_b.status_code == 403

    # 5. User A views detail successfully
    res_detail_a = client.get(f"/fir/saved/{saved_id}", headers=headers_user_a)
    assert res_detail_a.status_code == 200
    assert res_detail_a.json()["filename"] == "my_fir_report.pdf"

    # 6. User B attempts to delete User A's saved FIR (must return 403)
    res_del_b = client.delete(f"/fir/saved/{saved_id}", headers=headers_user_b)
    assert res_del_b.status_code == 403

    # 7. User A deletes saved FIR successfully
    res_del_a = client.delete(f"/fir/saved/{saved_id}", headers=headers_user_a)
    assert res_del_a.status_code == 200
    assert res_del_a.json()["status"] == "deleted"

    # 8. User A verifies it is gone
    res_detail_a_after = client.get(f"/fir/saved/{saved_id}", headers=headers_user_a)
    assert res_detail_a_after.status_code == 404
