import json
import os
import sys
import re

sys.path.insert(0, os.path.abspath('.'))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import (
    construct_query_generator_prompt,
    validate_llm_queries,
    _parse_json_from_llm
)
from scratch.test_benchmark_query_gen import generate_benchmark_mock_queries

bns_section_patterns = [
    r"351\(3\)", r"329\(3\)", r"303\(2\)", r"\bBNS\b", r"\bBNSS\b",
    r"\bSection\s+\d+\b", r"\bsec\.?\s*\d+\b", r"\b\d{3}\(\d+\)\b", r"\b\d{3}\b"
]
section_inquiry_patterns = [
    r"\bwhich\s+sections?\b", r"\bwhat\s+sections?\b", r"\bsection\s+numbers?\b"
]
conclusion_patterns = [
    r"\bsection\s+\d+\s+applies\b", r"\bapplies\b", r"\bis applicable\b", r"\bguilty of\b",
    r"\bviolates section\b", r"\bpunishable under section\b", r"\bconstitutes an offence under section\b"
]
filler_patterns = [
    r"\bunder\s+indian\s+(criminal\s+)?law\b", r"\bin\s+indian\s+(criminal\s+)?law\b",
    r"\bunder\s+bns\b", r"\bunder\s+bnss\b", r"\bin\s+india\b"
]
unsupported_concepts = [
    "aggravating factor", "aggravating factors", "aggravated", "robbery", "dacoity",
    "extortion", "ransom", "kidnapping", "homicide", "murder", "cybercrime", "hacking"
]
grounded_legal_concept_patterns = [
    r"\bdishonest(ly)?\s+taking\b", r"\bmovable\s+property\b", r"\bwithout\s+(that\s+person's\s+)?consent\b",
    r"\bwithout\s+permission\b", r"\bcriminal\s+trespass\b", r"\bhouse\s+trespass\b",
    r"\bcriminal\s+intimidation\b", r"\bcriminal\s+force\b", r"\bwrongful\s+restraint\b",
    r"\bwrongful\s+confinement\b", r"\breceiv(ing|es)\s+stolen\s+property\b", r"\bretain(ing|s)\s+stolen\s+property\b",
    r"\bbreach\s+of\s+trust\b", r"\bmisappropriation\b", r"\bcheating\b", r"\bforgery\b",
    r"\bmischief\b", r"\bassault\b", r"\bsnatching\b", r"\bseiz(ing|ure)\b", r"\bforcibl(y|e)\b",
    r"\bendangering\s+(human\s+)?life\b", r"\bendangering\s+personal\s+safety\b",
    r"\bpersonal\s+safety\b", r"\brash\s+or\s+negligent\b", r"\bcausing\s+hurt\b", r"\bcausing\s+injury\b"
]

section_regex = re.compile("|".join(bns_section_patterns), re.IGNORECASE)
inquiry_regex = re.compile("|".join(section_inquiry_patterns), re.IGNORECASE)
conclusion_regex = re.compile("|".join(conclusion_patterns), re.IGNORECASE)
filler_regex = re.compile("|".join(filler_patterns), re.IGNORECASE)
grounded_legal_regex = re.compile("|".join(grounded_legal_concept_patterns), re.IGNORECASE)

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

for case in gt_list:
    cid = case['id']
    incident = case['incident']
    ner_res = extract_entities(incident)
    prompt = construct_query_generator_prompt(ner_res)
    mock_json_str = generate_benchmark_mock_queries(prompt)
    parsed = _parse_json_from_llm(mock_json_str)
    
    val_res = validate_llm_queries(parsed, ner_res)
    if val_res is None:
        print(f"\nCase {cid} FAILED VALIDATION! Debugging queries:")
        raw_queries = parsed.get("queries", [])
        ner_str_lower = json.dumps(ner_res).lower()
        for idx, item in enumerate(raw_queries):
            q_str = item.get("query", "")
            reasons = []
            if section_regex.search(q_str):
                reasons.append(f"section_regex ({section_regex.search(q_str).group(0)})")
            if inquiry_regex.search(q_str):
                reasons.append("inquiry_regex")
            if conclusion_regex.search(q_str):
                reasons.append(f"conclusion_regex ({conclusion_regex.search(q_str).group(0)})")
            if filler_regex.search(q_str):
                reasons.append("filler_regex")
            for concept in unsupported_concepts:
                if concept in q_str.lower() and concept not in ner_str_lower:
                    reasons.append(f"unsupported_concept '{concept}'")
            
            words = re.findall(r"\b[A-Z][a-z]+\b", q_str)
            common_legal = {"The", "A", "An", "In", "On", "At", "For", "With", "Under", "Indian", "Law", "Legal", "State", "Penal", "Code"}
            for w in words:
                if w not in common_legal and w.lower() not in ner_str_lower:
                    reasons.append(f"proper_noun '{w}'")
                    
            print(f"  Q#{idx+1} ({item.get('query_type')}): {q_str}\n     Rejections: {reasons}")
