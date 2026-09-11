import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=True)

from ai.security.privacy_gateway import sanitize_text
from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.legal_analyzer import (
    build_legal_context,
    construct_analysis_prompt,
    validate_and_ground_analysis,
    MultiProviderLLMFailoverClient,
    _parse_json_from_llm
)
from ai.rag.pipeline import run_pipeline

incident_text = "Yesterday at around 7:30 PM, I was near the local market when an unknown man suddenly punched me and stole my mobile phone. I don't know the person who did it."

print("=== DIAGNOSTIC TRACE ===")
print("1. RAW INCIDENT:", incident_text)

# 1. Privacy Gateway
privacy_res = sanitize_text(incident_text)
sanitized = privacy_res.get("sanitized_text", "")
print("\n2. SANITIZED INCIDENT:", sanitized)

# 2. NER
ner_res = extract_entities(sanitized)
print("\n3. NER EXTRACTED ENTITIES:", json.dumps(ner_res, indent=2))

# 3. MultiProvider LLM client
llm_client = MultiProviderLLMFailoverClient()
print("\n4. PROVIDER CHAIN:", [f"{p.__class__.__name__}({getattr(p, 'model_name', 'unknown')})" for p in llm_client.providers])

# 4. Query Generation
query_output = generate_queries(ner_res, llm_client=llm_client)
raw_queries = query_output.get("queries", [])
queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]
if not queries and sanitized:
    queries = [sanitized]
print("\n5. RETRIEVAL QUERIES GENERATED:", queries)

# 5. ChromaDB Retrieval
candidate_map = {}
for q_str in queries:
    retrieved = retrieve(query=q_str, top_k=20)
    for item in retrieved:
        doc_id = item.get("id")
        if doc_id:
            if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
                candidate_map[doc_id] = item

raw_candidates = list(candidate_map.values())
print(f"\n6. CHROMADB RETRIEVAL: Retrieved {len(raw_candidates)} total candidates.")
for c in raw_candidates[:5]:
    print(f"   - Candidate ID: {c.get('id')} | Section: {c.get('section')} | Clause: {c.get('clause')} | Title: {c.get('title')}")

# 6. Reranking
reranked = rerank_candidates(incident_input=ner_res, candidates=raw_candidates, top_k=5)
print(f"\n7. RRF RERANKED TOP-5 CANDIDATES:")
for c in reranked:
    print(f"   - ID: {c.get('id')} | Section: {c.get('section')} | Clause: {c.get('clause')} | Title: {c.get('title')}")

# 7. Context Builder
context_obj = build_legal_context(ner_res, reranked)
prompt = construct_analysis_prompt(context_obj)
print("\n8. PROMPT LENGTH:", len(prompt))

# 8. LLM Generation attempt
print("\n9. EXECUTING LLM GENERATION VIA FAILOVER CLIENT...")
pipeline_res = run_pipeline(incident_text, llm_client=llm_client)

print("\n10. FINAL PIPELINE RESULT:")
print("   - Status:", pipeline_res.get("status"))
print("   - Analysis items count:", len(pipeline_res.get("analysis", [])))
for item in pipeline_res.get("analysis", []):
    print(f"     * Section {item.get('section')} ({item.get('title')}): applicability={item.get('applicability')}")
print("   - Limitations:", pipeline_res.get("limitations"))
if hasattr(llm_client, "last_execution_trace"):
    print("\n11. LLM FAILOVER EXECUTION TRACE:")
    for tr in llm_client.last_execution_trace:
        print(f"     * {tr.get('provider')} ({tr.get('model')}): status={tr.get('status')} | error={tr.get('error')} | latency={tr.get('latency_ms')}ms")
