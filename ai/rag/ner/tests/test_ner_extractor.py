"""test_ner_extractor.py — Comprehensive unit tests and manual realistic examples for hybrid NER system.

Located at: ai/rag/ner/tests/test_ner_extractor.py
"""

import sys
from pathlib import Path

# Add project root (LawAid) to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import unittest
import spacy
from ai.rag.ner.ner_extractor import extract_entities, _NLP, CONTROLLED_OFFENCES


class TestNERExtractor(unittest.TestCase):

    def test_1_simple_assault_incident(self):
        """Test: Simple assault incident with victim, accused, and location."""
        text = "On Friday in Connaught Place, victim Rahul was assaulted by Amit."
        res = extract_entities(text)
        
        self.assertIn("Rahul", res["victims"], f"Expected Rahul in victims: {res}")
        self.assertIn("Amit", res["accused"], f"Expected Amit in accused: {res}")
        self.assertTrue(any("Connaught Place" in loc for loc in res["locations"]), f"Expected Connaught Place in locations: {res}")
        self.assertIn("assault", res["offence_types"], f"Expected assault in offence_types: {res}")

    def test_2_theft_incident(self):
        """Test: Theft incident with date and location."""
        text = "On 15th August 2026, a wallet was stolen at Rohini."
        res = extract_entities(text)

        self.assertIn("15th August 2026", res["dates"], f"Expected 15th August 2026 in dates: {res}")
        self.assertTrue(any("Rohini" in loc for loc in res["locations"]), f"Expected Rohini in locations: {res}")
        self.assertIn("theft", res["offence_types"], f"Expected theft in offence_types: {res}")

    def test_3_multiple_accused(self):
        """Test: Multiple accused persons."""
        text = "The victim Suresh Kumar was attacked by Amit and accused Rajesh."
        res = extract_entities(text)

        self.assertIn("Suresh Kumar", res["victims"], f"Expected Suresh Kumar in victims: {res}")
        self.assertTrue(any("Amit" in a for a in res["accused"]), f"Expected Amit in accused: {res}")
        self.assertTrue(any("Rajesh" in a for a in res["accused"]), f"Expected Rajesh in accused: {res}")

    def test_4_multiple_victims(self):
        """Test: Multiple victims."""
        text = "The victim Rahul and victim Priya were threatened by accused Vikram."
        res = extract_entities(text)

        self.assertTrue(any("Rahul" in v for v in res["victims"]), f"Expected Rahul in victims: {res}")
        self.assertTrue(any("Priya" in v for v in res["victims"]), f"Expected Priya in victims: {res}")
        self.assertTrue(any("Vikram" in a for a in res["accused"]), f"Expected Vikram in accused: {res}")
        self.assertIn("criminal intimidation", res["offence_types"], f"Expected criminal intimidation in offence_types: {res}")

    def test_5_missing_entities(self):
        """Test: Missing entities."""
        text = "Something happened somewhere yesterday."
        res = extract_entities(text)

        self.assertEqual(res["victims"], [])
        self.assertEqual(res["accused"], [])
        self.assertEqual(res["offence_types"], [])

    def test_6_ambiguous_sentence_no_guessing(self):
        """Test: Ambiguous sentence containing PERSON entities where roles cannot safely be determined."""
        text = "Ramesh and Suresh met at the cafe."
        res = extract_entities(text)

        self.assertEqual(res["victims"], [], "Should not guess victims for ambiguous sentence")
        self.assertEqual(res["accused"], [], "Should not guess accused for ambiguous sentence")
        self.assertTrue(any("Ramesh" in p for p in res["persons"]) or any("Suresh" in p for p in res["persons"]),
                        f"Expected Ramesh/Suresh in persons: {res}")

    def test_7_entity_ruler_ordering_precedence(self):
        """Test: EntityRuler ordering — explicitly assert that pattern match is labeled ACCUSED (failing if labeled only generic PERSON)."""
        text = "Amit assaulted Rahul."
        doc = _NLP(text)

        labels = [ent.label_ for ent in doc.ents]
        self.assertIn("ACCUSED", labels, f"EntityRuler failed to label entity as ACCUSED! Found labels: {labels}")
        
        accused_ents = [ent.text for ent in doc.ents if ent.label_ == "ACCUSED"]
        self.assertTrue(any("Amit" in e for e in accused_ents),
                        f"Expected 'Amit' to be labeled ACCUSED by EntityRuler before statistical NER! Found ents: {[(ent.text, ent.label_) for ent in doc.ents]}")

    def test_8_controlled_offence_vocabulary_mapping(self):
        """Test: Controlled offence vocabulary — verify verbs map to controlled categories."""
        text = "He punched and beat the victim."
        res = extract_entities(text)

        self.assertIn("assault", res["offence_types"], f"Expected 'punched and beat' to map to controlled category 'assault': {res}")
        self.assertNotIn("punched", res["offence_types"], "Arbitrary verb 'punched' must not appear in offence_types")
        self.assertNotIn("beat", res["offence_types"], "Arbitrary verb 'beat' must not appear in offence_types")

    # --- SPECIFIC REGRESSION TESTS FOR LOCATION / PERSON SEPARATION ---

    def test_regression_1_multi_word_location_person_separation(self):
        """Regression Test 1: Multi-word location/person separation."""
        text = "Ramesh was walking near Patel Nagar."
        res = extract_entities(text)

        self.assertIn("Ramesh", res["persons"], f"Expected Ramesh in persons: {res}")
        self.assertIn("Patel Nagar", res["locations"], f"Expected Patel Nagar in locations: {res}")
        self.assertNotIn("Patel Nagar", res["persons"], f"Patel Nagar must NOT be in persons: {res}")
        self.assertNotIn("Patel", res["persons"], f"Patel must NOT be in persons: {res}")

    def test_regression_2_multi_word_person_name(self):
        """Regression Test 2: Multi-word person name."""
        text = "The victim Suresh Kumar was attacked near Patel Nagar."
        res = extract_entities(text)

        self.assertIn("Suresh Kumar", res["victims"], f"Expected Suresh Kumar in victims: {res}")
        self.assertIn("Patel Nagar", res["locations"], f"Expected Patel Nagar in locations: {res}")
        self.assertNotIn("Suresh", res["persons"], f"Suresh must NOT be separately in persons: {res}")
        self.assertNotIn("Kumar", res["persons"], f"Kumar must NOT be separately in persons: {res}")
        self.assertNotIn("Patel", res["persons"], f"Patel must NOT be separately in persons: {res}")

    def test_regression_3_existing_role_extraction(self):
        """Regression Test 3: Existing ACCUSED and VICTIM patterns still work exactly as before."""
        text = "victim Rahul was attacked by accused Sunil."
        res = extract_entities(text)

        self.assertIn("Rahul", res["victims"], f"Expected Rahul in victims: {res}")
        self.assertIn("Sunil", res["accused"], f"Expected Sunil in accused: {res}")

    def test_regression_4_existing_controlled_offence_vocabulary(self):
        """Regression Test 4: Existing offence mappings are unchanged."""
        text = "A fraud and theft incident occurred."
        res = extract_entities(text)

        self.assertIn("cheating", res["offence_types"], f"Expected cheating for fraud: {res}")
        self.assertIn("theft", res["offence_types"], f"Expected theft for theft: {res}")

    def test_regression_5_criminal_trespass_illegally_entered(self):
        """Regression Test 5: 'illegally entered' produces criminal trespass."""
        text = "The accused illegally entered the shop and threatened the owner."
        res = extract_entities(text)

        self.assertIn("criminal trespass", res["offence_types"], f"Expected criminal trespass in offence_types: {res}")
        self.assertIn("criminal intimidation", res["offence_types"], f"Expected criminal intimidation in offence_types: {res}")


def run_manual_realistic_examples():
    """Run 3 realistic manual incident examples."""
    print("\n" + "=" * 90)
    print("MANUAL REALISTIC INCIDENT EXAMPLES")
    print("=" * 90)

    examples = [
        ("Example 1 (Snatching / Theft Incident)",
         "Yesterday evening around 8 PM near Karol Bagh market, Ramesh was walking home when two unidentified men on a motorcycle snatched his gold chain and fled towards Patel Nagar."),
        
        ("Example 2 (Intimidation & Criminal Trespass)",
         "Sub-Inspector Sharma recorded that the accused Sunil illegally entered the shop in Chandni Chowk and threatened to kill the shopkeeper Vijay if he called the police."),
        
        ("Example 3 (Financial Fraud / Cheating)",
         "A complaint was lodged stating that Vijay defrauded several investors of 50 Lakhs through a fake real estate scheme in Noida.")
    ]

    for title, text in examples:
        print(f"\n--- {title} ---")
        print(f"Input Text: \"{text}\"")
        result = extract_entities(text)
        print("Extracted Structured Output:")
        print(json.dumps(result, indent=2))
        print("-" * 70)


if __name__ == "__main__":
    unittest.main(exit=False)
    run_manual_realistic_examples()
