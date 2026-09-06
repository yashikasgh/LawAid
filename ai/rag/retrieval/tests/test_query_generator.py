"""test_query_generator.py — Unit test suite for the Query Generator contract in LawAid RAG pipeline.

Located at: ai/rag/retrieval/tests/test_query_generator.py
"""

import copy
import json
import re
import sys
import unittest
from pathlib import Path

# Add project root (LawAid) to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add retrieval directory to sys.path
RETRIEVAL_DIR = Path(__file__).resolve().parent.parent
if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_DIR))

# Add analysis directory to sys.path
ANALYSIS_DIR = PROJECT_ROOT / "ai" / "rag" / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

try:
    from query_generator import generate_queries
except ImportError:
    try:
        from ai.rag.retrieval.query_generator import generate_queries
    except ImportError:
        generate_queries = None

try:
    from legal_analyzer import LLMClient, MockLLMClient
except ImportError:
    from ai.rag.analysis.legal_analyzer import LLMClient, MockLLMClient


def _extract_query_strings(res):
    """Helper to extract query strings regardless of whether res['queries'] contains dicts or strings."""
    if not isinstance(res, dict) or "queries" not in res:
        return []
    queries = res["queries"]
    if not isinstance(queries, list):
        return []
    extracted = []
    for q in queries:
        if isinstance(q, str):
            extracted.append(q)
        elif isinstance(q, dict) and "query" in q and isinstance(q["query"], str):
            extracted.append(q["query"])
    return extracted


