"""test_build_retrieval_query.py — Unit test suite for NER -> Baseline Retrieval Integration.

Located at: ai/rag/retrieval/tests/test_build_retrieval_query.py
"""

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add project root (LawAid) to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add retrieval directory to sys.path
RETRIEVAL_DIR = Path(__file__).resolve().parent.parent
if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_DIR))

from build_retrieval_query import build_retrieval_queries, retrieve_by_ner


class TestBuildRetrievalQuery(unittest.TestCase):

    def test_1_single_offence_query_generation(self):
        """Test 1: Single offence query generation."""
        ner_input = {"offence_types": ["theft"]}
        res = build_retrieval_queries(ner_input)

        expected = {
            "queries": [
                {
                    "offence_type": "theft",
                    "query": "theft"
                }
            ]
        }
        self.assertEqual(res, expected)

    def test_2_multiple_offence_query_generation(self):
        """Test 2: Multiple offence query generation."""
        ner_input = {"offence_types": ["criminal trespass", "criminal intimidation"]}
        res = build_retrieval_queries(ner_input)

        expected = {
            "queries": [
                {
                    "offence_type": "criminal trespass",
                    "query": "criminal trespass"
                },
                {
                    "offence_type": "criminal intimidation",
                    "query": "criminal intimidation"
                }
            ]
        }
        self.assertEqual(res, expected)

    def test_3_zero_offences(self):
        """Test 3: Zero offences handling."""
        ner_input_empty = {"offence_types": []}
        res_empty = build_retrieval_queries(ner_input_empty)
        self.assertEqual(res_empty, {"queries": []})

        ner_input_none = {}
        res_none = build_retrieval_queries(ner_input_none)
        self.assertEqual(res_none, {"queries": []})

    def test_4_controlled_vocabulary_preservation(self):
        """Test 4: Exact controlled-vocabulary preservation."""
        controlled_terms = ["assault", "theft", "criminal trespass", "murder", "cheating", "criminal intimidation"]
        ner_input = {"offence_types": controlled_terms}
        res = build_retrieval_queries(ner_input)

        extracted_terms = [q["query"] for q in res["queries"]]
        self.assertEqual(extracted_terms, controlled_terms)

    @patch("build_retrieval_query.retrieve")
    def test_5_direct_retrieve_call_mocked(self, mock_retrieve):
        """Test 5: Direct use of existing retrieve() function (mocked)."""
        mock_results = [
            {"rank": 1, "id": "bns_303", "section": 303, "clause": None, "distance": 0.25, "title": "Theft"}
        ]
        mock_retrieve.return_value = mock_results

        ner_input = {"offence_types": ["theft"]}
        res = retrieve_by_ner(ner_input, top_k=5)

        mock_retrieve.assert_called_once_with(query="theft", top_k=5)
        self.assertEqual(len(res["results"]), 1)
        self.assertEqual(res["results"][0]["offence_type"], "theft")
        self.assertEqual(res["results"][0]["retrieved"], mock_results)

    def test_6_input_ner_dict_not_mutated(self):
        """Test 6: Input NER dictionary is not mutated."""
        original_ner = {
            "victims": ["Ramesh"],
            "accused": ["Amit"],
            "persons": [],
            "dates": ["15th August"],
            "times": [],
            "locations": ["Rohini"],
            "organizations": [],
            "offence_types": ["theft"],
            "raw_text": "Sample text"
        }
        ner_copy = copy.deepcopy(original_ner)

        _ = build_retrieval_queries(original_ner)
        self.assertEqual(original_ner, ner_copy, "build_retrieval_queries mutated the input dictionary!")

    @patch("build_retrieval_query.retrieve")
    def test_7_results_grouped_per_offence(self, mock_retrieve):
        """Test 7: Results remain correctly grouped when multiple offences are present."""
        def mock_retrieve_side_effect(query, top_k):
            if query == "criminal trespass":
                return [{"rank": 1, "id": "bns_329", "section": 329, "clause": "329(1)", "distance": 0.2, "title": "Trespass"}]
            elif query == "criminal intimidation":
                return [{"rank": 1, "id": "bns_351", "section": 351, "clause": "351(1)", "distance": 0.3, "title": "Intimidation"}]
            return []

        mock_retrieve.side_effect = mock_retrieve_side_effect

        ner_input = {"offence_types": ["criminal trespass", "criminal intimidation"]}
        res = retrieve_by_ner(ner_input, top_k=5)

        self.assertEqual(len(res["results"]), 2)
        self.assertEqual(res["results"][0]["offence_type"], "criminal trespass")
        self.assertEqual(res["results"][0]["retrieved"][0]["id"], "bns_329")

        self.assertEqual(res["results"][1]["offence_type"], "criminal intimidation")
        self.assertEqual(res["results"][1]["retrieved"][0]["id"], "bns_351")


if __name__ == "__main__":
    unittest.main()
