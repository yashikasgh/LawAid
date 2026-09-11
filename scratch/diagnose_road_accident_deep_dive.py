import sys
import json
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

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
    analyze_incident
)
from ai.rag.pipeline import run_pipeline

# Road accident FIR text
road_accident_fir = (
    "FIRST INFORMATION REPORT. Date: 10/08/2026. Place of occurrence: Near Central Market road. "
    "Complainant states that while he was riding his motorcycle, an unknown motor car driven in a rash and negligent manner "
    "struck the motorcycle from behind. The complainant suffered hurt and bodily injury on his leg and arm. "
    "The driver of the car failed to stop and drove away at high speed."
)

print("==================================================")
print("1. ACTUAL FIR FACTS & SANITIZED INPUT")
print("==================================================")
privacy_res = sanitize_text(road_accident_fir)
sanitized = privacy_res.get("sanitized_text", "")
ner_res = extract_entities(sanitized)
print("Sanitized text:", sanitized)
print("Extracted NER Entities:", json.dumps(ner_res, indent=2))

print("\n==================================================")
print("2. GENERATED RETRIEVAL QUERIES")
print("==================================================")
llm_client = MultiProviderLLMFailoverClient()
query_output = generate_queries(ner_res, llm_client=llm_client)
raw_queries = query_output.get("queries", [])
queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]
if not queries and sanitized:
    queries = [sanitized]
print("Queries generated:", queries)

print("\n==================================================")
print("3. CHROMADB RETRIEVAL ACROSS ALL GENERATED QUERIES")
print("==================================================")
candidate_map = {}
for q_idx, q_str in enumerate(queries):
    retrieved = retrieve(query=q_str, top_k=20)
    print(f"\nQuery {q_idx + 1}: '{q_str}'")
    for rank, item in enumerate(retrieved, 1):
        doc_id = item.get("id")
        sec_num = str(item.get("section", ""))
        clause_str = str(item.get("clause", ""))
        dist = round(float(item.get("distance", 1.0)), 4)
        if sec_num in ["281", "285", "125"]:
            print(f"   * Rank {rank}: ID={doc_id} | Section {sec_num} ({clause_str}) | dist={dist} | Title: {item.get('title')}")
        if doc_id:
            if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
                candidate_map[doc_id] = item

raw_candidates = list(candidate_map.values())
print(f"\nTotal unique candidates collected: {len(raw_candidates)}")
print("Check for §281, §285, §125 in unique candidates pool:")
for sec in ["281", "285", "125"]:
    matches = [c for c in raw_candidates if str(c.get("section")) == sec]
    if matches:
        for m in matches:
            print(f"   - Section {sec} ({m.get('clause')}): ID={m.get('id')} | dist={round(m.get('distance', 1.0), 4)} | Title: {m.get('title')}")
    else:
        print(f"   - Section {sec}: NOT PRESENT in candidate pool.")

print("\n==================================================")
print("4. RRF RERANKING (TOP-5 CONTEXT)")
print("==================================================")
reranked = rerank_candidates(incident_input=ner_res, candidates=raw_candidates, top_k=5)
print("RRF Reranked Top 5 Candidates passed to LLM Prompt:")
for idx, c in enumerate(reranked, 1):
    print(f"   {idx}. ID={c.get('id')} | Section {c.get('section')} ({c.get('clause')}) | Title: {c.get('title')}")

print("\n==================================================")
print("5. LLM LEGAL ANALYSIS & GROUNDED OUTPUT")
print("==================================================")
pipeline_res = run_pipeline(road_accident_fir, llm_client=llm_client)
print("Pipeline Status:", pipeline_res.get("status"))
print("Pipeline Analysis Items Count:", len(pipeline_res.get("analysis", [])))
for item in pipeline_res.get("analysis", []):
    print(f"\n* Section {item.get('section')} ({item.get('title')})")
    print(f"  Applicability: {item.get('applicability')}")
    print(f"  Reasoning: {item.get('reasoning')}")

print("\n==================================================")
print("6. STATUTORY TEXT INSPECTION FROM INDEXED BNS SOURCE")
print("==================================================")
docs_path = PROJECT_ROOT / "ai" / "rag" / "data" / "processed" / "documents.json"
docs_data = json.load(open(docs_path, encoding="utf-8"))

for target_sec in ["281", "285", "125"]:
    print(f"\n--- Statutory Text for BNS Section {target_sec} ---")
    matched_docs = [d for d in docs_data if str(d.get("metadata", {}).get("section")) == target_sec]
    if not matched_docs:
        print(f"No documents found for Section {target_sec}!")
    for md in matched_docs:
        meta = md.get("metadata", {})
        print(f"ID: {meta.get('id')} | Section: {meta.get('section')} | Clause: {meta.get('clause')} | Title: {meta.get('title')}")
        print("Text:\n" + md.get("text", "")[:800])
        print("-" * 40)

print("\n==================================================")
print("7. INDEPENDENT CONTROLLED RETRIEVAL EXPERIMENT")
print("==================================================")
controlled_queries = [
    "rash and negligent driving on public road",
    "vehicle causing injury to person",
    "act endangering life or personal safety of others",
    "hurt caused by rash or negligent act"
]

for cq in controlled_queries:
    res = retrieve(query=cq, top_k=20)
    print(f"\nQuery: '{cq}'")
    for sec_check in ["281", "285", "125"]:
        matches = [(rank+1, r) for rank, r in enumerate(res) if str(r.get("section")) == sec_check]
        if matches:
            for rank, r in matches:
                print(f"   * Section {sec_check} ({r.get('clause')}): Rank {rank} | dist={round(r.get('distance', 1.0), 4)} | Title: {r.get('title')}")
        else:
            print(f"   * Section {sec_check}: NOT in top 20 retrieval results.")
