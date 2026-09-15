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

print("=== TESTING BENCHMARK QUERY GENERATOR MOCK ON ALL 30 CASES ===")

passed_cases = 0
failed_cases = 0

for idx, case in enumerate(gt_list, start=1):
    cid = case['id']
    incident = case['incident']
    
    # 1. Extract NER & construct prompt
    ner_res = extract_entities(incident)
    prompt = construct_query_generator_prompt(ner_res)
    
    # 2. Call mock generator
    mock_json_str = generate_benchmark_mock_queries(prompt)
    
    # 3. Parse JSON & Validate with production validate_llm_queries
    parsed_json = _parse_json_from_llm(mock_json_str)
    valid_queries = validate_llm_queries(parsed_json, ner_res)
    
    if valid_queries is not None:
        passed_cases += 1
        query_types = [q['query_type'] for q in valid_queries]
        print(f"Case {cid} ({len(valid_queries)} queries, types: {query_types}): PASSED")
        for q in valid_queries:
            print(f"   [{q['query_type']}] {q['query']}")
    else:
        failed_cases += 1
        print(f"Case {cid}: FAILED VALIDATION! Raw output:\n{mock_json_str}")

print(f"\nSummary: Passed {passed_cases}/30 cases, Failed {failed_cases}/30 cases.")
