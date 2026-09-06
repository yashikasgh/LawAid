"""test_legal_analyzer.py — Unit tests for Structured LLM Legal Analyzer.

Located at: ai/rag/analysis/tests/test_legal_analyzer.py
"""

import json
import os
import sys
import unittest
import unittest.mock
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

    def test_2_valid_json_parsing(self):
        """Test 2: Valid JSON candidate selection from LLM response attaches Python metadata."""
        llm_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_329_329(1)",
                    "applicability": "supported",
                    "reasoning": "Sunil entered illegally into the shop."
                }
            ],
            "limitations": []
        })

        mock_llm = MockLLMClient(responses=[llm_response])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=mock_llm)

        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["analysis"]), 1)
        self.assertEqual(res["analysis"][0]["section"], "329")
        self.assertEqual(res["analysis"][0]["clause"], "329(1)")
        self.assertEqual(res["analysis"][0]["title"], "Criminal trespass and house-trespass.")
        self.assertEqual(res["analysis"][0]["evidence"][0]["document_id"], "bns_329_329(1)")
        self.assertEqual(mock_llm.call_count, 1)

    def test_3_invalid_json_one_successful_retry(self):
        """Test 3: Invalid JSON followed by one successful retry."""
        invalid_first = "Here is the JSON: {document_id: bns_329_329(1)"  # Invalid JSON
        valid_retry = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_329_329(1)",
                    "applicability": "supported",
                    "reasoning": "Illegal entry."
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
        """Test 5: Fake nonexistent document_id is rejected into limitations."""
        llm_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_999",  # Fake doc ID not in retrieval!
                    "applicability": "supported",
                    "reasoning": "Hallucinated entry."
                }
            ],
            "limitations": []
        })

        mock_llm = MockLLMClient(responses=[llm_response])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=mock_llm)

        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["analysis"]), 0, "Fake document bns_999 must be rejected and removed!")
        self.assertTrue(any("bns_999" in lim or "not found" in lim for lim in res["limitations"]))

    def test_8_metadata_sourced_from_retrieved_context(self):
        """Test 8: Metadata (section, clause, title, punishment, bailable) is attached from retrieved context."""
        retrieval_with_sched = {
            "queries": [{"offence_type": "criminal trespass", "query": "criminal trespass"}],
            "results": [
                {
                    "offence_type": "criminal trespass",
                    "query": "criminal trespass",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_329_329(3)",
                            "section": 329,
                            "clause": "329(3)",
                            "title": "Criminal trespass and house-trespass.",
                            "distance": 0.22,
                            "text": "Legal text...",
                            "schedule_1": {
                                "offence": "Criminal trespass.",
                                "punishment": "Imprisonment for 3 months, or fine of 5,000 rupees, or both.",
                                "cognizable": "Cognizable.",
                                "bailable": "Bailable.",
                                "court": "Any Magistrate."
                            }
                        }
                    ]
                }
            ]
        }

        llm_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_329_329(3)",
                    "applicability": "supported",
                    "reasoning": "Trespass committed."
                }
            ],
            "limitations": []
        })

        mock_llm = MockLLMClient(responses=[llm_response])
        res = analyze_incident(self.sample_ner, retrieval_with_sched, llm_client=mock_llm)

        item = res["analysis"][0]
        self.assertEqual(item["section"], "329")
        self.assertEqual(item["clause"], "329(3)")
        self.assertEqual(item["punishment"], "Imprisonment for 3 months, or fine of 5,000 rupees, or both.")
        self.assertEqual(item["cognizable"], "Cognizable.")
        self.assertEqual(item["bailable"], "Bailable.")
        self.assertEqual(item["court"], "Any Magistrate.")

    def test_9_empty_llm_analysis_list_returns_clean_response(self):
        """Test 9: Empty LLM analysis list returns success with empty analysis without crashing."""
        llm_response = json.dumps({
            "status": "success",
            "analysis": [],
            "limitations": ["No applicable provisions found."]
        })

        mock_llm = MockLLMClient(responses=[llm_response])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=mock_llm)

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["analysis"], [])
        self.assertEqual(res["limitations"], ["No applicable provisions found."])

    def test_10_ollama_llm_client_configuration_error(self):
        """Test 10: OllamaLLMClient raises clear configuration error if no model is set."""
        client = OllamaLLMClient(model_name=None)
        with self.assertRaises(RuntimeError) as cm:
            client.generate("Test prompt")
        self.assertIn("No generative LLM model configured", str(cm.exception))

    @unittest.mock.patch("dotenv.load_dotenv")
    @unittest.mock.patch.dict("os.environ", {}, clear=True)
    def test_11_groq_llm_client_missing_api_key_error(self, mock_load):
        """Test 11: GroqLLMClient raises ValueError if GROQ_API_KEY is missing."""
        from legal_analyzer import GroqLLMClient
        with self.assertRaises(ValueError) as cm:
            GroqLLMClient(api_key=None)
        self.assertIn("GROQ_API_KEY environment variable is missing.", str(cm.exception))

    @unittest.mock.patch("groq.Groq")
    def test_12_groq_llm_client_initialization_and_model_config(self, mock_groq_cls):
        """Test 12: GroqLLMClient initializes with configured key and default/custom model."""
        from legal_analyzer import GroqLLMClient

        # Default model test
        client1 = GroqLLMClient(api_key="gsk_test_key_123")
        self.assertEqual(client1.model_name, "openai/gpt-oss-120b")
        mock_groq_cls.assert_called_with(api_key="gsk_test_key_123")

        # Custom model test
        client2 = GroqLLMClient(api_key="gsk_test_key_123", model_name="llama-3.3-70b-versatile")
        self.assertEqual(client2.model_name, "llama-3.3-70b-versatile")

    @unittest.mock.patch("groq.Groq")
    def test_13_groq_llm_client_generate_success(self, mock_groq_cls):
        """Test 13: GroqLLMClient generate calls Groq API correctly and passes through content."""
        from legal_analyzer import GroqLLMClient

        mock_response = unittest.mock.MagicMock()
        mock_choice = unittest.mock.MagicMock()
        mock_message = unittest.mock.MagicMock()
        mock_message.content = '{"status": "success", "analysis": []}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_instance = mock_groq_cls.return_value
        mock_instance.chat.completions.create.return_value = mock_response

        client = GroqLLMClient(api_key="gsk_test_key_123")
        res_text = client.generate("Test prompt")

        self.assertEqual(res_text, '{"status": "success", "analysis": []}')
        mock_instance.chat.completions.create.assert_called_once_with(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": "Test prompt"}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

    @unittest.mock.patch("groq.Groq")
    def test_14_groq_llm_client_api_error_conversion(self, mock_groq_cls):
        """Test 14: GroqLLMClient converts API exceptions to safe RuntimeError without exposing secrets."""
        from legal_analyzer import GroqLLMClient

        mock_instance = mock_groq_cls.return_value
        mock_instance.chat.completions.create.side_effect = Exception("API Connection Timeout")

        client = GroqLLMClient(api_key="gsk_secret_key_999")
        with self.assertRaises(RuntimeError) as cm:
            client.generate("Test prompt")

        err_msg = str(cm.exception)
        self.assertIn("Groq API text generation failed for model 'openai/gpt-oss-120b'", err_msg)
        self.assertNotIn("gsk_secret_key_999", err_msg, "API secret key exposed in exception string!")

    def test_15_prompt_contains_material_element_and_missing_facts_rules(self):
        """Test 15: Prompt explicitly forbids inferring missing facts and requires all material elements."""
        ctx = build_legal_context(self.sample_ner, self.sample_retrieval)
        prompt = construct_analysis_prompt(ctx)

        self.assertIn("material elements, conditions, monetary/quantity thresholds, and qualifiers", prompt)
        self.assertIn("You MUST NOT infer or assume missing facts", prompt)
        self.assertIn("uncertain", prompt)

    def test_16_section_303_missing_property_value_variant_marked_uncertain(self):
        """Test 16: Section 303 <₹5,000 Schedule I variant is marked uncertain when property value is unstated."""
        ner = {
            "victims": ["Vijay"],
            "accused": ["Rahul"],
            "persons": ["Vijay", "Rahul"],
            "offence_types": ["theft"],
            "raw_text": "Rahul entered the shop and took a mobile phone belonging to Vijay without permission."
        }
        retrieval = {
            "queries": [{"offence_type": "theft", "query": "theft"}],
            "results": [
                {
                    "offence_type": "theft",
                    "query": "theft",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_303_303(2)-2",
                            "section": 303,
                            "clause": "303(2)",
                            "title": "Theft.",
                            "schedule_1": {
                                "offence": "Where value of property is less than 5,000 rupees.",
                                "punishment": "Upon return of the value of property or restoration of the stolen property, shall be punished with community service.",
                                "cognizable": "Non-cognizable.",
                                "bailable": "Bailable.",
                                "court": "Any Magistrate."
                            }
                        },
                        {
                            "rank": 2,
                            "id": "bns_303_303(2)",
                            "section": 303,
                            "clause": "303(2)",
                            "title": "Theft.",
                            "schedule_1": {
                                "offence": "Theft.",
                                "punishment": "Rigorous imprisonment for not be less than 1 year but which may extend to 5 years, and fine.",
                                "cognizable": "Cognizable.",
                                "bailable": "Non-bailable.",
                                "court": "Any Magistrate."
                            }
                        }
                    ]
                }
            ]
        }

        llm_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_303_303(2)-2",
                    "applicability": "uncertain",
                    "reasoning": "Value of the stolen mobile phone is not specified in the incident facts, so the threshold of less than 5,000 rupees cannot be established without inferring facts."
                },
                {
                    "document_id": "bns_303_303(2)",
                    "applicability": "supported",
                    "reasoning": "Rahul took Vijay's mobile phone without permission, satisfying the material elements of theft."
                }
            ],
            "limitations": []
        })

        mock_llm = MockLLMClient(responses=[llm_response])
        res = analyze_incident(ner, retrieval, llm_client=mock_llm)

        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["analysis"]), 2)

        item_5k = next(item for item in res["analysis"] if item["evidence"][0]["document_id"] == "bns_303_303(2)-2")
        item_gen = next(item for item in res["analysis"] if item["evidence"][0]["document_id"] == "bns_303_303(2)")

        self.assertEqual(item_5k["applicability"], "uncertain", "<₹5,000 variant must be marked uncertain when property value is missing")
        self.assertEqual(item_gen["applicability"], "supported", "General theft must be supported when theft elements are established")


if __name__ == "__main__":
    unittest.main()
