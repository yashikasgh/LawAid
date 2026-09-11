"""query_generator.py — LLM-Backed & Deterministic Retrieval Query Generator for LawAid RAG.

What Query Generation Does:
    Transforms extracted Named Entity Recognition (NER) results and original incident
    descriptions into multiple structured, natural-language retrieval queries for BNS/BNSS corpus.

Why Multiple Queries Are Generated:
    Vector search (embeddings) and keyword retrieval perform differently depending on query phrasing.
    Generating distinct query formulations (incident context, fact-focused, legal concepts, action context)
    improves retrieval recall and ensures relevant statutory provisions are retrieved even when vocabulary varies.

Why Legal Section Numbers Are Deliberately Excluded:
    The Query Generator's responsibility is purely retrieval-oriented natural-language query formulation.
    It must NOT hypothesize, assume, or hardcode BNS/BNSS section numbers or make legal applicability
    conclusions, as doing so would pre-judge the legal analysis and bypass authoritative retrieval and reasoning.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure analysis directory is on sys.path for LLMClient imports
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ANALYSIS_DIR = PROJECT_ROOT / "ai" / "rag" / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from legal_analyzer import (
    LLMClient,
    OllamaLLMClient,
    MockLLMClient,
    _parse_json_from_llm,
)


QUERY_GENERATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": [
                            "incident_context",
                            "fact_focused",
                            "legal_concept",
                            "action_context",
                        ],
                    },
                    "query": {"type": "string"},
                },
                "required": ["query_type", "query"],
            },
        }
    },
    "required": ["queries"],
}


class OllamaQueryGeneratorLLMClient(OllamaLLMClient):
    """Subclass of OllamaLLMClient applying QUERY_GENERATOR_SCHEMA for structured query generation."""

    def generate(self, prompt: str) -> str:
        if not self.model_name:
            raise RuntimeError(
                "No generative LLM model configured. Please set OLLAMA_LLM_MODEL environment variable "
                "or pass a configured LLMClient instance."
            )
        if "nomic-embed" in self.model_name:
            raise RuntimeError(
                f"Configured model '{self.model_name}' is an embedding model and cannot be used for text generation."
            )
        import ollama

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                format=QUERY_GENERATOR_SCHEMA,
                options={"temperature": 0},
            )
            return response.get("message", {}).get("content", "")
        except Exception as e:
            raise RuntimeError(
                f"Ollama text generation failed for model '{self.model_name}': {e}"
            )


def construct_query_generator_prompt(ner_result: Dict[str, Any]) -> str:
    """Construct a strict system prompt for LLM retrieval query generation."""
    raw_text = ner_result.get("raw_text", "")
    if not isinstance(raw_text, str):
        raw_text = ""

    offence_types = ner_result.get("offence_types", [])
    if not isinstance(offence_types, list):
        offence_types = []

    entities = {}
    for key in (
        "victims",
        "accused",
        "persons",
        "locations",
        "organizations",
        "dates",
        "times",
    ):
        val = ner_result.get(key)
        if isinstance(val, list) and val:
            entities[key] = val

    prompt = (
        "You are a specialized retrieval-query generation assistant for Indian criminal law (BNS/BNSS).\n"
        "Generate 2 to 5 adaptive, diverse natural-language search queries that help retrieve relevant provisions "
        "from the BNS/BNSS legal corpus for the incident.\n\n"
        "ADAPTIVE QUERY COUNT RULES:\n"
        "1. For simple incidents with a single clear event, generate 2 to 3 complementary queries.\n"
        "2. For complex or multi-offence incidents containing distinct conduct segments (e.g., forced entry, physical assault, property theft), generate 3 to 5 complementary queries covering each distinct action segment and statutory element.\n"
        "3. Never generate redundant or duplicate queries merely to reach a higher count.\n\n"
        "STRICT GROUNDING & RETRIEVAL RULES:\n"
        "1. Every generated query MUST remain grounded in the incident's explicit facts or legal concepts directly supported by those facts.\n"
        "2. Do NOT include generic jurisdictional filler or meta-language such as 'under Indian criminal law', 'in Indian law', 'under BNS', 'under BNSS', 'in India', 'legal provisions relating to', or similar phrases that do not improve retrieval.\n"
        "3. Do NOT generate section numbers (e.g. §125, §281, §303), state that any provision applies, or hardcode section maps.\n"
        "4. Do NOT invent facts or events not present in the incident (e.g. do not invent 'failure to render assistance' or 'ransom' unless explicitly stated in the text).\n"
        "5. If offence_types are supplied, they may be used as retrieval concepts, but do not assume that they are legally correct.\n"
        "6. Do not upgrade, relabel, or introduce a more serious or legally distinct offence characterization "
        "(such as 'robbery', 'dacoity', 'extortion', 'kidnapping') that is not present in the supplied offence_types or incident facts.\n\n"
        "DYNAMIC MULTIPLE SEMANTIC PERSPECTIVES:\n"
        "Generate queries from complementary angles dynamically derived from the incident facts:\n"
        "1. FACTUAL CIRCUMSTANCES (query_type: 'fact_focused'): Factual details, objects, and circumstances.\n"
        "2. CONDUCT / PHYSICAL ACTION (query_type: 'action_context'): Specific physical conduct and acts.\n"
        "3. STATUTORY LEGAL CONCEPT (query_type: 'legal_concept'): Generic statutory legal elements represented by the facts (e.g., 'dishonest taking of movable property without consent', 'theft committed by sudden quick or forcible seizure of property', or 'fraudulent inducement to deliver property or money').\n"
        "4. CONSEQUENCE / HARM (query_type: 'legal_concept' or 'action_context'): Injury, bodily hurt, or safety endangerment when relevant.\n"
        "5. MULTI-OFFENCE CONDUCT SEGMENTS (query_type: 'action_context' or 'fact_focused'): For incidents with multiple distinct conduct segments, generate focused queries for each segment.\n\n"
        "Return ONLY JSON matching this format:\n"
        "{\n"
        '  "queries": [\n'
        "    {\n"
        '      "query_type": "incident_context | fact_focused | legal_concept | action_context",\n'
        '      "query": "string"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"INCIDENT RAW TEXT:\n{raw_text}\n\n"
        f"NER OFFENCE TYPES:\n{json.dumps(offence_types)}\n\n"
        f"NER EXTRACTED ENTITIES:\n{json.dumps(entities, indent=2)}\n"
    )
    return prompt


def validate_llm_queries(
    parsed_data: Any, ner_result: Dict[str, Any]
) -> Optional[List[Dict[str, str]]]:
    """Validates LLM-generated queries structure, query type diversity, section exclusion, content safety, and fact grounding."""
    if not isinstance(parsed_data, dict):
        return None

    raw_queries = parsed_data.get("queries")
    if not isinstance(raw_queries, list):
        return None

    allowed_query_types = {
        "incident_context",
        "fact_focused",
        "legal_concept",
        "action_context",
    }

    # BNS/BNSS section reference patterns (explicit section numbers)
    bns_section_patterns = [
        r"351\(3\)",
        r"329\(3\)",
        r"303\(2\)",
        r"\bBNS\b",
        r"\bBNSS\b",
        r"\bSection\s+\d+\b",
        r"\bsec\.?\s*\d+\b",
        r"\b\d{3}\(\d+\)\b",
        r"\b\d{3}\b",
    ]
    section_regex = re.compile("|".join(bns_section_patterns), re.IGNORECASE)

    # Section inquiry phrases asking for section numbers
    section_inquiry_patterns = [
        r"\bwhich\s+sections?\b",
        r"\bwhat\s+sections?\b",
        r"\bsection\s+numbers?\b",
        r"\bwhich\s+provisions?\s+numbers?\b",
        r"\bwhat\s+provisions?\s+numbers?\b",
        r"\bwhich\s+bns\s+sections?\b",
        r"\bwhich\s+bnss\s+sections?\b",
        r"\bwhat\s+bns\s+sections?\b",
        r"\bwhat\s+bnss\s+sections?\b",
    ]
    inquiry_regex = re.compile("|".join(section_inquiry_patterns), re.IGNORECASE)

    # Explicit legal applicability conclusion patterns
    conclusion_patterns = [
        r"\bsection\s+\d+\s+applies\b",
        r"\bapplies\b",
        r"\bis applicable\b",
        r"\bguilty of\b",
        r"\bviolates section\b",
        r"\bpunishable under section\b",
        r"\bconstitutes an offence under section\b",
    ]
    conclusion_regex = re.compile("|".join(conclusion_patterns), re.IGNORECASE)

    # Generic jurisdictional filler patterns to reject
    filler_patterns = [
        r"\bunder\s+indian\s+(criminal\s+)?law\b",
        r"\bin\s+indian\s+(criminal\s+)?law\b",
        r"\bunder\s+bns\b",
        r"\bunder\s+bnss\b",
        r"\bin\s+india\b",
        r"\blegal\s+provisions?\s+relating\s+to\b",
        r"\blegal\s+provisions?\s+concerning\b",
        r"\bpossession\s+under\s+law\b",
    ]
    filler_regex = re.compile("|".join(filler_patterns), re.IGNORECASE)

    # Specific unsupported legal concepts & upgraded offence characterizations to check for grounding
    unsupported_concepts = [
        "aggravating factor",
        "aggravating factors",
        "aggravated",
        "robbery",
        "dacoity",
        "extortion",
        "ransom",
        "kidnapping",
        "homicide",
        "murder",
        "cybercrime",
        "hacking",
    ]
    ner_str_lower = json.dumps(ner_result).lower()

    raw_text = ner_result.get("raw_text", "")
    if not isinstance(raw_text, str):
        raw_text = ""

    offence_types_raw = ner_result.get("offence_types", [])
    offence_types = [
        o.strip()
        for o in (
            offence_types_raw if isinstance(offence_types_raw, list) else []
        )
        if isinstance(o, str) and o.strip()
    ]

    entities_raw = []
    for k in ("victims", "accused", "persons", "locations", "organizations"):
        val_list = ner_result.get(k)
        if isinstance(val_list, list):
            for v in val_list:
                if isinstance(v, str) and v.strip():
                    entities_raw.append(v.strip())

    incident_content_str = (
        raw_text + " " + " ".join(offence_types) + " " + " ".join(entities_raw)
    ).lower()

    stop_words = {
        "the", "and", "was", "for", "that", "this", "with", "from", "were",
        "they", "been", "have", "has", "had", "will", "would", "could",
        "should", "into", "over", "under", "about", "after", "before",
        "accused", "person", "incident", "facts", "details"
    }
    incident_tokens = {
        w for w in re.findall(r"\b[a-z]{3,}\b", incident_content_str)
        if w not in stop_words
    }

    grounded_legal_concept_patterns = [
        r"\bdishonest(ly)?\s+taking\b",
        r"\bmovable\s+property\b",
        r"\bwithout\s+(that\s+person's\s+)?consent\b",
        r"\bwithout\s+permission\b",
        r"\bcriminal\s+trespass\b",
        r"\bhouse\s+trespass\b",
        r"\bcriminal\s+intimidation\b",
        r"\bcriminal\s+force\b",
        r"\bwrongful\s+restraint\b",
        r"\bwrongful\s+confinement\b",
        r"\breceiv(ing|es)\s+stolen\s+property\b",
        r"\bretain(ing|s)\s+stolen\s+property\b",
        r"\bbreach\s+of\s+trust\b",
        r"\bmisappropriation\b",
        r"\bcheating\b",
        r"\bforgery\b",
        r"\bmischief\b",
        r"\bassault\b",
        r"\bsnatching\b",
        r"\bseiz(ing|ure)\b",
        r"\bforcibl(y|e)\b",
        r"\bendangering\s+(human\s+)?life\b",
        r"\bendangering\s+personal\s+safety\b",
        r"\bpersonal\s+safety\b",
        r"\brash\s+or\s+negligent\b",
        r"\bcausing\s+hurt\b",
        r"\bcausing\s+injury\b",
    ]
    grounded_legal_regex = re.compile(
        "|".join(grounded_legal_concept_patterns), re.IGNORECASE
    )

    valid_queries: List[Dict[str, str]] = []
    seen_queries = set()

    for item in raw_queries:
        if not isinstance(item, dict):
            return None

        q_type = item.get("query_type")
        q_str = item.get("query")

        # query is a non-empty string
        if not isinstance(q_str, str) or not q_str.strip():
            return None

        q_clean = q_str.strip()

        # query_type is one of the allowed values
        if not isinstance(q_type, str) or q_type.strip() not in allowed_query_types:
            return None

        # Reject queries containing section numbers/BNS references
        if section_regex.search(q_clean):
            return None

        # Reject section inquiries (e.g. "which sections", "what section", "section number")
        if inquiry_regex.search(q_clean):
            return None

        # Reject queries making explicit applicability conclusions
        if conclusion_regex.search(q_clean):
            return None

        # Reject generic jurisdictional filler phrases
        if filler_regex.search(q_clean):
            return None

        # Reject unsupported legal concepts or upgraded offence characterizations not grounded in the incident
        for concept in unsupported_concepts:
            if concept in q_clean.lower() and concept not in ner_str_lower:
                return None

        # Fact check: proper nouns in query must exist in ner_result or incident
        words = re.findall(r"\b[A-Z][a-z]+\b", q_clean)
        common_legal = {
            "The", "A", "An", "In", "On", "At", "For", "With", "Under",
            "Indian", "Law", "Legal", "State", "Penal", "Code",
        }
        for w in words:
            if w in common_legal:
                continue
            if w.lower() not in ner_str_lower:
                return None

        # Anchoring check: query must contain either concrete incident facts/actions/objects OR a specific grounded legal concept
        q_lower = q_clean.lower()
        q_tokens = set(re.findall(r"\b[a-z]{3,}\b", q_lower)) - stop_words

        has_fact_match = bool(q_tokens & incident_tokens)
        has_legal_concept_match = bool(grounded_legal_regex.search(q_lower))

        if not has_fact_match and not has_legal_concept_match:
            return None

        # Deduplicate queries case-insensitively while preserving order
        normalized = q_clean.lower()
        if normalized not in seen_queries:
            seen_queries.add(normalized)

            matched_offence = ""
            if offence_types:
                for o in offence_types:
                    if o.lower() in normalized or any(
                        word in normalized
                        for word in o.lower().split()
                        if len(word) > 3
                    ):
                        matched_offence = o
                        break
                if not matched_offence:
                    matched_offence = offence_types[0]

            valid_queries.append(
                {
                    "offence_type": matched_offence,
                    "query_type": q_type.strip(),
                    "query": q_clean,
                }
            )

    # Maximum 5 queries
    if len(valid_queries) > 5:
        valid_queries = valid_queries[:5]

    # Adaptive minimum check: allow 2 to 5 queries
    if len(valid_queries) < 2:
        return None

    # Check query_type diversity: reject output where all queries have the exact same query_type when 2+ queries exist
    if len(valid_queries) >= 2:
        unique_types = {q["query_type"] for q in valid_queries}
        if len(unique_types) == 1:
            return None

    return valid_queries


def _generate_deterministic_queries(
    ner_result: Dict[str, Any]
) -> Dict[str, List[Dict[str, str]]]:
    """Fallback query generator returning only the original sanitized incident description as a single query."""
    if not isinstance(ner_result, dict):
        return {"queries": []}

    raw_text = ner_result.get("raw_text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {"queries": []}

    clean_text = raw_text.strip()
    return {
        "queries": [
            {
                "offence_type": "",
                "query_type": "incident_context",
                "query": clean_text
            }
        ]
    }



def generate_queries(
    ner_result: Dict[str, Any], llm_client: Optional[LLMClient] = None
) -> Dict[str, List[Dict[str, str]]]:
    """Generates multiple natural-language retrieval queries from NER output using LLM or fallback generator.

    Args:
        ner_result: Dictionary containing NER extraction results.
        llm_client (LLMClient, optional): Swappable LLM generation backend instance.

    Returns:
        dict: Standardized output structure: {"queries": [{"offence_type": ..., "query_type": ..., "query": ...}]}
    """
    if not isinstance(ner_result, dict):
        return {"queries": []}

    if llm_client is None:
        return _generate_deterministic_queries(ner_result)

    try:
        if type(llm_client) is OllamaLLMClient:
            llm_client = OllamaQueryGeneratorLLMClient(
                model_name=llm_client.model_name
            )

        prompt = construct_query_generator_prompt(ner_result)
        raw_output = llm_client.generate(prompt)

        parsed_json = _parse_json_from_llm(raw_output)
        valid_queries = validate_llm_queries(parsed_json, ner_result)

        if valid_queries is not None:
            return {"queries": valid_queries}
        else:
            return _generate_deterministic_queries(ner_result)
    except Exception:
        return _generate_deterministic_queries(ner_result)
