"""reranker.py — Deterministic legal candidate reranker for LawAid RAG.

Located at: ai/rag/retrieval/reranker.py
"""

from typing import List, Dict, Any, Union, Optional
import re


def _extract_incident_text(incident_input: Union[str, Dict[str, Any]]) -> str:
    """Extract raw incident text string from input."""
    if isinstance(incident_input, str):
        return incident_input.strip()
    elif isinstance(incident_input, dict):
        raw_text = incident_input.get("raw_text", "")
        if raw_text:
            return str(raw_text).strip()
        # Fallback to combining text fields
        parts = []
        for key in ["offence_types", "persons", "locations", "organizations"]:
            val = incident_input.get(key)
            if isinstance(val, list) and val:
                parts.extend([str(v) for v in val])
        return " ".join(parts).strip()
    return ""


def _extract_incident_facts(incident_text: str) -> Dict[str, bool]:
    """
    Extract factual indicator flags from incident text using generic pattern matching.
    """
    text = incident_text.lower()

    # Generic pattern groups in incident facts
    has_clerk_servant = bool(re.search(r'\b(clerk|servant|employee|employer|master|working as|hired by|assistant|worker)\b', text))
    has_assault_force = bool(re.search(r'\b(assault|assaulted|force|criminal force|attacked|slapped|hit|beat|pushed|struck|threatened with force)\b', text))
    has_preparation = bool(re.search(r'\b(preparation|prepared|armed|weapon|gun|pistol|knife|deadly weapon|in order to hurt|to restrain|with intent to hurt)\b', text))
    has_mint_coining = bool(re.search(r'\b(mint|coining|coin tool|coining tool|coining instrument|minting|stamping coin)\b', text))
    has_taking_without_consent = bool(re.search(r'\b(took|take|stole|steal|taken|stolen|without permission|without consent|dispossessed|movable property)\b', text))
    has_concealment_only = bool(re.search(r'\b(conceal|concealed|concealment|hide|hidden|released claim|fraudulent removal)\b', text)) and not has_taking_without_consent

    # Additional generic incident facts
    has_dwelling_transport = bool(re.search(r'\b(dwelling house|dwelling|residence|residential house|place of worship|temple|church|mosque|vessel|ship|boat|train|bus|car|vehicle|transportation)\b', text))
    has_gift_recovery = bool(re.search(r'\b(taking gift|gift|reward|gratification|reward to recover|help to recover|recovering stolen property)\b', text))
    has_property_mark = bool(re.search(r'\b(property mark|trade mark|trademark|brand mark|counterfeiting mark)\b', text))
    has_public_way_navigation = bool(re.search(r'\b(public way|line of navigation|navigation|public road|public street obstruction)\b', text))
    has_omission_to_inform = bool(re.search(r'\b(omission to give information|failed to inform|bound to inform|omission to report)\b', text))
    has_receiving_stolen = bool(re.search(r'\b(received stolen|retained stolen|buying stolen|bought stolen|possessing stolen property)\b', text)) and not has_taking_without_consent

    return {
        "clerk_servant": has_clerk_servant,
        "assault_force": has_assault_force,
        "preparation": has_preparation,
        "mint_coining": has_mint_coining,
        "taking_without_consent": has_taking_without_consent,
        "concealment_only": has_concealment_only,
        "dwelling_transport": has_dwelling_transport,
        "gift_recovery": has_gift_recovery,
        "property_mark": has_property_mark,
        "public_way_navigation": has_public_way_navigation,
        "omission_to_inform": has_omission_to_inform,
        "receiving_stolen": has_receiving_stolen,
    }


