# Lawyer Module API Handoff

All routes require the existing authenticated Lawyer session or bearer token. A case is visible only to its owning lawyer; inaccessible case IDs return `404`.

Base path: `/api/lawyer` (the same routes are also available without `/api`).

| Method | Route | Response/use |
|---|---|---|
| GET | `/cases/{caseId}` | Case metadata |
| GET/POST | `/cases/{caseId}/documents` | Existing document list/upload (multipart `files`); upload initially returns `processing`, then polling returns per-page `extraction_details` and `structured_extraction` when parsing completes |
| GET | `/cases/{caseId}/documents/metrics` | Real document/page/entity/status overview counts |
| POST | `/cases/{caseId}/documents/{documentId}/retry` | Retry parsing |
| DELETE | `/cases/{caseId}/documents/{documentId}` | Delete the GridFS file and metadata. Dependent analysis is marked `needs_review`; generated dependent timeline events are removed and edited ones are detached/marked for review. |
| GET | `/cases/{caseId}/documents/{documentId}/download` | Authenticated document download |
| POST | `/cases/{caseId}/analyze` | Persist source-linked extraction and timeline candidates |
| POST | `/cases/{caseId}/documents/analyze` | Backward-compatible alias for the canonical analyze route |
| GET/PATCH | `/cases/{caseId}/analysis` | Fetch/save the complete editable analysis payload |
| GET | `/cases/{caseId}/timeline?event_type=&source_document_id=&date_from=&date_to=&order=oldest` | Events, sorted chronologically and filterable by type, source, and ISO date range |
| PATCH | `/cases/{caseId}/timeline/{eventId}` | Patch `date`, `time`, `title`, `description`, `event_type` |
| GET/PATCH | `/cases/{caseId}/summary` | Fetch/save `executive_summary` and `current_stage` |
| POST | `/cases/{caseId}/export` | Download a PDF; see options below |

`POST /export` accepts `include_executive_summary`, `include_timeline`, `include_key_facts`, `include_bns_sections`, and `include_original_documents` booleans (all default to `true`). It returns `application/pdf`.

Analysis always marks heuristic extraction as `needs_review` and attaches a source object with document ID/name/excerpt. BNS sections are emitted only when an uploaded document explicitly names them; the backend does not infer legal provisions from unsupported facts.

PDF extraction is page-by-page: usable native text is retained, otherwise the server renders the page at the configured OCR DPI and invokes Tesseract with `TESSERACT_LANGUAGES` (default `eng+hin`). A document only reaches `parsed` after every page yields usable text. `structured_extraction` preserves raw and normalized text plus rule-derived FIR fields, explicit sections, snippets and page references; absent or ambiguous fields remain empty and must be reviewed. If Tesseract or its language packs are unavailable, the document enters `failed` with an actionable parser error; it is never reported as successfully parsed with empty text.

The original-documents export appendix is an authenticated package index (filename and processing status), not an embedded copy of original files. Use the authenticated download endpoint for originals.
