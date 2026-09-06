"""legal_analyzer.py — Structured LLM Legal Analysis Layer for LawAid RAG.

Located at: ai/rag/analysis/legal_analyzer.py
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure analysis directory is on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from context_builder import build_legal_context


LEGAL_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["success"]
        },
        "analysis": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "applicability": {
                        "type": "string",
                        "enum": ["supported", "uncertain", "not_supported"]
                    },
                    "reasoning": {"type": "string"}
                },
                "required": ["document_id", "applicability", "reasoning"]
            }
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["status", "analysis", "limitations"]
}


class LLMClient:
    """Base interface for swappable LLM generation backends."""
    def generate(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement generate()")


class OllamaLLMClient(LLMClient):
    """Ollama-backed text generation client using structured outputs."""
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get("OLLAMA_LLM_MODEL")

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
                format=LEGAL_ANALYSIS_SCHEMA,
                options={"temperature": 0}
            )
            return response.get("message", {}).get("content", "")
        except Exception as e:
            raise RuntimeError(f"Ollama text generation failed for model '{self.model_name}': {e}")


class MockLLMClient(LLMClient):
    """Mock LLM client for deterministic testing."""
    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = responses or []
        self.call_count = 0
        self.prompts_received = []

    def generate(self, prompt: str) -> str:
        self.prompts_received.append(prompt)
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return "{}"


class GroqLLMClient(LLMClient):
    """Groq API text generation client adapter."""
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        try:
            from dotenv import load_dotenv
            repo_root_env = CURRENT_DIR.parents[1] / ".env"
            if repo_root_env.exists():
                load_dotenv(dotenv_path=repo_root_env, override=False)
            else:
                load_dotenv(override=False)
        except ImportError:
            pass

        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing.")

        self.model_name = model_name or os.environ.get("GROQ_MODEL") or "openai/gpt-oss-120b"

        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Groq client: {e}")

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            if response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                return message.content if message and message.content else ""
            return ""
        except Exception as e:
            raise RuntimeError(f"Groq API text generation failed for model '{self.model_name}': {e}")


def construct_analysis_prompt(legal_context_obj: Dict[str, Any]) -> str:
    """Construct a strict, evidence-grounded system prompt for legal analysis."""
    incident = legal_context_obj.get("incident", {})
    raw_context = legal_context_obj.get("legal_context", [])

    formatted_context_groups = []
    for group in raw_context:
        offence_type = group.get("offence_type", "")
        query = group.get("query", "")
        formatted_docs = []
        for doc in group.get("results", []):
            formatted_docs.append({
                "rank": doc.get("rank"),
                "id": doc.get("id"),
                "section": doc.get("section"),
                "clause": doc.get("clause"),
                "title": doc.get("title"),
                "target_clause_text": doc.get("target_clause_text", doc.get("text", "")),
                "section_definition": doc.get("section_definition", ""),
                "schedule_1": doc.get("schedule_1", {})
            })
        formatted_context_groups.append({
            "offence_type": offence_type,
            "query": query,
            "results": formatted_docs
        })

    prompt = (
        "You are an expert legal analysis system for Indian criminal law (Bharatiya Nyaya Sanhita - BNS 2023).\n"
        "Analyze the provided INCIDENT FACTS strictly using ONLY the RETRIEVED BNS LEGAL CONTEXT provided below.\n\n"
        "STRICT GROUNDING & APPLICABILITY RULES:\n"
        "1. For each candidate document in the RETRIEVED BNS LEGAL CONTEXT, evaluate whether it applies to the INCIDENT FACTS.\n"
        "2. You MUST only reference candidate documents using their exact document_id string from the RETRIEVED BNS LEGAL CONTEXT.\n"
        "3. Evaluate applicability strictly against the INCIDENT FACTS for EACH candidate document independently:\n"
        "   - 'supported': Mark as 'supported' ONLY when ALL material elements, conditions, monetary/quantity thresholds, and qualifiers in the candidate document (including any specific Schedule I offence description, sub-clause, or monetary threshold like 'Where value of property is less than 5,000 rupees') are explicitly established by the INCIDENT FACTS.\n"
        "   - 'uncertain': Mark as 'uncertain' if ANY material element, condition, monetary threshold, or qualifier in that specific candidate document (such as property value, monetary threshold like < 5,000 rupees, specific location, age, intent, or force level) is missing, unspecified, or unknown in the INCIDENT FACTS. You MUST NOT infer or assume missing facts, nor mark a candidate document as 'supported' if its specific monetary threshold or condition is unstated in the facts.\n"
        "   - 'not_supported': Mark as 'not_supported' if the incident facts clearly contradict the provision or if the essential offence definition is inapplicable to the facts.\n"
        "4. Provide a clear, factual reasoning string explaining why the provision is supported, uncertain due to missing factual conditions or unstated thresholds, or not supported.\n"
        "5. Output ONLY valid JSON matching the exact schema below. Do NOT include markdown formatting or commentary outside the JSON.\n\n"
        "JSON OUTPUT SCHEMA:\n"
        "{\n"
        '  "status": "success",\n'
        '  "analysis": [\n'
        "    {\n"
        '      "document_id": "string",\n'
        '      "applicability": "supported | uncertain | not_supported",\n'
        '      "reasoning": "string"\n'
        "    }\n"
        "  ],\n"
        '  "limitations": ["string"]\n'
        "}\n\n"
        "INCIDENT FACTS:\n"
        f"{json.dumps(incident, indent=2)}\n\n"
        "RETRIEVED BNS LEGAL CONTEXT:\n"
        f"{json.dumps(formatted_context_groups, indent=2)}\n"
    )
    return prompt


def _parse_json_from_llm(raw_text: str) -> Dict[str, Any]:
    """Clean markdown formatting and parse JSON from raw LLM output."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    return json.loads(cleaned)


