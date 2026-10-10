from app.services.fir_extractor import extract_fir_fields


def test_extract_fir_fields_is_explicit_and_keeps_missing_values_missing():
    text = """FIRST INFORMATION REPORT
FIR No: 0182
District: North West
P.S.: Example Nagar
Date From: 05/07/2024
Place of Occurrence: Market Road
Complainant: Asha Kumar
Section 303 BNS
12. F.I.R. Contents
The complainant reported an incident at the stated location.
13. Action Taken
"""
    extraction = extract_fir_fields(text, [{"page": 1, "method": "native", "text": text}])
    assert extraction["rule_fields"]["fir_number"]["value"] == "0182"
    assert extraction["rule_fields"]["occurrence_date"]["normalized_date"] == "2024-07-05"
    assert extraction["rule_fields"]["investigating_officer"] is None
    assert extraction["incident_narrative"]["value"].startswith("The complainant")
    assert extraction["explicit_sections"][0]["section"] == "303"
    assert extraction["quality"] == "needs_review"
