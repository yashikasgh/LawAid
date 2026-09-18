import sys
import json
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

print("=== FIR UNDERSTANDING END-TO-END DIAGNOSTIC TRACE ===")
print("\n--- STEP 1: OCR / RAW TEXT ---")
print("Raw text length:", len(road_accident_fir))
print("Raw text snippet:", road_accident_fir)

# 2. Privacy & NER
privacy_res = sanitize_text(road_accident_fir)
sanitized = privacy_res.get("sanitized_text", "")
print("\n--- STEP 2: SANITIZED TEXT & NER ---")
ner_res = extract_entities(sanitized)
print("Extracted entities:", json.dumps(ner_res, indent=2))

# 3. Query Generation
print("\n--- STEP 3: RETRIEVAL QUERY GENERATION ---")
llm_client = MultiProviderLLMFailoverClient()
query_output = generate_queries(ner_res, llm_client=llm_client)
raw_queries = query_output.get("queries", [])
queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]
if not queries and sanitized:
    queries = [sanitized]
print("Generated queries:", queries)

# 4. ChromaDB Retrieval
print("\n--- STEP 4: CHROMADB CANDIDATE RETRIEVAL ---")
candidate_map = {}
for q_str in queries:
    retrieved = retrieve(query=q_str, top_k=20)
    for item in retrieved:
        doc_id = item.get("id")
        if doc_id:
            if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
                candidate_map[doc_id] = item

raw_candidates = list(candidate_map.values())
print(f"Retrieved {len(raw_candidates)} total candidates across queries.")
print("Retrieved Candidate Sections:")
for c in raw_candidates:
    print(f"  - ID: {c.get('id')} | Section: {c.get('section')} ({c.get('clause')}) | Title: {c.get('title')} | dist={round(c.get('distance', 1.0), 4)}")

# Check if 125, 125(a), 125(b), 281, 282, 285, 217, 72 are in candidates
candidate_sections = set(str(c.get('section')) for c in raw_candidates)
print("\nSpecific Section Check in Retrieved Candidates:")
for sec in ["72", "125", "217", "281", "282", "285"]:
    in_cand = sec in candidate_sections
    print(f"  - Section {sec}: {'PRESENT in ChromaDB candidates' if in_cand else 'NOT present in ChromaDB candidates'}")

# 5. Reranking
print("\n--- STEP 5: RRF RERANKED TOP-5 CANDIDATES ---")
reranked = rerank_candidates(incident_input=ner_res, candidates=raw_candidates, top_k=5)
for c in reranked:
    print(f"  - ID: {c.get('id')} | Section: {c.get('section')} ({c.get('clause')}) | Title: {c.get('title')}")

# 6. Legal Context & LLM Analysis
print("\n--- STEP 6 & 7: LLM GROUNDED LEGAL ANALYSIS ---")
context_obj = build_legal_context(ner_res, reranked)
pipeline_res = run_pipeline(road_accident_fir, llm_client=llm_client)

print("Pipeline Status:", pipeline_res.get("status"))
print("Pipeline Analysis Items Count:", len(pipeline_res.get("analysis", [])))
print("Pipeline Analysis Items:")
for item in pipeline_res.get("analysis", []):
    print(f"  - Section {item.get('section')} ({item.get('title')}): applicability={item.get('applicability')} | reasoning={item.get('reasoning')}")

# 8. Backend Router FIR Understand mapping check
print("\n--- STEP 8: BACKEND ROUTER FIR /UNDERSTAND RETURN VALUE ---")
charges_summary = []
for item in pipeline_res.get("analysis", []):
    charges_summary.append({
        "section": item.get("section", ""),
        "title": item.get("title", ""),
        "punishment": item.get("punishment", ""),
        "bailable": item.get("bailable", ""),
        "cognizable": item.get("cognizable", ""),
        "reasoning": item.get("reasoning", ""),
        "applicability": item.get("applicability", ""),
        "status": item.get("status", ""),
    })
print("Charges summary sent to frontend by /fir/understand:")
print(json.dumps(charges_summary, indent=2))
