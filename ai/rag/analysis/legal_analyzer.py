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


class LLMClient:
    """Base interface for swappable LLM generation backends."""
    def generate(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement generate()")


class OllamaLLMClient(LLMClient):
    """Ollama-backed text generation client."""
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
            response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])
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


def construct_analysis_prompt(legal_context_obj: Dict[str, Any]) -> str:
    """Construct a strict evidence-grounded prompt for structured JSON legal analysis."""
    incident = legal_context_obj.get("incident", {})
    legal_context = legal_context_obj.get("legal_context", [])

    prompt = (
        "You are an expert legal analysis system for Indian Criminal Law (Bharatiya Nyaya Sanhita - BNS, 2023).\n"
        "Analyze the provided incident facts and retrieved BNS legal provisions.\n\n"
        "STRICT EVIDENCE AND SAFETY RULES:\n"
        "1. Use ONLY the supplied incident facts and retrieved BNS context.\n"
        "2. Do NOT invent BNS sections, punishments, or legal classifications.\n"
        "3. Every proposed legal section MUST be grounded in retrieved evidence. Provide document_id, section, clause, and rank.\n"
        "4. For punishment, bailable status, and cognizable status: state the value ONLY if explicitly present in retrieved context.\n"
        "   If not explicitly present, write exactly 'not_available_in_retrieved_context'.\n"
        "5. Output ONLY valid JSON matching the exact schema below, with no surrounding commentary or markdown code blocks.\n\n"
        "JSON SCHEMA:\n"
        "{\n"
        '  "status": "success",\n'
        '  "analysis": [\n'
        "    {\n"
        '      "offence_type": "string",\n'
        '      "section": "string",\n'
        '      "title": "string",\n'
        '      "applicability": "supported|uncertain|not_supported",\n'
        '      "reasoning": "string",\n'
        '      "punishment": "string",\n'
        '      "bailable": "string",\n'
        '      "cognizable": "string",\n'
        '      "evidence": [\n'
        "        {\n"
        '          "document_id": "string",\n'
        '          "section": "string",\n'
        '          "clause": "string",\n'
        '          "rank": 1\n'
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ],\n"
        '  "limitations": ["string"]\n'
        "}\n\n"
        "INCIDENT FACTS:\n"
        f"{json.dumps(incident, indent=2)}\n\n"
        "RETRIEVED BNS LEGAL CONTEXT:\n"
        f"{json.dumps(legal_context, indent=2)}\n"
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
    """Validate parsed LLM response ensuring all evidence references valid retrieved document IDs."""
    if not isinstance(parsed_data, dict) or "analysis" not in parsed_data:
        return {
            "status": "generation_failed",
            "reason": "LLM response schema missing 'analysis' list.",
            "raw_llm_output": json.dumps(parsed_data)
        }

    # Collect set of all actual document IDs present in retrieval results
    actual_doc_ids = set()
    for group in legal_context_obj.get("legal_context", []):
        for doc in group.get("results", []):
            if doc.get("id"):
                actual_doc_ids.add(doc["id"])

    valid_analysis_items = []
    limitations = parsed_data.get("limitations", [])
    if not isinstance(limitations, list):
        limitations = []

    for item in parsed_data.get("analysis", []):
        if not isinstance(item, dict):
            continue

        evidences = item.get("evidence", [])
        if not isinstance(evidences, list):
            evidences = []

        valid_evidences = []
        for ev in evidences:
            if isinstance(ev, dict) and ev.get("document_id") in actual_doc_ids:
                valid_evidences.append(ev)

        if not valid_evidences:
            section_name = item.get("section", "unknown")
            limitations.append(
                f"Rejected analysis item for section '{section_name}': evidence references document ID(s) "
                f"not found in actual retrieval results."
            )
        else:
            item["evidence"] = valid_evidences
            # Enforce hallucination rule for missing legal properties
            for prop in ["punishment", "bailable", "cognizable"]:
                val = str(item.get(prop, "")).strip()
                if not val or val in ["unknown", "n/a", "none"]:
                    item[prop] = "not_available_in_retrieved_context"
            valid_analysis_items.append(item)

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
