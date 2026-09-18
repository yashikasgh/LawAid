import sys
import json
from pathlib import Path

# Ensure project root and backend are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.routers.police import generate_fir, GenerateFIRRequest
from ai.rag.pipeline import run_pipeline
from ai.rag.retrieval.retrieve_bns import retrieve, get_collection
from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.reranker import rerank_candidates
from ai.rag.analysis.legal_analyzer import analyze_incident, MultiProviderLLMFailoverClient

test_incident = (
    "On 10 August 2026, at around 8 PM, near Central Market Road, "
    "an unknown man punched the complainant and stole his mobile phone. The accused is not known"
)

print("=" * 100)
print("1. RUNNING POST /api/police/generate-fir ENDPOINT")
print("=" * 100)

req = GenerateFIRRequest(incident=test_incident)
police_res = generate_fir(req)

print("\n--- POLICE ENDPOINT RESPONSE (KEYS) ---")
print(list(police_res.keys()))

print("\n--- POLICE ENDPOINT supported_sections ---")
print(json.dumps(police_res.get("supported_sections", []), indent=2))

print("\n--- POLICE ENDPOINT fir_data['acts_sections'] ---")
print(json.dumps(police_res.get("fir_data", {}).get("acts_sections", []), indent=2))


print("\n" + "=" * 100)
print("2. RUNNING DIRECT run_pipeline() DETAILED STEP-BY-STEP TRACE")
print("=" * 100)

llm_client = MultiProviderLLMFailoverClient()
print(f"Active LLM Client Providers: {[p.__class__.__name__ for p in llm_client.providers]}")

# Step A: Privacy & NER
from ai.security.privacy_gateway import sanitize_text
privacy_res = sanitize_text(test_incident)
sanitized_text = privacy_res.get("sanitized_text", "")
print(f"\nSanitized Text: '{sanitized_text}'")

ner_result = extract_entities(sanitized_text)
print(f"\nNER Result: {json.dumps(ner_result, indent=2)}")

# Step B: Query Generation
query_output = generate_queries(ner_result, llm_client=llm_client)
raw_queries = query_output.get("queries", [])
queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]
print(f"\nGenerated Queries ({len(queries)}):")
for i, q in enumerate(queries, 1):
    print(f"  Q{i}: {q}")

# Step C: Retrieval & Candidate Map
candidate_map = {}
retrieved_by_query = {}
for q_str in queries:
    retrieved = retrieve(query=q_str, top_k=20)
    retrieved_by_query[q_str] = retrieved
    for item in retrieved:
        doc_id = item.get("id")
        if not doc_id:
            continue
        if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
            candidate_map[doc_id] = item

raw_candidates = list(candidate_map.values())
print(f"\nTotal Unique Retrieved Candidates across all queries: {len(raw_candidates)}")

print("\nRetrieved candidates list:")
for c in raw_candidates:
    print(f"  ID: {c.get('id')} | Sec: {c.get('section')} | Title: {c.get('title')} | Dist: {c.get('distance')}")

# Step D: Reranking
reranked_top_10 = rerank_candidates(
    incident_input=ner_result,
    candidates=raw_candidates,
    top_k=10
)
print(f"\nReranked Top-10 Candidates passed to Legal Analyzer:")
top_10_results = reranked_top_10.get("results", [])
for rank, c in enumerate(top_10_results, 1):
    print(f"  Rank {rank}: ID={c.get('id')} | Sec={c.get('section')} | Clause={c.get('clause')} | Title={c.get('title')}")

# Step E: Legal Analysis
analysis_result = analyze_incident(
    ner_result=ner_result,
    retrieval_result=reranked_top_10,
    llm_client=llm_client
)

print(f"\nLLM Failover Trace: {getattr(llm_client, 'last_execution_trace', [])}")
print(f"Active Provider Info: {getattr(llm_client, 'active_provider_info', {})}")

print("\n--- GROUNDED LEGAL ANALYSIS (FULL UNFILTERED CANDIDATE EVALUATIONS) ---")
grounded_analysis = analysis_result.get("analysis", [])
print(f"Total evaluated analysis items: {len(grounded_analysis)}")

for idx, item in enumerate(grounded_analysis, 1):
    print(f"\n[Analysis Item #{idx}]")
    print(f"  Section: {item.get('section')}")
    print(f"  Clause: {item.get('clause')}")
    print(f"  Title: {item.get('title')}")
    print(f"  Offence Type: {item.get('offence_type')}")
    print(f"  Applicability: {item.get('applicability')}")
    print(f"  Reasoning: {item.get('reasoning')}")
    print(f"  Cognizable: {item.get('cognizable')}")
    evidence = item.get("evidence", [])
    if evidence:
        doc_id = evidence[0].get("document_id")
        rank = evidence[0].get("rank")
        print(f"  Evidence Doc ID: {doc_id} (Rank: {rank})")


print("\n" + "=" * 100)
print("3. CHECKING CHROMADB CORPUS FOR SECTION 134 & SECTION 303 DOCUMENTS")
print("=" * 100)

col = get_collection()
res_134 = col.get(where={"section": "134"})
print("\nChromaDB documents with section='134':")
for id_, meta, doc in zip(res_134.get("ids", []), res_134.get("metadatas", []), res_134.get("documents", [])):
    print(f"  ID: {id_} | Title: {meta.get('title')} | Clause: {meta.get('clause')}")
    print(f"  Text snippet: {doc[:200]}...\n")

res_303 = col.get(where={"section": "303"})
print("\nChromaDB documents with section='303':")
for id_, meta, doc in zip(res_303.get("ids", []), res_303.get("metadatas", []), res_303.get("documents", [])):
    print(f"  ID: {id_} | Title: {meta.get('title')} | Clause: {meta.get('clause')}")
    print(f"  Text snippet: {doc[:200]}...\n")