class TestQueryGenerator(unittest.TestCase):

    def setUp(self):
        if generate_queries is None:
            self.skipTest("query_generator.py module or generate_queries function is not implemented yet.")

    def test_1_single_offence_multiple_queries(self):
        """1. Single offence with raw incident produces multiple retrieval-oriented queries."""
        ner_input = {
            "offence_types": ["criminal intimidation"],
            "raw_text": "The accused entered the shop without permission and threatened to kill Vijay if he called the police."
        }
        res = generate_queries(ner_input)
        self.assertIsInstance(res, dict, "Output must be a dictionary.")
        self.assertIn("queries", res, "Output dictionary must contain 'queries' key.")

        queries = _extract_query_strings(res)
        self.assertGreater(
            len(queries),
            1,
            f"Expected multiple retrieval queries for a single offence with raw text, got {len(queries)}"
        )

    def test_2_multiple_offences_produce_relevant_queries(self):
        """2. Multiple offences produce queries relevant to each offence."""
        ner_input = {
            "offence_types": ["criminal trespass", "criminal intimidation"],
            "raw_text": "The accused entered the shop without permission and threatened to kill Vijay if he called the police."
        }
        res = generate_queries(ner_input)
        queries = res.get("queries", [])
        self.assertIsInstance(queries, list, "'queries' must be a list.")

        trespass_found = False
        intimidation_found = False

        for q in queries:
            if isinstance(q, dict):
                offence = q.get("offence_type", "").lower()
                query_str = q.get("query", "").lower()
                if "trespass" in offence or "trespass" in query_str or "entered" in query_str:
                    trespass_found = True
                if "intimidation" in offence or "threatened" in query_str or "kill" in query_str or "intimidation" in query_str:
                    intimidation_found = True
            elif isinstance(q, str):
                q_lower = q.lower()
                if "trespass" in q_lower or "entered" in q_lower or "permission" in q_lower:
                    trespass_found = True
                if "intimidation" in q_lower or "threatened" in q_lower or "kill" in q_lower:
                    intimidation_found = True

        self.assertTrue(trespass_found, "Queries should cover 'criminal trespass' offence.")
        self.assertTrue(intimidation_found, "Queries should cover 'criminal intimidation' offence.")

    def test_3_empty_offence_types_and_missing_raw_text_returns_no_queries(self):
        """3. Empty offence_types AND missing/empty raw_text returns no queries."""
        ner_input_empty_all = {
            "offence_types": [],
            "raw_text": ""
        }
        res_empty = generate_queries(ner_input_empty_all)
        self.assertEqual(
            _extract_query_strings(res_empty),
            [],
            "Expected empty query list when both offence_types and raw_text are empty."
        )

        ner_input_no_keys = {}
        res_no_keys = generate_queries(ner_input_no_keys)
        self.assertEqual(
            _extract_query_strings(res_no_keys),
            [],
            "Expected empty query list when both offence_types and raw_text keys are missing."
        )

    def test_4_missing_raw_text_handled_safely(self):
        """4. Missing raw_text is handled safely."""
        inputs_to_test = [
            {"offence_types": ["theft"]},  # Missing raw_text key
            {"offence_types": ["theft"], "raw_text": ""},  # Empty string
            {"offence_types": ["theft"], "raw_text": None},  # None value
        ]
        for ner_input in inputs_to_test:
            with self.subTest(ner_input=ner_input):
                res = generate_queries(ner_input)
                self.assertIsInstance(res, dict, "Should return a dictionary safely.")
                self.assertIn("queries", res, "Should contain 'queries' key.")
                self.assertIsInstance(res["queries"], list, "'queries' must be a list.")

    def test_5_invalid_non_dict_input_handled_safely(self):
        """5. Invalid/non-dict input is handled safely."""
        invalid_inputs = [
            None,
            "invalid string",
            12345,
            ["criminal intimidation"],
            True
        ]
        for inv_input in invalid_inputs:
            with self.subTest(invalid_input=inv_input):
                res = generate_queries(inv_input)
                self.assertIsInstance(res, dict, "Should handle non-dict input safely and return dict.")
                self.assertEqual(res.get("queries"), [], "Should return empty queries list for invalid input.")

    def test_6_input_ner_dictionary_not_mutated(self):
        """6. Input NER dictionary is not mutated."""
        original_ner = {
            "victims": ["Vijay"],
            "accused": ["Sunil"],
            "persons": [],
            "dates": [],
            "times": [],
            "locations": ["Chandni Chowk"],
            "organizations": [],
            "offence_types": ["criminal trespass", "criminal intimidation"],
            "raw_text": "The accused entered the shop without permission and threatened to kill Vijay if he called the police."
        }
        ner_copy = copy.deepcopy(original_ner)

        _ = generate_queries(original_ner)
        self.assertEqual(
            original_ner,
            ner_copy,
            "generate_queries must not mutate the input NER dictionary."
        )

    def test_7_generated_queries_are_non_empty_natural_language_strings(self):
        """7. Generated queries are non-empty natural-language strings."""
        ner_input = {
            "offence_types": ["criminal intimidation"],
            "raw_text": "The accused entered the shop without permission and threatened to kill Vijay if he called the police."
        }
        res = generate_queries(ner_input)
        queries = _extract_query_strings(res)
        self.assertGreater(len(queries), 0, "Should generate at least one query.")

        for q in queries:
            self.assertIsInstance(q, str, "Query item must be a string.")
            self.assertTrue(q.strip(), "Query string must not be empty or whitespace only.")
            self.assertRegex(q, r'[a-zA-Z]{2,}', f"Query '{q}' should contain natural-language words.")

    def test_8_no_hardcoded_bns_section_numbers(self):
        """8. Generated queries do not contain hardcoded BNS section references such as '351(3)', '329(3)', etc."""
        ner_input = {
            "offence_types": ["criminal trespass", "criminal intimidation"],
            "raw_text": "The accused entered the shop without permission and threatened to kill Vijay if he called the police."
        }
        res = generate_queries(ner_input)
        queries = _extract_query_strings(res)

        bns_section_patterns = [
            r'351\(3\)',
            r'329\(3\)',
            r'303\(2\)',
            r'\bBNS\b',
            r'\bSection\s+\d+\b',
            r'\bsec\.?\s*\d+\b',
            r'\b\d{3}\(\d+\)\b',
            r'\b\d{3}\b',
        ]
        combined_pattern = re.compile('|'.join(bns_section_patterns), re.IGNORECASE)

        for q in queries:
            match = combined_pattern.search(q)
            self.assertIsNone(
                match,
                f"Query Generator must NOT output section numbers or BNS references. Found match '{match.group(0) if match else ''}' in query: '{q}'"
            )

    def test_9_duplicate_queries_are_removed(self):
        """9. Duplicate queries are removed."""
        ner_input = {
            "offence_types": ["criminal intimidation", "criminal intimidation"],
            "raw_text": "The accused entered the shop without permission and threatened to kill Vijay if he called the police."
        }
        res = generate_queries(ner_input)
        queries = _extract_query_strings(res)

        unique_queries = set(queries)
        self.assertEqual(
            len(queries),
            len(unique_queries),
            f"Queries list contains duplicates! Total queries: {len(queries)}, Unique queries: {len(unique_queries)}"
        )

    def test_10_one_offence_produces_multiple_distinct_queries(self):
        """10. One offence can produce more than one distinct retrieval query."""
        ner_input = {
            "offence_types": ["criminal intimidation"],
            "raw_text": "The accused entered the shop without permission and threatened to kill Vijay if he called the police."
        }
        res = generate_queries(ner_input)
        queries = _extract_query_strings(res)
        distinct_queries = set(queries)

        self.assertGreater(
            len(distinct_queries),
            1,
            f"Expected a single offence to produce > 1 distinct retrieval query, got {len(distinct_queries)} distinct queries."
        )

    def test_11_empty_offence_types_with_raw_text_generates_queries(self):
        """11. A valid raw_text with empty offence_types still generates multiple retrieval-oriented queries."""
        ner_input = {
            "victims": [],
            "accused": [],
            "persons": ["Vijay"],
            "dates": [],
            "times": [],
            "locations": [],
            "organizations": [],
            "offence_types": [],
            "raw_text": "The accused entered the shop and took a mobile phone belonging to Vijay without his permission."
        }
        res = generate_queries(ner_input)
        self.assertIsInstance(res, dict, "Output must be a dictionary.")
        self.assertIn("queries", res, "Output dictionary must contain 'queries' key.")

        queries = _extract_query_strings(res)
        self.assertGreater(
            len(queries),
            1,
            f"Expected multiple retrieval queries for valid raw_text even when offence_types is empty, got {len(queries)}"
        )

    def test_12_queries_from_raw_text_use_facts_and_are_non_empty(self):
        """12. Queries generated from raw_text use incident facts and are non-empty natural language strings."""
        ner_input = {
            "victims": [],
            "accused": [],
            "persons": ["Vijay"],
            "dates": [],
            "times": [],
            "locations": [],
            "organizations": [],
            "offence_types": [],
            "raw_text": "The accused entered the shop and took a mobile phone belonging to Vijay without his permission."
        }
        res = generate_queries(ner_input)
        queries = _extract_query_strings(res)

        for q in queries:
            self.assertIsInstance(q, str, "Query item must be a string.")
            self.assertTrue(q.strip(), "Query string must not be empty or whitespace only.")
            self.assertRegex(q, r'[a-zA-Z]{2,}', f"Query '{q}' should contain natural-language words.")

        combined_queries_text = " ".join(queries).lower()
        has_incident_facts = any(fact in combined_queries_text for fact in ["entered", "shop", "phone", "vijay", "permission", "took"])
        self.assertTrue(has_incident_facts, "Queries should incorporate key incident facts from raw_text.")

    def test_13_generator_does_not_assert_legal_offence_or_section(self):
        """13. The generator does not need to invent or assert a legal offence/section when offence_types is empty."""
        ner_input = {
            "victims": [],
            "accused": [],
            "persons": ["Vijay"],
            "dates": [],
            "times": [],
            "locations": [],
            "organizations": [],
            "offence_types": [],
            "raw_text": "The accused entered the shop and took a mobile phone belonging to Vijay without his permission."
        }
        res = generate_queries(ner_input)
        queries = _extract_query_strings(res)

        bns_section_patterns = [
            r'351\(3\)', r'329\(3\)', r'303\(2\)', r'\bBNS\b',
            r'\bSection\s+\d+\b', r'\bsec\.?\s*\d+\b', r'\b\d{3}\(\d+\)\b', r'\b\d{3}\b'
        ]
        combined_pattern = re.compile('|'.join(bns_section_patterns), re.IGNORECASE)

        for q in queries:
            match = combined_pattern.search(q)
            self.assertIsNone(
                match,
                f"Query Generator must NOT invent or assert legal section numbers when offence_types is empty. Found: '{match.group(0) if match else ''}' in query: '{q}'"
            )

    def test_14_mock_llm_valid_3_query_json(self):
        """14. Mock LLM returns valid 3-query JSON."""
        mock_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "unauthorized entry into shop and threats"},
                {"query_type": "fact_focused", "query": "accused entered shop without permission"},
                {"query_type": "legal_concept", "query": "elements of criminal trespass and intimidation"}
            ]
        })
        mock_llm = MockLLMClient([mock_response])
        ner_input = {
            "offence_types": ["criminal trespass"],
            "raw_text": "The accused entered the shop without permission."
        }
        res = generate_queries(ner_input, llm_client=mock_llm)
        self.assertEqual(len(res.get("queries", [])), 3)
        self.assertEqual(mock_llm.call_count, 1)

    def test_15_correct_json_parsing_with_markdown_blocks(self):
        """15. Correct JSON parsing when raw LLM response includes markdown code blocks."""
        raw_markdown = (
            "```json\n"
            "{\n"
            '  "queries": [\n'
            '    {"query_type": "incident_context", "query": "theft of mobile phone from shop"},\n'
            '    {"query_type": "fact_focused", "query": "taking Vijay phone without permission"},\n'
            '    {"query_type": "action_context", "query": "taking property without consent"}\n'
            "  ]\n"
            "}\n"
            "```"
        )
        mock_llm = MockLLMClient([raw_markdown])
        ner_input = {
            "persons": ["Vijay"],
            "raw_text": "The accused took a mobile phone belonging to Vijay."
        }
        res = generate_queries(ner_input, llm_client=mock_llm)
        self.assertEqual(len(res.get("queries", [])), 3)

    def test_16_query_types_validated(self):
        """16. Query with invalid query_type triggers fallback."""
        invalid_type_response = json.dumps({
            "queries": [
                {"query_type": "invalid_type", "query": "query one"},
                {"query_type": "fact_focused", "query": "query two"},
                {"query_type": "action_context", "query": "query three"}
            ]
        })
        mock_llm = MockLLMClient([invalid_type_response])
        ner_input = {"offence_types": ["theft"], "raw_text": "theft of phone"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        self.assertGreater(len(res.get("queries", [])), 0)
        q_types = [q.get("query_type") for q in res.get("queries", [])]
        self.assertNotIn("invalid_type", q_types)

    def test_17_section_number_output_rejected(self):
        """17. LLM response containing BNS section numbers is rejected and falls back."""
        section_number_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "punishable under Section 351(3) BNS"},
                {"query_type": "fact_focused", "query": "entering shop without permission"},
                {"query_type": "legal_concept", "query": "elements of criminal intimidation"}
            ]
        })
        mock_llm = MockLLMClient([section_number_response])
        ner_input = {"offence_types": ["criminal intimidation"], "raw_text": "threatened to kill"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        for q in _extract_query_strings(res):
            self.assertNotIn("351", q)

    def test_18_legal_applicability_conclusions_rejected(self):
        """18. Legal applicability conclusions (e.g. 'Section 351 applies') are rejected."""
        conclusion_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "Section 351 applies to the accused"},
                {"query_type": "fact_focused", "query": "entering shop without permission"},
                {"query_type": "legal_concept", "query": "elements of criminal intimidation"}
            ]
        })
        mock_llm = MockLLMClient([conclusion_response])
        ner_input = {"offence_types": ["criminal intimidation"], "raw_text": "threatened to kill"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        for q in _extract_query_strings(res):
            self.assertNotIn("applies", q.lower())

    def test_19_empty_query_string_rejected(self):
        """19. Empty query strings cause validation failure and trigger fallback."""
        empty_q_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": ""},
                {"query_type": "fact_focused", "query": "entering shop without permission"},
                {"query_type": "legal_concept", "query": "elements of criminal intimidation"}
            ]
        })
        mock_llm = MockLLMClient([empty_q_response])
        ner_input = {"offence_types": ["criminal intimidation"], "raw_text": "threatened to kill"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        for q in _extract_query_strings(res):
            self.assertTrue(q.strip())

    def test_20_duplicate_queries_removed(self):
        """20. Duplicate LLM queries are deduplicated."""
        dup_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "entering shop without permission"},
                {"query_type": "fact_focused", "query": "entering shop without permission"},
                {"query_type": "legal_concept", "query": "threatened to kill shopkeeper"},
                {"query_type": "action_context", "query": "unauthorized entry into shop"}
            ]
        })
        mock_llm = MockLLMClient([dup_response])
        ner_input = {"offence_types": ["criminal trespass"], "raw_text": "entering shop"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        queries = _extract_query_strings(res)
        self.assertEqual(len(queries), len(set(queries)))

    def test_21_more_than_5_queries_limited(self):
        """21. More than 5 queries returned by LLM are safely limited to 5."""
        six_queries_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "query one"},
                {"query_type": "fact_focused", "query": "query two"},
                {"query_type": "legal_concept", "query": "query three"},
                {"query_type": "action_context", "query": "query four"},
                {"query_type": "incident_context", "query": "query five"},
                {"query_type": "fact_focused", "query": "query six"}
            ]
        })
        mock_llm = MockLLMClient([six_queries_response])
        ner_input = {"raw_text": "some incident text"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        self.assertLessEqual(len(res.get("queries", [])), 5)

    def test_22_malformed_json_triggers_fallback(self):
        """22. Malformed LLM JSON output triggers deterministic fallback."""
        mock_llm = MockLLMClient(["INVALID JSON STRING NOT A DICT"])
        ner_input = {"offence_types": ["theft"], "raw_text": "took mobile phone"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        self.assertGreater(len(res.get("queries", [])), 0)

    def test_23_llm_exception_triggers_fallback(self):
        """23. LLM exception during generation triggers deterministic fallback."""
        class ExceptionLLMClient(LLMClient):
            def generate(self, prompt: str) -> str:
                raise RuntimeError("LLM connection error")

        err_llm = ExceptionLLMClient()
        ner_input = {"offence_types": ["theft"], "raw_text": "took mobile phone"}
        res = generate_queries(ner_input, llm_client=err_llm)
        self.assertGreater(len(res.get("queries", [])), 0)

    def test_24_theft_incident_empty_offence_types_with_mock_llm(self):
        """24. Theft-like incident with offence_types=[] produces useful queries via mock LLM."""
        mock_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "unauthorized taking of mobile phone from shop"},
                {"query_type": "fact_focused", "query": "took Vijay mobile phone without permission"},
                {"query_type": "action_context", "query": "entering shop and taking personal property"}
            ]
        })
        mock_llm = MockLLMClient([mock_response])
        ner_input = {
            "victims": [],
            "accused": [],
            "persons": ["Vijay"],
            "offence_types": [],
            "raw_text": "The accused entered the shop and took a mobile phone belonging to Vijay without his permission."
        }
        res = generate_queries(ner_input, llm_client=mock_llm)
        queries = _extract_query_strings(res)
        self.assertEqual(len(queries), 3)
        self.assertIn("mobile phone", " ".join(queries).lower())

    def test_25_trespass_and_intimidation_multiple_concepts(self):
        """25. Incident with trespass and intimidation produces queries covering both factual concepts."""
        mock_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "illegal entry into shop and death threats"},
                {"query_type": "fact_focused", "query": "Sunil entered Chandni Chowk shop and threatened Vijay"},
                {"query_type": "legal_concept", "query": "elements of criminal trespass and criminal intimidation"}
            ]
        })
        mock_llm = MockLLMClient([mock_response])
        ner_input = {
            "accused": ["Sunil"],
            "persons": ["Sharma", "Vijay"],
            "locations": ["Chandni Chowk"],
            "offence_types": ["criminal trespass", "criminal intimidation"],
            "raw_text": "Sub-Inspector Sharma recorded that the accused Sunil illegally entered the shop in Chandni Chowk and threatened to kill the shopkeeper Vijay if he called the police."
        }
        res = generate_queries(ner_input, llm_client=mock_llm)
        queries_text = " ".join(_extract_query_strings(res)).lower()
        self.assertTrue("entry" in queries_text or "trespass" in queries_text)
        self.assertTrue("threat" in queries_text or "intimidation" in queries_text)

    def test_26_input_ner_dict_not_mutated_with_llm(self):
        """26. Input NER dictionary is not mutated when LLM client is used."""
        mock_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "query 1"},
                {"query_type": "fact_focused", "query": "query 2"},
                {"query_type": "legal_concept", "query": "query 3"}
            ]
        })
        mock_llm = MockLLMClient([mock_response])
        original_ner = {
            "victims": ["Vijay"],
            "accused": ["Sunil"],
            "offence_types": ["criminal trespass"],
            "raw_text": "Sunil entered shop"
        }
        ner_copy = copy.deepcopy(original_ner)
        _ = generate_queries(original_ner, llm_client=mock_llm)
        self.assertEqual(original_ner, ner_copy)

    def test_27_existing_deterministic_behavior_without_llm(self):
        """27. Calling generate_queries(ner_result) without llm_client preserves deterministic behavior."""
        ner_input = {"offence_types": ["theft"], "raw_text": "took money"}
        res1 = generate_queries(ner_input)
        res2 = generate_queries(ner_input)
        self.assertEqual(res1, res2)

    def test_28_mock_llm_call_count_and_prompt_inspected(self):
        """28. MockLLMClient call count and received prompt content can be inspected."""
        mock_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "query A"},
                {"query_type": "fact_focused", "query": "query B"},
                {"query_type": "legal_concept", "query": "query C"}
            ]
        })
        mock_llm = MockLLMClient([mock_response])
        ner_input = {
            "persons": ["Vijay"],
            "offence_types": ["theft"],
            "raw_text": "The accused took Vijay phone."
        }
        _ = generate_queries(ner_input, llm_client=mock_llm)
        self.assertEqual(mock_llm.call_count, 1)
        self.assertIn("INCIDENT RAW TEXT:", mock_llm.prompts_received[0])
        self.assertIn("The accused took Vijay phone.", mock_llm.prompts_received[0])

    def test_29_all_same_query_type_rejected(self):
        """29. LLM output with 3+ queries having the exact same query_type is rejected and falls back."""
        all_same_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "query one about incident"},
                {"query_type": "incident_context", "query": "query two about incident"},
                {"query_type": "incident_context", "query": "query three about incident"}
            ]
        })
        mock_llm = MockLLMClient([all_same_response])
        ner_input = {"offence_types": ["theft"], "raw_text": "took mobile phone from shop"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        queries = res.get("queries", [])
        self.assertGreater(len(queries), 0)
        types = {q.get("query_type") for q in queries}
        self.assertGreater(len(types), 1, "Fallback queries must demonstrate query_type diversity.")

    def test_30_which_sections_inquiry_rejected(self):
        """30. Queries explicitly asking for section numbers ('which sections') are rejected and fall back."""
        inquiry_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "which sections of BNS cover entering shop without permission"},
                {"query_type": "fact_focused", "query": "what section applies to taking mobile phone"},
                {"query_type": "legal_concept", "query": "section number for criminal intimidation"}
            ]
        })
        mock_llm = MockLLMClient([inquiry_response])
        ner_input = {"offence_types": ["theft"], "raw_text": "took mobile phone"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        for q in _extract_query_strings(res):
            self.assertNotIn("which section", q.lower())
            self.assertNotIn("what section", q.lower())
            self.assertNotIn("section number", q.lower())

    def test_31_unsupported_aggravating_factors_rejected(self):
        """31. Queries introducing unsupported legal concepts ('aggravating factors') are rejected and fall back."""
        unsupported_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "theft of mobile phone with aggravating factors"},
                {"query_type": "fact_focused", "query": "unauthorized taking of property"},
                {"query_type": "legal_concept", "query": "elements of theft"}
            ]
        })
        mock_llm = MockLLMClient([unsupported_response])
        ner_input = {"offence_types": ["theft"], "raw_text": "took mobile phone"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        for q in _extract_query_strings(res):
            self.assertNotIn("aggravating factors", q.lower())

    def test_32_genuinely_diverse_valid_query_types_accepted(self):
        """32. Genuinely diverse valid query types from Mock LLM are accepted."""
        diverse_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "unauthorized entry into shop and theft"},
                {"query_type": "fact_focused", "query": "taking Vijay mobile phone without permission"},
                {"query_type": "legal_concept", "query": "elements of criminal trespass and theft"}
            ]
        })
        mock_llm = MockLLMClient([diverse_response])
        ner_input = {
            "persons": ["Vijay"],
            "offence_types": ["theft", "criminal trespass"],
            "raw_text": "entered shop and took Vijay phone"
        }
        res = generate_queries(ner_input, llm_client=mock_llm)
        queries = res.get("queries", [])
        self.assertEqual(len(queries), 3)
        types = {q.get("query_type") for q in queries}
        self.assertEqual(len(types), 3, "All 3 queries should be accepted with distinct query_types.")
        self.assertEqual(mock_llm.call_count, 1)

    def test_33_unsupported_offence_characterization_robbery_rejected(self):
        """33. Regression test: LLM query containing 'shop robbery' is rejected when incident only describes theft."""
        robbery_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "shop robbery where the accused entered a shop and took Vijay mobile phone without permission"},
                {"query_type": "fact_focused", "query": "taking another person mobile phone from a shop without consent"},
                {"query_type": "legal_concept", "query": "theft of movable property in a commercial premises"}
            ]
        })
        mock_llm = MockLLMClient([robbery_response])
        ner_input = {
            "victims": [],
            "accused": [],
            "persons": ["Vijay"],
            "offence_types": [],
            "raw_text": "The accused entered the shop and took a mobile phone belonging to Vijay without his permission."
        }
        res = generate_queries(ner_input, llm_client=mock_llm)
        queries = _extract_query_strings(res)
        for q in queries:
            self.assertNotIn("robbery", q.lower(), "Queries must not introduce ungrounded offence characterizations like 'robbery'.")

    def test_34_generic_jurisdictional_fluff_phrases_rejected(self):
        """34. LLM response containing generic jurisdictional filler ('under Indian criminal law') is rejected and falls back."""
        fluff_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "theft of mobile phone from shop under Indian criminal law"},
                {"query_type": "fact_focused", "query": "taking Vijay phone without permission"},
                {"query_type": "action_context", "query": "entering shop and taking property"}
            ]
        })
        mock_llm = MockLLMClient([fluff_response])
        ner_input = {"persons": ["Vijay"], "raw_text": "took Vijay phone from shop"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        for q in _extract_query_strings(res):
            self.assertNotIn("under indian criminal law", q.lower())

    def test_35_overly_abstract_unanchored_query_rejected(self):
        """35. Overly abstract/unanchored LLM query is rejected and triggers fallback."""
        abstract_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "possession under law"},
                {"query_type": "fact_focused", "query": "elements of legal status"},
                {"query_type": "action_context", "query": "general law provisions"}
            ]
        })
        mock_llm = MockLLMClient([abstract_response])
        ner_input = {"persons": ["Vijay"], "raw_text": "took Vijay mobile phone from shop"}
        res = generate_queries(ner_input, llm_client=mock_llm)
        for q in _extract_query_strings(res):
            self.assertNotIn("possession under law", q.lower())

    def test_36_valid_legal_concept_query_accepted(self):
        """36. Valid grounded legal-concept query ('dishonest taking of movable property without consent') is accepted."""
        concept_response = json.dumps({
            "queries": [
                {"query_type": "incident_context", "query": "taking Vijay phone from shop"},
                {"query_type": "fact_focused", "query": "unauthorized entry into shop"},
                {"query_type": "legal_concept", "query": "dishonest taking of movable property without consent"}
            ]
        })
        mock_llm = MockLLMClient([concept_response])
        ner_input = {"persons": ["Vijay"], "raw_text": "The accused entered the shop and took a mobile phone belonging to Vijay without permission."}
        res = generate_queries(ner_input, llm_client=mock_llm)
        queries = _extract_query_strings(res)
        self.assertEqual(len(queries), 3)
        self.assertIn("dishonest taking of movable property without consent", queries)

    def test_37_prompt_contains_grounding_and_no_fluff_instructions(self):
        """37. System prompt explicitly contains new grounding and no-fluff instructions."""
        from query_generator import construct_query_generator_prompt
        ner_input = {"offence_types": ["theft"], "raw_text": "took mobile phone"}
        prompt = construct_query_generator_prompt(ner_input)
        self.assertIn("under Indian criminal law", prompt)
        self.assertIn("grounded in the incident's explicit facts", prompt)
        self.assertIn("dishonest taking of movable property without consent", prompt)


if __name__ == "__main__":
    unittest.main()
