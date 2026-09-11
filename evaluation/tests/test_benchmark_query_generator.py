import unittest
import json
import re
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.run_evaluation import BenchmarkLLMClient
from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import (
    construct_query_generator_prompt,
    validate_llm_queries,
    _parse_json_from_llm
)
from ai.rag.analysis.legal_analyzer import MultiProviderLLMFailoverClient


class TestBenchmarkQueryGenerator(unittest.TestCase):
    """Test suite proving BenchmarkLLMClient handles query-generation prompts deterministically."""

    def setUp(self):
        real_failover = MultiProviderLLMFailoverClient()
        self.client = BenchmarkLLMClient(real_failover)

    def test_benchmark_query_generation_prompt_recognition(self):
        """Test that BenchmarkLLMClient recognizes query-generation prompts and returns valid JSON queries."""
        incident = "On 5 September 2026, an unknown person took the complainant's bicycle parked outside the grocery store without his consent."
        ner_res = extract_entities(incident)
        prompt = construct_query_generator_prompt(ner_res)

        # Force client to offline fallback path
        raw_output = self.client._offline_evaluate(prompt)
        parsed = _parse_json_from_llm(raw_output)
        
        self.assertIsNotNone(parsed)
        self.assertIn("queries", parsed)
        queries = parsed["queries"]
        self.assertGreaterEqual(len(queries), 2)

    def test_benchmark_receives_multiple_valid_queries(self):
        """Test that generated queries pass production validate_llm_queries."""
        incident = "On 12 September 2026, while the victim was walking on the street, two persons on a motorcycle snatched her gold chain from her neck with force and sped away."
        ner_res = extract_entities(incident)
        prompt = construct_query_generator_prompt(ner_res)

        raw_output = self.client._offline_evaluate(prompt)
        parsed = _parse_json_from_llm(raw_output)
        valid_queries = validate_llm_queries(parsed, ner_res)

        self.assertIsNotNone(valid_queries)
        self.assertGreaterEqual(len(valid_queries), 2)
        self.assertLessEqual(len(valid_queries), 5)

    def test_no_section_numbers_introduced(self):
        """Test that no BNS/BNSS section numbers or statutory numbers are present in queries."""
        incidents = [
            "On 5 September 2026, accused stole a watch worth Rs 800.",
            "On 10 October 2026, accused broke into shop at night, punched owner, and stole Rs 20,000.",
            "On 15 August 2026, two men snatched gold chain under section context."
        ]

        section_regex = re.compile(r"\bSection\s+\d+\b|\bsec\.?\s*\d+\b|\b\d{3}\b", re.IGNORECASE)

        for inc in incidents:
            ner_res = extract_entities(inc)
            prompt = construct_query_generator_prompt(ner_res)
            raw_output = self.client._offline_evaluate(prompt)
            parsed = _parse_json_from_llm(raw_output)
            valid_queries = validate_llm_queries(parsed, ner_res)

            self.assertIsNotNone(valid_queries)
            for q in valid_queries:
                q_text = q["query"]
                self.assertIsNone(
                    section_regex.search(q_text),
                    f"Query contains forbidden section number: {q_text}"
                )

    def test_no_unsupported_facts_introduced(self):
        """Test that queries do not introduce ungrounded facts or unsupported legal concepts."""
        incident = "On 1 September 2026, a stranger punched the victim in the chest in order to knock him down so he could snatch his leather bag."
        ner_res = extract_entities(incident)
        prompt = construct_query_generator_prompt(ner_res)

        raw_output = self.client._offline_evaluate(prompt)
        parsed = _parse_json_from_llm(raw_output)
        valid_queries = validate_llm_queries(parsed, ner_res)

        self.assertIsNotNone(valid_queries)
        forbidden_facts = ["ransom", "dacoity", "homicide", "cybercrime", "weapon"]
        for q in valid_queries:
            q_lower = q["query"].lower()
            for forbidden in forbidden_facts:
                self.assertNotIn(forbidden, q_lower)

    def test_adaptive_query_counts_simple_vs_complex(self):
        """Test that simple incidents receive 2-3 queries while complex incidents receive 4-5 queries."""
        simple_incident = "On 5 September 2026, an unknown person took the complainant's bicycle parked outside the grocery store without his consent."
        complex_incident = "On 10 October 2026, accused broke the lock of a residential house at night, entered inside, punched the house owner causing bodily pain, and stole Rs 20,000 cash."

        # Simple
        ner_simple = extract_entities(simple_incident)
        prompt_simple = construct_query_generator_prompt(ner_simple)
        out_simple = self.client._offline_evaluate(prompt_simple)
        valid_simple = validate_llm_queries(_parse_json_from_llm(out_simple), ner_simple)

        # Complex
        ner_complex = extract_entities(complex_incident)
        prompt_complex = construct_query_generator_prompt(ner_complex)
        out_complex = self.client._offline_evaluate(prompt_complex)
        valid_complex = validate_llm_queries(_parse_json_from_llm(out_complex), ner_complex)

        self.assertIsNotNone(valid_simple)
        self.assertIsNotNone(valid_complex)

        self.assertLessEqual(len(valid_simple), 3)
        self.assertGreater(len(valid_complex), len(valid_simple))

    def test_existing_legal_analysis_behavior_unchanged(self):
        """Test that legal-analysis prompt evaluation in BenchmarkLLMClient remains completely unchanged."""
        legal_prompt = (
            "STATUTORY EVALUATION TASK:\n"
            "Evaluate statutory applicability...\n\n"
            "RETRIEVED BNS LEGAL CONTEXT:\n"
            '[{"query": "theft", "results": [{"id": "bns_303_303(2)", "section": "303", "clause": "2", "schedule_1": {"offence": "theft"}}]}]\n'
        )
        
        out = self.client._offline_evaluate(legal_prompt.lower())
        parsed = json.loads(out)
        self.assertEqual(parsed.get("status"), "success")
        self.assertIn("analysis", parsed)


if __name__ == "__main__":
    unittest.main()
