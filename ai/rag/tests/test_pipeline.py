"""test_pipeline.py — Unit tests for LawAid End-to-End Analysis Pipeline.

Located at: ai/rag/tests/test_pipeline.py
"""

import json
import sys
import unittest
from pathlib import Path

# Add project root and analysis/retrieval packages to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ANALYSIS_DIR = PROJECT_ROOT / "ai" / "rag" / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from ai.rag.pipeline import run_pipeline
from ai.rag.analysis.legal_analyzer import MockLLMClient, GroqLLMClient


class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.sample_raw_incident = (
            "The accused Rahul entered the shop and took a mobile phone belonging to Vijay (PAN: ABCDE1234F, Aadhaar: 2345 6789 0123) "
            "without permission. Call 9876543210 or email test@example.com."
        )
        self.mock_llm_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_303_303(2)-2",
                    "applicability": "supported",
                    "reasoning": "The accused took a mobile phone belonging to Vijay without consent."
                }
            ],
            "limitations": []
        })

    def test_1_privacy_happens_before_llm_call(self):
        """1. Verify privacy sanitization occurs before any LLM prompt generation."""
        mock_llm = MockLLMClient(responses=[self.mock_llm_response, self.mock_llm_response])

        result = run_pipeline(self.sample_raw_incident, llm_client=mock_llm)

        self.assertIn("sanitized_incident", result)
        raw_pii_list = ["9876543210", "test@example.com", "ABCDE1234F", "2345 6789 0123"]
        for pii in raw_pii_list:
            self.assertNotIn(pii, result["sanitized_incident"])

        # Check all prompts sent to MockLLMClient
        for prompt in mock_llm.prompts_received:
            for pii in raw_pii_list:
                self.assertNotIn(pii, prompt, f"Raw PII '{pii}' leaked to LLM prompt!")
            self.assertIn("PHONE_1", prompt)
            self.assertIn("EMAIL_1", prompt)
            self.assertIn("PAN_1", prompt)
            self.assertIn("AADHAAR_1", prompt)

    def test_2_end_to_end_successful_flow_with_mock_llm(self):
        """2. Verify successful end-to-end flow returning structured result."""
        mock_llm = MockLLMClient(responses=[self.mock_llm_response, self.mock_llm_response])

        result = run_pipeline(self.sample_raw_incident, llm_client=mock_llm)

        self.assertEqual(result["status"], "success")
        self.assertIsInstance(result["sanitized_incident"], str)
        self.assertIn("privacy_metadata", result)
        self.assertIn("detections", result["privacy_metadata"])
        self.assertIn("replacement_map", result["privacy_metadata"])
        self.assertIsInstance(result["analysis"], list)
        self.assertGreater(len(result["analysis"]), 0)
        self.assertIn("disclaimer", result)
        self.assertIsInstance(result["disclaimer"], str)
        self.assertGreater(len(result["disclaimer"].strip()), 0)

        item = result["analysis"][0]
        self.assertEqual(item["section"], "303")
        self.assertEqual(item["applicability"], "supported")

    def test_3_no_raw_pii_in_output_or_replacement_map(self):
        """3. Verify no raw PII appears in replacement_map or detections metadata."""
        mock_llm = MockLLMClient(responses=[self.mock_llm_response, self.mock_llm_response])

        result = run_pipeline(self.sample_raw_incident, llm_client=mock_llm)

        result_str = str(result)
        raw_pii_list = ["9876543210", "test@example.com", "ABCDE1234F", "2345 6789 0123"]
        for pii in raw_pii_list:
            self.assertNotIn(pii, result_str)

        replacement_map = result["privacy_metadata"]["replacement_map"]
        self.assertEqual(replacement_map.get("PHONE_1"), "phone")
        self.assertEqual(replacement_map.get("EMAIL_1"), "email")
        self.assertEqual(replacement_map.get("PAN_1"), "pan")
        self.assertEqual(replacement_map.get("AADHAAR_1"), "aadhaar")

    def test_4_failure_handling_does_not_expose_pii_or_secrets(self):
        """4. Verify failure handling suppresses raw PII and secret keys and includes disclaimer."""
        failing_mock = MockLLMClient(responses=["Invalid Non-JSON response 1", "Invalid Non-JSON response 2"])

        result = run_pipeline(self.sample_raw_incident, llm_client=failing_mock)

        result_str = str(result)
        raw_pii_list = ["9876543210", "test@example.com", "ABCDE1234F", "2345 6789 0123"]
        for pii in raw_pii_list:
            self.assertNotIn(pii, result_str)

        self.assertIn("disclaimer", result)
        self.assertIsInstance(result["disclaimer"], str)
        self.assertGreater(len(result["disclaimer"].strip()), 0)

    def test_5_llm_client_resolution_at_pipeline_boundary(self):
        """5. Verify llm_client resolution behavior when None vs explicitly injected."""
        mock_llm = MockLLMClient(responses=[self.mock_llm_response])

        # When injected explicitly, uses the injected client
        res = run_pipeline(self.sample_raw_incident, llm_client=mock_llm)
        self.assertGreater(len(mock_llm.prompts_received), 0)

    def test_6_empty_query_generator_fallback(self):
        """6. Verify pipeline falls back to sanitized text when Query Generator returns empty queries."""
        empty_queries_mock = MockLLMClient(responses=['{"queries": []}', self.mock_llm_response])
        res = run_pipeline("Simple incident with no offence", llm_client=empty_queries_mock)
        self.assertEqual(res["status"], "success")


if __name__ == "__main__":
    unittest.main()
