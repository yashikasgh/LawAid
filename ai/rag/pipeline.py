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

        if sec == "303":
            punishment_val = (
                "General/First Conviction: Imprisonment of either description up to 3 years, or fine, or both. "
                "Repeat Conviction (second or subsequent): Rigorous imprisonment for 1 to 5 years, and fine. "
                "Special Proviso (first conviction where stolen property value is less than 5,000 rupees and property/value is restored): Community service."
            )
            cognizable_val = "Cognizable for general theft. Non-cognizable if special proviso applies (value < 5,000 rupees & restored for first conviction)."
            bailable_val = "Non-bailable for general theft. Bailable if special proviso applies (value < 5,000 rupees & restored for first conviction)."
            court_val = "Any Magistrate."

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
    from ai.rag.analysis.legal_analyzer import construct_analysis_prompt, estimate_tokens
    sample_static_prompt = construct_analysis_prompt({"incident": {}, "legal_context": []})
    actual_static_tokens = estimate_tokens(sample_static_prompt) + 200

    # Derive real prompt overhead dynamically while preserving explicit overrides for testing
    effective_base_tokens = max(base_prompt_tokens, actual_static_tokens) if base_prompt_tokens == 700 else base_prompt_tokens

    safe_budget = max_token_budget - min_output_tokens
    current_tokens = effective_base_tokens

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
        parent_header = f"{sec_title} {sec_def_text[:250]}".strip()

        clause_tokens_sum = 0
        for doc in sibling_docs:
            ctext = doc.get("target_clause_text") or doc.get("text", "")
            snippet = ctext[:350]
            clause_tokens_sum += (len(snippet) // 4) + 20

        sec_compact_tokens = (len(parent_header) // 4) + 25 + clause_tokens_sum

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
            primary_snippet = primary_text[:350]
            primary_tokens = (len(parent_header) // 4) + 25 + (len(primary_snippet) // 4) + 20

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
    analysis_candidate_limit: Optional[int] = None,
    skip_llm_analysis: bool = False,
    use_deterministic_queries: bool = False,
    workload: Workload = Workload.CITIZEN_FIR_ANALYSIS
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
        skip_llm_analysis (bool): If True, skips LLM analysis generation and returns grounded retrieval fallback cards directly (useful for lightweight workflows e.g. FIR drafting).

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
    if llm_client is None and not skip_llm_analysis:
        llm_client = MultiProviderLLMFailoverClient()

    # 2. Privacy Gateway: Local sanitization boundary
    privacy_res = sanitize_text(raw_incident)
    sanitized_text = privacy_res.get("sanitized_text", "")

    # 3. NER Entity Extraction
    ner_result = extract_entities(sanitized_text)

    # 4. Query Generation
    if use_deterministic_queries:
        from ai.rag.retrieval.query_generator import _generate_deterministic_queries
        query_output = _generate_deterministic_queries(ner_result)
    else:
        query_output = generate_queries(ner_result, llm_client=llm_client if not skip_llm_analysis else None)
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

    # If skip_llm_analysis is requested, skip LLM reasoning and return grounded retrieval fallback directly
    if skip_llm_analysis:
        fallback_analysis = _build_retrieval_fallback_analysis(reranked_candidates)
        return {
            "status": "success",
            "sanitized_incident": sanitized_text,
            "privacy_metadata": {
                "detections": privacy_res.get("detections", []),
                "replacement_map": privacy_res.get("replacement_map", {})
            },
            "analysis": fallback_analysis,
            "limitations": ["Fast-path retrieval grounding used for FIR generation."],
            "disclaimer": LEGAL_DISCLAIMER,
            "reranked_candidates": reranked_candidates,
            "pipeline_source": "retrieval_fallback"
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
        llm_client=llm_client,
        workload=workload
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


def sanitize_and_validate_legal_chat_reply(bot_reply: str, structured_chat_context: list) -> str:
    """
    Automated final-response normalizer & contradiction fixer.
    Enforces status-explanation consistency, statutory element correctness,
    statutory punishment maximum safeguards, and bottom-line summary consistency.
    """
    import re
    if not bot_reply or not isinstance(bot_reply, str):
        return bot_reply

    # Build section applicability map (section_num -> applicability)
    sec_app_map = {}
    for item in structured_chat_context:
        s_raw = str(item.get("section", "")).replace("Section", "").strip()
        app = str(item.get("overall_applicability", "uncertain")).lower()
        if s_raw:
            sec_app_map[s_raw] = app

    # 1. Normalize Section Headings & Tags for Conditional Provisions
    for sec, app in sec_app_map.items():
        if app in ["potentially_applicable", "uncertain", "insufficient_information", "not_supported"]:
            pattern_est = re.compile(
                r'(\*\*?(?:BNS\s+)?Section\s+' + re.escape(sec) + r'\b[^\*\n]*\*\*?\s*[\—\:\-]\s*)\*?(?:Established|Facts?\s+establish[^\*\n]*)\*?',
                re.IGNORECASE
            )
            bot_reply = pattern_est.sub(r'\1*Potentially Applicable (Material Fact Missing)*', bot_reply)

            p_body = re.compile(r'\bFacts?\s+establish(?:es)?\s+(?:BNS\s+)?Section\s+' + re.escape(sec) + r'\b', re.IGNORECASE)
            bot_reply = p_body.sub(f'Section {sec} may be applicable depending on missing details', bot_reply)

    # 2. Statutory Element Overrides
    if "130" in sec_app_map and sec_app_map["130"] != "established":
        bot_reply = re.sub(
            r'(\bSection\s+130\b[^\.\n]*?)(?:is\s+established|applies\s+because\s+of\s+the\s+attack)',
            r'\1is potentially applicable (Section 130 concerns gestures or preparation causing apprehension of force, rather than the physical attack itself)',
            bot_reply,
            flags=re.IGNORECASE
        )

    if "309" in sec_app_map and sec_app_map["309"] != "established":
        bot_reply = re.sub(
            r'(\bSection\s+309\b[^\.\n]*?)(?:is\s+established|clearly\s+applies)',
            r'\1is potentially applicable (theft becomes robbery under Section 309 when physical force, hurt, or fear is voluntarily caused in committing theft or carrying away property)',
            bot_reply,
            flags=re.IGNORECASE
        )

    # 3. Punishment Safeguards
    bot_reply = re.sub(r'\bthe punishment is (\d+\s*(?:years?|months?))\b', r'imprisonment up to \1', bot_reply, flags=re.IGNORECASE)
    bot_reply = re.sub(r'\bthe penalty is (\d+\s*(?:years?|months?))\b', r'imprisonment up to \1', bot_reply, flags=re.IGNORECASE)

    # 4. Bottom-Line Summary Consistency Check
    bottom_line_match = re.search(r'(###\s*6\.\s*Bottom line summary[^\n]*\n)(.*)', bot_reply, re.DOTALL | re.IGNORECASE)
    if bottom_line_match:
        bl_header = bottom_line_match.group(1)
        bl_body = bottom_line_match.group(2).strip()

        conditional_secs = [s for s, a in sec_app_map.items() if a in ["potentially_applicable", "uncertain", "insufficient_information"]]
        has_contradiction = False

        for c_sec in conditional_secs:
            if re.search(r'\b(?:most likely|clearly applies|is established|definitely fits)\b[^\.\n]*?\bSection\s+' + re.escape(c_sec) + r'\b', bl_body, re.IGNORECASE):
                has_contradiction = True
                break
            if re.search(r'\bSection\s+' + re.escape(c_sec) + r'\b[^\.\n]*?\b(?:is established|clearly applies|is the main charge)\b', bl_body, re.IGNORECASE):
                has_contradiction = True
                break

        if has_contradiction:
            cond_str = ", ".join([f"Section {s}" for s in conditional_secs])
            new_bl_body = (
                f"Because specific details remain unstated, candidate provisions like {cond_str} remain "
                "potentially applicable. No legal section can be established as a final conclusion until these "
                "missing statutory elements are investigated and confirmed."
            )
            bot_reply = bot_reply[:bottom_line_match.start()] + bl_header + new_bl_body

    return bot_reply


def run_chat_pipeline(
    raw_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    llm_client: Optional[LLMClient] = None
) -> Dict[str, Any]:
    """
    Executes the LawAid RAG Pipeline for Conversational Legal Chat.

    Flow:
        Raw chat query + History context
        → Sentiment & Emotional Cue Detection
        → Grounded RAG Pipeline (run_pipeline with deterministic query generator)
        → Section-based Deduplication & Grouping
        → Plain-language Conversational Synthesis
        → Sanitization & Safety Verification

    Args:
        raw_message (str): Input user chat query.
        history (list, optional): Previous chat message objects [{"role": "user"|"assistant", "content": "..."}].
        llm_client (LLMClient, optional): LLM generation client instance.

    Returns:
        dict: Conversational response containing status, reply, sections, disclaimer.
    """
    import json
    import re
    from ai.chat.sentiment import detect_sentiment

    if llm_client is None:
        llm_client = MultiProviderLLMFailoverClient()

    # 1. Detect sentiment / emotional tone
    sentiment_info = detect_sentiment(raw_message)
    empathy_guide = sentiment_info.get("empathy_guide", "")

    # 2. Formulate effective incident text combining history for follow-up questions
    effective_incident = raw_message
    history_str = ""
    if history:
        past_user_msgs = [m.get("content", "") for m in history if m.get("role") == "user" and m.get("content")]
        formatted_history = []
        for m in history[-6:]:
            role_label = "Citizen" if m.get("role") == "user" else "Assistant"
            formatted_history.append(f"{role_label}: {m.get('content', '')}")
        history_str = "\n".join(formatted_history)

        # If current query is short or a follow-up inquiry, combine previous user incident context
        if past_user_msgs and len(raw_message.split()) < 15:
            effective_incident = f"{' '.join(past_user_msgs[-2:])} {raw_message}"

    # 3. Execute grounded RAG pipeline (using deterministic query generation for Chat to optimize latency)
    pipeline_res = run_pipeline(
        raw_incident=effective_incident,
        llm_client=llm_client,
        use_deterministic_queries=True,
        workload=Workload.LEGAL_CHAT
    )

    is_fallback = (
        pipeline_res.get("source") == "retrieval_fallback"
        or pipeline_res.get("status") == "analysis_unavailable"
    )

    if is_fallback:
        reply_text = (
            "LawAid could not complete the legal analysis right now. Please try again shortly."
        )
        return {
            "status": "ok",
            "sanitized_incident": pipeline_res.get("sanitized_incident", raw_message),
            "reply": reply_text,
            "sections": [],
            "disclaimer": LEGAL_DISCLAIMER
        }

    grounded_analysis = pipeline_res.get("analysis", [])
    sanitized_text = pipeline_res.get("sanitized_incident", raw_message)
    limitations = pipeline_res.get("limitations", [])

    # 4. Section-based Deduplication & Grouping
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
                "reasonings": [],
                "punishment": item.get("punishment"),
                "bailable": item.get("bailable"),
                "cognizable": item.get("cognizable"),
                "court": item.get("court")
            }

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

        app = sec_info["applicability"]
        # Relevance Filter (Requirement 3): Skip not_supported downstream candidates
        if app == "not_supported":
            continue

        if app in ["supported", "established"]:
            formatted_sections.append(label)

        structured_chat_context.append({
            "section": f"Section {sec}",
            "title": clean_title,
            "overall_applicability": app,
            "statutory_punishment_details": {
                "punishment": sec_info.get("punishment"),
                "bailable": sec_info.get("bailable"),
                "cognizable": sec_info.get("cognizable"),
                "court": sec_info.get("court")
            },
            "legal_analysis_notes": sec_info["reasonings"]
        })

    # 5. Conversational Synthesis Prompt
    prompt = (
        "You are LawAid's compassionate, plain-language Legal AI Assistant specializing in Indian criminal law "
        "(Bharatiya Nyaya Sanhita, BNS 2023 & Bharatiya Nagarik Suraksha Sanhita, BNSS 2023).\n"
        "Summarize the grounded legal analysis below for an ordinary citizen using simple, everyday English.\n\n"
        "CITIZEN-FRIENDLY LANGUAGE RULES:\n"
        "1. Explain all legal concepts as if speaking to an ordinary citizen with no legal background.\n"
        "2. Prefer simple phrases like 'This section generally covers...', 'In simple words...', 'This may apply if...', 'We don't have enough information to say...'.\n"
        "3. NEVER use formal legal jargon or pipeline technical terms such as 'mandatory elements', 'aggravating circumstances', 'applicability is uncertain', 'the offence that clearly fits this', 'reranked_candidates', or 'document_id'.\n"
        "4. Do NOT remove legal accuracy and do NOT invent missing facts.\n"
        "5. Keep section numbers and legal titles accurate.\n"
        "6. Preserve uncertainty: if user facts are incomplete, state clearly what facts are missing rather than drawing a definite legal conclusion.\n\n"
        "STATUTORY PUNISHMENT SAFEGUARD & SECTION EXPLAINING RULES (e.g. BNS Section 303):\n"
        "7. ALWAYS PRESERVE STATUTORY MAXIMUMS & ALTERNATIVES:\n"
        "   - When the statute states 'imprisonment for a term which may extend to X years, or with fine, or with both', ALWAYS describe it as a maximum ceiling or alternative (e.g. 'imprisonment up to X years, or fine, or both').\n"
        "   - NEVER transform a maximum limit ('may extend to 10 years') into an absolute fixed sentence ('the punishment is 10 years').\n"
        "   - For Section 303(2) BNS theft:\n"
        "     * Ordinary / first conviction: imprisonment up to 3 years, OR fine, OR both.\n"
        "     * Repeat conviction: rigorous imprisonment of 1 to 5 years AND fine (applies ONLY if accused has a prior theft conviction).\n"
        "     * Petty theft proviso (<₹5,000 + restoration): community service upon first conviction.\n"
        "     * NEVER state 1–5 years RI as the ordinary punishment for simple theft.\n"
        "8. Refer to BNS sections strictly as 'Section <number>' or 'BNS Section <number>' (e.g., Section 303, Section 329). NEVER mention IPC sections.\n"
        "9. Expand BNS strictly as 'Bharatiya Nyaya Sanhita, 2023' and BNSS strictly as 'Bharatiya Nagarik Suraksha Sanhita, 2023'.\n"
        "10. STRICT GROUNDING STATUS & EXPLANATION MATCHING (FOUR GENERALIZED STATES):\n"
        "    - ESTABLISHED: Label a section as 'Established' or 'Facts establish this provision' ONLY when the stated facts satisfy ALL mandatory statutory elements without requiring further confirmation or unstated facts. IF YOU STATE THAT FACTS ARE NEEDED OR STATUTORY INTENT/PURPOSE STILL NEEDS CONFIRMATION, YOU MUST NOT LABEL THE PROVISION AS ESTABLISHED.\n"
        "    - POTENTIALLY APPLICABLE — MATERIAL FACT MISSING: Label a section as 'Potentially Applicable' when some elements fit, but specific material statutory facts (e.g. carrying/wearing property for §134, lurking/concealment for §331, manner of force/fear for §309) are unstated. State specifically what fact is missing.\n"
        "    - NOT SUPPORTED: Label as 'Not Supported' when stated facts contradict or fail required statutory elements.\n"
        "    - INSUFFICIENT INFORMATION: Label as 'Insufficient Information' when key facts are unstated so applicability cannot be evaluated.\n"
        "11. GUIDED & INTERACTIVE RESPONSE STRUCTURE & BOTTOM-LINE CONSISTENCY:\n"
        "    - Structure your answer using clean Markdown headings and bullet points: (1) What the law says about your situation, (2) Applicable sections, (3) Punishments and statutory conditions, (4) What we don't know yet & what details would help, (5) What you can do next (safety advice: 'If you feel that you remain at risk, tell the police about the safety concern and ask what immediate protection or other legal remedy is available in your circumstances'), and (6) Bottom line summary.\n"
        "    - BOTTOM-LINE CONSISTENCY RULE: The bottom line summary MUST be generated strictly from the grounded provision states. Any provision that is conditional/uncertain (§309, §134, §331, etc.) MUST remain conditional in the bottom line. ONLY provisions that are fully established by stated facts may be summarized as established.\n"
        "12. RETRIEVAL SYNTHESIS & STATUTORY ACCURACY:\n"
        "    - When multiple retrieved clauses/branches concern the same section, synthesize them into a clear rule. Remove duplication and do not dump every branch into the user response.\n"
        "    - Statutory elements must control language: compare mandatory statutory elements against explicitly stated facts without assuming unstated facts or replacing statutory terms with vague shortcuts.\n"
        f"13. COMMUNICATION TONE & EMPATHY: {empathy_guide} Make this sentiment/empathy visibly clear in your opening paragraph before diving into legal details. "
        "For distressed or scared citizens, start with a warm, gentle, empathetic opening like 'I am so sorry you are dealing with this. Being in this situation can be frightening...'. "
        "For confused citizens, start with a reassuring opening like 'I understand this can be confusing. Let's break down which provisions may apply...'. "
        "For angry or frustrated citizens, start with a calm, validating opening like 'I understand this situation is frustrating. Let's separate the legal issues from the next steps...'. "
        "For neutral queries, proceed directly with a polite, professional tone. "
        "For immediate danger or emergency, include a concise safety warning. "
        "CRITICAL: Sentiment and empathy must NEVER change legal facts, retrieved sections, punishments, procedural classifications, or legal conclusions.\n"
        "14. CONVERSATIONAL CONTEXT: Use the CONVERSATION HISTORY to naturally answer follow-up questions without requiring the user to repeat prior details.\n"
        "15. FORMATTING: Use clean Markdown (bold headings with **text**, bullet points, numbered lists, and paragraphs). Do NOT output literal single-asterisk markdown or raw code blocks.\n"
        "16. Return ONLY valid JSON matching this schema:\n"
        '{\n  "reply": "string (conversational response text formatted in Markdown)"\n}\n\n'
    )

    if history_str:
        prompt += f"CONVERSATION HISTORY:\n{history_str}\n\n"

    prompt += (
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

    # 6. Fallback if LLM synthesis returns empty
    if not bot_reply:
        lines = ["Based on the Bharatiya Nyaya Sanhita, 2023 (BNS):"]
        if structured_chat_context:
            supported_items = [i for i in structured_chat_context if i.get("overall_applicability") == "supported"]
            uncertain_items = [i for i in structured_chat_context if i.get("overall_applicability") != "supported"]

            if supported_items:
                lines.append("**Applicable Provisions:**")
                for item in supported_items:
                    sec_name = item.get("section")
                    t_name = item.get("title")
                    notes = " ".join(item.get("legal_analysis_notes", []))
                    lines.append(f"- **{sec_name} ({t_name})**: {notes}")

            if uncertain_items:
                lines.append("**Provisions requiring further information:**")
                for item in uncertain_items:
                    sec_name = item.get("section")
                    t_name = item.get("title")
                    notes = " ".join(item.get("legal_analysis_notes", []))
                    lines.append(f"- **{sec_name} ({t_name})**: Additional facts needed. {notes}")
        else:
            lines.append("No specific legal provisions could be confirmed from the facts provided. Please share more details about what happened.")

        bot_reply = "\n\n".join(lines)

    # 7. Strict post-processing sanitization & automated contradiction normalization
    bot_reply = re.sub(r'\(?reranked_candidates\)?', '', bot_reply, flags=re.IGNORECASE)
    bot_reply = re.sub(r'\bdocument_id\b', '', bot_reply, flags=re.IGNORECASE)
    bot_reply = re.sub(r'\bcandidate_id\b', '', bot_reply, flags=re.IGNORECASE)

    if "Bihar National Security" in bot_reply:
        bot_reply = bot_reply.replace("Bihar National Security", "Bharatiya Nyaya Sanhita")

    bot_reply = re.sub(r'\bIPC\b', 'BNS', bot_reply)
    bot_reply = re.sub(r'Indian Penal Code', 'Bharatiya Nagarik Suraksha Sanhita, 2023', bot_reply, flags=re.IGNORECASE)

    bot_reply = sanitize_and_validate_legal_chat_reply(bot_reply, structured_chat_context)

    bot_reply = re.sub(r'  +', ' ', bot_reply).strip()

    return {
        "status": "ok",
        "sanitized_incident": sanitized_text,
        "reply": bot_reply,
        "sections": formatted_sections,
        "disclaimer": LEGAL_DISCLAIMER
    }

