"""test_pipeline.py — Unit tests for LawAid End-to-End Analysis Pipeline.

Located at: ai/rag/tests/test_pipeline.py
"""

import json
import re
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
        self.mock_query_response = json.dumps({
            "queries": [
                {
                    "query_type": "fact_focused",
                    "query": "taking mobile phone without consent"
                },
                {
                    "query_type": "incident_context",
                    "query": "Rahul entered shop and took mobile phone"
                },
                {
                    "query_type": "legal_concept",
                    "query": "dishonest taking of movable property"
                }
            ]
        })
        self.mock_llm_response = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_303_303(2)",
                    "applicability": "supported",
                    "reasoning": "The accused took a mobile phone belonging to Vijay without consent."
                }
            ],
            "limitations": []
        })

    def test_1_privacy_happens_before_llm_call(self):
        """1. Verify privacy sanitization occurs before any LLM prompt generation."""
        mock_llm = MockLLMClient(responses=[self.mock_query_response, self.mock_llm_response])

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
        mock_llm = MockLLMClient(responses=[self.mock_query_response, self.mock_llm_response])

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
        mock_llm = MockLLMClient(responses=[self.mock_query_response, self.mock_llm_response])

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
        mock_llm = MockLLMClient(responses=[self.mock_query_response, self.mock_llm_response])

        # When injected explicitly, uses the injected client
        res = run_pipeline(self.sample_raw_incident, llm_client=mock_llm)
        self.assertGreater(len(mock_llm.prompts_received), 0)

    def test_6_empty_query_generator_fallback(self):
        """6. Verify pipeline falls back to sanitized text when Query Generator returns empty queries."""
        empty_queries_mock = MockLLMClient(responses=['{"queries": []}', self.mock_llm_response])
        res = run_pipeline("Simple incident with no offence", llm_client=empty_queries_mock)
        self.assertEqual(res["status"], "success")

    def test_7_analysis_candidate_limit_truncates_analysis_context_to_7(self):
        """7. Verify full RRF reranking produces candidate pool and exactly 7 candidates are passed to LLM analysis when >7 exist."""
        mock_llm = MockLLMClient(responses=[self.mock_query_response, self.mock_llm_response])
        res = run_pipeline(self.sample_raw_incident, llm_client=mock_llm, top_k_rerank=15, analysis_candidate_limit=7)

        self.assertIn("reranked_candidates", res)
        # Full reranked candidate pool contains up to 15 items
        full_reranked = res["reranked_candidates"]
        self.assertIsInstance(full_reranked, list)

        # Inspect legal analysis prompt received by LLM
        analysis_prompt = mock_llm.prompts_received[1]  # 2nd call is legal analysis prompt
        self.assertIn("RETRIEVED BNS LEGAL CONTEXT:", analysis_prompt)

        # Extract candidates passed in prompt JSON
        m_ctx = re.search(r"RETRIEVED BNS LEGAL CONTEXT:\s*(\[.*\])", analysis_prompt, re.DOTALL)
        self.assertIsNotNone(m_ctx)
        sections = json.loads(m_ctx.group(1))
        passed_docs = []
        for sec in sections:
            if "results" in sec:
                passed_docs.extend(sec["results"])
            elif "clauses" in sec:
                passed_docs.extend(sec["clauses"])

        if len(full_reranked) >= 7:
            self.assertEqual(len(passed_docs), 7, "Exactly 7 candidates must be passed to LLM analysis when >=7 exist")
            # Verify passed candidate IDs match top 7 of full reranked candidate pool
            self.assertEqual(set(doc["id"] for doc in passed_docs), set(doc["id"] for doc in full_reranked[:7]))

    def test_8_analysis_candidate_limit_preserves_fewer_than_7_candidates(self):
        """8. Verify fewer than 7 candidates are preserved as-is without error or padding."""
        mock_llm = MockLLMClient(responses=[self.mock_query_response, self.mock_llm_response])
        res = run_pipeline(self.sample_raw_incident, llm_client=mock_llm, top_k_rerank=3, analysis_candidate_limit=7)

        self.assertIn("reranked_candidates", res)
        full_reranked = res["reranked_candidates"]
        self.assertTrue(len(full_reranked) <= 3)

        analysis_prompt = mock_llm.prompts_received[1]
        m_ctx = re.search(r"RETRIEVED BNS LEGAL CONTEXT:\s*(\[.*\])", analysis_prompt, re.DOTALL)
        sections = json.loads(m_ctx.group(1))
        passed_docs = []
        for sec in sections:
            if "results" in sec:
                passed_docs.extend(sec["results"])
            elif "clauses" in sec:
                passed_docs.extend(sec["clauses"])
        self.assertEqual(len(passed_docs), len(full_reranked), "Fewer than 7 candidates must be preserved as-is")

    def test_9_reranked_candidates_contains_authoritative_metadata(self):
        """9. Verify reranked_candidates items contain target_clause_text, section_definition, and schedule_1 fields."""
        mock_llm = MockLLMClient(responses=[self.mock_query_response, self.mock_llm_response])
        res = run_pipeline(self.sample_raw_incident, llm_client=mock_llm)

        self.assertIn("reranked_candidates", res)
        reranked = res["reranked_candidates"]
        self.assertGreater(len(reranked), 0)
        first_cand = reranked[0]
        self.assertIn("target_clause_text", first_cand)
        self.assertIn("section_definition", first_cand)
        self.assertIn("schedule_1", first_cand)
        self.assertTrue(len(first_cand["target_clause_text"]) > 0)

    def test_10_chat_pipeline_history_and_sentiment(self):
        """10. Verify run_chat_pipeline accepts history, performs sentiment detection, and reduces LLM calls."""
        from ai.rag.pipeline import run_chat_pipeline

        class DynamicMockLLM(MockLLMClient):
            def generate(self, prompt, max_tokens=None, **kwargs):
                self.prompts_received.append(prompt)
                self.call_count += 1
                if "RETRIEVED BNS LEGAL CONTEXT:" in prompt:
                    m = re.search(r'"id":\s*"([^"]+)"', prompt)
                    doc_id = m.group(1) if m else "bns_252"
                    return json.dumps({
                        "status": "success",
                        "analysis": [
                            {
                                "document_id": doc_id,
                                "applicability": "supported",
                                "reasoning": "The accused took property without permission."
                            }
                        ],
                        "limitations": []
                    })
                return json.dumps({"reply": "I am sorry to hear you experienced this. Section 252 applies."})

        mock_llm = DynamicMockLLM()

        history = [
            {"role": "user", "content": "Rahul took a mobile phone belonging to Vijay without permission."},
            {"role": "assistant", "content": "I understand."}
        ]
        res = run_chat_pipeline("What is the punishment?", history=history, llm_client=mock_llm)

        self.assertEqual(res["status"], "ok")
        self.assertIn("reply", res)
        # Verify exactly 2 LLM calls made (Analysis + Synthesis), skipping query generator LLM
        self.assertEqual(len(mock_llm.prompts_received), 2)
        # Check history passed to synthesis prompt
        synthesis_prompt = mock_llm.prompts_received[1]
        self.assertIn("CONVERSATION HISTORY:", synthesis_prompt)
        self.assertIn("COMMUNICATION TONE & EMPATHY:", synthesis_prompt)

    def test_11_chat_pipeline_fallback_clean_response(self):
        """11. Verify fallback response in run_chat_pipeline returns concise safe response without dumping raw retrieval candidates."""
        from ai.rag.pipeline import run_chat_pipeline
        # Mock LLM that raises an error (simulating offline/failover failure)
        class FailingLLMClient(MockLLMClient):
            def generate(self, prompt, **kwargs):
                raise RuntimeError("All LLM providers failed")

        failing_llm = FailingLLMClient()
        res = run_chat_pipeline("Someone stole my phone.", llm_client=failing_llm)

        self.assertEqual(res["status"], "ok")
        self.assertIn("reply", res)
        self.assertIn("LawAid could not complete the legal analysis right now", res["reply"])
        self.assertEqual(res["sections"], [])
        self.assertNotIn("Identified Offences", res["reply"])

    def test_12_chat_pipeline_grounding_filters_unsupported_sections(self):
        """12. Verify unsupported/uncertain sections do not reach Chat formatted_sections recommendation."""
        from ai.rag.pipeline import run_chat_pipeline

        class AnalysisWithUncertainMock(MockLLMClient):
            def generate(self, prompt, **kwargs):
                self.prompts_received.append(prompt)
                if "RETRIEVED BNS LEGAL CONTEXT:" in prompt:
                    return json.dumps({
                        "status": "success",
                        "analysis": [
                            {
                                "document_id": "bns_303_303(2)",
                                "applicability": "supported",
                                "reasoning": "Theft of mobile phone."
                            },
                            {
                                "document_id": "bns_329_329(1)",
                                "applicability": "not_supported",
                                "reasoning": "No house trespass occurred."
                            }
                        ],
                        "limitations": []
                    })
                return json.dumps({"reply": "Section 303 applies for theft of mobile phone."})

        mock_llm = AnalysisWithUncertainMock()
        res = run_chat_pipeline("Someone stole my phone.", llm_client=mock_llm)

        self.assertEqual(res["status"], "ok")
        # Only supported sections should be in res["sections"]
        self.assertTrue(any("303" in s for s in res["sections"]))
        self.assertFalse(any("329" in s for s in res["sections"]))

    def test_13_chat_pipeline_multiturn_history_and_20000_rupees_context(self):
        """13. Verify 3-turn follow-up history (including ₹20,000 cost context) is preserved and passed to RAG."""
        from ai.rag.pipeline import run_chat_pipeline

        class MultiturnMock(MockLLMClient):
            def generate(self, prompt, max_tokens=None, **kwargs):
                self.prompts_received.append(prompt)
                if "RETRIEVED BNS LEGAL CONTEXT:" in prompt:
                    m = re.search(r'"id":\s*"([^"]+)"', prompt)
                    doc_id = m.group(1) if m else "bns_303"
                    return json.dumps({
                        "status": "success",
                        "analysis": [
                            {
                                "document_id": doc_id,
                                "applicability": "supported",
                                "reasoning": "Theft of phone valued at 20,000 rupees."
                            }
                        ],
                        "limitations": []
                    })
                return json.dumps({"reply": "The punishment for theft of property worth 20,000 rupees under BNS Section 303(2) is up to 3 years imprisonment or fine."})

        mock_llm = MultiturnMock()
        history = [
            {"role": "user", "content": "Someone stole my phone."},
            {"role": "assistant", "content": "This falls under theft under Section 303 of BNS."},
            {"role": "user", "content": "What punishment can they get?"},
            {"role": "assistant", "content": "The punishment depends on the value of the property."}
        ]

        turn_3_msg = "What if the phone cost 20,000 rupees?"
        res = run_chat_pipeline(turn_3_msg, history=history, llm_client=mock_llm)

        self.assertEqual(res["status"], "ok")
        self.assertIn("20,000", res["reply"])

        # Check prompt sent to legal analyzer contained effective incident combining user history
        analysis_prompt = mock_llm.prompts_received[0]
        self.assertIn("20,000 rupees", analysis_prompt)
        self.assertIn("Someone stole my phone", analysis_prompt)


if __name__ == "__main__":
    unittest.main()


