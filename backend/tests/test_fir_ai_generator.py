import os
import sys
import base64
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.main import app
from ai.fir_engine.fir_ai_generator import generate_structured_fir, _extract_factual_heuristics
from ai.fir_engine.fir_pdf_generator import generate_fir_pdf

client = TestClient(app)

SAMPLE_INCIDENT = (
    "On 8 September 2026 at approximately 7:30 PM, the complainant was returning home from the local market "
    "when an unknown man approached him near the main road. The man suddenly punched the complainant in the face, "
    "causing a bleeding injury to his nose. During the incident, the accused took the complainant's mobile phone "
    "without his consent and immediately fled from the scene on a motorcycle."
)

SAMPLE_ANALYSIS = [
    {
        "section": "303(2)",
        "title": "Theft",
        "applicability": "supported",
        "reasoning": "Dishonest taking of movable property (mobile phone) without consent."
    },
    {
        "section": "115(2)",
        "title": "Voluntarily causing hurt",
        "applicability": "supported",
        "reasoning": "Accused punched victim in the face causing bodily hurt and nose bleeding."
    }
]


def test_empty_rag_provisions_fallback_offline():
    """
    Test fallback behavior when RAG returns 0 provisions and LLM fails/is offline.
    Verifies:
    1. acts_sections NEVER contains 'Under Investigation'.
    2. acts_sections contains 'Not provided' for sections.
    3. Factual heuristics extract date (8 September 2026), time (7:30 PM), property (mobile phone), accused.
    4. complainant_signature remains 'Not provided'.
    """
    # Create mock LLM client that raises an exception (simulating 429 quota / offline error)
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = RuntimeError("Groq API 429 Rate Limit Exceeded")

    # Run generator with 0 grounded provisions
    fir_data = generate_structured_fir(SAMPLE_INCIDENT, grounded_analysis=[], llm_client=mock_llm)

    assert isinstance(fir_data, dict)
    
    # 1. Check acts_sections
    acts_sections = fir_data.get("acts_sections", [])
    assert len(acts_sections) > 0
    sections_str = str(acts_sections)
    assert "Under Investigation" not in sections_str
    assert "303" not in sections_str  # No hardcoded section numbers!
    assert "115" not in sections_str
    assert acts_sections[0]["sections"] == "Not provided"

    # 2. Check deterministic factual extractions from statement
    assert "08/09/2026" in fir_data["occurrence"]["date"] or "8 September 2026" in fir_data["occurrence"]["date"]
    assert "7:30 PM" in fir_data["occurrence"]["time"]
    assert "mobile phone" in fir_data["property_details"].lower()
    assert "unknown male accused" in fir_data["accused_details"].lower()

    # 3. Check signature and officer placeholders
    assert fir_data["complainant_signature"] == "Not provided"
    assert fir_data["officer"]["name"] == "Not provided"

    # 4. Verify PyMuPDF renders valid PDF without errors
    pdf_bytes = generate_fir_pdf(fir_data)
    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF")


def test_grounded_rag_provisions_with_mock_llm():
    """Test FIR generation when grounded analysis is provided but LLM fails."""
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = RuntimeError("Groq API 429 Rate Limit Exceeded")

    fir_data = generate_structured_fir(SAMPLE_INCIDENT, grounded_analysis=SAMPLE_ANALYSIS, llm_client=mock_llm)
    
    # Verify grounded sections 303 and 115 are used from grounded_analysis without hardcoding
    acts_sections = fir_data.get("acts_sections", [])
    assert len(acts_sections) == 2
    assert acts_sections[0]["sections"] == "303"
    assert acts_sections[1]["sections"] == "115"
    assert "Under Investigation" not in str(acts_sections)
