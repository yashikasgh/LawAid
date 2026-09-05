"""test_fir_template.py — Validation test suite for official Form IF1 FIR template (.docx).

Located at: ai/rag/generation/tests/test_fir_template.py
"""

import unittest
from pathlib import Path
import docx
from docxtpl import DocxTemplate

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "fir_template.docx"

REQUIRED_PLACEHOLDERS = [
    "fir_sections",
    "occurrence_day",
    "occurrence_date",
    "occurrence_time",
    "information_date",
    "information_time",
    "information_type",
    "place_address",
    "place_direction",
    "place_distance",
    "jurisdiction_police_station",
    "accused_details",
    "delay_reason",
    "property_details",
    "property_value",
    "fir_contents",
    "complainant_name",
    "father_husband_name",
    "date_of_birth",
    "nationality",
    "id_type",
    "id_number",
    "occupation",
    "address",
    "phone"
]

FIELD_LABELS = [
    "FORM I.F.1",
    "FIRST INFORMATION REPORT",
    "2. Act(s) and Section(s) Involved:",
    "3. Occurrence of Offence and Information Received:",
    "4. Place of Occurrence:",
    "5. Complainant / Informant Details:",
    "6. Details of Known / Suspected / Unknown Accused",
    "7. Reasons for Delay in Reporting",
    "8. Particulars of Properties Stolen / Involved:",
    "9. Total Value of Properties Stolen / Involved:",
    "10. Inquest Report / U.D. Case No.",
    "11. First Information Contents",
    "12. Action Taken / Investigation Details:",
    "13. Administrative Sign-off and Court Dispatch:"
]


class TestFIRTemplate(unittest.TestCase):

    def test_file_exists_and_opens(self):
        """Verify fir_template.docx exists and opens with docxtpl and python-docx."""
        self.assertTrue(TEMPLATE_PATH.exists(), f"Template not found at {TEMPLATE_PATH}")
        doc = docx.Document(str(TEMPLATE_PATH))
        self.assertIsNotNone(doc)

        tpl = DocxTemplate(str(TEMPLATE_PATH))
        self.assertIsNotNone(tpl)

    def test_field_labels_present(self):
        """Verify official Form IF1 field labels are present."""
        doc = docx.Document(str(TEMPLATE_PATH))
        full_text = []
        for p in doc.paragraphs:
            full_text.append(p.text)
        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    full_text.append(cell.text)
        combined_text = "\n".join(full_text)

        for label in FIELD_LABELS:
            self.assertIn(label, combined_text, f"Missing expected field label: '{label}'")

    def test_required_placeholders_exist(self):
        """Verify all 24 required placeholders exist in the template."""
        tpl = DocxTemplate(str(TEMPLATE_PATH))
        undeclared_tags = tpl.get_undeclared_template_variables()

        for tag in REQUIRED_PLACEHOLDERS:
            self.assertIn(tag, undeclared_tags, f"Required placeholder tag '{{{{{tag}}}}}' missing from template!")

    def test_fir_sections_jinja2_loop_validity(self):
        """Verify fir_sections Jinja2 loop is syntactically valid by performing a mock render."""
        tpl = DocxTemplate(str(TEMPLATE_PATH))
        
        mock_context = {
            "jurisdiction_police_station": "Connaught Place P.S.",
            "fir_sections": [
                {"act": "Bharatiya Nyaya Sanhita (BNS), 2023", "sections": "Section 304 (Snatching), Section 308"},
                {"act": "Arms Act, 1959", "sections": "Section 25, Section 27"}
            ],
            "occurrence_day": "Friday",
            "occurrence_date": "15-08-2026",
            "occurrence_time": "21:30 hrs",
            "information_date": "15-08-2026",
            "information_time": "22:15 hrs",
            "information_type": "Written Complaint",
            "place_distance": "2 km",
            "place_direction": "North-East",
            "place_address": "Inner Circle, Connaught Place, New Delhi",
            "complainant_name": "Ramesh Kumar",
            "father_husband_name": "Suresh Kumar",
            "date_of_birth": "12-04-1988",
            "nationality": "Indian",
            "id_type": "Aadhaar",
            "id_number": "XXXX-XXXX-1234",
            "occupation": "Business",
            "address": "H.No 45, Sector 14, Rohini, New Delhi",
            "phone": "+91-9876543210",
            "accused_details": "Two unknown persons on a black motorcycle, faces covered with helmets.",
            "delay_reason": "No delay; report filed immediately at P.S.",
            "property_details": "Gold chain weighing 15 grams",
            "property_value": "INR 95,000",
            "fir_contents": "On 15-08-2026 at approximately 21:30 hrs, while walking near Block C Connaught Place..."
        }

        # Should render cleanly without raising Jinja2 syntax error
        try:
            tpl.render(mock_context)
        except Exception as e:
            self.fail(f"Jinja2 template render failed with error: {e}")

    def test_no_hardcoded_official_values(self):
        """Verify official administrative fields (FIR No, Officer Name, etc.) are unpopulated/blank."""
        doc = docx.Document(str(TEMPLATE_PATH))
        full_text = "\n".join([p.text for p in doc.paragraphs] + [cell.text for t in doc.tables for row in t.rows for cell in row.cells])

        forbidden_fake_values = [
            "FIR No.: 123",
            "FIR No.: 2026",
            "Inspector Rajesh",
            "Officer Rajesh",
            "Sub-Inspector Sharma"
        ]

        for fake_val in forbidden_fake_values:
            self.assertNotIn(fake_val, full_text, f"Hardcoded fake official value found: '{fake_val}'")


if __name__ == "__main__":
    unittest.main()
