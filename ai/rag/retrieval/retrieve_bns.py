"""retrieve_bns.py — Baseline vector retrieval for LawAid RAG.

Located at: ai/rag/retrieval/retrieve_bns.py
"""

import sys
import os
from pathlib import Path
import chromadb
import ollama

# Configuration Constants
EMBEDDING_MODEL = "nomic-embed-text"
COLLECTION_NAME = "lawaid"
DB_PATH = "ai/rag/data/chroma_db"
TOP_K = 5


def retrieve(query: str, top_k: int = TOP_K, db_path: str = DB_PATH, collection_name: str = COLLECTION_NAME):
    """
    Performs baseline vector similarity search in ChromaDB using Ollama embeddings.
    
    Returns a list of dictionaries, each containing:
    - rank: int (1..top_k)
    - id: str
    - section: int or str
    - clause: str
    - title: str
    - distance: float
    - text: str
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

    # 2. Embed query using Ollama
    try:
        response = ollama.embed(model=EMBEDDING_MODEL, input=str(query).strip())
        embeddings = response.get("embeddings", [])
        if not embeddings:
            raise ValueError("Ollama returned empty embeddings response.")
        query_embedding = embeddings[0]
    except Exception as e:
        raise RuntimeError(f"Ollama embedding failed for model '{EMBEDDING_MODEL}': {e}")

    # 3. Query ChromaDB collection
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        raise RuntimeError(f"ChromaDB query failed: {e}")

    # 4. Format and return results
    retrieved_items = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for idx in range(len(ids)):
        meta = metadatas[idx] if idx < len(metadatas) else {}
        retrieved_items.append({
            "rank": idx + 1,
            "id": ids[idx],
            "section": meta.get("section", ""),
            "clause": meta.get("clause", ""),
            "title": meta.get("title", ""),
            "distance": float(distances[idx]) if idx < len(distances) else 0.0,
            "text": docs[idx] if idx < len(docs) else ""
        })

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
