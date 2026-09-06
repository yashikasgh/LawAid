"""test_reranker.py — Unit tests for deterministic legal candidate reranker.

Located at: ai/rag/retrieval/tests/test_reranker.py
"""

import unittest
import inspect
import re
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.rag.retrieval.reranker import rerank_candidates, _extract_incident_facts, _analyze_candidate_requirements


class TestReranker(unittest.TestCase):

    def setUp(self):
        # Sample mock candidates resembling real BNS corpus entries
        self.cand_303_gen = {
            "id": "bns_303_303(2)-2",
            "section": "303",
            "clause": "303(2)",
            "title": "Theft.",
            "distance": 0.60,
            "rank": 8,
            "text": "303. Theft.—(1) Whoever, intending to take dishonestly any movable property out of the possession of any person without that person's consent, moves that property in order to such taking, is said to commit theft."
        }
        self.cand_306_clerk = {
            "id": "bns_306",
            "section": "306",
            "clause": "",
            "title": "Theft by clerk or servant of property in possession of master.",
            "distance": 0.45,
            "rank": 2,
            "text": "306. Theft by clerk or servant of property in possession of master.—Whoever, being a clerk or servant, or being employed in the capacity of a clerk or servant, commits theft in respect of any property in the possession of his master or employer..."
        }
        self.cand_134_assault = {
            "id": "bns_134",
            "section": "134",
            "clause": "",
            "title": "Assault or criminal force in attempt to commit theft of property carried by a person.",
            "distance": 0.50,
            "rank": 3,
            "text": "134. Assault or criminal force in attempt to commit theft of property carried by a person.—Whoever uses assault or criminal force to any person, in attempting to commit theft on any property which that person is wearing or carrying..."
        }
        self.cand_307_prep = {
            "id": "bns_307",
            "section": "307",
            "clause": "",
            "title": "Theft after preparation made for causing death, hurt or restraint in order to committing of theft.",
            "distance": 0.55,
            "rank": 5,
            "text": "307. Theft after preparation made for causing death, hurt or restraint in order to committing of theft.—Whoever commits theft, having made preparation for causing death, or hurt, or restraint..."
        }
        self.cand_323_conceal = {
            "id": "bns_323",
            "section": "323",
            "clause": "",
            "title": "Dishonest or fraudulent removal or concealment of property.",
            "distance": 0.52,
            "rank": 4,
            "text": "323. Dishonest or fraudulent removal or concealment of property.—Whoever dishonestly or fraudulently conceals or removes any property of himself or any other person..."
        }
        self.cand_188_mint = {
            "id": "bns_188",
            "section": "188",
            "clause": "",
            "title": "Unlawfully taking coining instrument from mint.",
            "distance": 0.58,
            "rank": 7,
            "text": "188. Unlawfully taking coining instrument from mint.—Whoever, without lawful authority, takes out of any mint, lawfully established in India, any coining tool or instrument..."
        }

    def test_1_simple_theft_incident_ranks_section_303_highest(self):
        """1. Theft incident ranks Section 303 above Sections 306, 134, 307, 323, and 188."""
        incident = "The accused entered the shop and took a mobile phone belonging to Vijay without his permission."
        candidates = [
            self.cand_306_clerk,
            self.cand_134_assault,
            self.cand_323_conceal,
            self.cand_307_prep,
            self.cand_188_mint,
            self.cand_303_gen
        ]

        reranked = rerank_candidates(incident, candidates)
        self.assertGreater(len(reranked), 0)
        top_cand = reranked[0]
        self.assertEqual(top_cand["section"], "303")
        self.assertEqual(top_cand["id"], "bns_303_303(2)-2")

    def test_2_clerk_servant_incident_increases_section_306_relevance(self):
        """2. A clerk/servant theft incident increases Section 306 relevance."""
        incident = "The accused, working as a clerk in the shop, stole money from his master."
        candidates = [self.cand_303_gen, self.cand_306_clerk]

        reranked = rerank_candidates(incident, candidates)
        self.assertEqual(reranked[0]["section"], "306")

    def test_3_assault_incident_increases_section_134_relevance(self):
        """3. An assault/force theft incident increases Section 134 relevance."""
        incident = "The accused assaulted Vijay and used criminal force to take a wallet he was carrying."
        candidates = [self.cand_303_gen, self.cand_134_assault]

        reranked = rerank_candidates(incident, candidates)
        self.assertEqual(reranked[0]["section"], "134")

    def test_4_preparation_incident_increases_section_307_relevance(self):
        """4. A theft incident involving preparation for hurt/death/restraint increases Section 307 relevance."""
        incident = "The accused made preparation armed with a weapon to hurt anyone before committing theft."
        candidates = [self.cand_303_gen, self.cand_307_prep]

        reranked = rerank_candidates(incident, candidates)
        self.assertEqual(reranked[0]["section"], "307")

    def test_5_mint_incident_increases_section_188_relevance(self):
        """5. A mint/coining-instrument incident increases Section 188 relevance."""
        incident = "The accused unlawfully took a coining instrument out of the mint."
        candidates = [self.cand_303_gen, self.cand_188_mint]

        reranked = rerank_candidates(incident, candidates)
        self.assertEqual(reranked[0]["section"], "188")

    def test_6_missing_specialized_elements_penalizes_candidates(self):
        """6. Missing specialized elements cause the corresponding candidate to be penalized."""
        incident = "The accused took a watch from the counter without consent."
        candidates = [self.cand_306_clerk, self.cand_188_mint]

        reranked = rerank_candidates(incident, candidates)
        for cand in reranked:
            reasons_text = " ".join(cand["scoring_reasons"])
            self.assertIn("absent in incident", reasons_text)

    def test_7_original_retrieval_data_remains_unchanged(self):
        """7. Original retrieval data remains unchanged."""
        incident = "The accused took a mobile phone without permission."
        candidates = [self.cand_303_gen]

        reranked = rerank_candidates(incident, candidates)
        res = reranked[0]
        self.assertEqual(res["id"], self.cand_303_gen["id"])
        self.assertEqual(res["rank"], self.cand_303_gen["rank"])
        self.assertEqual(res["distance"], self.cand_303_gen["distance"])
        self.assertEqual(res["section"], self.cand_303_gen["section"])
        self.assertEqual(res["clause"], self.cand_303_gen["clause"])
        self.assertEqual(res["title"], self.cand_303_gen["title"])
        self.assertEqual(res["text"], self.cand_303_gen["text"])
        self.assertIn("rerank_score", res)
        self.assertIn("scoring_reasons", res)

    def test_8_empty_candidates_handled_safely(self):
        """8. Empty candidates are handled safely."""
        self.assertEqual(rerank_candidates("any incident", []), [])

    def test_9_malformed_candidates_handled_safely(self):
        """9. Malformed candidates are handled safely."""
        malformed_list = [
            "not a dict",
            None,
            {},
            {"title": "Valid title", "text": "Valid text"}
        ]
        res = rerank_candidates("incident text", malformed_list)
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 2)  # {} and valid dict are processed safely

    def test_10_no_section_number_mapping_table_exists(self):
        """10. No section-number mapping table exists in the implementation."""
        import ai.rag.retrieval.reranker as reranker_mod
        source_code = inspect.getsource(reranker_mod)

        # Confirm source does not map section numbers like "303": "theft" or 306: "clerk"
        forbidden_patterns = [
            r'[\'"]303[\'"]\s*:', r'[\'"]306[\'"]\s*:', r'[\'"]134[\'"]\s*:',
            r'[\'"]307[\'"]\s*:', r'[\'"]188[\'"]\s*:', r'[\'"]323[\'"]\s*:',
            r'303\s*:\s*[\'"]', r'306\s*:\s*[\'"]', r'134\s*:\s*[\'"]',
        ]
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, source_code)
            self.assertEqual(len(matches), 0, f"Found forbidden section mapping pattern: {pattern}")

    def test_11_distinctive_circumstances_mismatch_receives_penalty(self):
        """11. Candidates requiring distinctive circumstances absent from incident receive penalty."""
        incident = "The accused entered the shop and took a mobile phone belonging to Vijay without his permission."

        cand_dwelling = {
            "id": "bns_305",
            "section": "305",
            "title": "Theft in a dwelling house, or means of transportation or place of worship, etc.",
            "distance": 0.40,
            "text": "Whoever commits theft in any building, tent or vessel, which building, tent or vessel is used as a human dwelling, or used for the custody of property..."
        }
        cand_gift_recovery = {
            "id": "bns_252",
            "section": "252",
            "title": "Taking gift to help to recover stolen property, etc.",
            "distance": 0.40,
            "text": "Whoever takes any gratification or gift under pretence or on account of helping any person to recover any stolen property..."
        }
        cand_property_mark = {
            "id": "bns_348",
            "section": "348",
            "title": "Making or possession of any instrument for counterfeiting a property mark.",
            "distance": 0.40,
            "text": "Whoever makes or has in his possession any die, plate or other instrument for the purpose of counterfeiting a property mark..."
        }

        candidates = [self.cand_303_gen, cand_dwelling, cand_gift_recovery, cand_property_mark]
        reranked = rerank_candidates(incident, candidates)

        # Section 303 should be rank 1
        self.assertEqual(reranked[0]["id"], self.cand_303_gen["id"])

        # Confirm all mismatch candidates received penalty explanations
        for c in reranked[1:]:
            reasons_text = " ".join(c["scoring_reasons"])
            self.assertIn("absent in incident", reasons_text)
            self.assertLess(c["rerank_score"], reranked[0]["rerank_score"])


if __name__ == "__main__":
    unittest.main()