def _analyze_candidate_requirements(candidate: Dict[str, Any]) -> Dict[str, bool]:
    """
    Inspect candidate title and operative text to detect legal requirements/qualifications
    using generic corpus-based pattern matching.
    """
    title = str(candidate.get("title", "")).lower()
    text = str(candidate.get("text", "")).lower()

    # Split off Illustrations section if present to avoid false matches on illustrative examples
    text_operative = text.split("illustrations")[0] if "illustrations" in text else text
    full_target_str = f"{title} {text_operative}"

    # Generic candidate legal element detection (checked against title and operative legal text)
    requires_clerk_servant = bool(re.search(r'\b(clerk or servant|theft by clerk|in the capacity of a clerk|in possession of master|master or employer)\b', full_target_str)) or ("clerk" in title or "servant" in title)
    requires_assault_force = bool(re.search(r'\b(assault or criminal force|uses assault|assault in attempt|criminal force in attempt)\b', full_target_str)) or ("assault" in title or "criminal force" in title)
    requires_preparation = bool(re.search(r'\b(preparation made for causing|preparation for causing|having made preparation)\b', full_target_str)) or ("preparation made" in title or "preparation for" in title)
    requires_mint_coining = bool(re.search(r'\b(coining tool|coining instrument|out of any mint|takes out of any mint)\b', full_target_str)) or ("mint" in title or "coining" in title)
    requires_concealment = bool(re.search(r'\b(conceals or removes|concealment or removal|dishonestly releases any demand)\b', full_target_str)) or ("concealment" in title)

    requires_dwelling_transport = bool(re.search(r'\b(dwelling house|means of transportation|place of worship|building, tent or vessel)\b', full_target_str)) or ("dwelling house" in title or "means of transportation" in title or "place of worship" in title)
    requires_gift_recovery = bool(re.search(r'\b(taking gift|help to recover stolen property|gratification|taking gift to help)\b', full_target_str)) or ("taking gift" in title or "recover stolen property" in title)
    requires_property_mark = bool(re.search(r'\b(property mark|counterfeiting a property mark|tampering with property mark)\b', full_target_str)) or ("property mark" in title)
    requires_public_way_navigation = bool(re.search(r'\b(public way|line of navigation|navigation|obstruction in public way)\b', full_target_str)) or ("public way" in title or "line of navigation" in title)
    requires_omission_to_inform = bool(re.search(r'\b(omission to give information|person bound to inform|intentional omission)\b', full_target_str)) or ("omission to give information" in title or "bound to inform" in title)
    requires_receiving_stolen = bool(re.search(r'\b(dishonestly receives or retains|receives any stolen property|retains any stolen property)\b', full_target_str)) or (title.strip().startswith("stolen property"))

    is_general_theft = bool(re.search(r'\b(intending to take dishonestly any movable property|out of the possession of any person without that person\'s consent|moves that property)\b', text)) or title.strip() in ["theft.", "theft"]

    return {
        "requires_clerk_servant": requires_clerk_servant,
        "requires_assault_force": requires_assault_force,
        "requires_preparation": requires_preparation,
        "requires_mint_coining": requires_mint_coining,
        "requires_concealment": requires_concealment,
        "requires_dwelling_transport": requires_dwelling_transport,
        "requires_gift_recovery": requires_gift_recovery,
        "requires_property_mark": requires_property_mark,
        "requires_public_way_navigation": requires_public_way_navigation,
        "requires_omission_to_inform": requires_omission_to_inform,
        "requires_receiving_stolen": requires_receiving_stolen,
        "is_general_theft": is_general_theft,
    }