def validate_and_ground_analysis(parsed_data: Dict[str, Any], legal_context_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parsed LLM response and attach deterministic legal metadata from retrieved corpus."""
    if not isinstance(parsed_data, dict) or "analysis" not in parsed_data:
        return {
            "status": "generation_failed",
            "reason": "LLM response schema missing 'analysis' list.",
            "raw_llm_output": json.dumps(parsed_data)
        }

    # Map actual document ID -> (doc_object, group_offence_type)
    doc_map = {}
    for group in legal_context_obj.get("legal_context", []):
        group_offence = group.get("offence_type", "")
        for doc in group.get("results", []):
            doc_id = doc.get("id")
            if doc_id:
                doc_map[doc_id] = (doc, group_offence)

    valid_analysis_items = []
    limitations = parsed_data.get("limitations", [])
    if not isinstance(limitations, list):
        limitations = []

    for item in parsed_data.get("analysis", []):
        if not isinstance(item, dict):
            continue

        doc_id = item.get("document_id")
        if not doc_id or doc_id not in doc_map:
            limitations.append(
                f"Rejected analysis item for document_id '{doc_id}': evidence references document ID "
                f"not found in actual retrieval results."
            )
            continue

        doc_info, group_offence = doc_map[doc_id]
        sched_1 = doc_info.get("schedule_1", {})
        if not isinstance(sched_1, dict):
            sched_1 = {}

        # Sourced deterministically from the validated retrieved BNS/BNSS corpus
        offence_name = sched_1.get("offence") or group_offence or doc_info.get("title", "")
        punishment_val = sched_1.get("punishment") or "not_available_in_retrieved_context"
        bailable_val = sched_1.get("bailable") or "not_available_in_retrieved_context"
        cognizable_val = sched_1.get("cognizable") or "not_available_in_retrieved_context"
        court_val = sched_1.get("court") or "not_available_in_retrieved_context"

        applicability = item.get("applicability", "supported")
        if applicability not in ["supported", "uncertain", "not_supported"]:
            applicability = "supported"

        reasoning = item.get("reasoning", "")

        grounded_item = {
            "offence_type": offence_name,
            "section": str(doc_info.get("section", "")),
            "clause": doc_info.get("clause", ""),
            "title": doc_info.get("title", ""),
            "applicability": applicability,
            "reasoning": reasoning,
            "punishment": punishment_val,
            "bailable": bailable_val,
            "cognizable": cognizable_val,
            "court": court_val,
            "evidence": [
                {
                    "document_id": doc_id,
                    "section": str(doc_info.get("section", "")),
                    "clause": doc_info.get("clause", ""),
                    "rank": doc_info.get("rank")
                }
            ]
        }
        valid_analysis_items.append(grounded_item)

    return {
        "status": "success",
        "analysis": valid_analysis_items,
        "limitations": limitations
    }


def analyze_incident(ner_result: Dict[str, Any], retrieval_result: Dict[str, Any], llm_client: Optional[LLMClient] = None) -> Dict[str, Any]:
    """Execute legal analysis on incident facts and BNS retrieval context using structured LLM generation.

    Args:
        ner_result (dict): Structured output from extract_entities().
        retrieval_result (dict): Grouped output from retrieve_by_ner().
        llm_client (LLMClient, optional): Client instance for LLM generation.

    Returns:
        dict: Structured legal analysis object with evidence grounding and limitation reports.
    """
    if llm_client is None:
        llm_client = OllamaLLMClient()

    context_obj = build_legal_context(ner_result, retrieval_result)
    prompt = construct_analysis_prompt(context_obj)

    raw_output = ""
    parsed_json = None
    parse_error = None

    # Attempt 1
    try:
        raw_output = llm_client.generate(prompt)
        parsed_json = _parse_json_from_llm(raw_output)
    except Exception as err1:
        parse_error = str(err1)

    # Attempt 2 (Retry on JSON parse failure)
    if parsed_json is None:
        retry_prompt = (
            f"{prompt}\n\n"
            "PREVIOUS GENERATION ERROR:\n"
            f"Your previous response failed to parse as valid JSON with error: {parse_error}\n"
            f"Raw Response: {raw_output}\n\n"
            "RETRY INSTRUCTION:\n"
            "Return ONLY corrected, strict, valid JSON matching the schema. Do NOT include any markdown code blocks or text outside the JSON."
        )
        try:
            raw_output = llm_client.generate(retry_prompt)
            parsed_json = _parse_json_from_llm(raw_output)
        except Exception as err2:
            return {
                "status": "generation_failed",
                "raw_llm_output": raw_output,
                "reason": f"JSON parse failed after retry: {err2}"
            }

    # Ground analysis against actual retrieved evidence
    return validate_and_ground_analysis(parsed_json, context_obj)
