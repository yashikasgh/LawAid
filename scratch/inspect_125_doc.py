import chromadb
import json

client = chromadb.PersistentClient(path="ai/rag/data/chroma_db")
coll = client.get_collection("lawaid")

# Fetch all ids and search for 125
all_data = coll.get(include=["metadatas", "documents"])
ids = all_data["ids"]
metas = all_data["metadatas"]
docs = all_data["documents"]

matching = []
for doc_id, meta, doc in zip(ids, metas, docs):
    if "125" in str(meta.get("section")) or "125" in doc_id:
        matching.append((doc_id, meta, doc))

print(f"Total matching 125 documents found: {len(matching)}")
for doc_id, meta, doc in matching:
    print(f"\nDocument ID: {doc_id}")
    print(f"Metadata: {json.dumps(meta, indent=2)}")
    print(f"Document Text:\n{doc}")
