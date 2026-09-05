"""test_context_builder.py — Unit tests for Legal Context Builder.

Located at: ai/rag/analysis/tests/test_context_builder.py
"""

import copy
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

from context_builder import build_legal_context


class TestContextBuilder(unittest.TestCase):

    def test_1_single_offence_context(self):
        """Test 1: Single offence context construction."""
        ner_res = {
            "victims": [],
            "accused": ["Sunil"],
            "persons": ["Sharma"],
            "dates": [],
            "times": [],
            "locations": ["Chandni Chowk"],
            "organizations": [],
            "offence_types": ["criminal trespass"],
            "raw_text": "Sunil entered the shop."
        }
        ret_res = {
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
                            "title": "Criminal trespass",
                            "distance": 0.22,
                            "text": "Trespass definition..."
                        }
                    ]
                }
            ]
        }

        ctx = build_legal_context(ner_res, ret_res)

        self.assertEqual(ctx["incident"]["raw_text"], "Sunil entered the shop.")
        self.assertEqual(ctx["incident"]["accused"], ["Sunil"])
        self.assertEqual(len(ctx["legal_context"]), 1)
        self.assertEqual(ctx["legal_context"][0]["offence_type"], "criminal trespass")
        self.assertEqual(len(ctx["legal_context"][0]["results"]), 1)
        self.assertEqual(ctx["legal_context"][0]["results"][0]["id"], "bns_329_329(1)")
        self.assertEqual(ctx["legal_context"][0]["results"][0]["section"], "329")

    def test_2_multiple_offence_context(self):
        """Test 2: Multiple offence context construction."""
        ner_res = {
            "victims": [],
            "accused": ["Sunil"],
            "persons": ["Vijay"],
            "dates": [],
            "times": [],
            "locations": [],
            "organizations": [],
            "offence_types": ["criminal trespass", "criminal intimidation"],
            "raw_text": "Sunil entered shop and threatened Vijay."
        }
        ret_res = {
            "queries": [
                {"offence_type": "criminal trespass", "query": "criminal trespass"},
                {"offence_type": "criminal intimidation", "query": "criminal intimidation"}
            ],
            "results": [
                {
                    "offence_type": "criminal trespass",
                    "query": "criminal trespass",
                    "retrieved": [{"rank": 1, "id": "bns_329", "section": 329, "clause": None, "title": "Trespass", "distance": 0.2, "text": "Text 1"}]
                },
                {
                    "offence_type": "criminal intimidation",
                    "query": "criminal intimidation",
                    "retrieved": [{"rank": 1, "id": "bns_351", "section": 351, "clause": None, "title": "Intimidation", "distance": 0.3, "text": "Text 2"}]
                }
            ]
        }

        ctx = build_legal_context(ner_res, ret_res)

        self.assertEqual(len(ctx["legal_context"]), 2)
        self.assertEqual(ctx["legal_context"][0]["offence_type"], "criminal trespass")
        self.assertEqual(ctx["legal_context"][0]["results"][0]["id"], "bns_329")
        self.assertEqual(ctx["legal_context"][1]["offence_type"], "criminal intimidation")
        self.assertEqual(ctx["legal_context"][1]["results"][0]["id"], "bns_351")

    def test_3_zero_retrieval_results(self):
        """Test 3: Zero retrieval results handling."""
        ner_res = {"offence_types": [], "raw_text": "Nothing happened."}
        ret_res = {"queries": [], "results": []}

        ctx = build_legal_context(ner_res, ret_res)

        self.assertEqual(ctx["incident"]["raw_text"], "Nothing happened.")
        self.assertEqual(ctx["legal_context"], [])

    def test_4_missing_ner_fields(self):
        """Test 4: Missing NER fields gracefully populated with defaults."""
        ner_res = {}
        ret_res = {}

        ctx = build_legal_context(ner_res, ret_res)

        self.assertEqual(ctx["incident"]["raw_text"], "")
        self.assertEqual(ctx["incident"]["victims"], [])
        self.assertEqual(ctx["incident"]["accused"], [])
        self.assertEqual(ctx["legal_context"], [])

    def test_5_group_preservation(self):
        """Test 5: Offence retrieval groups remain distinct."""
        ner_res = {"offence_types": ["theft"]}
        ret_res = {
            "results": [
                {
                    "offence_type": "theft",
                    "query": "theft",
                    "retrieved": [
                        {"rank": 1, "id": "bns_304", "section": 304, "clause": None, "title": "Snatching", "distance": 0.28, "text": "Snatching text"},
                        {"rank": 2, "id": "bns_303", "section": 303, "clause": "303(1)", "title": "Theft", "distance": 0.30, "text": "Theft text"}
                    ]
                }
            ]
        }

        ctx = build_legal_context(ner_res, ret_res)

        docs = ctx["legal_context"][0]["results"]
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0]["rank"], 1)
        self.assertEqual(docs[0]["id"], "bns_304")
        self.assertEqual(docs[1]["rank"], 2)
        self.assertEqual(docs[1]["id"], "bns_303")

    def test_6_input_dictionaries_not_mutated(self):
        """Test 6: Input NER and Retrieval dictionaries are not mutated."""
        ner_res = {"offence_types": ["theft"], "raw_text": "Sample"}
        ret_res = {"results": [{"offence_type": "theft", "retrieved": []}]}

        ner_copy = copy.deepcopy(ner_res)
        ret_copy = copy.deepcopy(ret_res)

        _ = build_legal_context(ner_res, ret_res)

        self.assertEqual(ner_res, ner_copy, "build_legal_context mutated ner_result!")
        self.assertEqual(ret_res, ret_copy, "build_legal_context mutated retrieval_result!")


if __name__ == "__main__":
    unittest.main()
