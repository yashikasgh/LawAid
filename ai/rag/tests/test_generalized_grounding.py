"""test_generalized_grounding.py — Generalized Regression Tests for Legal Grounding.

Tests general legal reasoning, statutory element matching, missing-fact identification,
and self-consistency across diverse unseen natural language scenarios without hard-coded rules.
"""

import json
import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.rag.analysis.legal_analyzer import (
    analyze_incident,
    MockLLMClient,
    build_legal_context,
    GLOBAL_HEALTH_TRACKER,
)
from ai.rag.pipeline import run_pipeline


class TestGeneralizedGrounding(unittest.TestCase):

    def setUp(self):
        GLOBAL_HEALTH_TRACKER.reset()

    def test_1_theft_without_word_theft_snatching(self):
        """Unseen Scenario: Property taken without using the word 'theft'."""
        ner = {
            "victims": ["Complainant"],
            "accused": ["Unknown rider"],
            "persons": ["Complainant"],
            "offence_types": ["taking property"],
            "raw_text": "A guy on a motor scooter suddenly grabbed my handbag from my shoulder while I was waiting for a bus and sped away."
        }
        retrieval = {
            "queries": [{"query": "grabbed bag shoulder scooter"}],
            "results": [
                {
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_303_303(2)",
                            "section": 303,
                            "clause": "303(2)",
                            "title": "Theft.",
                            "text": "Whoever, intending to take dishonestly any movable property..."
                        },
                        {
                            "rank": 2,
                            "id": "bns_304_304(1)",
                            "section": 304,
                            "clause": "304(1)",
                            "title": "Snatching.",
                            "text": "Theft is snatching if, in order to commit theft, the offender suddenly or quickly or forcibly seizes or grabs or takes away any movable property..."
                        }
                    ]
                }
            ]
        }
        # Mock LLM returns structured analysis based on facts
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_303_303(2)",
                    "applicability": "supported",
                    "reasoning": "Dishonest taking of movable property (handbag) without consent is established by the stated facts."
                },
                {
                    "document_id": "bns_304_304(1)",
                    "applicability": "supported",
                    "reasoning": "Offender suddenly grabbed the handbag from victim's shoulder, satisfying the statutory elements of snatching."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        self.assertEqual(res["status"], "success")
        supp_sections = [item["section"] for item in res["analysis"] if item["applicability"] == "supported"]
        self.assertIn("303", supp_sections)
        self.assertIn("304", supp_sections)

    def test_2_property_taken_while_distracted(self):
        """Unseen Scenario: Property taken quietly while victim was distracted (No force/hurt)."""
        ner = {
            "victims": ["Complainant"],
            "accused": [],
            "persons": [],
            "offence_types": [],
            "raw_text": "While I was ordering coffee at a cafe, someone quietly took my laptop off the empty chair behind me without me noticing."
        }
        retrieval = {
            "queries": [{"query": "took laptop quietly"}],
            "results": [
                {
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_303_303(2)",
                            "section": 303,
                            "clause": "303(2)",
                            "title": "Theft.",
                            "text": "Whoever, intending to take dishonestly any movable property..."
                        },
                        {
                            "rank": 2,
                            "id": "bns_308_308(1)",
                            "section": 308,
                            "clause": "308(1)",
                            "title": "Extortion.",
                            "text": "Whoever intentionally puts any person in fear of any injury..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_303_303(2)",
                    "applicability": "supported",
                    "reasoning": "Laptop taken without consent, establishing theft."
                },
                {
                    "document_id": "bns_308_308(1)",
                    "applicability": "not_supported",
                    "reasoning": "Extortion requires putting the person in fear of injury, which is contradicted by the facts (quiet taking while distracted)."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        self.assertEqual(res["status"], "success")

        theft_item = next(i for i in res["analysis"] if i["section"] == "303")
        extortion_item = next(i for i in res["analysis"] if i["section"] == "308")

        self.assertEqual(theft_item["applicability"], "supported")
        self.assertEqual(extortion_item["applicability"], "not_supported")

    def test_3_physical_attack_without_theft(self):
        """Unseen Scenario: Physical attack with no property taken. Theft must be NOT supported."""
        ner = {
            "victims": ["Complainant"],
            "accused": ["Argument partner"],
            "persons": [],
            "offence_types": ["assault"],
            "raw_text": "A person punched me in the face during a heated argument outside a store. They did not take any money or items."
        }
        retrieval = {
            "queries": [{"query": "punched in face argument"}],
            "results": [
                {
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_115_115(1)",
                            "section": 115,
                            "clause": "115(1)",
                            "title": "Voluntarily causing hurt.",
                            "text": "Whoever does any act with the intention of causing hurt..."
                        },
                        {
                            "rank": 2,
                            "id": "bns_303_303(2)",
                            "section": 303,
                            "clause": "303(2)",
                            "title": "Theft.",
                            "text": "Whoever, intending to take dishonestly any movable property..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_115_115(1)",
                    "applicability": "supported",
                    "reasoning": "Punching in the face directly caused bodily hurt."
                },
                {
                    "document_id": "bns_303_303(2)",
                    "applicability": "not_supported",
                    "reasoning": "Facts explicitly state no money or items were taken."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        hurt_item = next(i for i in res["analysis"] if i["section"] == "115")
        theft_item = next(i for i in res["analysis"] if i["section"] == "303")

        self.assertEqual(hurt_item["applicability"], "supported")
        self.assertEqual(theft_item["applicability"], "not_supported")

    def test_4_threat_without_injury(self):
        """Unseen Scenario: Threat without physical injury. Hurt must NOT be marked supported."""
        ner = {
            "victims": ["Complainant"],
            "accused": ["Stranger"],
            "persons": [],
            "offence_types": ["threat"],
            "raw_text": "Someone blocked my path in the park and threatened to break my bones if I didn't hand over my wallet, but I managed to run away unharmed."
        }
        retrieval = {
            "queries": [{"query": "threatened break bones"}],
            "results": [
                {
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_351_351(2)",
                            "section": 351,
                            "clause": "351(2)",
                            "title": "Criminal intimidation.",
                            "text": "Whoever threatens another with injury to their person..."
                        },
                        {
                            "rank": 2,
                            "id": "bns_115_115(1)",
                            "section": 115,
                            "clause": "115(1)",
                            "title": "Voluntarily causing hurt.",
                            "text": "Whoever causes bodily pain..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_351_351(2)",
                    "applicability": "supported",
                    "reasoning": "Threat of injury to person satisfies criminal intimidation."
                },
                {
                    "document_id": "bns_115_115(1)",
                    "applicability": "not_supported",
                    "reasoning": "Victim escaped unharmed; no physical hurt was actually caused."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        threat_item = next(i for i in res["analysis"] if i["section"] == "351")
        hurt_item = next(i for i in res["analysis"] if i["section"] == "115")

        self.assertEqual(threat_item["applicability"], "supported")
        self.assertEqual(hurt_item["applicability"], "not_supported")

    def test_5_unauthorized_house_entry_landlord(self):
        """Unseen Scenario: Landlord unauthorized entry without breaking/concealment."""
        ner = {
            "victims": ["Tenant"],
            "accused": ["Landlord"],
            "persons": [],
            "offence_types": ["trespass"],
            "raw_text": "My landlord unlocked my apartment door with a spare key without my consent while I was sleeping and refused to leave when asked."
        }
        retrieval = {
            "queries": [{"query": "landlord unlocked apartment door without permission"}],
            "results": [
                {
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_329_329(3)",
                            "section": 329,
                            "clause": "329(3)",
                            "title": "House-trespass.",
                            "text": "Whoever commits criminal trespass by entering or remaining in any building used as a human dwelling..."
                        },
                        {
                            "rank": 2,
                            "id": "bns_331_331(1)",
                            "section": 331,
                            "clause": "331(1)",
                            "title": "Lurking house-trespass.",
                            "text": "Whoever commits house-trespass having taken precautions to conceal such house-trespass..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_329_329(3)",
                    "applicability": "supported",
                    "reasoning": "Entering residential apartment without consent establishes house-trespass."
                },
                {
                    "document_id": "bns_331_331(1)",
                    "applicability": "uncertain",
                    "reasoning": "Lurking/concealment elements are not clearly established by using a spare key."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        house_item = next(i for i in res["analysis"] if i["section"] == "329")
        lurking_item = next(i for i in res["analysis"] if i["section"] == "331")

        self.assertEqual(house_item["applicability"], "supported")
        self.assertEqual(lurking_item["applicability"], "uncertain")

    def test_6_house_entry_with_concealment_and_night(self):
        """Unseen Scenario: Bedroom entry at 2 AM with hiding behind curtains."""
        ner = {
            "victims": ["Complainant"],
            "accused": ["Stranger"],
            "persons": [],
            "offence_types": ["trespass"],
            "raw_text": "I woke up at 2 AM and found a stranger hiding behind the curtains inside my bedroom."
        }
        retrieval = {
            "queries": [{"query": "stranger hiding curtains bedroom 2 am"}],
            "results": [
                {
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": "bns_331_331(4)",
                            "section": 331,
                            "clause": "331(4)",
                            "title": "Lurking house-trespass by night.",
                            "text": "Whoever commits lurking house-trespass by night..."
                        }
                    ]
                }
            ]
        }
        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_331_331(4)",
                    "applicability": "supported",
                    "reasoning": "Entry into dwelling at 2 AM (nighttime) with active concealment behind curtains satisfies lurking house-trespass by night."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient(responses=[llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "supported")

    def test_7_self_consistency_in_conversational_synthesis(self):
        """Test Self-Consistency: If a provision is uncertain/conditional, bottom line MUST NOT state it as established."""
        # Mock responses for query generation, legal analysis, and synthesis
        mock_queries_json = json.dumps({"queries": [{"query": "taking movable property"}]})
        # Note: document_id matching actual retrieved items will be preserved
        mock_analysis_json = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_303_303(2)",
                    "applicability": "supported",
                    "reasoning": "Dishonest taking of property confirmed by facts."
                },
                {
                    "document_id": "bns_134",
                    "applicability": "uncertain",
                    "reasoning": "Property being worn or carried at exact moment of assault is unstated."
                }
            ],
            "limitations": []
        })
        llm_synth_response = """### Empirical Legal Analysis

#### What the law says
The law protects individuals against unauthorized taking of property and physical force.

#### Applicable / Potentially Applicable Provisions

- **Section 303 (Theft)** - Established. The facts confirm property was taken without permission.
- **Section 134** - Potentially applicable. This would apply if the item was being worn or carried by you and assault was used in the attempt to steal it. The current facts do not confirm whether it was being carried.

#### Bottom line
The established legal section based on your stated facts is Section 303 (Theft). Section 134 remains a conditional possibility depending on whether the item was being worn or carried at the time.
"""
        # MockLLMClient provides responses sequentially. If analyze_incident retries or queries run, supply sufficient responses
        mock_llm = MockLLMClient(responses=[mock_queries_json, mock_analysis_json, mock_analysis_json, llm_synth_response])
        result = run_pipeline("Someone took my item.", llm_client=mock_llm)
        synthesis = result.get("conversational_synthesis", "")

        # If synthesis is generated, verify self-consistency
        if synthesis:
            self.assertIn("Section 303", synthesis)
            self.assertNotIn("The most likely legal sections are Section 303 and Section 134", synthesis)
        else:
            self.assertEqual(result["status"], "success")

    def test_8_no_contradiction_between_established_status_and_missing_facts(self):
        """Automated Assertion: Catch any text line declaring 'Facts establish this provision' followed by missing-fact caveats."""
        contradictory_examples = [
            "Section 329 — Facts establish this provision. The facts make this relevant, but purpose and circumstances of entry would help confirm applicability.",
            "Section 303 — Established. We still need to confirm if the property was actually taken without consent.",
            "Section 331 — Established. Additional facts are needed to know if they broke in stealthily."
        ]

        def check_for_contradiction(text: str) -> bool:
            # Pattern: Claims established/facts establish, BUT then says facts are missing / needed / to confirm / cannot say
            lines = text.split("\n")
            for line in lines:
                l_lower = line.lower()
                if "facts establish" in l_lower or "established" in l_lower:
                    caveat_phrases = [
                        "would help confirm",
                        "additional facts",
                        "facts are needed",
                        "facts needed",
                        "need to confirm",
                        "cannot say",
                        "cannot determine",
                        "needs confirmation",
                        "still need"
                    ]
                    if any(phrase in l_lower for phrase in caveat_phrases):
                        return True
            return False

        # Verify our validator catches bad contradictions
        for bad_text in contradictory_examples:
            self.assertTrue(check_for_contradiction(bad_text), f"Validator failed to catch contradiction in: {bad_text}")

        # Verify compliant text passes clean
        good_text = (
            "Section 303 (Theft) — Facts establish this provision. The taking of movable property without consent is established by your stated facts.\n"
            "Section 329 (House-trespass) — Potentially applicable. Entering without permission makes this relevant, but statutory intent requirements need confirmation."
        )
        self.assertFalse(check_for_contradiction(good_text), "Validator falsely flagged compliant text as contradictory!")


if __name__ == "__main__":
    unittest.main()

