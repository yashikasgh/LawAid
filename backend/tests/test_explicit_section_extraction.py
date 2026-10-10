import pytest
from ai.rag.parser.clean_ocr import extract_explicit_fir_sections
from backend.app.routers.fir import detect_bns_sections


def test_jahangirpuri_fir_item2_explicit_section_extraction():
    """
    Regression test verifying explicit section extraction from Item 2 (Acts & Sections).
    Inputs Jahangir Puri realistic FIR OCR text with Item 2 '134/303(2)' and repeated narrative references.
    """
    sample_fir_text = """
    FIRST INFORMATION REPORT
    (Under Section 173 BNSS)
    1. District: CENTRAL P.S: Jahangir Puri Year: 2026 FIR No: 101 Date: 09/10/2026
    2. (i) Act: THE BHARATIYA NYAYA SANHITA (BNS), 2023 Sections: 134/303(2)
       (ii) Act: Sections:
       (iii) Act: Sections:
       (iv) Other Acts & Sections:
    3. (a) Occurrence of offence Day: Tuesday Date from: 07/10/2026 Time: 14:30
       (b) Information received at P.S. Date: 09/10/2026 Time: 16:00
       (c) General Diary Reference Entry No(s): 12 Time: 16:15
    4. Type of Information: Written
    5. Place of Occurrence: Near Gate No 1, Main Market, Jahangir Puri
    6. Complainant / Informant: Ramesh Kumar S/o Suresh Kumar Age: 35 Nationality: Indian Address: H.No 45, Sector 3
    7. Details of known / suspected / unknown accused: 2 Unknown persons on motorcycle
    8. Reasons for delay in reporting: N/A
    12. FIR Contents:
    On 07/10/2026 at 14:30 hrs, while complainant was walking near Gate No 1, two unknown persons riding a motorcycle approached him. 
    The pillion rider used criminal force and snatched complainant's mobile phone and purse containing Rs 2000 cash. 
    A complaint was registered U/s 134/303(2) BNS. Investigation taken up by SI Vijay Singh No 452.
    """

    extracted = extract_explicit_fir_sections(sample_fir_text)
    detected = detect_bns_sections(sample_fir_text)

    # 1. Assert explicit recorded sections are EXACTLY ['134', '303(2)']
    expected = ["134", "303(2)"]
    assert extracted == expected, f"Expected {expected}, got {extracted}"
    assert detected == expected, f"Expected {expected}, got {detected}"

    # 2. Assert subsection (2) is preserved
    assert "303(2)" in extracted
    assert "303" not in extracted  # Must NOT be stripped to 303

    # 3. Assert no duplicate 134 or duplicate 303(2)
    assert extracted.count("134") == 1
    assert extracted.count("303(2)") == 1

    # 4. Assert no fake section 1 or random narrative numbers (2026, 101, 14, 30, 45, 12, 452, 2000)
    assert "1" not in extracted
    assert "2026" not in extracted
    assert "101" not in extracted
    assert "45" not in extracted
    assert "12" not in extracted
    assert "452" not in extracted
    assert "2000" not in extracted

    # 5. Assert no IPC mapping or IPC sections
    assert not any("IPC" in s for s in extracted)


def test_ipc_act_item2_rejected():
    """Verify sections listed under IPC Act are rejected (no IPC -> BNS mapping)."""
    ipc_text = """
    2. (i) Act: INDIAN PENAL CODE, 1860 Sections: 379/411
    """
    extracted = extract_explicit_fir_sections(ipc_text)
    assert extracted == []


def test_nia_fir_explicit_sections_pipeline_dataflow():
    """
    Regression test verifying:
    1. Item 2 section extraction for NIA FIR style.
    2. Explicit sections reach sections_recorded_in_fir.
    3. Explicit sections reach explained_sections.
    4. Potential sections remain separate/empty when explicit sections exist.
    5. Summary does not become an Act-name dump.
    """
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from app.main import app
    import io, fitz

    sample_nia_fir_text = """
    NATIONAL INVESTIGATION AGENCY
    BHARATIYA NYAYA SANHITA, 2023
    EXPLOSIVE SUBSTANCES ACT, 1908
    UNLAWFUL ACTIVITIES (PREVENTION) ACT, 1967
    FIRST INFORMATION REPORT
    1. District: GUWAHATI P.S: NIA Police Station Year: 2024 FIR No: RC-04-2024 Date: 15/05/2024
    2. (i) Act: THE BHARATIYA NYAYA SANHITA (BNS), 2023 Sections: 147/148/152/196/197/61/4/5
    3. Place of Occurrence: Guwahati Border Checkpost
    12. FIR Contents:
    On 15/05/2024, a group of individuals assembled near the border checkpoint and engaged in unauthorized activities threatening public peace and safety. The officers on duty intervened and registered a complaint.
    """

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), sample_nia_fir_text)
    pdf_bytes = doc.tobytes()
    doc.close()

    mock_pipeline_res = {
        "status": "success",
        "sanitized_incident": sample_nia_fir_text,
        "privacy_metadata": {"detections": [], "replacement_map": {}},
        "analysis": [
            {
                "section": "147",
                "title": "Rioting",
                "punishment": "Imprisonment up to 2 years, or fine, or both",
                "bailable": "Bailable",
                "cognizable": "Cognizable",
                "reasoning": "Assembly of persons creating public disorder.",
                "applicability": "uncertain"
            },
            {
                "section": "148",
                "title": "Rioting, armed with deadly weapon",
                "punishment": "Imprisonment up to 3 years, or fine, or both",
                "bailable": "Bailable",
                "cognizable": "Cognizable",
                "reasoning": "Use of deadly weapons during unlawful assembly.",
                "applicability": "uncertain"
            }
        ],
        "disclaimer": "Legal analysis provided by LawAid AI is for informational purposes only.",
        "pipeline_source": "retrieval_fallback"
    }

    with patch("app.routers.fir._run_pipeline", return_value=mock_pipeline_res) as mock_pipe:
        client = TestClient(app)
        response = client.post(
            "/fir/understand",
            files={"file": ("RC-04-2024-NIA-GUW.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        )

        assert response.status_code == 200
        data = response.json()

        # 1. Assert target_sections passed to _run_pipeline
        assert mock_pipe.called
        kwargs = mock_pipe.call_args.kwargs
        assert "target_sections" in kwargs
        assert "147" in kwargs["target_sections"]

        # 2. Assert explicit sections reach sections_recorded_in_fir
        assert data["has_sections_in_fir"] is True
        assert "147" in data["sections_recorded_in_fir"]
        assert "148" in data["sections_recorded_in_fir"]

        # 3. Assert explicit sections reach explained_sections (NOT empty)
        assert len(data["explained_sections"]) > 0
        explained_secs = [c["section"] for c in data["explained_sections"]]
        assert "147" in explained_secs

        # 4. Assert potential_sections is empty
        assert data["potential_sections"] == []

        # 5. Assert summary describes the incident and is NOT an Act-name dump
        summary_text = data["summary"]
        assert "NATIONAL INVESTIGATION AGENCY" not in summary_text
        assert "BHARATIYA NYAYA SANHITA" not in summary_text
        assert "Explosive Substances Act" not in summary_text

