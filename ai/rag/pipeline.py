"""pipeline.py — LawAid End-to-End Analysis Pipeline.

Located at: ai/rag/pipeline.py
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure project root and analysis/retrieval packages are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ANALYSIS_DIR = PROJECT_ROOT / "ai" / "rag" / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

RETRIEVAL_DIR = PROJECT_ROOT / "ai" / "rag" / "retrieval"
if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_DIR))

from ai.security.privacy_gateway import sanitize_text
from ai.rag.ner.ner_extractor import extract_entities
from ai.rag.retrieval.query_generator import generate_queries
from ai.rag.retrieval.retrieve_bns import retrieve
from ai.rag.retrieval.reranker import rerank_candidates, rerank_section_candidates
from ai.rag.analysis.legal_analyzer import analyze_incident, GroqLLMClient, MultiProviderLLMFailoverClient, LLMClient, Workload
from ai.rag.analysis.context_builder import _extract_clause_parts, _parse_schedule_1


LEGAL_DISCLAIMER = (
    "Legal analysis provided by LawAid AI is for informational and educational purposes only. "
    "It does not constitute formal legal advice or substitute for consultation with a qualified legal professional."
)


def _build_retrieval_fallback_analysis(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build deterministic, grounded fallback analysis cards from retrieved ChromaDB/RRF candidates when LLM reasoning is unavailable."""
    fallback_items = []
    seen_sections = set()

    for cand in candidates:
        sec = str(cand.get("section", "")).strip()
        if not sec:
            continue

        # Deduplicate sibling clauses for cleaner citizen presentation
        if sec in seen_sections:
            continue
        seen_sections.add(sec)

        title = str(cand.get("title", "")).strip()
        clause = str(cand.get("clause", "")).strip()
        doc_id = cand.get("id") or f"bns_{sec}"

        sched_1 = cand.get("schedule_1", {})
        if not isinstance(sched_1, dict):
            sched_1 = {}

        offence_name = sched_1.get("offence") or title or f"Section {sec}"
        punishment_val = sched_1.get("punishment") or "Not available in retrieved source"
        bailable_val = sched_1.get("bailable") or "Not available in retrieved source"
        cognizable_val = sched_1.get("cognizable") or "Not available in retrieved source"
        court_val = sched_1.get("court") or "Not available in retrieved source"

        sec_def = cand.get("section_definition") or cand.get("target_clause_text") or cand.get("text", "")
        clean_def = sec_def.strip() if sec_def else title
        if len(clean_def) > 300:
            clean_def = clean_def[:297] + "..."

        reasoning = (
            f"Relevant BNS provision retrieved from legal database: {title} (§{sec}). "
            f"Statutory text: \"{clean_def}\". "
            "Further factual investigation required to determine statutory applicability."
        )

        distance = float(cand.get("distance", 1.0))
        similarity = round(max(0.0, 1.0 - distance), 4)

        fallback_items.append({
            "offence_type": offence_name,
            "section": sec,
            "clause": clause,
            "title": title,
            "unit_type": "core_definition",
            "applicability": "uncertain",
            "statutory_structure": {
                "structural_unit_type": "core_definition",
                "core_elements": [title],
                "conditional_elements": [],
                "aggravated_elements": [],
                "mitigating_elements": []
            },
            "prerequisite_evidence": [
                {
                    "requirement": title,
                    "requirement_type": "core",
                    "evidence_status": "missing",
                    "incident_evidence": "Retrieved from BNS database.",
                    "reason": "Vector search match candidate."
                }
            ],
            "core_elements": [title],
            "conditional_elements": [],
            "satisfied_elements": [],
            "missing_elements": [title],
            "contradicted_elements": [],
            "relationship_analysis": {
                "relationship_type": "none",
                "related_candidate": "",
                "reason": "Retrieved provision candidate."
            },
            "reasoning": reasoning,
            "explanation": reasoning,
            "punishment": punishment_val,
            "bailable": bailable_val,
            "cognizable": cognizable_val,
            "court": court_val,
            "similarity": similarity,
            "evidence": [
                {
                    "document_id": doc_id,
                    "section": sec,
                    "clause": clause,
                    "rank": cand.get("rank", 0)
                }
            ]
        })

    return fallback_items


