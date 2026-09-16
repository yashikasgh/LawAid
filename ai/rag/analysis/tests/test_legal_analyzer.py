"""test_legal_analyzer.py — Unit tests for Structured LLM Legal Analyzer.

Located at: ai/rag/analysis/tests/test_legal_analyzer.py
"""

import json
import os
import re
import sys
import unittest
import unittest.mock
from pathlib import Path
from typing import Optional, Dict, List, Any

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
    OllamaLLMClient,
    MultiProviderLLMFailoverClient,
    GroqLLMClient,
    GeminiLLMClient,
    CerebrasLLMClient,
    OpenRouterLLMClient,
    _classify_llm_error,
    LLMClient,
    Workload,
    ProviderHealthStatus,
    GLOBAL_HEALTH_TRACKER,
    estimate_tokens,
    GROQ_SAFE_REQUEST_TOKEN_BUDGET
)
from context_builder import build_legal_context
from ai.rag.retrieval.query_generator import generate_queries
from ai.fir_engine.fir_ai_generator import generate_structured_fir


class TestLegalAnalyzer(unittest.TestCase):

    def setUp(self):
        GLOBAL_HEALTH_TRACKER.reset()
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
        """Test 4: Invalid JSON followed by second failure returns analysis_unavailable status."""
        invalid_1 = "Malformed output 1"
        invalid_2 = "Malformed output 2"

        mock_llm = MockLLMClient(responses=[invalid_1, invalid_2])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=mock_llm)

        self.assertEqual(res["status"], "analysis_unavailable")
        self.assertEqual(res["analysis"], [])
        self.assertTrue(len(res["limitations"]) > 0)
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

        # Default/env model test
        client1 = GroqLLMClient(api_key="gsk_test_key_123")
        self.assertTrue(bool(client1.model_name))
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
            model=client.model_name,
            messages=[{"role": "user", "content": "Test prompt"}],
            temperature=0.0
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
        self.assertIn("Groq API text generation failed for model", err_msg)
        self.assertNotIn("gsk_secret_key_999", err_msg, "API secret key exposed in exception string!")

    def test_15_prompt_contains_material_element_and_missing_facts_rules(self):
        """Test 15: Prompt explicitly requires evidence-grounded applicability rules."""
        ctx = build_legal_context(self.sample_ner, self.sample_retrieval)
        prompt = construct_analysis_prompt(ctx)

        self.assertIn("STRICT GROUNDING & APPLICABILITY RULES", prompt)
        self.assertIn("supported", prompt)
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

    def test_17_applicability_states_and_missing_metadata_formatting(self):
        """Test 17: Validates supported, uncertain, not_supported applicability states and clean missing metadata string."""
        retrieval = {
            "queries": [{"offence_type": "theft", "query": "theft"}],
            "results": [
                {
                    "offence_type": "theft",
                    "query": "theft",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_303_303(2)",
                            "section": 303,
                            "clause": "303(2)",
                            "title": "Theft.",
                            "schedule_1": {}
                        },
                        {
                            "rank": 2,
                            "id": "bns_314",
                            "section": 314,
                            "title": "Dishonest misappropriation of property.",
                            "schedule_1": {}
                        },
                        {
                            "rank": 3,
                            "id": "bns_318",
                            "section": 318,
                            "title": "Cheating.",
                            "schedule_1": {}
                        }
                    ]
                }
            ]
        }

        llm_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_303_303(2)",
                    "applicability": "supported",
                    "reasoning": "Direct taking of movable property."
                },
                {
                    "document_id": "bns_314",
                    "applicability": "uncertain",
                    "reasoning": "Unstated initial possession facts."
                },
                {
                    "document_id": "bns_318",
                    "applicability": "not_supported",
                    "reasoning": "No deception or inducement stated."
                }
            ],
            "limitations": []
        })

        mock_llm = MockLLMClient(responses=[llm_response])
        res = analyze_incident(self.sample_ner, retrieval, llm_client=mock_llm)

        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["analysis"]), 3)

        item_supp = next(i for i in res["analysis"] if i["section"] == "303")
        item_uncert = next(i for i in res["analysis"] if i["section"] == "314")
        item_notsupp = next(i for i in res["analysis"] if i["section"] == "318")

        self.assertEqual(item_supp["applicability"], "supported")
        self.assertEqual(item_uncert["applicability"], "uncertain")
        self.assertEqual(item_notsupp["applicability"], "not_supported")

        self.assertEqual(item_supp["punishment"], "Not available in retrieved source")
        self.assertEqual(item_supp["bailable"], "Not available in retrieved source")
        self.assertEqual(item_supp["cognizable"], "Not available in retrieved source")
        self.assertEqual(item_supp["court"], "Not available in retrieved source")

    def test_18_synthetic_core_supported_optional_proviso_uncertain(self):
        """Test 18: Synthetic test - Core offence supported + optional proviso uncertain."""
        ner = {"raw_text": "The suspect took a laptop without consent."}
        retrieval = {
            "queries": [{"offence_type": "taking", "query": "taking"}],
            "results": [
                {
                    "offence_type": "taking",
                    "query": "taking",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "synth_100_core",
                            "section": 100,
                            "clause": "100(1)",
                            "title": "Unlawful taking.",
                            "text": "Whoever unlawfully takes property without consent..."
                        },
                        {
                            "rank": 2,
                            "id": "synth_100_proviso",
                            "section": 100,
                            "clause": "100(2)",
                            "title": "Unlawful taking under threshold.",
                            "text": "Provided that if the property value is under 1,000 credits..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "synth_100_core",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "core_elements": ["Unlawful taking", "Without consent"],
                    "conditional_elements": [],
                    "satisfied_elements": ["Unlawful taking", "Without consent"],
                    "missing_elements": [],
                    "contradicted_elements": [],
                    "reasoning": "Core taking without consent is established."
                },
                {
                    "document_id": "synth_100_proviso",
                    "unit_type": "conditional_proviso",
                    "applicability": "uncertain",
                    "core_elements": ["Unlawful taking"],
                    "conditional_elements": ["Property value under 1,000 credits"],
                    "satisfied_elements": ["Unlawful taking"],
                    "missing_elements": ["Property value under 1,000 credits"],
                    "contradicted_elements": [],
                    "reasoning": "Value in credits is unstated."
                }
            ],
            "limitations": []
        })
        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "supported")
        self.assertEqual(res["analysis"][1]["applicability"], "uncertain")

    def test_19_synthetic_core_uncertain_missing_element(self):
        """Test 19: Synthetic test - Core offence uncertain because a core element is missing."""
        ner = {"raw_text": "An item was found in the hallway."}
        retrieval = {
            "queries": [{"offence_type": "unlawful act", "query": "unlawful act"}],
            "results": [
                {
                    "offence_type": "unlawful act",
                    "query": "unlawful act",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "synth_200_core",
                            "section": 200,
                            "clause": "200(1)",
                            "title": "Dishonest conversion.",
                            "text": "Whoever dishonestly converts property to their own use..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "synth_200_core",
                    "unit_type": "core_definition",
                    "applicability": "uncertain",
                    "core_elements": ["Dishonest intention", "Conversion to own use"],
                    "satisfied_elements": [],
                    "missing_elements": ["Dishonest intention", "Conversion to own use"],
                    "contradicted_elements": [],
                    "reasoning": "Incident merely states finding an item; dishonest conversion is unresolved."
                }
            ],
            "limitations": []
        })
        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "uncertain")

    def test_20_synthetic_core_not_supported_contradicted(self):
        """Test 20: Synthetic test - Core offence not supported because a core element is contradicted."""
        ner = {"raw_text": "The driver stopped immediately and safely parked the vehicle."}
        retrieval = {
            "queries": [{"offence_type": "fleeing", "query": "fleeing"}],
            "results": [
                {
                    "offence_type": "fleeing",
                    "query": "fleeing",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "synth_300_core",
                            "section": 300,
                            "title": "Fleeing scene of accident.",
                            "text": "Whoever flees the scene of an accident without stopping..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "synth_300_core",
                    "unit_type": "core_definition",
                    "applicability": "not_supported",
                    "core_elements": ["Accident occurred", "Flees scene without stopping"],
                    "satisfied_elements": ["Accident occurred"],
                    "missing_elements": [],
                    "contradicted_elements": ["Flees scene without stopping (driver stopped immediately)"],
                    "reasoning": "Prerequisite of fleeing is explicitly contradicted because the driver stopped immediately."
                }
            ],
            "limitations": []
        })
        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "not_supported")

    def test_21_synthetic_conditional_branch_supported_when_all_conditions_met(self):
        """Test 21: Synthetic test - Conditional branch supported when all branch conditions are established."""
        ner = {"raw_text": "An authorized accountant took 50,000 cash from the firm's safe."}
        retrieval = {
            "queries": [{"offence_type": "taking", "query": "taking"}],
            "results": [
                {
                    "offence_type": "taking",
                    "query": "taking",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "synth_400_aggravated",
                            "section": 400,
                            "title": "Theft by employee.",
                            "text": "Whoever, being an employee, takes property of master..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "synth_400_aggravated",
                    "unit_type": "aggravated_branch",
                    "applicability": "supported",
                    "core_elements": ["Taking property"],
                    "conditional_elements": ["Employee status", "Property of master"],
                    "satisfied_elements": ["Taking property", "Employee status (accountant)", "Property of master"],
                    "missing_elements": [],
                    "contradicted_elements": [],
                    "reasoning": "Both core taking and employment relationship are established."
                }
            ],
            "limitations": []
        })
        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "supported")

    def test_22_synthetic_multiple_clauses_evaluated_independently(self):
        """Test 22: Synthetic test - Multiple clauses within the same section evaluated independently."""
        ner = {"raw_text": "The intruder entered a residential building at 2 PM."}
        retrieval = {
            "queries": [{"offence_type": "entry", "query": "entry"}],
            "results": [
                {
                    "offence_type": "entry",
                    "query": "entry",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "synth_500_day",
                            "section": 500,
                            "clause": "500(1)",
                            "title": "House trespass by day.",
                            "text": "Whoever commits house trespass by day..."
                        },
                        {
                            "rank": 2,
                            "id": "synth_500_night",
                            "section": 500,
                            "clause": "500(2)",
                            "title": "House trespass by night.",
                            "text": "Whoever commits house trespass by night..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "synth_500_day",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "core_elements": ["House trespass", "By day"],
                    "conditional_elements": [],
                    "satisfied_elements": ["House trespass", "By day (2 PM)"],
                    "missing_elements": [],
                    "contradicted_elements": [],
                    "reasoning": "Entry at 2 PM satisfies day house trespass."
                },
                {
                    "document_id": "synth_500_night",
                    "unit_type": "core_definition",
                    "applicability": "not_supported",
                    "core_elements": ["House trespass", "By night"],
                    "satisfied_elements": ["House trespass"],
                    "missing_elements": [],
                    "contradicted_elements": ["By night (entry occurred at 2 PM daytime)"],
                    "reasoning": "Night time requirement is contradicted by 2 PM daytime entry."
                }
            ],
            "limitations": []
        })
        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "supported")
        self.assertEqual(res["analysis"][1]["applicability"], "not_supported")

    def test_23_existing_section_303_monetary_proviso_regression(self):
        """Test 23: Existing Section 303 regression - Core theft supported while <5000 proviso uncertain."""
        ner = {"raw_text": "An unknown person stole the complainant's mobile phone."}
        retrieval = {
            "queries": [{"offence_type": "theft", "query": "theft"}],
            "results": [
                {
                    "offence_type": "theft",
                    "query": "theft",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_303_303(2)",
                            "section": 303,
                            "clause": "303(2)",
                            "title": "Theft.",
                            "text": "Whoever commits theft shall be punished..."
                        },
                        {
                            "rank": 2,
                            "id": "bns_303_303(2)-2",
                            "section": 303,
                            "clause": "303(2)",
                            "title": "Theft under 5,000 rupees.",
                            "text": "Where value of property is less than 5,000 rupees..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_303_303(2)",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "core_elements": ["Dishonest taking of property", "Without consent"],
                    "conditional_elements": [],
                    "satisfied_elements": ["Dishonest taking of property", "Without consent"],
                    "missing_elements": [],
                    "contradicted_elements": [],
                    "reasoning": "Dishonest taking of mobile phone without consent established."
                },
                {
                    "document_id": "bns_303_303(2)-2",
                    "unit_type": "conditional_proviso",
                    "applicability": "uncertain",
                    "core_elements": ["Dishonest taking of property"],
                    "conditional_elements": ["Property value less than 5,000 rupees"],
                    "satisfied_elements": ["Dishonest taking of property"],
                    "missing_elements": ["Property value less than 5,000 rupees"],
                    "contradicted_elements": [],
                    "reasoning": "Property value is unstated in incident facts."
                }
            ],
            "limitations": []
        })
        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "supported")
        self.assertEqual(res["analysis"][1]["applicability"], "uncertain")

    def test_24_existing_death_prerequisite_regression(self):
        """Test 24: Existing death prerequisite regression - Contradicted death returns not_supported."""
        ner = {"raw_text": "Victim hit by car and suffered arm injury but survived."}
        retrieval = {
            "queries": [{"offence_type": "accident", "query": "accident"}],
            "results": [
                {
                    "offence_type": "accident",
                    "query": "accident",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_106_106(1)",
                            "section": 106,
                            "clause": "106(1)",
                            "title": "Causing death by negligence.",
                            "text": "Whoever causes death of any person by rash or negligent act..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_106_106(1)",
                    "unit_type": "aggravated_branch",
                    "applicability": "not_supported",
                    "core_elements": ["Rash or negligent act"],
                    "conditional_elements": ["Causing death"],
                    "satisfied_elements": ["Rash or negligent act"],
                    "missing_elements": [],
                    "contradicted_elements": ["Causing death (victim survived)"],
                    "reasoning": "Death element contradicted."
                }
            ],
            "limitations": []
        })
        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "not_supported")

    def test_25_no_hardcoded_bns_mappings_in_analyzer_source(self):
        """Test 25: Source code check - Verifies zero hardcoded section numbers or if section == statements exist."""
        import legal_analyzer
        with open(legal_analyzer.__file__, "r", encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("bns_106", src)
        self.assertNotIn("bns_306", src)
        self.assertNotIn("if section == ", src)

    def test_26_sibling_clauses_deduplicate_section_definition(self):
        """Test 26: Sibling clauses from the same BNS section share section_definition only once in prompt context."""
        retrieval_with_siblings = [
            {
                "id": "bns_303_303(1)",
                "section": 303,
                "clause": "303(1)",
                "title": "Theft.",
                "target_clause_text": "303.(1) Whoever, intending to take dishonestly...",
                "section_definition": "303.(1) Whoever, intending to take dishonestly any movable property out of the possession of any person..."
            },
            {
                "id": "bns_303_303(2)",
                "section": 303,
                "clause": "303(2)",
                "title": "Theft.",
                "target_clause_text": "(2) Whoever commits theft shall be punished...",
                "section_definition": "303.(1) Whoever, intending to take dishonestly any movable property out of the possession of any person..."
            },
            {
                "id": "bns_303_303(2)-2",
                "section": 303,
                "clause": "303(2)",
                "title": "Theft.",
                "target_clause_text": "Where value of property is less than 5,000 rupees...",
                "section_definition": "303.(1) Whoever, intending to take dishonestly any movable property out of the possession of any person..."
            }
        ]
        ctx = build_legal_context(self.sample_ner, retrieval_with_siblings)
        prompt = construct_analysis_prompt(ctx)

        # Parse RETRIEVED BNS LEGAL CONTEXT JSON from prompt
        m_ctx = re.search(r"RETRIEVED BNS LEGAL CONTEXT:\s*(\[.*\])", prompt, re.DOTALL)
        self.assertIsNotNone(m_ctx)
        sections = json.loads(m_ctx.group(1))

        self.assertEqual(len(sections), 1)
        sec_obj = sections[0]
        self.assertEqual(str(sec_obj["section"]), "303")
        self.assertIn("section_definition", sec_obj)

        clauses = sec_obj["clauses"]
        self.assertEqual(len(clauses), 3)

        # Sibling clauses do NOT repeat section_definition
        for cl in clauses:
            self.assertNotIn("section_definition", cl)
            self.assertIn("target_clause_text", cl)

    def test_27_distinct_bns_sections_retain_their_own_section_definitions(self):
        """Test 27: Distinct BNS sections each retain their own section_definition in prompt context."""
        retrieval_multi_sec = [
            {
                "id": "bns_303_303(2)",
                "section": 303,
                "clause": "303(2)",
                "title": "Theft.",
                "target_clause_text": "(2) Whoever commits theft shall be punished...",
                "section_definition": "303.(1) Theft definition text..."
            },
            {
                "id": "bns_304",
                "section": 304,
                "clause": "304(1)",
                "title": "Snatching.",
                "target_clause_text": "(1) Theft is snatching if...",
                "section_definition": "304.(1) Snatching definition text..."
            }
        ]
        ctx = build_legal_context(self.sample_ner, retrieval_multi_sec)
        prompt = construct_analysis_prompt(ctx)

        m_ctx = re.search(r"RETRIEVED BNS LEGAL CONTEXT:\s*(\[.*\])", prompt, re.DOTALL)
        self.assertIsNotNone(m_ctx)
        sections = json.loads(m_ctx.group(1))

        self.assertEqual(len(sections), 2)
        # Both distinct sections (303 and 304) retain their own section_definition
        self.assertIn("section_definition", sections[0])
        self.assertIn("section_definition", sections[1])
        self.assertEqual(sections[0]["section_definition"], "303.(1) Theft definition text...")
        self.assertEqual(sections[1]["section_definition"], "304.(1) Snatching definition text...")




class TestMultiProviderLLMFailover(unittest.TestCase):

    def setUp(self):
        GLOBAL_HEALTH_TRACKER.reset()
        self.sample_ner = {
            "victims": [],
            "accused": ["Sunil"],
            "persons": ["Vijay"],
            "dates": [],
            "times": [],
            "locations": ["Market"],
            "organizations": [],
            "offence_types": ["theft"],
            "raw_text": "Sunil stole a mobile phone."
        }
        self.sample_retrieval = {
            "queries": [{"offence_type": "theft", "query": "theft"}],
            "results": [
                {
                    "offence_type": "theft",
                    "query": "theft",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_303_303(2)",
                            "section": 303,
                            "clause": "303(2)",
                            "title": "Theft.",
                            "distance": 0.15,
                            "text": "Whoever, intending to take dishonestly..."
                        }
                    ]
                }
            ]
        }

    def test_failover_1_primary_groq_succeeds(self):
        """1. Primary Groq provider succeeds -> no fallback."""
        p1 = MockLLMClient(responses=[json.dumps({
            "status": "success",
            "analysis": [{"document_id": "bns_303_303(2)", "applicability": "supported", "reasoning": "Stole phone."}],
            "limitations": []
        })])
        p1.model_name = "openai/gpt-oss-120b"
        p2 = MockLLMClient(responses=[])
        p2.model_name = "gemini-1.5-flash"

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2])
        res_text = failover_client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        self.assertIn("success", res_text)
        self.assertEqual(p1.call_count, 1)
        self.assertEqual(p2.call_count, 0)
        self.assertEqual(failover_client.active_provider_info["model"], "openai/gpt-oss-120b")

    def test_failover_2_groq_429_fails_over_to_gemini(self):
        """2. Groq returns HTTP 429 -> Gemini is attempted."""
        class RateLimitedClient(LLMClient):
            model_name = "openai/gpt-oss-120b"
            def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
                raise RuntimeError("Groq API text generation failed for model 'openai/gpt-oss-120b': HTTP 429 Rate Limit Exceeded")

        p1 = RateLimitedClient()
        p2 = MockLLMClient(responses=[json.dumps({
            "status": "success",
            "analysis": [{"document_id": "bns_303_303(2)", "applicability": "supported", "reasoning": "Stole phone."}],
            "limitations": []
        })])
        p2.model_name = "gemini-1.5-flash"

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2])
        res_text = failover_client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        self.assertIn("success", res_text)
        self.assertEqual(p2.call_count, 1)
        self.assertEqual(failover_client.active_provider_info["model"], "gemini-1.5-flash")
        self.assertEqual(len(failover_client.last_execution_trace), 2)
        self.assertEqual(failover_client.last_execution_trace[0]["status"], "failed")
        self.assertEqual(failover_client.last_execution_trace[1]["status"], "success")

    def test_failover_3_malformed_json_tries_next_provider(self):
        """3. Provider returns empty output -> reject and try next provider."""
        p1 = MockLLMClient(responses=[""])
        p1.model_name = "openai/gpt-oss-120b"
        p2 = MockLLMClient(responses=[json.dumps({
            "status": "success",
            "analysis": [{"document_id": "bns_303_303(2)", "applicability": "supported", "reasoning": "Stole phone."}],
            "limitations": []
        })])
        p2.model_name = "gemini-1.5-flash"

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2])
        res_text = failover_client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        self.assertIn("success", res_text)
        self.assertEqual(p1.call_count, 1)
        self.assertEqual(p2.call_count, 1)
        self.assertEqual(failover_client.active_provider_info["model"], "gemini-1.5-flash")

    def test_failover_4_all_providers_fail_returns_analysis_unavailable(self):
        """4. All providers fail -> returns status 'analysis_unavailable'."""
        class AlwaysFailingClient(LLMClient):
            def __init__(self, name):
                self.model_name = name
            def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
                raise RuntimeError(f"{self.model_name} offline")

        p1 = AlwaysFailingClient("openai/gpt-oss-120b")
        p2 = AlwaysFailingClient("gemini-1.5-flash")
        p3 = AlwaysFailingClient("openai/gpt-oss-20b")

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2, p3])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=failover_client)

        self.assertEqual(res["status"], "analysis_unavailable")
        self.assertEqual(res["analysis"], [])
        self.assertIn("AI legal analysis is temporarily unavailable", res["limitations"][0])

    def test_failover_5_groq_and_gemini_fail_groq20b_succeeds(self):
        """5. Groq 120B fails -> Gemini fails -> Groq 20B succeeds."""
        class AlwaysFailingClient(LLMClient):
            def __init__(self, name):
                self.model_name = name
            def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
                raise RuntimeError(f"{self.model_name} rate limit or connection error")

        p1 = AlwaysFailingClient("openai/gpt-oss-120b")
        p2 = AlwaysFailingClient("gemini-3.8-flash")
        p3 = MockLLMClient(responses=[json.dumps({
            "status": "success",
            "analysis": [{"document_id": "bns_303_303(2)", "applicability": "supported", "reasoning": "Stole phone."}],
            "limitations": []
        })])
        p3.model_name = "openai/gpt-oss-20b"
        p4 = MockLLMClient(responses=[])
        p4.model_name = "openrouter/free"

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2, p3, p4])
        res_text = failover_client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        self.assertIn("success", res_text)
        self.assertEqual(p3.call_count, 1)
        self.assertEqual(p4.call_count, 0)
        self.assertEqual(failover_client.active_provider_info["model"], "openai/gpt-oss-20b")
        self.assertEqual(len(failover_client.last_execution_trace), 3)
        self.assertEqual(failover_client.last_execution_trace[0]["status"], "failed")
        self.assertEqual(failover_client.last_execution_trace[1]["status"], "failed")
        self.assertEqual(failover_client.last_execution_trace[2]["status"], "success")

    def test_failover_6_groq_gemini_groq20b_fail_openrouter_succeeds(self):
        """6. Groq 120B fails -> Gemini fails -> Groq 20B fails -> OpenRouter succeeds."""
        class AlwaysFailingClient(LLMClient):
            def __init__(self, name):
                self.model_name = name
            def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
                raise RuntimeError(f"{self.model_name} rate limit or payment error")

        p1 = AlwaysFailingClient("openai/gpt-oss-120b")
        p2 = AlwaysFailingClient("gemini-3.8-flash")
        p3 = AlwaysFailingClient("openai/gpt-oss-20b")
        p4 = MockLLMClient(responses=[json.dumps({
            "status": "success",
            "analysis": [{"document_id": "bns_303_303(2)", "applicability": "supported", "reasoning": "Stole phone."}],
            "limitations": []
        })])
        p4.model_name = "openrouter/free"

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2, p3, p4])
        res_text = failover_client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        self.assertIn("success", res_text)
        self.assertEqual(p4.call_count, 1)
        self.assertEqual(failover_client.active_provider_info["model"], "openrouter/free")
        self.assertEqual(len(failover_client.last_execution_trace), 4)
        self.assertEqual(failover_client.last_execution_trace[0]["status"], "failed")
        self.assertEqual(failover_client.last_execution_trace[1]["status"], "failed")
        self.assertEqual(failover_client.last_execution_trace[2]["status"], "failed")
        self.assertEqual(failover_client.last_execution_trace[3]["status"], "success")

    def test_failover_7_all_4_providers_unavailable(self):
        """7. All 4 providers fail -> returns status 'analysis_unavailable'."""
        class AlwaysFailingClient(LLMClient):
            def __init__(self, name):
                self.model_name = name
            def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
                raise RuntimeError(f"{self.model_name} error")

        p1 = AlwaysFailingClient("openai/gpt-oss-120b")
        p2 = AlwaysFailingClient("gemini-3.8-flash")
        p3 = AlwaysFailingClient("gpt-oss-120b")
        p4 = AlwaysFailingClient("openai/gpt-oss-20b")

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2, p3, p4])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=failover_client)

        self.assertEqual(res["status"], "analysis_unavailable")
        self.assertEqual(res["analysis"], [])
        self.assertIn("AI legal analysis is temporarily unavailable", res["limitations"][0])

    @unittest.mock.patch("dotenv.load_dotenv")
    @unittest.mock.patch.dict("os.environ", {}, clear=True)
    def test_openrouter_llm_client_missing_api_key_error(self, mock_load):
        """Test OpenRouterLLMClient raises ValueError when OPENROUTER_API_KEY is missing."""
        with self.assertRaises(ValueError) as cm:
            OpenRouterLLMClient(api_key=None)
        self.assertIn("OPENROUTER_API_KEY environment variable is missing", str(cm.exception))

    @unittest.mock.patch.dict("os.environ", {}, clear=True)
    def test_openrouter_llm_client_custom_model(self):
        """Test OpenRouterLLMClient uses OPENROUTER_MODEL, explicit model_name, or default openrouter/free."""
        # 1. Default when OPENROUTER_MODEL is absent -> openrouter/free
        client1 = OpenRouterLLMClient(api_key="or_test_key_123")
        self.assertEqual(client1.model_name, "openrouter/free")

        # 2. Explicit model_name passed in constructor -> respects passed model_name
        client2 = OpenRouterLLMClient(api_key="or_test_key_123", model_name="google/gemini-2.0-flash-lite-001:free")
        self.assertEqual(client2.model_name, "google/gemini-2.0-flash-lite-001:free")

        # 3. OPENROUTER_MODEL set in env -> respects env override
        with unittest.mock.patch.dict("os.environ", {"OPENROUTER_MODEL": "meta-llama/llama-3.3-70b-instruct:free"}):
            client3 = OpenRouterLLMClient(api_key="or_test_key_123")
            self.assertEqual(client3.model_name, "meta-llama/llama-3.3-70b-instruct:free")

    def test_error_classification_categories(self):
        """Test _classify_llm_error correctly categorizes 402, 429, 413, and validation errors."""
        self.assertEqual(_classify_llm_error("HTTP 402 Payment Required: Insufficient balance"), "payment_required")
        self.assertEqual(_classify_llm_error("Groq API error HTTP 429 Rate limit exceeded"), "rate_limited")
        self.assertEqual(_classify_llm_error("HTTP 413 Request entity too large"), "request_too_large")
        self.assertEqual(_classify_llm_error("Output failed structured JSON validation"), "json_validation_failed")
        self.assertEqual(_classify_llm_error("Unknown connection drop"), "api_error")

    @unittest.mock.patch("google.generativeai.GenerativeModel")
    @unittest.mock.patch("google.generativeai.configure")
    @unittest.mock.patch.dict("os.environ", {
        "GROQ_API_KEY": "test_groq",
        "GEMINI_API_KEY": "test_gemini",
        "OPENROUTER_API_KEY": "test_openrouter"
    }, clear=True)
    def test_default_provider_chain_excludes_cerebras_and_includes_openrouter(self, mock_config, mock_genai):
        """Test default provider chain excludes Cerebras and registers OpenRouter after Groq providers."""
        client = MultiProviderLLMFailoverClient()
        provider_names = [p.__class__.__name__ for p in client.providers]

        self.assertNotIn("CerebrasLLMClient", provider_names, "CerebrasLLMClient must not be in default failover chain!")
        self.assertIn("OpenRouterLLMClient", provider_names, "OpenRouterLLMClient must be in default failover chain!")

        # Verify provider order: Groq (120b), Gemini, Groq (20b), OpenRouter
        self.assertEqual(provider_names, ["GroqLLMClient", "GeminiLLMClient", "GroqLLMClient", "OpenRouterLLMClient"])

    def test_compact_prompt_omits_redundant_fields_while_preserving_grounding(self):
        """Test construct_analysis_prompt omits redundant fields (rank, distance, punishment) from LLM prompt while legal_context_obj and grounding retain them."""
        full_retrieval = {
            "queries": [{"offence_type": "theft", "query": "theft"}],
            "results": [
                {
                    "offence_type": "theft",
                    "query": "theft",
                    "retrieved": [
                        {
                            "rank": 1,
                            "distance": 0.12,
                            "id": "bns_303_303(2)",
                            "section": 303,
                            "clause": "303(2)",
                            "title": "Theft.",
                            "text": "Whoever, intending to take dishonestly...",
                            "target_clause_text": "Whoever, intending to take dishonestly...",
                            "schedule_1": {
                                "offence": "Theft.",
                                "punishment": "Rigorous imprisonment for 1 to 5 years.",
                                "cognizable": "Cognizable.",
                                "bailable": "Non-bailable.",
                                "court": "Any Magistrate."
                            }
                        }
                    ]
                }
            ]
        }
        ctx = build_legal_context(self.sample_ner, full_retrieval)
        prompt = construct_analysis_prompt(ctx)

        # 1. Prompt includes essential legal identifiers & text
        self.assertIn("bns_303_303(2)", prompt)
        self.assertIn("Whoever, intending to take dishonestly", prompt)

        # 2. Prompt omits redundant/procedural fields to conserve tokens
        self.assertNotIn('"rank"', prompt)
        self.assertNotIn('"distance"', prompt)
        self.assertNotIn('"punishment"', prompt)
        self.assertNotIn('"bailable"', prompt)
        self.assertNotIn('"cognizable"', prompt)

        # 3. Grounding still accesses full legal_context_obj to attach metadata
        llm_response = json.dumps({
            "status": "success",
            "analysis": [{"document_id": "bns_303_303(2)", "applicability": "supported", "reasoning": "Theft elements met."}],
            "limitations": []
        })
        res = analyze_incident(self.sample_ner, full_retrieval, llm_client=MockLLMClient(responses=[llm_response]))
        self.assertEqual(res["analysis"][0]["punishment"], "Rigorous imprisonment for 1 to 5 years.")
        self.assertEqual(res["analysis"][0]["cognizable"], "Cognizable.")


