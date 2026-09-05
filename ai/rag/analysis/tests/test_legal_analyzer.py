"""test_legal_analyzer.py — Unit tests for Structured LLM Legal Analyzer.

Located at: ai/rag/analysis/tests/test_legal_analyzer.py
"""

import json
import sys
import unittest
from pathlib import Path

# Add LawAid root and analysis directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ANALYSIS_DIR = Path(__file__).resolve().parent.parent
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from legal_analyzer import (
    analyze_incident,
    construct_analysis_prompt,
    MockLLMClient,
    OllamaLLMClient
)
from context_builder import build_legal_context


class TestLegalAnalyzer(unittest.TestCase):

    def setUp(self):
        self.sample_ner = {
            "victims": [],
            "accused": ["Sunil"],
            "persons": ["Vijay"],
            "dates": [],
            "times": [],
            "locations": ["Chandni Chowk"],
            "organizations": [],
            "offence_types": ["criminal trespass"],
            "raw_text": "Sunil entered the shop."
        }
        self.sample_retrieval = {
            "queries": [{"offence_type": "criminal trespass", "query": "criminal trespass"}],
            "results": [
                {
                    "offence_type": "criminal trespass",
                    "query": "criminal trespass",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_329_329(1)",
                            "section": 329,
                            "clause": "329(1)",
                            "title": "Criminal trespass and house-trespass.",
                            "distance": 0.22,
                            "text": "Whoever enters into or upon property in possession of another..."
                        }
                    ]
                }
            ]
        }

    def test_1_prompt_construction(self):
        """Test 1: Prompt construction contains incident facts and retrieved context."""
        ctx = build_legal_context(self.sample_ner, self.sample_retrieval)
        prompt = construct_analysis_prompt(ctx)

        self.assertIn("INCIDENT FACTS:", prompt)
        self.assertIn("RETRIEVED BNS LEGAL CONTEXT:", prompt)
        self.assertIn("Sunil", prompt)
        self.assertIn("bns_329_329(1)", prompt)
        self.assertIn("not_available_in_retrieved_context", prompt)

    def test_2_valid_json_parsing(self):
        """Test 2: Valid JSON parsing from LLM response."""
        llm_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "offence_type": "criminal trespass",
                    "section": "329",
                    "title": "Criminal trespass",
                    "applicability": "supported",
                    "reasoning": "Sunil entered illegally.",
                    "punishment": "Imprisonment up to 3 months",
                    "bailable": "bailable",
                    "cognizable": "cognizable",
                    "evidence": [
                        {
                            "document_id": "bns_329_329(1)",
                            "section": "329",
                            "clause": "329(1)",
                            "rank": 1
                        }
                    ]
                }
            ],
            "limitations": []
        })

        mock_llm = MockLLMClient(responses=[llm_response])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=mock_llm)

        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["analysis"]), 1)
        self.assertEqual(res["analysis"][0]["section"], "329")
        self.assertEqual(res["analysis"][0]["evidence"][0]["document_id"], "bns_329_329(1)")
        self.assertEqual(mock_llm.call_count, 1)

    def test_3_invalid_json_one_successful_retry(self):
        """Test 3: Invalid JSON followed by one successful retry."""
        invalid_first = "Here is the JSON: {offence_type: criminal trespass"  # Invalid JSON
        valid_retry = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "offence_type": "criminal trespass",
                    "section": "329",
                    "title": "Criminal trespass",
                    "applicability": "supported",
                    "reasoning": "Illegal entry.",
                    "punishment": "not_available_in_retrieved_context",
                    "bailable": "not_available_in_retrieved_context",
                    "cognizable": "not_available_in_retrieved_context",
                    "evidence": [
                        {"document_id": "bns_329_329(1)", "section": "329", "clause": "329(1)", "rank": 1}
                    ]
                }
            ],
            "limitations": []
        })

        mock_llm = MockLLMClient(responses=[invalid_first, valid_retry])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=mock_llm)

        self.assertEqual(res["status"], "success")
        self.assertEqual(mock_llm.call_count, 2)
        self.assertIn("RETRY INSTRUCTION:", mock_llm.prompts_received[1])

    def test_4_invalid_json_second_failure_generation_failed(self):
        """Test 4: Invalid JSON followed by second failure returns generation_failed."""
        invalid_1 = "Malformed output 1"
        invalid_2 = "Malformed output 2"

        mock_llm = MockLLMClient(responses=[invalid_1, invalid_2])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=mock_llm)

        self.assertEqual(res["status"], "generation_failed")
        self.assertIn("raw_llm_output", res)
        self.assertIn("reason", res)
        self.assertEqual(mock_llm.call_count, 2)

    def test_5_fake_nonexistent_document_id_rejected(self):
        """Test 5 & 6 & 7: Evidence document ID must exist in actual retrieval results (bns_999 rejected)."""
        llm_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "offence_type": "criminal trespass",
                    "section": "999",
                    "title": "Fake Section",
                    "applicability": "supported",
                    "reasoning": "Hallucinated entry.",
                    "punishment": "10 years",
                    "bailable": "non-bailable",
                    "cognizable": "cognizable",
                    "evidence": [
                        {
                            "document_id": "bns_999",  # Fake doc ID not in retrieval!
                            "section": "999",
                            "clause": None,
                            "rank": 1
                        }
                    ]
                }
            ],
            "limitations": []
        })

        mock_llm = MockLLMClient(responses=[llm_response])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=mock_llm)

        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["analysis"]), 0, "Fake section bns_999 must be rejected and removed!")
        self.assertTrue(any("bns_999" in lim or "not found" in lim for lim in res["limitations"]))

    def test_8_missing_punishment_status_enforces_placeholder(self):
        """Test 8: Missing or empty punishment/status fields become 'not_available_in_retrieved_context'."""
        llm_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "offence_type": "criminal trespass",
                    "section": "329",
                    "title": "Criminal trespass",
                    "applicability": "supported",
                    "reasoning": "Trespass.",
                    "punishment": "",
                    "bailable": "unknown",
                    "cognizable": "none",
                    "evidence": [
                        {"document_id": "bns_329_329(1)", "section": "329", "clause": "329(1)", "rank": 1}
                    ]
                }
            ],
            "limitations": []
        })

        mock_llm = MockLLMClient(responses=[llm_response])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=mock_llm)

        item = res["analysis"][0]
        self.assertEqual(item["punishment"], "not_available_in_retrieved_context")
        self.assertEqual(item["bailable"], "not_available_in_retrieved_context")
        self.assertEqual(item["cognizable"], "not_available_in_retrieved_context")

    def test_10_ollama_llm_client_configuration_error(self):
        """Test 10: OllamaLLMClient raises clear configuration error if no model is set."""
        client = OllamaLLMClient(model_name=None)
        with self.assertRaises(RuntimeError) as cm:
            client.generate("Test prompt")
        self.assertIn("No generative LLM model configured", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
