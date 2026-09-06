"""test_privacy_gateway.py — Unit tests for Privacy & Security Gateway.

Located at: ai/security/tests/test_privacy_gateway.py
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.security.privacy_gateway import detect_sensitive_data, sanitize_text


class TestPrivacyGateway(unittest.TestCase):

    def test_1_phone_detection_and_sanitization(self):
        """1. Test Indian Phone/Mobile number detection and sanitization."""
        text = "Contact the accused at 9876543210 or +91 9123456789."
        res = sanitize_text(text)

        self.assertIn("PHONE_1", res["sanitized_text"])
        self.assertIn("PHONE_2", res["sanitized_text"])
        self.assertNotIn("9876543210", res["sanitized_text"])
        self.assertNotIn("9123456789", res["sanitized_text"])

    def test_2_email_detection_and_sanitization(self):
        """2. Test email detection and sanitization."""
        text = "Report sent to complainant@example.com and officer.test@gov.in."
        res = sanitize_text(text)

        self.assertIn("EMAIL_1", res["sanitized_text"])
        self.assertIn("EMAIL_2", res["sanitized_text"])
        self.assertNotIn("complainant@example.com", res["sanitized_text"])
        self.assertNotIn("officer.test@gov.in", res["sanitized_text"])

    def test_3_aadhaar_detection_and_sanitization(self):
        """3. Test Aadhaar-like 12-digit number detection and sanitization."""
        text = "Aadhaar verified: 2345 6789 0123 for the victim."
        res = sanitize_text(text)

        self.assertIn("AADHAAR_1", res["sanitized_text"])
        self.assertNotIn("2345 6789 0123", res["sanitized_text"])

    def test_4_pan_detection_and_sanitization(self):
        """4. Test PAN-like identifier detection and sanitization."""
        text = "Accused PAN card number is ABCDE1234F."
        res = sanitize_text(text)

        self.assertIn("PAN_1", res["sanitized_text"])
        self.assertNotIn("ABCDE1234F", res["sanitized_text"])

    def test_5_repeated_sensitive_value_gets_same_placeholder(self):
        """5. Test repeated sensitive value receives the exact same placeholder."""
        text = "Call 9876543210 immediately. Repeating 9876543210 for confirmation."
        res = sanitize_text(text)

        self.assertEqual(res["sanitized_text"].count("PHONE_1"), 2)
        self.assertNotIn("PHONE_2", res["sanitized_text"])
        self.assertEqual(res["replacement_map"]["PHONE_1"], "phone")

    def test_6_multiple_different_values_get_different_placeholders(self):
        """6. Test multiple different values get distinct placeholders."""
        text = "First email: a@example.com, second email: b@example.com."
        res = sanitize_text(text)

        self.assertIn("EMAIL_1", res["sanitized_text"])
        self.assertIn("EMAIL_2", res["sanitized_text"])
        self.assertEqual(res["replacement_map"]["EMAIL_1"], "email")
        self.assertEqual(res["replacement_map"]["EMAIL_2"], "email")

    def test_7_normal_legal_text_remains_unchanged(self):
        """7. Test normal legal text without PII remains unchanged."""
        text = "The accused entered the shop and took a mobile phone belonging to Vijay without his permission."
        res = sanitize_text(text)

        self.assertEqual(res["sanitized_text"], text)
        self.assertEqual(res["detections"], [])
        self.assertEqual(res["replacement_map"], {})

    def test_8_empty_input_handled_safely(self):
        """8. Test empty input handling."""
        res = sanitize_text("")
        self.assertEqual(res["sanitized_text"], "")
        self.assertEqual(res["detections"], [])
        self.assertEqual(res["replacement_map"], {})

    def test_9_none_and_malformed_input_handled_safely(self):
        """9. Test None / non-string input handling."""
        res_none = sanitize_text(None)
        self.assertEqual(res_none["sanitized_text"], "")
        self.assertEqual(res_none["detections"], [])

        res_int = sanitize_text(12345)
        self.assertEqual(res_int["sanitized_text"], "12345")

    def test_10_original_input_not_mutated_and_raw_pii_not_exposed(self):
        """10. Test original input string is untouched and raw PII is never exposed in output dict."""
        original_pii_email = "victim.test@domain.org"
        original_pii_phone = "9876543210"
        text = f"Contact {original_pii_email} or call {original_pii_phone}."

        res = sanitize_text(text)

        # Output dict inspection: PII must never appear in replacement_map or detections!
        output_str = str(res)
        self.assertNotIn(original_pii_email, output_str, "Raw email PII exposed in output dict!")
        self.assertNotIn(original_pii_phone, output_str, "Raw phone PII exposed in output dict!")

        # Confirm replacement map contains category metadata only
        self.assertEqual(res["replacement_map"]["EMAIL_1"], "email")
        self.assertEqual(res["replacement_map"]["PHONE_1"], "phone")


if __name__ == "__main__":
    unittest.main()
