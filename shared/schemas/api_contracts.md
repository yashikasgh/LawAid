# LawAid API Contracts

Single source of truth for all request/response shapes between
`frontend/lib/api.ts` and `backend/app/routers/`.

---

## Authentication

### POST /auth/register
```json
Request:  { "email": "string", "password": "string", "role": "citizen|police|lawyer" }
Response: { "access_token": "string", "token_type": "bearer" }
```

### POST /auth/login
```json
Request:  { "email": "string", "password": "string", "role": "citizen|police|lawyer" }
Response: { "access_token": "string", "token_type": "bearer" }
```

### GET /auth/me
```
Headers:  Authorization: Bearer <token>
Response: { "id": "uuid", "email": "string", "role": "string" }
```

---

## Legal Incident Analysis (AI RAG Pipeline)

### POST /fir/analyze
Citizens submit their raw incident description. The backend passes it to `run_pipeline()`, which executes Privacy Sanitization -> NER -> Query Generation -> ChromaDB Vector Retrieval -> Reranking -> LLM Grounded Analysis (Groq GPT-OSS 120B).

```json
Request:
{
  "incident": "The accused entered the shop and took a mobile phone without permission."
}

Response (success):
{
  "status": "ok",
  "source": "pipeline | retrieval_fallback | mock",
  "data": {
    "status": "success",
    "sanitized_incident": "The accused entered the shop and took a mobile phone without permission.",
    "privacy_metadata": { "detections": [], "replacement_map": {} },
    "analysis": [
      {
        "offence_type": "Theft",
        "section": "303",
        "clause": "2",
        "title": "Theft",
        "applicability": "supported | uncertain | not_supported",
        "reasoning": "The accused took movable property dishonestly out of possession without consent.",
        "punishment": "Imprisonment up to 3 years, or fine, or both.",
        "bailable": "Non-bailable",
        "cognizable": "Cognizable",
        "court": "Any Magistrate",
        "similarity": 0.85
      }
    ],
    "limitations": [],
    "disclaimer": "Legal analysis provided by LawAid AI is for informational and educational purposes only..."
  }
}
```

---

## BNS Search

### GET /fir/bns/search?query=\<string\>

```json
Response (success):
{
  "status": "ok",
  "source": "rag | mock",
  "results": [
    {
      "rank": 1,
      "section": "318",
      "clause": "",
      "title": "Cheating",
      "text": "Whoever, by deceiving any person...",
      "chapter": "CHAPTER XVII",
      "bailable": "Bailable",
      "cognizable": "Non-Cognizable",
      "similarity": 0.81
    }
  ]
}

Response (low confidence):
{ "status": "insufficient_information", "source": "rag | mock", "results": [] }
```

**Similarity:** float 0–1 (1 = perfect match). Computed as `max(0, 1 - cosine_distance)`.  
**Threshold:** results below 0.30 similarity are filtered out.

---

## FIR Upload

### POST /fir/upload
```
Request:  multipart/form-data  field="file"  (PDF | JPEG | PNG)
Response: { "status": "uploaded", "file_id": "string", "filename": "string" }
```

---

## FIR Understand

### POST /fir/understand
```
Request:  multipart/form-data  field="file"  (PDF | JPEG | PNG)
Response:
{
  "status": "ok",
  "file_id": "string",
  "filename": "string",
  "extracted_text": "string",
  "summary": "string",
  "charges": [
    {
      "section": "string",
      "title": "string",
      "punishment": "string",
      "bailable": "string",
      "reasoning": "string"
    }
  ],
  "rights": ["string"],
  "next_steps": ["string"]
}
```

---

## FIR Generate

### POST /fir/generate
```json
Request:
{
  "complaint": "string",
  "station_code": "PS001",
  "district": "Central",
  "complainant_name": "string"
}
Response:
{
  "fir_id": "FIR/2026/0123",
  "status": "draft_created",
  "sha256_hash": "string",
  "created_at": "ISO-8601 string",
  "station_code": "string",
  "district": "string",
  "pdf_url": null,
  "summary": "string"
}
```

---

## FIR Register

### POST /fir/register
```
Request:  multipart/form-data  field="file"  + query param station_code
Headers:  Authorization: Bearer <token>
Response: { "fir_id": "string", "sha256_hash": "string", "status": "string", "created_at": "datetime" }
```

---

## FIR Verify

### POST /fir/verify?fir_id=\<string\>
```
Request:  multipart/form-data  field="file"
Response: { "verified": true|false, "fir_id": "string" }
```

---

## Duplicate Check

### POST /fir/check-duplicate
```json
Request:  { "complaint_text": "string" }
Response: { "is_duplicate": false, "similar_fir_id": null, "similarity_score": 0.0 }
```
> Stub — real version will use sentence-transformer embeddings.

---

## Chat  *(stubs)*

### POST /chat/message
```json
Request:  { "session_id": "string", "message": "string" }
Response: { "reply": "string" }
```

### GET /chat/history/\<session_id\>
```json
Response: { "history": [] }
```

---

## Police  *(stubs)*

### POST /police/transcribe  —  multipart audio field
### POST /police/validate-fir  —  fir fields JSON body
### POST /police/approve-fir  —  `{ "fir_draft_id": "string" }`

---

## Health

### GET /health  →  `{ "status": "ok" }`
### GET /health/db  →  `{ "status": "ok" }`
