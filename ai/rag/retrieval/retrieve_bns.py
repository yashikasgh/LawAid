"""retrieve_bns.py — Baseline vector retrieval for LawAid RAG.

Located at: ai/rag/retrieval/retrieve_bns.py
"""

import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
import ollama

# Configuration Constants
EMBEDDING_MODEL = "nomic-embed-text"
COLLECTION_NAME = "lawaid"
# Use absolute path derived from this file's location so it works regardless of CWD
# ai/rag/retrieval/ -> ai/rag/ -> ai/ -> project_root
_RETRIEVAL_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _RETRIEVAL_DIR.parents[2]  # go up: retrieval -> rag -> ai -> project root
DB_PATH = str(_PROJECT_ROOT / "ai" / "rag" / "data" / "chroma_db")
TOP_K = 5


def _extract_explicit_section_numbers(query: str) -> List[int]:
    """
    Extracts explicit section numbers from user query.
    Handles patterns like:
    - Section 303, sec 303, s. 303, §303, § 303
    - BNS Section 303, BNS Sec 303, BNS 303
    - Section 303 of BNS, Section 303 of the Bharatiya Nyaya Sanhita
    - Standalone number query e.g. "303" or "281"
    """
    if not query or not isinstance(query, str):
        return []

    q_clean = query.strip()
    sections = []

    # 1. Explicit section keywords (Section 303, sec 303, §303, etc.)
    p1 = re.findall(r'\b(?:section|sec\.?|s\.|§)\s*(\d{1,3})\b', q_clean, re.I)
    for match in p1:
        try:
            val = int(match)
            if 1 <= val <= 358 and val not in sections:
                sections.append(val)
        except ValueError:
            pass

    # 2. BNS prefixed numbers (BNS 303, BNS Section 303, etc.)
    p2 = re.findall(r'\bbns\s*(?:section|sec\.?|s\.|§)?\s*(\d{1,3})\b', q_clean, re.I)
    for match in p2:
        try:
            val = int(match)
            if 1 <= val <= 358 and val not in sections:
                sections.append(val)
        except ValueError:
            pass

    # 3. Short standalone number query e.g. "303" or "281"
    if not sections and re.match(r'^\s*(\d{1,3})\s*$', q_clean):
        try:
            val = int(q_clean.strip())
            if 1 <= val <= 358:
                sections.append(val)
        except ValueError:
            pass

    return sections


def _extract_offence_keywords(query: str) -> List[str]:
    """
    Extracts core statutory offence terms from query to ensure canonical provision discovery
    (e.g., general theft Section 303 for 'theft').
    """
    if not query or not isinstance(query, str):
        return []

    q_lower = query.lower()
    canonical_offences = [
        "theft", "snatching", "robbery", "dacoity", "extortion",
        "cheating", "forgery", "trespass", "house-breaking", "burglary",
        "murder", "culpable homicide", "hurt", "grievous hurt", "assault",
        "kidnapping", "abduction", "rape", "outraging modesty", "stalking",
        "dowry", "cruelty", "defamation", "affray", "rioting", "unlawful assembly"
    ]
    matched = []
    for off in canonical_offences:
        if re.search(r'\b' + re.escape(off) + r'\b', q_lower):
            matched.append(off)
    return matched


