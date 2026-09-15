"""test_phase3_generic_analyzer.py — 15 Generic Statutory Applicability Architecture Unit Tests.

Located at: ai/rag/analysis/tests/test_phase3_generic_analyzer.py
"""

import json
import os
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

from legal_analyzer import (
    analyze_incident,
    construct_analysis_prompt,
    validate_and_ground_analysis,
    MockLLMClient
)
from context_builder import build_legal_context


class TestPhase3GenericAnalyzer(unittest.TestCase):
    """Test suite covering the 15 required section-agnostic statutory applicability rules."""

    def _build_mock_retrieval(self, doc_id: str, title: str, section_def: str, unit_type: str = "core_definition"):
        return {
            "queries": [{"offence_type": title, "query": title}],
            "results": [
                {
                    "offence_type": title,
                    "query": title,
                    "retrieved": [
                        {
                            "rank": 1,
                            "id": doc_id,
                            "section": doc_id.split("_")[1] if "_" in doc_id else "999",
                            "clause": doc_id,
                            "title": title,
                            "target_clause_text": section_def,
                            "section_definition": section_def,
                            "schedule_1": {
                                "offence": title,
                                "punishment": "As per statute",
                                "bailable": "Bailable",
                                "cognizable": "Cognizable",
                                "court": "Magistrate"
                            }
                        }
                    ]
                }
            ]
        }

    # 1. Missing special-capacity prerequisite
    def test_1_missing_special_capacity_prerequisite(self):
        ner = {"raw_text": "A person took a box from a shop counter."}
        retrieval = self._build_mock_retrieval(
            "bns_701_701", "Theft by Clerk or Servant",
            "Whoever, being a clerk or servant, commits theft in respect of any property in the possession of his master."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_701_701",
                    "unit_type": "aggravated_branch",
                    "applicability": "not_supported",
                    "statutory_structure": {
                        "structural_unit_type": "aggravated_branch",
                        "core_elements": ["theft of property"],
                        "conditional_elements": ["offender is a clerk or servant", "property in possession of master"],
                        "aggravated_elements": ["clerk or servant status"],
                        "mitigating_elements": []
                    },
                    "prerequisite_evidence": [
                        {
                            "requirement": "clerk or servant relationship",
                            "requirement_type": "aggravated",
                            "evidence_status": "missing",
                            "incident_evidence": "Incident describes an ordinary person in a shop with no employment relationship stated.",
                            "reason": "Special capacity requirement is unstated and unestablished."
                        }
                    ],
                    "core_elements": ["theft of property"],
                    "conditional_elements": ["clerk or servant status"],
                    "satisfied_elements": ["theft of property"],
                    "missing_elements": ["clerk or servant status"],
                    "contradicted_elements": [],
                    "relationship_analysis": {"relationship_type": "none", "related_candidate": "", "reason": "No capacity established."},
                    "reasoning": "Special capacity of clerk or servant is absent from incident facts."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "not_supported")
        self.assertIn("clerk or servant status", item["missing_elements"])
        self.assertEqual(item["prerequisite_evidence"][0]["evidence_status"], "missing")

    # 2. Missing specific object/instrumentality
    def test_2_missing_specific_object_instrumentality(self):
        ner = {"raw_text": "Ramesh altered the text of a private letter."}
        retrieval = self._build_mock_retrieval(
            "bns_702_702", "Tampering with Property Mark",
            "Whoever removes, destroys, defaces or adds to any property mark with intent to cause injury."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_702_702",
                    "unit_type": "core_definition",
                    "applicability": "not_supported",
                    "statutory_structure": {
                        "structural_unit_type": "core_definition",
                        "core_elements": ["existence of property mark", "defacing or altering property mark"],
                        "conditional_elements": [],
                        "aggravated_elements": [],
                        "mitigating_elements": []
                    },
                    "prerequisite_evidence": [
                        {
                            "requirement": "existence of a property mark",
                            "requirement_type": "core",
                            "evidence_status": "missing",
                            "incident_evidence": "Incident involves altering a private letter, not a property mark.",
                            "reason": "Required specific object (property mark) is absent."
                        }
                    ],
                    "satisfied_elements": [],
                    "missing_elements": ["existence of property mark"],
                    "contradicted_elements": [],
                    "reasoning": "Specific object required by statute (property mark) is absent from the facts."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "not_supported")
        self.assertIn("existence of property mark", item["missing_elements"])

    # 3. Required consequence absent
    def test_3_required_consequence_absent(self):
        ner = {"raw_text": "A vehicle struck a pedestrian, who suffered minor bruises and was discharged from hospital."}
        retrieval = self._build_mock_retrieval(
            "bns_703_703", "Causing Death by Rash Act",
            "Whoever causes the death of any person by doing any rash or negligent act not amounting to culpable homicide."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_703_703",
                    "unit_type": "core_definition",
                    "applicability": "not_supported",
                    "statutory_structure": {
                        "structural_unit_type": "core_definition",
                        "core_elements": ["rash or negligent act", "death of a person caused thereby"],
                        "conditional_elements": []
                    },
                    "prerequisite_evidence": [
                        {
                            "requirement": "death of a person",
                            "requirement_type": "core",
                            "evidence_status": "contradicted",
                            "incident_evidence": "Victim suffered minor bruises and survived.",
                            "reason": "Statutory consequence of death is explicitly contradicted by victim survival."
                        }
                    ],
                    "satisfied_elements": ["rash or negligent act"],
                    "missing_elements": [],
                    "contradicted_elements": ["death of a person"],
                    "reasoning": "Required statutory consequence (death) did not occur."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "not_supported")
        self.assertIn("death of a person", item["contradicted_elements"])

    # 4. Required consequence unknown
    def test_4_required_consequence_unknown(self):
        ner = {"raw_text": "A fight broke out outside a restaurant and Suresh was pushed to the ground."}
        retrieval = self._build_mock_retrieval(
            "bns_704_704", "Voluntarily Causing Grievous Hurt",
            "Whoever voluntarily causes grievous hurt, defined as emasculation, permanent privation of sight/hearing, fracture, etc."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_704_704",
                    "unit_type": "core_definition",
                    "applicability": "uncertain",
                    "statutory_structure": {
                        "structural_unit_type": "core_definition",
                        "core_elements": ["voluntary act", "grievous hurt injury as legally defined"],
                        "conditional_elements": []
                    },
                    "prerequisite_evidence": [
                        {
                            "requirement": "grievous hurt injury",
                            "requirement_type": "core",
                            "evidence_status": "missing",
                            "incident_evidence": "Incident states Suresh was pushed, but extent of physical injury is unstated.",
                            "reason": "Specific consequence of grievous hurt cannot be established without medical injury facts."
                        }
                    ],
                    "satisfied_elements": ["voluntary act"],
                    "missing_elements": ["grievous hurt injury"],
                    "contradicted_elements": [],
                    "reasoning": "Injury severity is unstated; grievous hurt consequence is uncertain."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "uncertain")
        self.assertIn("grievous hurt injury", item["missing_elements"])

    # 5. Possession-state distinction
    def test_5_possession_state_distinction(self):
        ner = {"raw_text": "An abandoned watch was lying on an empty street, and Mohan picked it up."}
        retrieval = self._build_mock_retrieval(
            "bns_705_705", "Theft from Possession",
            "Whoever, intending to take dishonestly any movable property out of the possession of any person without that person's consent."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_705_705",
                    "unit_type": "core_definition",
                    "applicability": "uncertain",
                    "statutory_structure": {
                        "structural_unit_type": "core_definition",
                        "core_elements": ["taking movable property", "taking out of active possession of a person"],
                        "conditional_elements": []
                    },
                    "prerequisite_evidence": [
                        {
                            "requirement": "taking out of active possession of a person",
                            "requirement_type": "core",
                            "evidence_status": "missing",
                            "incident_evidence": "Property was lying abandoned on an empty street.",
                            "reason": "Property was not in active possession of any person when picked up."
                        }
                    ],
                    "satisfied_elements": ["taking movable property"],
                    "missing_elements": ["taking out of active possession of a person"],
                    "contradicted_elements": [],
                    "reasoning": "Property was unpossessed/lost when picked up; active possession requirement unestablished."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "uncertain")

    # 6. Mens rea requirement
    def test_6_mens_rea_requirement(self):
        ner = {"raw_text": "An actor slipped on stage and bumped into another performer."}
        retrieval = self._build_mock_retrieval(
            "bns_706_706", "Voluntarily Causing Hurt",
            "Whoever does any act with the intention of thereby causing hurt to any person, or with the knowledge that he is likely thereby to cause hurt."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_706_706",
                    "unit_type": "core_definition",
                    "applicability": "not_supported",
                    "statutory_structure": {
                        "structural_unit_type": "core_definition",
                        "core_elements": ["physical act causing hurt", "intentional or knowing mens rea to cause hurt"],
                        "conditional_elements": []
                    },
                    "prerequisite_evidence": [
                        {
                            "requirement": "intentional or knowing mens rea",
                            "requirement_type": "core",
                            "evidence_status": "contradicted",
                            "incident_evidence": "Actor accidentally slipped on stage.",
                            "reason": "Mens rea requirement of intentional or knowing voluntary act is absent."
                        }
                    ],
                    "satisfied_elements": ["physical act causing hurt"],
                    "missing_elements": [],
                    "contradicted_elements": ["intentional or knowing mens rea"],
                    "reasoning": "Accidental slip refutes required voluntary criminal mens rea."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "not_supported")

    # 7. Conditional proviso preservation
    def test_7_conditional_proviso_preservation(self):
        ner = {"raw_text": "Karan stole a ring from a jewelry display."}
        retrieval_core = {
            "rank": 1, "id": "bns_303_core", "section": 303, "clause": "303(1)",
            "title": "Theft Definition", "target_clause_text": "Whoever dishonestly takes movable property...",
            "schedule_1": {"offence": "Theft"}
        }
        retrieval_proviso = {
            "rank": 2, "id": "bns_303_proviso", "section": 303, "clause": "303(2)-2",
            "title": "Theft under 5,000 rupees proviso", "target_clause_text": "Where stolen property value is less than 5000 rupees...",
            "schedule_1": {"offence": "Theft under 5,000 rupees"}
        }
        grouped = {
            "queries": [{"offence_type": "theft", "query": "theft"}],
            "results": [{"offence_type": "theft", "query": "theft", "retrieved": [retrieval_core, retrieval_proviso]}]
        }

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_303_core",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "core_elements": ["dishonest taking of movable property without consent"],
                    "conditional_elements": [],
                    "satisfied_elements": ["dishonest taking of movable property without consent"],
                    "missing_elements": [],
                    "contradicted_elements": [],
                    "reasoning": "Core theft definition fully supported."
                },
                {
                    "document_id": "bns_303_proviso",
                    "unit_type": "conditional_proviso",
                    "applicability": "uncertain",
                    "core_elements": ["dishonest taking"],
                    "conditional_elements": ["stolen property value below 5,000 rupees"],
                    "satisfied_elements": ["dishonest taking"],
                    "missing_elements": ["stolen property value below 5,000 rupees"],
                    "contradicted_elements": [],
                    "reasoning": "Property value is unstated; proviso applicability is uncertain."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, grouped, llm_client=MockLLMClient([llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "supported")
        self.assertEqual(res["analysis"][1]["applicability"], "uncertain")

    # 8. Aggravated branch gating
    def test_8_aggravated_branch_gating(self):
        ner = {"raw_text": "A bicycle was taken from a sidewalk outside a park."}
        retrieval = self._build_mock_retrieval(
            "bns_708_708", "Theft in Dwelling House",
            "Whoever commits theft in any building, tent or vessel used as a human dwelling."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_708_708",
                    "unit_type": "aggravated_branch",
                    "applicability": "not_supported",
                    "statutory_structure": {
                        "structural_unit_type": "aggravated_branch",
                        "core_elements": ["theft of property"],
                        "conditional_elements": ["location in building/tent/vessel used as human dwelling"],
                        "aggravated_elements": ["dwelling location"],
                        "mitigating_elements": []
                    },
                    "prerequisite_evidence": [
                        {
                            "requirement": "dwelling location",
                            "requirement_type": "aggravated",
                            "evidence_status": "contradicted",
                            "incident_evidence": "Bicycle taken from sidewalk outside a park, not inside a dwelling.",
                            "reason": "Aggravated branch condition (dwelling house) is contradicted by open sidewalk location."
                        }
                    ],
                    "satisfied_elements": ["theft of property"],
                    "missing_elements": [],
                    "contradicted_elements": ["dwelling location"],
                    "reasoning": "Theft occurred on open sidewalk; dwelling aggravated branch condition not met."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "not_supported")

    # 9. Mitigating branch gating
    def test_9_mitigating_branch_gating(self):
        ner = {"raw_text": "An argument occurred over parking, and Vikas struck Amit."}
        retrieval = self._build_mock_retrieval(
            "bns_709_709", "Voluntarily Causing Hurt on Provocation",
            "Whoever voluntarily causes hurt on grave and sudden provocation, if he neither intends nor knows himself likely to cause hurt."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_709_709",
                    "unit_type": "mitigating_branch",
                    "applicability": "not_supported",
                    "statutory_structure": {
                        "structural_unit_type": "mitigating_branch",
                        "core_elements": ["causing hurt"],
                        "conditional_elements": ["grave and sudden provocation"],
                        "aggravated_elements": [],
                        "mitigating_elements": ["grave and sudden provocation"]
                    },
                    "prerequisite_evidence": [
                        {
                            "requirement": "grave and sudden provocation",
                            "requirement_type": "mitigating",
                            "evidence_status": "missing",
                            "incident_evidence": "Ordinary parking argument does not constitute statutory grave and sudden provocation.",
                            "reason": "Triggering condition for mitigating branch is absent."
                        }
                    ],
                    "satisfied_elements": ["causing hurt"],
                    "missing_elements": ["grave and sudden provocation"],
                    "contradicted_elements": [],
                    "reasoning": "Mitigating condition of grave and sudden provocation is unestablished."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "not_supported")

    # 10. Contradiction handling
    def test_10_contradiction_handling(self):
        ner = {"raw_text": "Item was given voluntarily as a gift."}
        retrieval = self._build_mock_retrieval(
            "bns_710_710", "Theft",
            "Whoever dishonestly takes movable property without consent."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_710_710",
                    "unit_type": "core_definition",
                    "applicability": "not_supported",
                    "prerequisite_evidence": [
                        {
                            "requirement": "taking without consent",
                            "requirement_type": "core",
                            "evidence_status": "contradicted",
                            "incident_evidence": "Item was given voluntarily as a gift with full consent.",
                            "reason": "Lack of consent is explicitly contradicted."
                        }
                    ],
                    "satisfied_elements": [],
                    "missing_elements": [],
                    "contradicted_elements": ["taking without consent"],
                    "reasoning": "Explicit consent contradicts theft core element."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "not_supported")
        self.assertIn("taking without consent", item["contradicted_elements"])

    # 11. Independent concurrent offences
    def test_11_independent_concurrent_offences(self):
        ner = {"raw_text": "Driver sped down main street hitting a pole and stole a watch from a passerby."}
        retrieval_rash = {
            "rank": 1, "id": "bns_281", "section": 281, "clause": "281",
            "title": "Rash Driving", "target_clause_text": "Whoever drives any vehicle on any public way rashly...",
            "schedule_1": {"offence": "Rash driving"}
        }
        retrieval_theft = {
            "rank": 2, "id": "bns_303", "section": 303, "clause": "303(1)",
            "title": "Theft", "target_clause_text": "Whoever dishonestly takes movable property...",
            "schedule_1": {"offence": "Theft"}
        }
        grouped = {
            "queries": [{"offence_type": "traffic", "query": "rash driving theft"}],
            "results": [{"offence_type": "traffic", "query": "rash driving theft", "retrieved": [retrieval_rash, retrieval_theft]}]
        }

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_281",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "relationship_analysis": {"relationship_type": "independent_concurrent", "related_candidate": "bns_303", "reason": "Independent criminal conduct."},
                    "reasoning": "Rash driving on public road established."
                },
                {
                    "document_id": "bns_303",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "relationship_analysis": {"relationship_type": "independent_concurrent", "related_candidate": "bns_281", "reason": "Independent criminal conduct."},
                    "reasoning": "Theft of watch established."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, grouped, llm_client=MockLLMClient([llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "supported")
        self.assertEqual(res["analysis"][1]["applicability"], "supported")
        self.assertEqual(res["analysis"][0]["relationship_analysis"]["relationship_type"], "independent_concurrent")

    # 12. General-vs-specific relationship
    def test_12_general_vs_specific_relationship(self):
        ner = {"raw_text": "A thief snatched a purse from a victim's shoulder while running past."}
        retrieval_general = {
            "rank": 1, "id": "bns_303_gen", "section": 303, "clause": "303(1)",
            "title": "Theft (General)", "target_clause_text": "Whoever dishonestly takes movable property...",
            "schedule_1": {"offence": "Theft"}
        }
        retrieval_specific = {
            "rank": 2, "id": "bns_304_spec", "section": 304, "clause": "304(1)",
            "title": "Snatching (Specific)", "target_clause_text": "Theft is snatching if offender suddenly or quickly seizes property...",
            "schedule_1": {"offence": "Snatching"}
        }
        grouped = {
            "queries": [{"offence_type": "theft", "query": "snatching purse theft"}],
            "results": [{"offence_type": "theft", "query": "snatching purse theft", "retrieved": [retrieval_general, retrieval_specific]}]
        }

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_304_spec",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "relationship_analysis": {
                        "relationship_type": "specific_over_general",
                        "related_candidate": "bns_303_gen",
                        "reason": "Specific statutory provision for sudden/quick seizure governs."
                    },
                    "reasoning": "Snatching elements affirmatively satisfied."
                },
                {
                    "document_id": "bns_303_gen",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "relationship_analysis": {
                        "relationship_type": "specific_over_general",
                        "related_candidate": "bns_304_spec",
                        "reason": "Underlying general theft provision subsumed under specific snatching section."
                    },
                    "reasoning": "General theft core elements present."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, grouped, llm_client=MockLLMClient([llm_resp]))
        self.assertEqual(res["analysis"][0]["relationship_analysis"]["relationship_type"], "specific_over_general")

    # 13. Civil/ambiguous incident
    def test_13_civil_ambiguous_incident(self):
        ner = {"raw_text": "Two business partners disagreed over profit sharing ratios defined in an agreement."}
        retrieval = self._build_mock_retrieval(
            "bns_713_713", "Criminal Breach of Trust",
            "Whoever being in any manner entrusted with property dishonestly misappropriates or converts to his own use."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_713_713",
                    "unit_type": "core_definition",
                    "applicability": "not_supported",
                    "statutory_structure": {
                        "structural_unit_type": "core_definition",
                        "core_elements": ["entrustment of property", "dishonest misappropriation/conversion"],
                        "conditional_elements": []
                    },
                    "prerequisite_evidence": [
                        {
                            "requirement": "dishonest criminal misappropriation",
                            "requirement_type": "core",
                            "evidence_status": "missing",
                            "incident_evidence": "Commercial dispute over contract interpretation without dishonest conversion established.",
                            "reason": "Civil contract ambiguity cannot be converted into criminal mens rea."
                        }
                    ],
                    "satisfied_elements": [],
                    "missing_elements": ["dishonest criminal misappropriation"],
                    "contradicted_elements": [],
                    "reasoning": "Civil contract disagreement lacks mandatory criminal mens rea."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "not_supported")
        self.assertIn("dishonest criminal misappropriation", item["missing_elements"])

    # 14. Cross-candidate isolation
    def test_14_cross_candidate_isolation(self):
        ner = {"raw_text": "A driver showed a valid driving license."}
        doc_a = {
            "rank": 1, "id": "bns_doc_A", "section": 100, "clause": "100",
            "title": "Vehicle Operation Compliance", "target_clause_text": "Driving with valid license.",
            "schedule_1": {"offence": "Compliance"}
        }
        doc_b = {
            "rank": 2, "id": "bns_doc_B", "section": 200, "clause": "200",
            "title": "Breach of Special Trust by Trustee", "target_clause_text": "Trustee dishonestly converting trust funds.",
            "schedule_1": {"offence": "Trustee Breach"}
        }
        grouped = {
            "queries": [{"offence_type": "general", "query": "query"}],
            "results": [{"offence_type": "general", "query": "query", "retrieved": [doc_a, doc_b]}]
        }

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_doc_A",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "satisfied_elements": ["valid license present"],
                    "missing_elements": [],
                    "contradicted_elements": [],
                    "reasoning": "Doc A elements satisfied."
                },
                {
                    "document_id": "bns_doc_B",
                    "unit_type": "core_definition",
                    "applicability": "not_supported",
                    "satisfied_elements": [],
                    "missing_elements": ["trustee capacity", "dishonest conversion"],
                    "contradicted_elements": [],
                    "reasoning": "Doc B prerequisites entirely absent; evidence for Doc A cannot satisfy Doc B."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, grouped, llm_client=MockLLMClient([llm_resp]))
        self.assertEqual(res["analysis"][0]["applicability"], "supported")
        self.assertEqual(res["analysis"][1]["applicability"], "not_supported")
        self.assertEqual(len(res["analysis"][1]["satisfied_elements"]), 0)

    # 15. Unseen generic provision
    def test_15_unseen_generic_provision(self):
        ner = {"raw_text": "An unauthorized drone flew into controlled airspace above 500 feet without a flight permit."}
        retrieval = self._build_mock_retrieval(
            "bns_999_custom_drone_regulation", "Unauthorized Aerial Navigation",
            "Whoever operates an unmanned aerial vehicle in restricted airspace above prescribed altitude without valid authorization."
        )

        llm_resp = json.dumps({
            "status": "success",
            "analysis": [
                {
                    "document_id": "bns_999_custom_drone_regulation",
                    "unit_type": "core_definition",
                    "applicability": "supported",
                    "statutory_structure": {
                        "structural_unit_type": "core_definition",
                        "core_elements": ["operation of UAV", "controlled/restricted airspace", "absence of flight permit"],
                        "conditional_elements": []
                    },
                    "prerequisite_evidence": [
                        {
                            "requirement": "operation of UAV",
                            "requirement_type": "core",
                            "evidence_status": "satisfied",
                            "incident_evidence": "Drone flew above 500 feet.",
                            "reason": "Directly established."
                        },
                        {
                            "requirement": "controlled airspace",
                            "requirement_type": "core",
                            "evidence_status": "satisfied",
                            "incident_evidence": "Controlled airspace entered.",
                            "reason": "Directly established."
                        },
                        {
                            "requirement": "absence of permit",
                            "requirement_type": "core",
                            "evidence_status": "satisfied",
                            "incident_evidence": "Flew without a flight permit.",
                            "reason": "Directly established."
                        }
                    ],
                    "satisfied_elements": ["operation of UAV", "controlled airspace", "absence of permit"],
                    "missing_elements": [],
                    "contradicted_elements": [],
                    "reasoning": "All statutory prerequisites for unseen drone provision are fully satisfied."
                }
            ],
            "limitations": []
        })

        res = analyze_incident(ner, retrieval, llm_client=MockLLMClient([llm_resp]))
        item = res["analysis"][0]
        self.assertEqual(item["applicability"], "supported")
        self.assertEqual(item["section"], "999")
        self.assertEqual(len(item["satisfied_elements"]), 3)


if __name__ == "__main__":
    unittest.main()