class TestMaxTokensBudgetsAndProviderKwargs(unittest.TestCase):

    def test_query_generation_uses_max_tokens_250(self):
        """1. generate_queries passes max_tokens = 250 to LLM generation."""
        mock_llm = MockLLMClient(responses=['{"queries": [{"query_type": "fact_focused", "query": "stolen phone"}, {"query_type": "action_context", "query": "stole phone"}]}'])
        ner = {"raw_text": "A phone was stolen.", "offence_types": ["theft"]}
        res = generate_queries(ner, llm_client=mock_llm)
        self.assertEqual(mock_llm.last_max_tokens, 250)

    def test_legal_analysis_uses_max_tokens_1300(self):
        """2. analyze_incident / legal analysis passes max_tokens = 1300 to LLM generation."""
        mock_llm = MockLLMClient(responses=['{"status": "success", "analysis": []}'])
        ner = {"raw_text": "A phone was stolen.", "offence_types": ["theft"]}
        retrieval = {"queries": [], "results": []}
        res = analyze_incident(ner, retrieval, llm_client=mock_llm)
        self.assertEqual(mock_llm.last_max_tokens, 1300)

    def test_fir_generation_uses_max_tokens_700(self):
        """3. generate_structured_fir passes max_tokens = 700 to LLM generation."""
        mock_llm = MockLLMClient(responses=['{"district": "Central"}'])
        res = generate_structured_fir("A phone was stolen.", [], llm_client=mock_llm)
        self.assertEqual(mock_llm.last_max_tokens, 700)

    @unittest.mock.patch("groq.Groq")
    def test_groq_includes_max_tokens_in_request(self, mock_groq_cls):
        """4a. GroqLLMClient includes max_completion_tokens in chat.completions.create kwargs."""
        mock_response = unittest.mock.MagicMock()
        mock_choice = unittest.mock.MagicMock()
        mock_message = unittest.mock.MagicMock()
        mock_message.content = '{"status": "success"}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_instance = mock_groq_cls.return_value
        mock_instance.chat.completions.create.return_value = mock_response

        client = GroqLLMClient(api_key="gsk_test_123")
        client.generate("Test prompt", max_tokens=1300)

        mock_instance.chat.completions.create.assert_called_once_with(
            model=client.model_name,
            messages=[{"role": "user", "content": "Test prompt"}],
            temperature=0.0,
            max_completion_tokens=1300
        )

    @unittest.mock.patch("google.generativeai.GenerativeModel")
    @unittest.mock.patch("google.generativeai.configure")
    def test_gemini_includes_max_output_tokens_in_request(self, mock_config, mock_model_cls):
        """4b. GeminiLLMClient includes max_output_tokens in GenerationConfig."""
        mock_model = mock_model_cls.return_value
        mock_response = unittest.mock.MagicMock()
        mock_response.text = '{"status": "success"}'
        mock_model.generate_content.return_value = mock_response

        client = GeminiLLMClient(api_key="gemini_test_123")
        client.generate("Test prompt", max_tokens=1300)

        mock_model.generate_content.assert_called_once()
        _, kwargs = mock_model.generate_content.call_args
        gen_config = kwargs.get("generation_config")
        self.assertIsNotNone(gen_config)
        self.assertEqual(getattr(gen_config, "max_output_tokens", None), 1300)

    @unittest.mock.patch("urllib.request.urlopen")
    def test_openrouter_includes_max_tokens_in_request(self, mock_urlopen):
        """4c. OpenRouterLLMClient includes max_tokens in API payload."""
        mock_response = unittest.mock.MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": '{"status": "success"}'}}]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        client = OpenRouterLLMClient(api_key="or_test_123")
        with unittest.mock.patch.dict("sys.modules", {"openai": None, "requests": None}):
            res_text = client.generate("Test prompt", max_tokens=700)

        self.assertEqual(res_text, '{"status": "success"}')
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        sent_payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(sent_payload.get("max_tokens"), 700)


