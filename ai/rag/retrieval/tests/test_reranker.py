"""test_reranker.py — Unit tests for semantic RRF legal candidate reranker.

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

from ai.rag.retrieval.reranker import rerank_candidates


class TestReranker(unittest.TestCase):

    def setUp(self):
        # Sample mock candidates resembling real BNS corpus entries
        self.cand_303 = {
            "id": "bns_303_303(2)-2",
            "section": "303",
            "clause": "303(2)",
            "title": "Theft.",
            "distance": 0.30,
            "rank": 1,
            "text": "303. Theft.—(1) Whoever, intending to take dishonestly any movable property..."
        }
        self.cand_115 = {
            "id": "bns_115",
            "section": "115",
            "clause": "115(2)",
            "title": "Voluntarily causing hurt.",
            "distance": 0.40,
            "rank": 2,
            "text": "115. Voluntarily causing hurt.—Whoever does any act with the intention..."
        }
        self.cand_304 = {
            "id": "bns_304",
            "section": "304",
            "clause": "304(1)",
            "title": "Snatching.",
            "distance": 0.60,
            "rank": 5,
            "text": "304. Snatching.—Theft is snatching if..."
        }

    def test_1_rerank_sorts_candidates_by_semantic_rrf_score(self):
        """1. Reranker sorts candidates by vector similarity and RRF score."""
        incident = "Sample incident text"
        candidates = [self.cand_304, self.cand_303, self.cand_115]

        reranked = rerank_candidates(incident, candidates)
        self.assertEqual(len(reranked), 3)

        # Cand 303 has smallest distance (0.30) and best rank (1), so it should rank first
        self.assertEqual(reranked[0]["id"], self.cand_303["id"])
        self.assertGreaterEqual(reranked[0]["rerank_score"], reranked[1]["rerank_score"])
        self.assertGreaterEqual(reranked[1]["rerank_score"], reranked[2]["rerank_score"])

    def test_2_multiquery_occurrences_boost_rrf_score(self):
        """2. Candidates appearing across multiple retrieval queries get higher RRF score."""
        incident = "Sample incident text"

        # Cand 303 appears twice (simulating multi-query retrieval)
        candidates = [self.cand_304, self.cand_303, self.cand_115, self.cand_303]

        reranked = rerank_candidates(incident, candidates)

        # Cand 303 merged and scored higher due to multiple occurrences
        top_doc = reranked[0]
        self.assertEqual(top_doc["id"], self.cand_303["id"])
        self.assertIn("across 2 retrieval query occurrence(s)", top_doc["scoring_reasons"][1])

    def test_3_preserves_original_candidate_fields(self):
        """3. Candidate data structure fields are preserved after reranking."""
        incident = "Sample incident text"
        candidates = [self.cand_303]

        reranked = rerank_candidates(incident, candidates)
        res = reranked[0]
        self.assertEqual(res["id"], self.cand_303["id"])
        self.assertEqual(res["section"], self.cand_303["section"])
        self.assertEqual(res["clause"], self.cand_303["clause"])
        self.assertEqual(res["title"], self.cand_303["title"])
        self.assertEqual(res["text"], self.cand_303["text"])
        self.assertIn("rerank_score", res)
        self.assertIn("scoring_reasons", res)

    def test_4_empty_candidates_handled_safely(self):
        """4. Empty candidates list handled safely."""
        self.assertEqual(rerank_candidates("incident", []), [])

    def test_5_malformed_candidates_handled_safely(self):
        """5. Malformed candidates in input list are skipped safely."""
        malformed = ["not a dict", None, {}, {"id": "bns_303", "distance": 0.3, "rank": 1}]
        res = rerank_candidates("incident", malformed)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], "bns_303")

    def test_6_no_section_number_or_keyword_mapping_tables(self):
        """6. Implementation contains zero section-number or offence keyword mapping tables."""
        import ai.rag.retrieval.reranker as reranker_mod
        source_code = inspect.getsource(reranker_mod)

        forbidden_patterns = [
            r'[\'"]303[\'"]\s*:', r'[\'"]306[\'"]\s*:', r'[\'"]134[\'"]\s*:',
            r'has_assault_force', r'has_taking_without_consent', r'requires_clerk_servant',
            r'\+0\.45', r'\-0\.30', r'\+0\.35'
        ]
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, source_code)
            self.assertEqual(len(matches), 0, f"Found forbidden rule pattern: {pattern}")


if __name__ == "__main__":
    unittest.main()



if __name__ == "__main__":
    unittest.main()