def rerank_candidates(
    incident_input: Union[str, Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    top_k: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Reranks retrieved legal candidates using transparent, explainable legal feature signals
    and vector similarity.

    Args:
        incident_input: Raw incident text or structured NER dictionary.
        candidates: List of candidate dictionaries retrieved from ChromaDB vector search.
        top_k: Optional number of top candidates to return.

    Returns:
        Sorted list of candidate dictionaries containing rerank metadata:
        - document_id (or id)
        - original retrieval rank
        - original distance
        - rerank_score
        - scoring_reasons
    """
    if not candidates:
        return []

    incident_text = _extract_incident_text(incident_input)
    incident_facts = _extract_incident_facts(incident_text)

    reranked = []

    for idx, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            continue

        # Preserve original fields
        candidate_copy = dict(cand)
        orig_distance = float(cand.get("distance", 1.0))
        orig_rank = int(cand.get("rank", idx + 1))

        # 1. Base vector similarity score (higher is better, 0.0 - 1.0 scale approx)
        # ChromaDB distance for cosine distance ranges 0.0 (identical) to ~2.0
        similarity_score = max(0.0, 1.0 - (orig_distance / 2.0))

        score = similarity_score
        reasons = [f"Base vector similarity score: {similarity_score:.4f} (distance: {orig_distance:.4f})"]

        # 2. Candidate element analysis
        cand_reqs = _analyze_candidate_requirements(cand)

        # 3. Apply element rewards and penalties

        # General Theft Core Alignment
        if cand_reqs["is_general_theft"]:
            if incident_facts["taking_without_consent"]:
                score += 0.35
                reasons.append("Matches core elements of dishonest taking of movable property without consent (+0.35)")

        # Clerk / Servant requirement
        if cand_reqs["requires_clerk_servant"]:
            if incident_facts["clerk_servant"]:
                score += 0.45
                reasons.append("Incident matches required clerk/servant/employment relationship (+0.45)")
            else:
                score -= 0.30
                reasons.append("Candidate requires clerk/servant relationship absent in incident (-0.30)")

        # Assault / Criminal Force requirement
        if cand_reqs["requires_assault_force"]:
            if incident_facts["assault_force"]:
                score += 0.45
                reasons.append("Incident matches required assault/criminal force element (+0.45)")
            else:
                score -= 0.25
                reasons.append("Candidate requires assault/criminal force absent in incident (-0.25)")

        # Preparation for Death/Hurt/Restraint requirement
        if cand_reqs["requires_preparation"]:
            if incident_facts["preparation"]:
                score += 0.45
                reasons.append("Incident matches required preparation for death/hurt/restraint (+0.45)")
            else:
                score -= 0.25
                reasons.append("Candidate requires preparation for death/hurt/restraint absent in incident (-0.25)")

        # Mint / Coining Instrument requirement
        if cand_reqs["requires_mint_coining"]:
            if incident_facts["mint_coining"]:
                score += 0.50
                reasons.append("Incident matches specialized mint/coining instrument domain (+0.50)")
            else:
                score -= 0.50
                reasons.append("Candidate specifies mint/coining instrument domain absent in incident (-0.50)")

        # Concealment / Fraudulent Removal emphasis vs Direct Taking
        if cand_reqs["requires_concealment"]:
            if incident_facts["concealment_only"]:
                score += 0.20
                reasons.append("Incident matches property concealment/fraudulent release (+0.20)")
            elif incident_facts["taking_without_consent"]:
                score -= 0.15
                reasons.append("Candidate focuses on concealment/release rather than direct taking (-0.15)")

        # Dwelling House / Transportation / Place of Worship requirement
        if cand_reqs["requires_dwelling_transport"]:
            if incident_facts["dwelling_transport"]:
                score += 0.30
                reasons.append("Incident matches required dwelling house/transportation/worship venue (+0.30)")
            else:
                score -= 0.25
                reasons.append("Candidate specifies specialized dwelling house/transportation/worship venue absent in incident (-0.25)")

        # Gift / Consideration to help recover stolen property requirement
        if cand_reqs["requires_gift_recovery"]:
            if incident_facts["gift_recovery"]:
                score += 0.40
                reasons.append("Incident matches required gift/reward for stolen property recovery (+0.40)")
            else:
                score -= 0.30
                reasons.append("Candidate specifies taking gift/reward for stolen property recovery absent in incident (-0.30)")

        # Property Mark / Counterfeiting requirement
        if cand_reqs["requires_property_mark"]:
            if incident_facts["property_mark"]:
                score += 0.40
                reasons.append("Incident matches required property mark/counterfeiting domain (+0.40)")
            else:
                score -= 0.30
                reasons.append("Candidate specifies property mark / counterfeiting domain absent in incident (-0.30)")

        # Public Way / Navigation Obstruction requirement
        if cand_reqs["requires_public_way_navigation"]:
            if incident_facts["public_way_navigation"]:
                score += 0.40
                reasons.append("Incident matches public way / line of navigation domain (+0.40)")
            else:
                score -= 0.30
                reasons.append("Candidate specifies public way / navigation obstruction domain absent in incident (-0.30)")

        # Omission to Inform requirement
        if cand_reqs["requires_omission_to_inform"]:
            if incident_facts["omission_to_inform"]:
                score += 0.40
                reasons.append("Incident matches intentional omission to give information (+0.40)")
            else:
                score -= 0.30
                reasons.append("Candidate specifies intentional omission to give information absent in incident (-0.30)")

        # Receiving / Retaining Stolen Property vs Direct Taking
        if cand_reqs["requires_receiving_stolen"]:
            if incident_facts["receiving_stolen"]:
                score += 0.30
                reasons.append("Incident matches receiving/retaining stolen property (+0.30)")
            elif incident_facts["taking_without_consent"]:
                score -= 0.15
                reasons.append("Candidate specifies receiving/retaining stolen property rather than direct taking (-0.15)")

        # Attach rerank metadata
        candidate_copy["rerank_score"] = round(score, 4)
        candidate_copy["scoring_reasons"] = reasons
        # Maintain document_id alias if needed
        if "id" in candidate_copy and "document_id" not in candidate_copy:
            candidate_copy["document_id"] = candidate_copy["id"]

        reranked.append(candidate_copy)

    # Sort candidates by rerank_score in descending order
    reranked.sort(key=lambda x: x.get("rerank_score", -999.0), reverse=True)

    if top_k is not None and isinstance(top_k, int) and top_k > 0:
        return reranked[:top_k]

    return reranked
