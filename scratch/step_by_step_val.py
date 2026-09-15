import json
import os
import sys
import re

sys.path.insert(0, os.path.abspath('.'))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import (
    construct_query_generator_prompt,
    _parse_json_from_llm
)
from scratch.test_benchmark_query_gen import generate_benchmark_mock_queries

bns_section_patterns = [
    r"351\(3\)", r"329\(3\)", r"303\(2\)", r"\bBNS\b", r"\bBNSS\b",
    r"\bSection\s+\d+\b", r"\bsec\.?\s*\d+\b", r"\b\d{3}\(\d+\)\b", r"\b\d{3}\b"
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

grounded_legal_regex = re.compile("|".join(grounded_legal_concept_patterns), re.IGNORECASE)

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

for cid in ['T13', 'T16', 'T25']:
    case = [c for c in gt_list if c['id'] == cid][0]
    incident = case['incident']
    ner_res = extract_entities(incident)
    prompt = construct_query_generator_prompt(ner_res)
    mock_json_str = generate_benchmark_mock_queries(prompt)
    parsed = _parse_json_from_llm(mock_json_str)
    
    print(f"\n================ STEP BY STEP Case {cid} ================")
    raw_queries = parsed.get("queries", [])
    
    ner_str_lower = json.dumps(ner_res).lower()
    raw_text = ner_res.get("raw_text", "")
    offence_types_raw = ner_res.get("offence_types", [])
    offence_types = [o for o in (offence_types_raw if isinstance(offence_types_raw, list) else []) if isinstance(o, str)]
    entities_raw = []
    for k in ("victims", "accused", "persons", "locations", "organizations"):
        val_list = ner_res.get(k)
        if isinstance(val_list, list):
            entities_raw.extend([v for v in val_list if isinstance(v, str)])
    incident_content_str = (raw_text + " " + " ".join(offence_types) + " " + " ".join(entities_raw)).lower()
    stop_words = {"the", "and", "was", "for", "that", "this", "with", "from", "were", "they", "been", "have", "has", "had", "will", "would", "could", "should", "into", "over", "under", "about", "after", "before", "accused", "person", "incident", "facts", "details"}
    incident_tokens = {w for w in re.findall(r"\b[a-z]{3,}\b", incident_content_str) if w not in stop_words}

    for idx, item in enumerate(raw_queries):
        q_str = item.get("query", "")
        q_type = item.get("query_type", "")
        q_lower = q_str.lower()
        q_tokens = set(re.findall(r"\b[a-z]{3,}\b", q_lower)) - stop_words
        has_fact = bool(q_tokens & incident_tokens)
        has_legal = bool(grounded_legal_regex.search(q_lower))
        
        print(f"Query {idx+1}: '{q_str}'")
        print(f"  q_tokens: {q_tokens}")
        print(f"  incident_tokens: {incident_tokens}")
        print(f"  has_fact: {has_fact}, has_legal: {has_legal}")
        if not has_fact and not has_legal:
            print("  FAILED FACT/LEGAL MATCH CHECK!")
