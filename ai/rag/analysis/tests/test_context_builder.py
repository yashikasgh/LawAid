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

    def test_7_candidate_focused_fields(self):
        """Test 7: Candidate-focused target_clause_text and schedule_1 fields are properly extracted."""
        ner_res = {"offence_types": ["criminal intimidation"], "raw_text": "Threatened to kill."}
        sample_text = (
            "Bharatiya Nyaya Sanhita (BNS), 2023\n\n"
            "Section: 351 (Clause 351(3))\n"
            "Title: Criminal intimidation.\n\n"
            "Legal Text:\n"
            "351. Criminal intimidation.—(1) Whoever threatens another by any means...\n"
            "(2) Whoever commits the offence...\n"
            "(3) Whoever commits the offence of criminal intimidation by threatening to cause death...\n\n"
            "Schedule I Classification\n\n"
            "Offence:\n"
            "If threat be to cause death or grievous hurt, etc.\n\n"
            "Punishment:\n"
            "Imprisonment for 7 years, or fine, or both.\n\n"
            "Cognizable:\n"
            "Non-cognizable\n\n"
            "Bailable:\n"
            "Bailable\n\n"
            "Court:\n"
            "Magistrate of the first class."
        )
        ret_res = {
            "results": [
                {
                    "offence_type": "criminal intimidation",
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_351_351(3)",
                            "section": 351,
                            "clause": "351(3)",
                            "title": "Criminal intimidation.",
                            "distance": 0.25,
                            "text": sample_text
                        }
                    ]
                }
            ]
        }

        ctx = build_legal_context(ner_res, ret_res)
        doc = ctx["legal_context"][0]["results"][0]

        self.assertIn("target_clause_text", doc)
        self.assertIn("section_definition", doc)
        self.assertIn("schedule_1", doc)
        self.assertIn("threatening to cause death", doc["target_clause_text"])
        self.assertEqual(doc["schedule_1"]["punishment"], "Imprisonment for 7 years, or fine, or both.")
        self.assertEqual(doc["schedule_1"]["cognizable"], "Non-cognizable")

    def test_8_reranked_candidates_integration_preserves_invariants(self):
        """Test 8: Reranked candidates list preserves document_id, section, clause, target_clause_text and Schedule I invariants."""
        ner_res = {
            "offence_types": [],
            "persons": ["Vijay"],
            "raw_text": "The accused entered the shop and took a mobile phone belonging to Vijay without his permission."
        }
        reranked_candidates = [
            {
                "id": "bns_303_303(2)-2",
                "document_id": "bns_303_303(2)-2",
                "section": "303",
                "clause": "303(2)",
                "title": "Theft.",
                "distance": 0.4040,
                "rank": 9,
                "rerank_score": 1.1480,
                "scoring_reasons": ["Base vector similarity score: 0.7980", "Matches core elements (+0.35)"],
                "text": (
                    "Bharatiya Nyaya Sanhita (BNS), 2023\n\n"
                    "Section: 303\nTitle: Theft.\n\nLegal Text:\n303. Theft.—(1) Whoever, intending to take dishonestly...\n"
                    "(2) Whoever commits theft shall be punished...\n\n"
                    "Schedule I Classification\n\nOffence:\nTheft.\n\nPunishment:\nImprisonment for 3 years, or fine, or both.\n\n"
                    "Cognizable:\nCognizable.\n\nBailable:\nNon-bailable.\n\nCourt:\nAny Magistrate."
                )
            }
        ]

        ctx = build_legal_context(ner_res, reranked_candidates)

        self.assertIn("legal_context", ctx)
        self.assertEqual(len(ctx["legal_context"]), 1)
        doc = ctx["legal_context"][0]["results"][0]

        # Verify invariants
        self.assertEqual(doc["document_id"], "bns_303_303(2)-2")
        self.assertEqual(doc["id"], "bns_303_303(2)-2")
        self.assertEqual(doc["section"], "303")
        self.assertEqual(doc["clause"], "303(2)")
        self.assertIn("Whoever commits theft shall be punished", doc["target_clause_text"])
        self.assertEqual(doc["schedule_1"]["offence"], "Theft.")
        self.assertEqual(doc["schedule_1"]["punishment"], "Imprisonment for 3 years, or fine, or both.")
        self.assertEqual(doc["schedule_1"]["cognizable"], "Cognizable.")
        self.assertEqual(doc["schedule_1"]["bailable"], "Non-bailable.")
        self.assertEqual(doc["schedule_1"]["court"], "Any Magistrate.")
        self.assertEqual(doc["rerank_score"], 1.1480)
        self.assertIn("scoring_reasons", doc)


if __name__ == "__main__":
    unittest.main()
