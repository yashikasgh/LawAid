import json
import os
import sys
import time
from pathlib import Path

import chromadb
import ollama
from tqdm import tqdm

# Configuration Constants
EMBEDDING_MODEL = "nomic-embed-text"
COLLECTION_NAME = "lawaid"
DB_PATH = "ai/rag/data/chroma_db"
DOCUMENTS_PATH = "ai/rag/data/processed/documents.json"
BATCH_SIZE = 25


def get_embeddings_for_batch(batch_texts, model=EMBEDDING_MODEL):
    """
    Generates embeddings using Ollama's true batch embedding API.
    If the batch request fails, falls back to item-by-item generation to isolate malformed documents.
    Returns: (list_of_embeddings, list_of_failed_indices)
    """
    try:
        response = ollama.embed(model=model, input=batch_texts)
        embeddings = response.get("embeddings", [])
        if len(embeddings) == len(batch_texts):
            return embeddings, []
        else:
            raise ValueError(
                f"Mismatch: expected {len(batch_texts)} embeddings, got {len(embeddings)}"
            )
    except Exception as batch_err:
        # Fall back to document-by-document processing
        embeddings = []
        failed_indices = []
        for idx, text in enumerate(batch_texts):
            try:
                single_res = ollama.embed(model=model, input=text)
                single_emb = single_res.get("embeddings", [[]])[0]
                embeddings.append(single_emb)
            except Exception:
                embeddings.append(None)
                failed_indices.append(idx)
        return embeddings, failed_indices


def build_embeddings():
    start_time = time.time()
    print("=" * 60)
    print("LawAid RAG - Embedding Generation Pipeline")
    print("=" * 60)
    print(f"Embedding Model  : {EMBEDDING_MODEL}")
    print(f"Collection Name  : {COLLECTION_NAME}")
    print(f"Database Path    : {DB_PATH}")
    print(f"Documents Path   : {DOCUMENTS_PATH}")
    print(f"Batch Size       : {BATCH_SIZE}")
    print("=" * 60)

    # 1. Load documents.json
    docs_file = Path(DOCUMENTS_PATH)
    if not docs_file.exists():
        print(f"Error: Document file not found at {DOCUMENTS_PATH}")
        sys.exit(1)

    with open(docs_file, "r", encoding="utf-8") as f:
        documents = json.load(f)

    total_docs = len(documents)
    print(f"Loaded {total_docs} documents from {DOCUMENTS_PATH}")

    # 2. Initialize Persistent ChromaDB Client
    db_dir = Path(DB_PATH)
    db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_dir))

    # Get or create collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    # Track existing IDs for accurate insert/update metrics
    existing_ids = set(collection.get(include=[])["ids"])

    processed = 0
    inserted = 0
    updated = 0
    skipped = 0
    failures = 0

    # 3. Process documents in batches
    for i in tqdm(range(0, total_docs, BATCH_SIZE), desc="Generating Embeddings"):
        batch = documents[i : i + BATCH_SIZE]
        batch_ids = [doc["id"] for doc in batch]
        batch_texts = [doc["text"] for doc in batch]
        batch_metadatas = [doc.get("metadata", {}) for doc in batch]

        embeddings, failed_indices = get_embeddings_for_batch(
            batch_texts, model=EMBEDDING_MODEL
        )

        valid_ids = []
        valid_texts = []
        valid_metadatas = []
        valid_embeddings = []

        for idx, emb in enumerate(embeddings):
            doc_id = batch_ids[idx]
            if idx in failed_indices or emb is None:
                failures += 1
            else:
                valid_ids.append(doc_id)
                valid_texts.append(batch_texts[idx])
                valid_metadatas.append(batch_metadatas[idx])
                valid_embeddings.append(emb)

                if doc_id in existing_ids:
                    updated += 1
                else:
                    inserted += 1

        if valid_ids:
            collection.upsert(
                ids=valid_ids,
                documents=valid_texts,
                metadatas=valid_metadatas,
                embeddings=valid_embeddings,
            )
            existing_ids.update(valid_ids)

        processed += len(batch)

    total_time = time.time() - start_time

    # 4. Validation
    print("\n" + "=" * 60)
    print("Running Validation Checks...")
    print("=" * 60)

    # 4.1 Collection count == documents.json count
    coll_count = collection.count()
    assert (
        coll_count == total_docs
    ), f"Validation Failed: collection count ({coll_count}) != documents count ({total_docs})"
    print(
        f"[VALIDATION PASSED] Collection count ({coll_count}) matches documents.json count ({total_docs})."
    )

    # 4.2 Unique IDs
    ids_in_db = collection.get(include=[])["ids"]
    assert len(ids_in_db) == len(
        set(ids_in_db)
    ), "Validation Failed: Duplicate IDs found in ChromaDB collection!"
    print(
        f"[VALIDATION PASSED] All {len(ids_in_db)} document IDs in ChromaDB are unique."
    )

    # 4.3 Embeddings presence & dimension
    sample = collection.get(include=["embeddings"], limit=1)
    sample_embeddings = sample.get("embeddings")
    assert (
        sample_embeddings is not None and len(sample_embeddings) > 0
    ), "Validation Failed: No embeddings found in collection!"
    embedding_dim = len(sample_embeddings[0])
    assert embedding_dim > 0, "Validation Failed: Embedding dimension is 0!"
    print(
        f"[VALIDATION PASSED] Verified embeddings are present for stored documents. Dimension: {embedding_dim}."
    )

    # 4.4 Metadata preserved exactly
    sample_doc = documents[0]
    sample_id = sample_doc["id"]
    db_item = collection.get(ids=[sample_id], include=["metadatas"])
    db_metadata = db_item["metadatas"][0]
    expected_metadata = sample_doc.get("metadata", {})
    for key, val in expected_metadata.items():
        assert (
            db_metadata.get(key) == val
        ), f"Validation Failed for metadata key '{key}': expected '{val}', got '{db_metadata.get(key)}'"
    print(
        f"[VALIDATION PASSED] Preserved every metadata field exactly for sample document '{sample_id}'."
    )

    # 5. Final Execution Summary
    print("\n" + "=" * 60)
    print("EMBEDDING PIPELINE EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Processed Documents     : {processed}")
    print(f"Inserted Documents      : {inserted}")
    print(f"Updated Documents       : {updated}")
    print(f"Skipped Documents       : {skipped}")
    print(f"Failures                : {failures}")
    print(f"Total Execution Time    : {total_time:.2f} seconds")
    print(f"Embedding Model         : {EMBEDDING_MODEL}")
    print(f"Embedding Dimension     : {embedding_dim}")
    print(f"Batch Size              : {BATCH_SIZE}")
    print(f"Database Location       : {Path(DB_PATH).resolve()}")
    print(
        "Embedding Implementation: True Batch Embedding (ollama.embed API with list input)"
    )
    print("=" * 60)


if __name__ == "__main__":
    build_embeddings()
