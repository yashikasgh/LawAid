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
    OllamaLLMClient,
    MultiProviderLLMFailoverClient,
    GeminiLLMClient,
    CerebrasLLMClient,
    LLMClient
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




class TestMultiProviderLLMFailover(unittest.TestCase):

    def setUp(self):
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
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=failover_client)

        self.assertEqual(res["status"], "success")
        self.assertEqual(p1.call_count, 1)
        self.assertEqual(p2.call_count, 0)
        self.assertEqual(res["provider_used"]["model"], "openai/gpt-oss-120b")

    def test_failover_2_groq_429_fails_over_to_gemini(self):
        """2. Groq returns HTTP 429 -> Gemini is attempted."""
        class RateLimitedClient(LLMClient):
            model_name = "openai/gpt-oss-120b"
            def generate(self, prompt: str) -> str:
                raise RuntimeError("Groq API text generation failed for model 'openai/gpt-oss-120b': HTTP 429 Rate Limit Exceeded")

        p1 = RateLimitedClient()
        p2 = MockLLMClient(responses=[json.dumps({
            "status": "success",
            "analysis": [{"document_id": "bns_303_303(2)", "applicability": "supported", "reasoning": "Stole phone."}],
            "limitations": []
        })])
        p2.model_name = "gemini-1.5-flash"

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=failover_client)

        self.assertEqual(res["status"], "success")
        self.assertEqual(p2.call_count, 1)
        self.assertEqual(res["provider_used"]["model"], "gemini-1.5-flash")
        self.assertEqual(len(res["provider_trace"]), 2)
        self.assertEqual(res["provider_trace"][0]["status"], "failed")
        self.assertEqual(res["provider_trace"][1]["status"], "success")

    def test_failover_3_malformed_json_tries_next_provider(self):
        """3. Provider returns malformed structured output -> reject and try next provider."""
        p1 = MockLLMClient(responses=["Not JSON content at all"])
        p1.model_name = "openai/gpt-oss-120b"
        p2 = MockLLMClient(responses=[json.dumps({
            "status": "success",
            "analysis": [{"document_id": "bns_303_303(2)", "applicability": "supported", "reasoning": "Stole phone."}],
            "limitations": []
        })])
        p2.model_name = "gemini-1.5-flash"

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=failover_client)

        self.assertEqual(res["status"], "success")
        self.assertEqual(p1.call_count, 1)
        self.assertEqual(p2.call_count, 1)
        self.assertEqual(res["provider_used"]["model"], "gemini-1.5-flash")

    def test_failover_4_all_providers_fail_returns_analysis_unavailable(self):
        """4. All providers fail -> returns status 'analysis_unavailable'."""
        class AlwaysFailingClient(LLMClient):
            def __init__(self, name):
                self.model_name = name
            def generate(self, prompt: str) -> str:
                raise RuntimeError(f"{self.model_name} offline")

        p1 = AlwaysFailingClient("openai/gpt-oss-120b")
        p2 = AlwaysFailingClient("gemini-1.5-flash")
        p3 = AlwaysFailingClient("openai/gpt-oss-20b")

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2, p3])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=failover_client)

        self.assertEqual(res["status"], "analysis_unavailable")
        self.assertEqual(res["analysis"], [])
        self.assertIn("AI legal analysis is temporarily unavailable", res["limitations"][0])
        self.assertEqual(len(res["provider_trace"]), 3)

    def test_failover_5_groq_and_gemini_fail_cerebras_succeeds(self):
        """5. Groq 120B fails -> Gemini fails -> Cerebras succeeds."""
        class AlwaysFailingClient(LLMClient):
            def __init__(self, name):
                self.model_name = name
            def generate(self, prompt: str) -> str:
                raise RuntimeError(f"{self.model_name} rate limit or connection error")

        p1 = AlwaysFailingClient("openai/gpt-oss-120b")
        p2 = AlwaysFailingClient("gemini-3.8-flash")
        p3 = MockLLMClient(responses=[json.dumps({
            "status": "success",
            "analysis": [{"document_id": "bns_303_303(2)", "applicability": "supported", "reasoning": "Stole phone."}],
            "limitations": []
        })])
        p3.model_name = "gpt-oss-120b"
        p4 = MockLLMClient(responses=[])
        p4.model_name = "openai/gpt-oss-20b"

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2, p3, p4])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=failover_client)

        self.assertEqual(res["status"], "success")
        self.assertEqual(p3.call_count, 1)
        self.assertEqual(p4.call_count, 0)
        self.assertEqual(res["provider_used"]["model"], "gpt-oss-120b")
        self.assertEqual(len(res["provider_trace"]), 3)
        self.assertEqual(res["provider_trace"][0]["status"], "failed")
        self.assertEqual(res["provider_trace"][1]["status"], "failed")
        self.assertEqual(res["provider_trace"][2]["status"], "success")

    def test_failover_6_groq_gemini_cerebras_fail_groq20b_succeeds(self):
        """6. Groq 120B fails -> Gemini fails -> Cerebras fails -> Groq 20B succeeds."""
        class AlwaysFailingClient(LLMClient):
            def __init__(self, name):
                self.model_name = name
            def generate(self, prompt: str) -> str:
                raise RuntimeError(f"{self.model_name} rate limit or payment error")

        p1 = AlwaysFailingClient("openai/gpt-oss-120b")
        p2 = AlwaysFailingClient("gemini-3.8-flash")
        p3 = AlwaysFailingClient("gpt-oss-120b")
        p4 = MockLLMClient(responses=[json.dumps({
            "status": "success",
            "analysis": [{"document_id": "bns_303_303(2)", "applicability": "supported", "reasoning": "Stole phone."}],
            "limitations": []
        })])
        p4.model_name = "openai/gpt-oss-20b"

        failover_client = MultiProviderLLMFailoverClient(providers=[p1, p2, p3, p4])
        res = analyze_incident(self.sample_ner, self.sample_retrieval, llm_client=failover_client)

        self.assertEqual(res["status"], "success")
        self.assertEqual(p4.call_count, 1)
        self.assertEqual(res["provider_used"]["model"], "openai/gpt-oss-20b")
        self.assertEqual(len(res["provider_trace"]), 4)
        self.assertEqual(res["provider_trace"][0]["status"], "failed")
        self.assertEqual(res["provider_trace"][1]["status"], "failed")
        self.assertEqual(res["provider_trace"][2]["status"], "failed")
        self.assertEqual(res["provider_trace"][3]["status"], "success")

    def test_failover_7_all_4_providers_unavailable(self):
        """7. All 4 providers fail -> returns status 'analysis_unavailable'."""
        class AlwaysFailingClient(LLMClient):
            def __init__(self, name):
                self.model_name = name
            def generate(self, prompt: str) -> str:
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
        self.assertEqual(len(res["provider_trace"]), 4)


if __name__ == "__main__":
    unittest.main()