def retrieve(query: str, top_k: int = TOP_K, db_path: str = DB_PATH, collection_name: str = COLLECTION_NAME):
    """
    Performs Hybrid (Exact Metadata + Semantic Vector) retrieval in ChromaDB.
    
    Flow:
    - Explicit section query -> Exact metadata lookup prioritized (distance=0.0)
    - Offence keyword query -> General canonical section surfaced alongside specialized sections
    - Semantic vector similarity -> Ollama nomic-embed-text embedding search
    - Merges and deduplicates results preserving top rank for exact matches
    """
    if not query or not str(query).strip():
        raise ValueError("Query string cannot be empty.")

    # 1. Connect to Persistent ChromaDB
    db_dir = Path(db_path)
    if not db_dir.exists():
        raise FileNotFoundError(f"ChromaDB persistent directory not found at {db_dir.resolve()}")

    try:
        client = chromadb.PersistentClient(path=str(db_dir))
    except Exception as e:
        raise RuntimeError(f"Failed to connect to ChromaDB at {db_dir}: {e}")

    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        raise RuntimeError(f"Collection '{collection_name}' not found in ChromaDB at {db_dir}: {e}")

    retrieved_items = []
    seen_ids = set()

    # Step 1: Detect explicit section numbers & perform exact metadata lookup
    explicit_sections = _extract_explicit_section_numbers(query)
    for sec_num in explicit_sections:
        try:
            exact_res = collection.get(
                where={"section": sec_num},
                include=["documents", "metadatas"]
            )
            e_ids = exact_res.get("ids", [])
            e_docs = exact_res.get("documents", [])
            e_metas = exact_res.get("metadatas", [])

            for idx in range(len(e_ids)):
                d_id = e_ids[idx]
                if d_id in seen_ids:
                    continue
                seen_ids.add(d_id)

                meta = e_metas[idx] if idx < len(e_metas) else {}
                item_dict = dict(meta) if isinstance(meta, dict) else {}
                item_dict.update({
                    "rank": len(retrieved_items) + 1,
                    "id": d_id,
                    "act": meta.get("act", "BNS"),
                    "act_name": meta.get("act_name", "Bharatiya Nyaya Sanhita (BNS), 2023"),
                    "section": meta.get("section", sec_num),
                    "clause": meta.get("clause", ""),
                    "title": meta.get("title", ""),
                    "distance": 0.0,  # Exact section match given highest priority
                    "text": e_docs[idx] if idx < len(e_docs) else "",
                    "retrieval_method": "exact_section_match"
                })
                if not item_dict.get("target_clause_text") and item_dict.get("text"):
                    item_dict["target_clause_text"] = item_dict["text"]
                retrieved_items.append(item_dict)
        except Exception as e:
            print(f"[Exact Section Retrieval Notice] Section {sec_num} metadata query: {e}")

    # Step 2: Canonical Offence Root Section Discovery
    offence_terms = _extract_offence_keywords(query)
    if offence_terms:
        for off_term in offence_terms:
            try:
                title_clean = off_term.capitalize() + "."
                title_res = collection.get(
                    where={"title": title_clean},
                    include=["documents", "metadatas"]
                )
                t_ids = title_res.get("ids", [])
                t_docs = title_res.get("documents", [])
                t_metas = title_res.get("metadatas", [])

                for idx in range(len(t_ids)):
                    d_id = t_ids[idx]
                    if d_id in seen_ids:
                        continue
                    seen_ids.add(d_id)

                    meta = t_metas[idx] if idx < len(t_metas) else {}
                    item_dict = dict(meta) if isinstance(meta, dict) else {}
                    item_dict.update({
                        "rank": len(retrieved_items) + 1,
                        "id": d_id,
                        "act": meta.get("act", "BNS"),
                        "act_name": meta.get("act_name", "Bharatiya Nyaya Sanhita (BNS), 2023"),
                        "section": meta.get("section", ""),
                        "clause": meta.get("clause", ""),
                        "title": meta.get("title", ""),
                        "distance": 0.05,  # High priority canonical title match
                        "text": t_docs[idx] if idx < len(t_docs) else "",
                        "retrieval_method": "canonical_title_match"
                    })
                    if not item_dict.get("target_clause_text") and item_dict.get("text"):
                        item_dict["target_clause_text"] = item_dict["text"]
                    retrieved_items.append(item_dict)
            except Exception:
                pass

    # Step 3: Semantic Vector Search
    fetch_limit = max(top_k, 15) if (explicit_sections or offence_terms) else top_k
    try:
        response = ollama.embed(model=EMBEDDING_MODEL, input=str(query).strip())
        embeddings = response.get("embeddings", [])
        if embeddings:
            query_embedding = embeddings[0]
            vector_res = collection.query(
                query_embeddings=[query_embedding],
                n_results=fetch_limit,
                include=["documents", "metadatas", "distances"]
            )
            v_ids = vector_res.get("ids", [[]])[0]
            v_docs = vector_res.get("documents", [[]])[0]
            v_metas = vector_res.get("metadatas", [[]])[0]
            v_dists = vector_res.get("distances", [[]])[0]

            for idx in range(len(v_ids)):
                d_id = v_ids[idx]
                if d_id in seen_ids:
                    continue
                seen_ids.add(d_id)

                meta = v_metas[idx] if idx < len(v_metas) else {}
                item_dict = dict(meta) if isinstance(meta, dict) else {}
                item_dict.update({
                    "rank": len(retrieved_items) + 1,
                    "id": d_id,
                    "act": meta.get("act", "BNS"),
                    "act_name": meta.get("act_name", "Bharatiya Nyaya Sanhita (BNS), 2023"),
                    "section": meta.get("section", ""),
                    "clause": meta.get("clause", ""),
                    "title": meta.get("title", ""),
                    "distance": float(v_dists[idx]) if idx < len(v_dists) else 0.5,
                    "text": v_docs[idx] if idx < len(v_docs) else "",
                    "retrieval_method": "semantic_vector_search"
                })
                if not item_dict.get("target_clause_text") and item_dict.get("text"):
                    item_dict["target_clause_text"] = item_dict["text"]
                retrieved_items.append(item_dict)
    except Exception as e:
        print(f"[Semantic Vector Search Notice] {e}")

    # Step 4: Re-assign consecutive ranks and return top_k
    for idx, item in enumerate(retrieved_items):
        item["rank"] = idx + 1

    if top_k is not None and isinstance(top_k, int) and top_k > 0:
        if explicit_sections and len(retrieved_items) > top_k:
            exact_count = len([x for x in retrieved_items if x.get("retrieval_method") == "exact_section_match"])
            effective_k = max(top_k, exact_count)
            return retrieved_items[:effective_k]
        return retrieved_items[:top_k]

    return retrieved_items


def main():
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = "Is Section 58(b) bailable?"

    print(f"Executing baseline retrieval for query: '{user_query}' (TOP_K={TOP_K})...\n")
    try:
        results = retrieve(user_query, top_k=TOP_K)
        print("=" * 80)
        print(f"{'Rank':<5} | {'Doc ID':<18} | {'Sec':<5} | {'Clause':<8} | {'Distance':<10} | {'Title'}")
        print("-" * 80)
        for r in results:
            sec_str = str(r['section'])
            cls_str = r['clause'] if r['clause'] else "-"
            print(f"{r['rank']:<5} | {r['id']:<18} | {sec_str:<5} | {cls_str:<8} | {r['distance']:<10.4f} | {r['title']}")
        print("=" * 80)
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