class TestMaxTokensBudgetsAndProviderKwargs(unittest.TestCase):

    @unittest.mock.patch("google.generativeai.GenerativeModel")
    @unittest.mock.patch("google.generativeai.configure")
    def test_failover_order_and_exclusions(self, mock_config, mock_genai):
        """5, 6, 7. Failover order is Groq 120B -> Gemini -> Groq 20B -> OpenRouter, Cerebras excluded."""
        client = MultiProviderLLMFailoverClient()
        provider_names = [p.__class__.__name__ for p in client.providers]

        self.assertEqual(
            provider_names,
            ["GroqLLMClient", "GeminiLLMClient", "GroqLLMClient", "OpenRouterLLMClient"],
            "Failover order must be Groq 120B -> Gemini -> Groq 20B -> OpenRouter"
        )
        self.assertNotIn("CerebrasLLMClient", provider_names, "Cerebras must remain excluded.")
        self.assertIn("OpenRouterLLMClient", provider_names, "OpenRouter must remain in failover chain.")

class TestWorkloadAwareRoutingAndHealth(unittest.TestCase):

    def setUp(self):
        GLOBAL_HEALTH_TRACKER.reset()

    def test_scenario_a_small_legal_chat_selects_groq120b(self):
        """A. Small Legal Chat -> Groq 120B selected first."""
        g120 = MockLLMClient(responses=["Legal chat answer"])
        g120.model_name = "openai/gpt-oss-120b"
        gem = MockLLMClient(responses=["Gemini answer"])
        gem.model_name = "gemini-3.8-flash"

        client = MultiProviderLLMFailoverClient(providers=[g120, gem])
        res = client.generate("Small prompt", workload=Workload.LEGAL_CHAT)

        self.assertEqual(res, "Legal chat answer")
        self.assertEqual(g120.call_count, 1)
        self.assertEqual(gem.call_count, 0)

    def test_scenario_b_large_legal_chat_selects_gemini(self):
        """B. Large Legal Chat -> Gemini selected first (Groq 120B skipped due to token budget)."""
        g120 = MockLLMClient(responses=["Groq 120B answer"])
        g120.model_name = "openai/gpt-oss-120b"
        gem = MockLLMClient(responses=["Gemini answer"])
        gem.model_name = "gemini-3.8-flash"

        large_prompt = "x" * 30000  # ~7500 tokens > 6700 threshold

        client = MultiProviderLLMFailoverClient(providers=[g120, gem])
        res = client.generate(large_prompt, max_tokens=1000, workload=Workload.LEGAL_CHAT)

        self.assertEqual(res, "Gemini answer")
        self.assertEqual(g120.call_count, 0, "Groq 120B must be skipped without network call!")
        self.assertEqual(gem.call_count, 1)

    def test_scenario_c_small_fir_request_prefers_gemini(self):
        """C. Small FIR request -> Gemini remains preferred according to workload policy."""
        g120 = MockLLMClient(responses=[json.dumps({"status": "success", "analysis": []})])
        g120.model_name = "openai/gpt-oss-120b"
        gem = MockLLMClient(responses=[json.dumps({"status": "success", "analysis": []})])
        gem.model_name = "gemini-3.8-flash"

        client = MultiProviderLLMFailoverClient(providers=[g120, gem])
        res = client.generate("Small FIR text", workload=Workload.CITIZEN_FIR_ANALYSIS)

        self.assertEqual(gem.call_count, 1)
        self.assertEqual(g120.call_count, 0)

    def test_scenario_d_groq120b_too_large_skipped_without_network_call(self):
        """D. Groq 120B request too large -> skipped without network call."""
        g120 = MockLLMClient(responses=["Groq 120B answer"])
        g120.model_name = "openai/gpt-oss-120b"
        gem = MockLLMClient(responses=["Gemini answer"])
        gem.model_name = "gemini-3.8-flash"

        large_prompt = "word " * 7000  # ~7000 tokens
        client = MultiProviderLLMFailoverClient(providers=[g120, gem])
        res = client.generate(large_prompt, workload=Workload.LEGAL_CHAT)

        self.assertEqual(g120.call_count, 0)
        self.assertEqual(res, "Gemini answer")

    def test_scenario_e_groq120b_returns_413_falls_over(self):
        """E. Groq 120B returns 413 -> fallback provider called without repeating Groq 120B."""
        class HTTP413Client(LLMClient):
            model_name = "openai/gpt-oss-120b"
            def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
                raise RuntimeError("HTTP 413 Request entity too large")

        g120 = HTTP413Client()
        gem = MockLLMClient(responses=["Gemini fallback"])
        gem.model_name = "gemini-3.8-flash"

        client = MultiProviderLLMFailoverClient(providers=[g120, gem])
        res = client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        self.assertEqual(res, "Gemini fallback")
        self.assertEqual(gem.call_count, 1)

    def test_scenario_f_provider_returns_429_enters_cooldown(self):
        """F. Provider returns 429 -> enters cooldown (~60s)."""
        class RateLimitClient(LLMClient):
            model_name = "openai/gpt-oss-120b"
            def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
                raise RuntimeError("HTTP 429 Rate Limit Exceeded")

        g120 = RateLimitClient()
        gem = MockLLMClient(responses=["Gemini fallback"])
        gem.model_name = "gemini-3.8-flash"

        client = MultiProviderLLMFailoverClient(providers=[g120, gem])
        client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        status, reason = GLOBAL_HEALTH_TRACKER.get_status(g120)
        self.assertEqual(status, ProviderHealthStatus.COOLING_DOWN)
        self.assertEqual(reason, "rate_limited")

    def test_scenario_g_provider_in_cooldown_skipped(self):
        """G. Provider in cooldown -> skipped without network call."""
        g120 = MockLLMClient(responses=["Groq answer"])
        g120.model_name = "openai/gpt-oss-120b"
        gem = MockLLMClient(responses=["Gemini answer"])
        gem.model_name = "gemini-3.8-flash"

        GLOBAL_HEALTH_TRACKER.record_failure(g120, "HTTP 429 Rate Limit")

        client = MultiProviderLLMFailoverClient(providers=[g120, gem])
        res = client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        self.assertEqual(res, "Gemini answer")
        self.assertEqual(g120.call_count, 0, "Provider in cooldown must be skipped without network call!")

    def test_scenario_h_provider_returns_401_auth_disabled(self):
        """H. Provider returns 401 -> AUTH_DISABLED."""
        class AuthFailureClient(LLMClient):
            model_name = "openrouter/free"
            def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
                raise RuntimeError("HTTP 401 User not found")

        or_client = AuthFailureClient()

        client = MultiProviderLLMFailoverClient(providers=[or_client])
        with self.assertRaises(RuntimeError):
            client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        status, reason = GLOBAL_HEALTH_TRACKER.get_status(or_client)
        self.assertEqual(status, ProviderHealthStatus.AUTH_DISABLED)
        self.assertEqual(reason, "auth_disabled")

    def test_scenario_i_openrouter_currently_auth_disabled_skipped(self):
        """I. OpenRouter currently AUTH_DISABLED -> skipped automatically."""
        or_client = MockLLMClient(responses=["OpenRouter answer"])
        or_client.model_name = "openrouter/free"
        gem = MockLLMClient(responses=["Gemini answer"])
        gem.model_name = "gemini-3.8-flash"

        GLOBAL_HEALTH_TRACKER.set_status(or_client, ProviderHealthStatus.AUTH_DISABLED)

        client = MultiProviderLLMFailoverClient(providers=[or_client, gem])
        res = client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        self.assertEqual(res, "Gemini answer")
        self.assertEqual(or_client.call_count, 0, "AUTH_DISABLED OpenRouter must be skipped without network call!")

    def test_scenario_j_provider_succeeds_resets_health_state(self):
        """J. Provider succeeds -> health state reset."""
        g120 = MockLLMClient(responses=["Groq answer"])
        g120.model_name = "openai/gpt-oss-120b"

        GLOBAL_HEALTH_TRACKER.record_failure(g120, "HTTP 503 Service Unavailable")
        GLOBAL_HEALTH_TRACKER.reset()

        client = MultiProviderLLMFailoverClient(providers=[g120])
        res = client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        self.assertEqual(res, "Groq answer")
        status, _ = GLOBAL_HEALTH_TRACKER.get_status(g120)
        self.assertEqual(status, ProviderHealthStatus.HEALTHY)

    def test_scenario_k_all_providers_fail_safe_fallback(self):
        """K. All cloud providers fail -> existing safe fallback behavior."""
        class FailingClient(LLMClient):
            def __init__(self, name):
                self.model_name = name
            def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
                raise RuntimeError(f"HTTP 500 {self.model_name} Error")

        p1 = FailingClient("openai/gpt-oss-120b")
        p2 = FailingClient("gemini-3.8-flash")

        client = MultiProviderLLMFailoverClient(providers=[p1, p2])
        with self.assertRaises(RuntimeError) as cm:
            client.generate("Prompt", workload=Workload.LEGAL_CHAT)

        self.assertIn("All LLM providers", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