def pack_candidates_by_section(
    reranked_candidates: List[Dict[str, Any]],
    base_prompt_tokens: int = 700,
    min_output_tokens: int = 3500,
    max_token_budget: int = 6700
) -> Dict[str, Any]:
    """Group reranked clause documents by parent legal section and dynamically pack complete section groups

    into the LLM context within safe token budget limits.

    Args:
        reranked_candidates (list): RRF-ordered list of retrieved clause document dicts.
        base_prompt_tokens (int): Overhead tokens for system instructions and incident facts.
        min_output_tokens (int): Required completion token budget.
        max_token_budget (int): Hard safety limit for provider request (e.g. 6,700 tokens for Groq/Gemini).

    Returns:
        dict: {
            "packed_candidates": list of clause document dicts preserving RRF rank order,
            "packed_sections": list of section numbers included,
            "capacity_reached": bool indicating if packing stopped due to token limit,
            "total_tokens_estimated": int total estimated tokens packed
        }
    """
    safe_budget = max_token_budget - min_output_tokens
    current_tokens = base_prompt_tokens

    # Step 1: Group sibling clause documents by parent section while preserving first-seen RRF rank order
    section_groups: Dict[str, List[Dict[str, Any]]] = {}
    section_order: List[str] = []

    for cand in reranked_candidates:
        sec = str(cand.get("section", "")).strip() or "unknown"
        if sec not in section_groups:
            section_groups[sec] = []
            section_order.append(sec)
        section_groups[sec].append(cand)

    packed_candidates: List[Dict[str, Any]] = []
    packed_sections: List[str] = []
    capacity_reached = False

    # Step 2: Pack sections in RRF rank order, accounting tokens for compact section representation
    for sec in section_order:
        sibling_docs = section_groups[sec]

        # Calculate compact section token footprint (1 parent header + sum of sub-clause snippets)
        sec_title = sibling_docs[0].get("title", "")
        sec_def_text = sibling_docs[0].get("section_definition", "")
        parent_header = f"{sec_title} {sec_def_text}".strip()

        clause_tokens_sum = 0
        for doc in sibling_docs:
            ctext = doc.get("target_clause_text") or doc.get("text", "")
            clause_tokens_sum += (len(ctext) // 4) + 25

        sec_compact_tokens = (len(parent_header) // 4) + 30 + clause_tokens_sum

        if current_tokens + sec_compact_tokens <= safe_budget:
            packed_candidates.extend(sibling_docs)
            packed_sections.append(sec)
            current_tokens += sec_compact_tokens
        else:
            # Entire section group cannot fit within safe_budget. Mark capacity_reached.
            capacity_reached = True

            # Check if packing at least the primary (highest-ranked) clause of this section fits safely.
            primary_doc = sibling_docs[0]
            primary_text = primary_doc.get("target_clause_text") or primary_doc.get("text", "")
            primary_tokens = (len(parent_header) // 4) + 30 + (len(primary_text) // 4) + 25

            if current_tokens + primary_tokens <= safe_budget:
                packed_candidates.append(primary_doc)
                packed_sections.append(sec)
                current_tokens += primary_tokens
            # Continue scanning subsequent sections to see if smaller ranked sections fit into remaining budget

    # Safe Minimum Fallback: Ensure at least the top RRF candidate is included if reranked candidates exist
    if not packed_candidates and reranked_candidates:
        packed_candidates = [reranked_candidates[0]]
        packed_sections = [str(reranked_candidates[0].get("section", ""))]

    return {
        "packed_candidates": packed_candidates,
        "packed_sections": packed_sections,
        "capacity_reached": capacity_reached,
        "total_tokens_estimated": current_tokens
    }


def run_pipeline(
    raw_incident: str,
    llm_client: Optional[LLMClient] = None,
    top_k_retrieval: int = 20,
    top_k_rerank: int = 15,
    analysis_candidate_limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes the end-to-end LawAid RAG Legal Analysis Pipeline.

    Flow:
        Raw incident
        → Privacy Gateway (local sanitization before any cloud call)
        → NER (entity extraction on sanitized text)
        → Query Generator (retrieval query formulation)
        → ChromaDB Vector Retrieval (Top-20 per query)
        → Reranker (deterministic RRF reranking to Top-15 candidate pool)
        → Analysis Context Window (Top-7 candidates passed to LLM)
        → Context Builder & Legal Analyzer (grounded analysis via LLM)
        → Final Structured Result

    Args:
        raw_incident (str): Original input incident description text.
        llm_client (LLMClient, optional): Swappable LLM generation backend instance.
            If None, resolves to GroqLLMClient() once at the pipeline boundary.
        top_k_retrieval (int): Number of candidates to retrieve per query from ChromaDB (default 20).
        top_k_rerank (int): Number of top reranked candidates in candidate pool (default 15).
        analysis_candidate_limit (int): Maximum candidates passed to LLM analysis context (default 7).

    Returns:
        dict: Structured analysis result containing:
            - status
            - sanitized_incident
            - privacy_metadata (detections, replacement_map)
            - analysis (grounded legal analysis list)
            - limitations
            - disclaimer (non-binding legal advisory statement)
            - reranked_candidates (full RRF reranked candidate pool)
    """
    # 1. Resolve LLM client ONCE at the pipeline boundary
    if llm_client is None:
        llm_client = MultiProviderLLMFailoverClient()

    # 2. Privacy Gateway: Local sanitization boundary
    privacy_res = sanitize_text(raw_incident)
    sanitized_text = privacy_res.get("sanitized_text", "")

    # 3. NER Entity Extraction
    ner_result = extract_entities(sanitized_text)

    # 4. Query Generation
    query_output = generate_queries(ner_result, llm_client=llm_client)
    raw_queries = query_output.get("queries", [])
    queries = [q["query"] for q in raw_queries if isinstance(q, dict) and "query" in q]

    # Fallback to sanitized raw text if no queries generated
    if not queries and sanitized_text:
        queries = [sanitized_text]

    # 5. ChromaDB Multi-Query Retrieval
    all_retrieved_candidates: List[Dict[str, Any]] = []
    for q_str in queries:
        try:
            retrieved = retrieve(query=q_str, top_k=top_k_retrieval)
            for item in retrieved:
                doc_id = item.get("id")
                if not doc_id:
                    continue
                item_copy = dict(item)
                item_copy["query"] = q_str
                all_retrieved_candidates.append(item_copy)
        except Exception:
            continue

    # 6. Section-Level RRF Reranking across candidate pool
    if analysis_candidate_limit is not None:
        # Legacy/Test explicit candidate limit path
        reranked_candidates = rerank_candidates(
            incident_input=ner_result,
            candidates=all_retrieved_candidates,
            top_k=top_k_rerank
        )
    else:
        # Parent Section-Level RRF Reranking (Unbounded RRF Pool, Section Grouped)
        section_reranked = rerank_section_candidates(
            candidates=all_retrieved_candidates,
            top_k=None
        )
        # Flatten section candidate records in section-RRF rank order while preserving all child clause records
        reranked_candidates = []
        for sec_rec in section_reranked:
            reranked_candidates.extend(sec_rec.get("clauses", []))

    # Enrich reranked_candidates with clause text and Schedule 1 metadata for clean fallback presentation
    for cand in reranked_candidates:
        raw_doc_text = cand.get("text", "")
        clause_str = cand.get("clause", "") or ""
        clause_parts = _extract_clause_parts(raw_doc_text, clause_str)
        schedule_1_raw = cand.get("schedule_1") or _parse_schedule_1(raw_doc_text)

        cand["target_clause_text"] = clause_parts["target_clause_text"] or cand.get("target_clause_text") or raw_doc_text
        cand["section_definition"] = clause_parts["section_definition"] or cand.get("section_definition", "")
        if isinstance(schedule_1_raw, dict) and schedule_1_raw:
            cand["schedule_1"] = {
                "offence": schedule_1_raw.get("offence", ""),
                "punishment": schedule_1_raw.get("punishment", ""),
                "cognizable": schedule_1_raw.get("cognizable", ""),
                "bailable": schedule_1_raw.get("bailable", ""),
                "court": schedule_1_raw.get("court", "") or schedule_1_raw.get("triable_by", "")
            }

    # 7. Analysis Context Limit: Select candidates for LLM prompt
    if analysis_candidate_limit is not None:
        analysis_candidates = (
            reranked_candidates[:analysis_candidate_limit]
            if len(reranked_candidates) > analysis_candidate_limit
            else reranked_candidates
        )
    else:
        # Parent Section-Level Dynamic Token Budget Candidate Selection
        pack_res = pack_candidates_by_section(
            reranked_candidates=reranked_candidates,
            base_prompt_tokens=700,
            min_output_tokens=3500,
            max_token_budget=6700
        )
        analysis_candidates = pack_res["packed_candidates"]

    # 8. Legal Analysis (Internal context building & evidence grounding)
    analysis_result = analyze_incident(
        ner_result=ner_result,
        retrieval_result=analysis_candidates,
        llm_client=llm_client
    )

    analysis_items = analysis_result.get("analysis", [])
    pipeline_source = "pipeline"

    # If LLM generation fails or returns empty analysis, use deterministic retrieval fallback
    if not analysis_items or analysis_result.get("status") == "analysis_unavailable":
        fallback_analysis = _build_retrieval_fallback_analysis(reranked_candidates)
        if fallback_analysis:
            analysis_items = fallback_analysis
            pipeline_source = "retrieval_fallback"

    # 9. Return Final Pipeline Structure
    return {
        "status": analysis_result.get("status", "success"),
        "source": pipeline_source,
        "sanitized_incident": sanitized_text,
        "privacy_metadata": {
            "detections": privacy_res.get("detections", []),
            "replacement_map": privacy_res.get("replacement_map", {})
        },
        "analysis": analysis_items,
        "limitations": analysis_result.get("limitations", []),
        "disclaimer": LEGAL_DISCLAIMER,
        "reranked_candidates": reranked_candidates
    }


def run_chat_pipeline(
    raw_message: str,
    llm_client: Optional[LLMClient] = None
) -> Dict[str, Any]:
    """
    Executes the LawAid RAG Pipeline for Conversational Legal Chat.

    Flow:
        Raw chat query
        → Grounded RAG Pipeline (run_pipeline)
        → Section-based Deduplication & Grouping
        → Plain-language Conversational Synthesis
        → Sanitization & Safety Verification

    Args:
        raw_message (str): Input user chat query.
        llm_client (LLMClient, optional): LLM generation client instance.

    Returns:
        dict: Conversational response containing:
            - status ("ok")
            - sanitized_incident
            - reply (conversational plain-language answer)
            - sections (list of clean BNS section titles)
            - disclaimer (LEGAL_DISCLAIMER)
    """
    import json
    import re

    if llm_client is None:
        llm_client = MultiProviderLLMFailoverClient()

    # 1. Execute grounded RAG pipeline
    pipeline_res = run_pipeline(raw_incident=raw_message, llm_client=llm_client)

    if pipeline_res.get("status") == "analysis_unavailable":
        return {
            "status": "analysis_unavailable",
            "sanitized_incident": pipeline_res.get("sanitized_incident", raw_message),
            "reply": "AI legal analysis is temporarily unavailable. The legal knowledge base was reached successfully, but the reasoning service is currently unavailable. Please try again shortly.",
            "sections": [],
            "disclaimer": LEGAL_DISCLAIMER
        }

    grounded_analysis = pipeline_res.get("analysis", [])
    sanitized_text = pipeline_res.get("sanitized_incident", raw_message)
    limitations = pipeline_res.get("limitations", [])

    # 2. Section-based Deduplication & Grouping
    grouped_sections_map = {}
    for item in grounded_analysis:
        sec = str(item.get("section", "")).strip()
        if not sec:
            continue

        raw_title = str(item.get("title", "")).strip()
        raw_offence = str(item.get("offence_type", "")).strip()

        if raw_offence == "reranked_candidates":
            raw_offence = ""

        title_clean = raw_title or raw_offence or f"Section {sec}"
        title_clean = re.sub(r'[\s\.\,\;]+$', '', title_clean)

        applicability = item.get("applicability", "supported")
        reasoning = str(item.get("reasoning", "")).strip()

        if sec not in grouped_sections_map:
            grouped_sections_map[sec] = {
                "section": sec,
                "title": title_clean,
                "applicability": applicability,
                "reasonings": []
            }

        # Update applicability priority: supported > uncertain > not_supported
        curr_app = grouped_sections_map[sec]["applicability"]
        if applicability == "supported" or (applicability == "uncertain" and curr_app == "not_supported"):
            grouped_sections_map[sec]["applicability"] = applicability

        if title_clean and title_clean not in grouped_sections_map[sec]["title"]:
            grouped_sections_map[sec]["title"] += f" / {title_clean}"

        if reasoning and reasoning not in grouped_sections_map[sec]["reasonings"]:
            grouped_sections_map[sec]["reasonings"].append(reasoning)

    structured_chat_context = []
    formatted_sections = []

    for sec, sec_info in grouped_sections_map.items():
        clean_title = re.sub(r'[\s\.\,\;]+$', '', sec_info["title"])
        clean_title = re.sub(r'\s*/\s*', ' / ', clean_title)
        label = f"Section {sec}: {clean_title}"

        # ONLY include supported sections in the recommended sections list
        if sec_info["applicability"] == "supported":
            formatted_sections.append(label)

        structured_chat_context.append({
            "section": f"Section {sec}",
            "title": clean_title,
            "overall_applicability": sec_info["applicability"],
            "legal_analysis_notes": sec_info["reasonings"]
        })

    # 3. Conversational Synthesis Prompt
    prompt = (
        "You are LawAid's compassionate, plain-language Legal AI Assistant specializing in Indian criminal law "
        "(Bharatiya Nyaya Sanhita, BNS 2023 & Bharatiya Nagarik Suraksha Sanhita, BNSS 2023).\n"
        "Summarize the grounded legal analysis below for the user in a clear, empathetic, conversational response.\n\n"
        "STRICT CONSTRAINTS:\n"
        "1. Base your legal explanations ONLY on the provided GROUNDED BNS ANALYSIS data.\n"
        "2. Refer to BNS sections strictly as 'Section <number>' or 'BNS Section <number>' (e.g., Section 303, Section 329). NEVER mention or introduce Indian Penal Code (IPC) sections.\n"
        "3. Expand BNS strictly as 'Bharatiya Nyaya Sanhita, 2023' and BNSS strictly as 'Bharatiya Nagarik Suraksha Sanhita, 2023'. NEVER expand BNS as 'Bihar National Security'.\n"
        "4. Output strictly natural, plain-language legal guidance for a citizen. NEVER expose internal pipeline terms, implementation labels, or metadata such as 'reranked_candidates', 'document_id', 'vector distance', 'candidate', 'score', or 'raw metadata'.\n"
        "5. Present multiple retrieved aspects of the same section (e.g. Criminal Trespass and House-trespass under Section 329) as a single coherent section discussion, explaining its scope rather than creating separate duplicate paragraphs.\n"
        "6. RECOMMENDATION RESTRICTION: When advising what sections to register or report to the police (e.g., 'ask police to register under...'), mention ONLY sections whose overall_applicability is 'supported'. NEVER recommend or advise registering under any section marked 'uncertain' or 'not_supported'.\n"
        "7. EXPLAINING UNCERTAIN OR NOT SUPPORTED PROVISIONS: If a section is marked 'uncertain' or 'not_supported', explain clearly why it is not established or what missing facts/intents would be required (e.g. unstated intent to commit an offence, unstated initial lawful possession, or unstated compound conditions). Do NOT assert that it definitely applies.\n"
        "8. STATUTORY CONDITIONS & PROVISOS: For provisions with special penalty clauses or provisos (such as theft under 5,000 rupees), do NOT state that a single threshold (like property value) automatically triggers the provision. Explain generically that the statutory proviso requires meeting all conjunctive conditions (e.g. value under 5,000 rupees, first conviction status, and return/restoration of property).\n"
        "9. Do NOT invent or hallucinate missing facts or legal section numbers.\n"
        "10. Do NOT present yourself as a lawyer or provide formal legal representation.\n"
        "11. Return ONLY valid JSON matching this schema:\n"
        '{\n  "reply": "string (conversational response text)"\n}\n\n'
        f"USER QUERY: {sanitized_text}\n\n"
        f"GROUNDED BNS ANALYSIS:\n{json.dumps(structured_chat_context, indent=2)}\n\n"
        f"LIMITATIONS & NOTES:\n{json.dumps(limitations, indent=2)}\n"
    )

    bot_reply = ""
    try:
        raw_llm_out = llm_client.generate(prompt, workload=Workload.LEGAL_CHAT)
        if raw_llm_out:
            cleaned = raw_llm_out.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            parsed = json.loads(cleaned)
            bot_reply = parsed.get("reply", "")
    except Exception:
        bot_reply = ""

    # 4. Fallback if LLM synthesis returns empty
    if not bot_reply:
        lines = ["Based on the grounded legal analysis under the Bharatiya Nyaya Sanhita, 2023 (BNS):"]
        if structured_chat_context:
            supported_items = [i for i in structured_chat_context if i.get("overall_applicability") == "supported"]
            uncertain_items = [i for i in structured_chat_context if i.get("overall_applicability") != "supported"]

            if supported_items:
                lines.append("Applicable Provisions to Register:")
                for item in supported_items:
                    sec_name = item.get("section")
                    t_name = item.get("title")
                    notes = " ".join(item.get("legal_analysis_notes", []))
                    lines.append(f"- {sec_name} ({t_name}): Supported. {notes}")

            if uncertain_items:
                lines.append("Provisions requiring further factual clarification (not directly applicable without further facts):")
                for item in uncertain_items:
                    sec_name = item.get("section")
                    t_name = item.get("title")
                    app = item.get("overall_applicability")
                    notes = " ".join(item.get("legal_analysis_notes", []))
                    lines.append(f"- {sec_name} ({t_name}): Status is {app}. {notes}")
        else:
            lines.append("No specific BNS provisions could be confirmed from the facts provided. Please provide more concrete details about what occurred.")

        bot_reply = "\n\n".join(lines)

    # 5. Strict post-processing sanitization filter
    bot_reply = re.sub(r'\(?reranked_candidates\)?', '', bot_reply, flags=re.IGNORECASE)
    bot_reply = re.sub(r'\bdocument_id\b', '', bot_reply, flags=re.IGNORECASE)
    bot_reply = re.sub(r'\bcandidate_id\b', '', bot_reply, flags=re.IGNORECASE)

    if "Bihar National Security" in bot_reply:
        bot_reply = bot_reply.replace("Bihar National Security", "Bharatiya Nyaya Sanhita")

    bot_reply = re.sub(r'\bIPC\b', 'BNS', bot_reply)
    bot_reply = re.sub(r'Indian Penal Code', 'Bharatiya Nyaya Sanhita, 2023', bot_reply, flags=re.IGNORECASE)

    bot_reply = re.sub(r'  +', ' ', bot_reply).strip()

    return {
        "status": "ok",
        "sanitized_incident": sanitized_text,
        "reply": bot_reply,
        "sections": formatted_sections,
        "disclaimer": LEGAL_DISCLAIMER
    }

