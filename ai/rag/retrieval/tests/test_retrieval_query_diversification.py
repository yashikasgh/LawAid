"""test_retrieval_query_diversification.py — Phase 2 Retrieval Unit & Regression Tests.

Located at: ai/rag/retrieval/tests/test_retrieval_query_diversification.py
"""

import sys
import unittest
import re
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import (
    generate_queries,
    validate_llm_queries,
    _generate_deterministic_queries,
    construct_query_generator_prompt
)
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.pipeline import run_pipeline


from ai.rag.analysis.legal_analyzer import MockLLMClient


class TestRetrievalQueryDiversification(unittest.TestCase):

    def test_single_offence_adaptive_query_diversification(self):
        """Verify adaptive query validation for simple single-offence incidents (2-3 queries)."""
        incident = "On 15 August 2026, two men on a motorcycle grabbed a woman's gold chain from her neck and fled."
        ner_res = extract_entities(incident)
        
        mock_response = '''{
            "queries": [
                {"query_type": "incident_context", "query": "two men on motorcycle grabbed gold chain from woman neck"},
                {"query_type": "legal_concept", "query": "theft committed by sudden quick or forcible seizure of property"}
            ]
        }'''
        mock_llm = MockLLMClient([mock_response])
        q_out = generate_queries(ner_res, llm_client=mock_llm)
        queries = q_out.get("queries", [])

        self.assertGreaterEqual(len(queries), 2)
        self.assertLessEqual(len(queries), 3)

        # Check section number absence
        for q in queries:
            q_text = q["query"]
            self.assertNotRegex(q_text, r"\b(Section|sec|\d{3})\b", f"Query contained section reference: {q_text}")

    def test_multi_offence_adaptive_query_diversification(self):
        """Verify adaptive query validation for complex multi-offence incidents (3-5 queries)."""
        incident = "On 10 October 2026, the accused broke the lock of a house at night, entered inside, punched the house owner causing bodily pain, and stole 20,000 rupees cash."
        ner_res = extract_entities(incident)

        mock_response = '''{
            "queries": [
                {"query_type": "incident_context", "query": "accused broke lock of residential house entered punched house owner and stole cash"},
                {"query_type": "action_context", "query": "broke lock of residential house at night"},
                {"query_type": "legal_concept", "query": "voluntarily causing hurt bodily pain to house owner"},
                {"query_type": "fact_focused", "query": "stole 20000 rupees cash inside dwelling house"}
            ]
        }'''
        mock_llm = MockLLMClient([mock_response])
        q_out = generate_queries(ner_res, llm_client=mock_llm)
        queries = q_out.get("queries", [])

        self.assertGreaterEqual(len(queries), 3)
        self.assertLessEqual(len(queries), 5)

        query_types = [q["query_type"] for q in queries]
        self.assertIn("incident_context", query_types)
        self.assertIn("action_context", query_types)

    def test_no_section_numbers_in_prompt_or_generated_queries(self):
        """Verify prompt and validator strictly prohibit BNS section numbers and section inquiry terms."""
        ner_res = {"raw_text": "A thief stole a phone.", "offence_types": ["theft"]}
        prompt = construct_query_generator_prompt(ner_res)

        self.assertIn("Do NOT generate section numbers", prompt)
        self.assertIn("ADAPTIVE QUERY COUNT RULES", prompt)

        # Rejection test for section numbers in validator
        invalid_llm_json = {
            "queries": [
                {"query_type": "incident_context", "query": "Theft under Section 303"},
                {"query_type": "legal_concept", "query": "Theft of mobile phone"}
            ]
        }
        res = validate_llm_queries(invalid_llm_json, ner_res)
        self.assertIsNone(res, "Validator should reject queries containing section numbers.")

    def test_no_invented_facts_validation(self):
        """Verify validator rejects ungrounded facts or upgraded offences (e.g. ransom, cybercrime)."""
        ner_res = {"raw_text": "A man grabbed a phone and ran away.", "offence_types": ["theft"]}
        unsupported_json = {
            "queries": [
                {"query_type": "incident_context", "query": "A man grabbed a phone and ran away."},
                {"query_type": "legal_concept", "query": "Kidnapping for ransom and cybercrime"}
            ]
        }
        res = validate_llm_queries(unsupported_json, ner_res)
        self.assertIsNone(res, "Validator should reject ungrounded legal concepts like ransom.")

    def test_candidate_retention_window_in_pipeline(self):
        """Verify pipeline candidate retention window defaults to top_k_rerank = 15."""
        import inspect
        sig = inspect.signature(run_pipeline)
        top_k_param = sig.parameters.get("top_k_rerank")
        self.assertIsNotNone(top_k_param)
        self.assertEqual(top_k_param.default, 15, "top_k_rerank default in pipeline should be 15.")

    def test_rrf_mathematical_behavior_unaltered(self):
        """Verify RRF formula accumulates score across multi-query occurrences without altered math."""
        candidates = [
            {"id": "doc1", "rank": 1, "distance": 0.4, "title": "Doc 1"},
            {"id": "doc2", "rank": 2, "distance": 0.5, "title": "Doc 2"},
            {"id": "doc1", "rank": 3, "distance": 0.42, "title": "Doc 1"}, # doc1 appears twice
        ]
        reranked = rerank_candidates("test incident", candidates, top_k=10)

        self.assertEqual(len(reranked), 2)
        # Doc 1 has 2 RRF contributions: 1/(60+1) + 1/(60+3) = 0.016393 + 0.015873 = 0.032266
        # Similarity: 1 - 0.4/2 = 0.8 -> +0.08 = ~0.112266
        doc1_cand = next(c for c in reranked if c["id"] == "doc1")
        doc2_cand = next(c for c in reranked if c["id"] == "doc2")

        self.assertGreater(doc1_cand["rerank_score"], doc2_cand["rerank_score"])
        self.assertIn("across 2 retrieval query occurrence(s)", doc1_cand["scoring_reasons"][1])

    def test_no_hardcoded_section_mappings_in_retrieval_module(self):
        """Verify retrieval module files contain zero hardcoded section maps or offence-to-section dicts."""
        retrieval_dir = PROJECT_ROOT / "ai" / "rag" / "retrieval"
        python_files = list(retrieval_dir.glob("*.py"))

        section_map_patterns = [
            r'"304"\s*:\s*',
            r'"318"\s*:\s*',
            r'"316"\s*:\s*',
            r'"125"\s*:\s*',
            r'if\s+section\s*==',
            r'section_mappings\s*=',
            r'offence_section_map\s*='
        ]
        regex = re.compile("|".join(section_map_patterns))

        for py_file in python_files:
            if "backup" in py_file.name:
                continue
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                matches = regex.findall(content)
                self.assertEqual(
                    len(matches),
                    0,
                    f"File {py_file.name} contains illegal hardcoded section mapping: {matches}"
                )


if __name__ == "__main__":
    unittest.main()
