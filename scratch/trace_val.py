import json
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import (
    construct_query_generator_prompt,
    validate_llm_queries,
    _parse_json_from_llm
)
from scratch.test_benchmark_query_gen import generate_benchmark_mock_queries

with open('evaluation/ground_truth.json', 'r', encoding='utf-8') as f:
    gt_list = json.load(f)

for cid in ['T13', 'T16', 'T25']:
    case = [c for c in gt_list if c['id'] == cid][0]
    incident = case['incident']
    ner_res = extract_entities(incident)
    prompt = construct_query_generator_prompt(ner_res)
    mock_json_str = generate_benchmark_mock_queries(prompt)
    parsed = _parse_json_from_llm(mock_json_str)
    
    print(f"\n================ Case {cid} ================")
    print("Parsed JSON queries:")
    for q in parsed.get("queries", []):
        print("  ", q)
        
    res = validate_llm_queries(parsed, ner_res)
    print("validate_llm_queries result:", res)
