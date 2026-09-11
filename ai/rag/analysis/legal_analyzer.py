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
                    "unit_type": {
                        "type": "string",
                        "enum": ["core_definition", "conditional_proviso", "aggravated_branch", "mitigating_branch"]
                    },
                    "applicability": {
                        "type": "string",
                        "enum": ["supported", "uncertain", "not_supported"]
                    },
                    "statutory_structure": {
                        "type": "object",
                        "properties": {
                            "structural_unit_type": {
                                "type": "string",
                                "enum": ["core_definition", "conditional_proviso", "aggravated_branch", "mitigating_branch"]
                            },
                            "core_elements": {"type": "array", "items": {"type": "string"}},
                            "conditional_elements": {"type": "array", "items": {"type": "string"}},
                            "aggravated_elements": {"type": "array", "items": {"type": "string"}},
                            "mitigating_elements": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["structural_unit_type", "core_elements", "conditional_elements"]
                    },
                    "prerequisite_evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "requirement": {"type": "string"},
                                "requirement_type": {
                                    "type": "string",
                                    "enum": ["core", "conditional", "aggravated", "mitigating"]
                                },
                                "evidence_status": {
                                    "type": "string",
                                    "enum": ["satisfied", "missing", "contradicted", "not_applicable"]
                                },
                                "incident_evidence": {"type": "string"},
                                "reason": {"type": "string"}
                            },
                            "required": ["requirement", "requirement_type", "evidence_status", "incident_evidence", "reason"]
                        }
                    },
                    "core_elements": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "conditional_elements": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "satisfied_elements": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "missing_elements": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "contradicted_elements": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "relationship_analysis": {
                        "type": "object",
                        "properties": {
                            "relationship_type": {
                                "type": "string",
                                "enum": ["none", "specific_over_general", "ancillary_conduct", "mutually_exclusive", "alternative_branch", "independent_concurrent"]
                            },
                            "related_candidate": {"type": "string"},
                            "reason": {"type": "string"}
                        },
                        "required": ["relationship_type", "related_candidate", "reason"]
                    },
                    "reasoning": {"type": "string"},
                    "explanation": {"type": "string"}
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
                load_dotenv(dotenv_path=repo_root_env, override=True)
            else:
                load_dotenv(override=True)
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


class GeminiLLMClient(LLMClient):
    """Google Gemini API text generation client adapter."""
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        try:
            from dotenv import load_dotenv
            repo_root_env = CURRENT_DIR.parents[1] / ".env"
            if repo_root_env.exists():
                load_dotenv(dotenv_path=repo_root_env, override=True)
            else:
                load_dotenv(override=True)
        except ImportError:
            pass

        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing.")

        self.model_name = model_name or os.environ.get("GEMINI_MODEL") or "gemini-3.8-flash"

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini client for model '{self.model_name}': {e}")

    def generate(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, "text") and response.text:
                return response.text
            return ""
        except Exception as e:
            raise RuntimeError(f"Gemini API text generation failed for model '{self.model_name}': {e}")


class CerebrasLLMClient(LLMClient):
    """Cerebras Cloud API text generation client adapter."""
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        try:
            from dotenv import load_dotenv
            repo_root_env = CURRENT_DIR.parents[1] / ".env"
            if repo_root_env.exists():
                load_dotenv(dotenv_path=repo_root_env, override=True)
            else:
                load_dotenv(override=True)
        except ImportError:
            pass

        self.api_key = api_key or os.environ.get("CEREBRAS_API_KEY")
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY environment variable is missing.")

        self.model_name = model_name or os.environ.get("CEREBRAS_MODEL") or "gpt-oss-120b"

        try:
            from cerebras.cloud.sdk import Cerebras
            self.client = Cerebras(api_key=self.api_key)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Cerebras client: {e}")

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
            raise RuntimeError(f"Cerebras API text generation failed for model '{self.model_name}': {e}")


class MultiProviderLLMFailoverClient(LLMClient):
    """
    Production-quality multi-provider LLM failover manager for LawAid RAG.

    Priority order:
    1. Google Gemini — gemini-3.8-flash (Primary)
    2. Groq — openai/gpt-oss-120b
    3. Cerebras — gpt-oss-120b (Free/Low-cost Tier)
    4. Groq — openai/gpt-oss-20b
    """

    def __init__(self, providers: Optional[List[LLMClient]] = None):
        if providers is not None:
            self.providers = providers
        else:
            self.providers = self._build_default_provider_chain()
        self.last_execution_trace: List[Dict[str, Any]] = []
        self.active_provider_info: Dict[str, str] = {}

    def _build_default_provider_chain(self) -> List[LLMClient]:
        chain = []
        try:
            from dotenv import load_dotenv
            repo_root_env = CURRENT_DIR.parents[1] / ".env"
            if repo_root_env.exists():
                load_dotenv(dotenv_path=repo_root_env, override=True)
            else:
                load_dotenv(override=True)
        except ImportError:
            pass

        groq_key = os.environ.get("GROQ_API_KEY")
        gemini_key = os.environ.get("GEMINI_API_KEY")
        cerebras_key = os.environ.get("CEREBRAS_API_KEY")

        # 1. Gemini 3.8 Flash (Primary)
        if gemini_key:
            try:
                chain.append(GeminiLLMClient(api_key=gemini_key, model_name="gemini-3.8-flash"))
            except Exception as e:
                print(f"[LLM Failover Config Warning] Gemini init skipped: {e}")

        # 2. Groq GPT-OSS 120B
        if groq_key:
            try:
                chain.append(GroqLLMClient(api_key=groq_key, model_name="openai/gpt-oss-120b"))
            except Exception as e:
                print(f"[LLM Failover Config Warning] Groq 120B init skipped: {e}")

        # 3. Cerebras GPT-OSS 120B
        if cerebras_key:
            try:
                chain.append(CerebrasLLMClient(api_key=cerebras_key, model_name="gpt-oss-120b"))
            except Exception as e:
                print(f"[LLM Failover Config Warning] Cerebras init skipped: {e}")

        # 4. Groq GPT-OSS 20B
        if groq_key:
            try:
                chain.append(GroqLLMClient(api_key=groq_key, model_name="openai/gpt-oss-20b"))
            except Exception as e:
                print(f"[LLM Failover Config Warning] Groq 20B init skipped: {e}")

        # 5. Fallback to Ollama if configured and no cloud keys available
        if not chain and os.environ.get("OLLAMA_LLM_MODEL"):
            try:
                chain.append(OllamaLLMClient())
            except Exception:
                pass

        return chain

    def generate(self, prompt: str) -> str:
        import time

        self.last_execution_trace = []
        self.active_provider_info = {}

        if not self.providers:
            raise RuntimeError(
                "No LLM providers are configured in the failover chain. "
                "Please set GROQ_API_KEY or GEMINI_API_KEY in the environment."
            )

        for provider_client in self.providers:
            provider_name = provider_client.__class__.__name__
            model_name = getattr(provider_client, "model_name", "unknown")
            start_time = time.time()

            try:
                raw_out = provider_client.generate(prompt)
                latency_ms = round((time.time() - start_time) * 1000, 2)

                if not raw_out or not raw_out.strip():
                    raise RuntimeError("Provider returned empty string output.")

                # Try parsing JSON output
                try:
                    parsed = _parse_json_from_llm(raw_out)
                    if isinstance(parsed, dict):
                        self.last_execution_trace.append({
                            "provider": provider_name,
                            "model": model_name,
                            "status": "success",
                            "latency_ms": latency_ms
                        })
                        self.active_provider_info = {
                            "provider": provider_name,
                            "model": model_name
                        }
                        return raw_out
                    else:
                        raise ValueError("Output is not a valid JSON dictionary.")
                except Exception as json_err:
                    raise RuntimeError(f"Output failed structured JSON validation: {json_err}")

            except Exception as err:
                latency_ms = round((time.time() - start_time) * 1000, 2)
                err_msg = str(err)
                print(f"[LLM Failover Trace] {provider_name} ({model_name}) failed in {latency_ms}ms: {err_msg}")
                self.last_execution_trace.append({
                    "provider": provider_name,
                    "model": model_name,
                    "status": "failed",
                    "error": err_msg,
                    "latency_ms": latency_ms
                })

        raise RuntimeError("All LLM providers in failover chain failed.")


def construct_analysis_prompt(legal_context_obj: Dict[str, Any]) -> str:
    """Construct a strict, evidence-grounded system prompt for multi-pass statutory applicability analysis."""
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
        "STRICT PROVISO & CLAUSE PREREQUISITE EVALUATION:\n"
        "==================================================\n"
        "6-PASS GENERIC STATUTORY APPLICABILITY REASONING\n"
        "==================================================\n\n"
        "PASS 1 — STATUTORY REQUIREMENT EXTRACTION:\n"
        "For EACH candidate provision independently, derive from the supplied statutory text:\n"
        "1. Core legal elements\n"
        "2. Conditional/proviso elements\n"
        "3. Aggravated branch elements\n"
        "4. Mitigating branch elements\n"
        "5. Special capacity/relationship requirements (e.g., clerk, servant, public servant, trustee, carrier)\n"
        "6. Specific object/instrumentality requirements (e.g., property mark, forged document, vehicle, weapon)\n"
        "7. Required consequence/outcome (e.g., death, grievous hurt, wrongful gain, loss)\n"
        "8. Required victim/offender/property state (e.g., active possession vs unpossessed/found, public place, night-time)\n"
        "9. Mens rea requirements (e.g., dishonest, fraudulent, rash, negligent, intentional, knowledge)\n"
        "10. Any other material statutory prerequisite\n"
        "Do NOT assume these categories exist in every section. Populate a category only when supported by the actual statutory text.\n\n"
        "PASS 2 — EVIDENCE STATUS FOR EVERY MATERIAL REQUIREMENT:\n"
        "For every extracted requirement, classify the incident evidence strictly as:\n"
        "- SATISFIED: Explicitly supported by affirmative factual evidence in stated INCIDENT FACTS.\n"
        "- MISSING: Required by the statute but not affirmatively established by the INCIDENT FACTS.\n"
        "- CONTRADICTED: Incident explicitly establishes that the requirement did not occur.\n"
        "- NOT_APPLICABLE: Only for conditional/aggravated/mitigating branches that are not triggered.\n\n"
        "CRITICAL ANTI-HALLUCINATION & AFFIRMATIVE EVIDENCE GATING RULES:\n"
        "- The incident is the ONLY source of factual evidence.\n"
        "- The candidate text is the ONLY source of statutory requirements.\n"
        "- A mandatory requirement MUST NOT be classified as satisfied merely because it is compatible, plausible, or because another element is satisfied.\n"
        "- Do NOT infer missing facts. Invalid reasoning examples:\n"
        "  * 'Property stolen, therefore offender was a clerk' (INVALID - missing capacity)\n"
        "  * 'Property involved, therefore property mark existed' (INVALID - missing object)\n"
        "  * 'Accident occurred, therefore death occurred' (INVALID - missing consequence)\n"
        "  * 'Dishonest conversion, therefore property was lost' (INVALID - missing state)\n"
        "  * 'Physical force occurred, therefore every assault provision applies' (INVALID - missing specific context)\n"
        "- Require affirmative factual evidence for all material prerequisites.\n\n"
        "PASS 3 — CORE VS CONDITIONAL STRUCTURE:\n"
        "- Preserve Core vs Conditional architecture.\n"
        "- A missing conditional proviso MUST NOT invalidate an otherwise supported core offence definition.\n"
        "- (e.g. Core definition supported + value proviso unknown => core definition is 'supported', proviso branch is 'uncertain'). If the property value is UNSTATED or MISSING from the facts, mark that specific proviso candidate document as 'uncertain' or 'not_supported'.\n"
        "- Aggravated and mitigating branches must only be activated when their triggering conditions are established by facts.\n\n"
        "PASS 4 — STRICT APPLICABILITY DECISION:\n"
        "- 'supported': ALL mandatory core elements affirmatively satisfied, NO mandatory core element contradicted, required mens rea supported by facts, required capacity/relationship supported when required, required object/instrumentality supported when required, required consequence/state supported when required.\n"
        "- 'not_supported': Mandatory requirement explicitly contradicted OR a mandatory special prerequisite (such as special capacity, specific object/instrumentality, or specific statutory outcome) is absent from the stated incident facts in a way that makes the candidate impossible to establish (e.g. candidate describes a public-way obstruction/hazard requiring property in possession whose mandatory conditions are absent).\n"
        "- 'uncertain': Material requirement could be true but incident simply lacks enough information to establish it, and candidate cannot honestly be classified as supported.\n"
        "- Be conservative with 'supported'. Do NOT convert every unknown into 'not_supported' automatically. Preserve 'uncertain' where appropriate.\n\n"
        "PASS 5 — CANDIDATE RELATIONSHIP ANALYSIS:\n"
        "After evaluating candidates independently, perform a separate generic relationship analysis across retrieved candidates:\n"
        "- Determine whether candidates have relationships such as:\n"
        "  * specific_over_general: Specific provision vs general provision (e.g., snatching vs theft, specific cheat vs general cheat)\n"
        "  * ancillary_conduct: Core offence vs ancillary/secondary conduct\n"
        "  * mutually_exclusive: Mutually exclusive factual states (e.g., property taken from active possession vs property found/lost)\n"
        "  * alternative_branch: Alternative statutory branches of the same act\n"
        "  * independent_concurrent: Independent concurrent offences (e.g., rash driving + hurt caused + theft are independent concurrent offences)\n"
        "  * none: Independent conduct with no relationship suppression\n"
        "- Only suppress a candidate when statutory text AND incident facts justify that relationship.\n"
        "- Do NOT assume a more serious offence automatically eliminates a less serious offence.\n"
        "- Do NOT assume physical hurt automatically eliminates another offence.\n"
        "- Do NOT assume robbery automatically eliminates every related offence.\n"
        "- Explain the statutory basis for any relationship decision.\n\n"
        "PASS 6 — FINAL CLASSIFICATION & STRUCTURED OUTPUT:\n"
        "Return structured JSON matching the schema.\n\n"
        "JSON OUTPUT SCHEMA FORMAT:\n"
        "{\n"
        '  "status": "success",\n'
        '  "analysis": [\n'
        "    {\n"
        '      "document_id": "string",\n'
        '      "unit_type": "core_definition | conditional_proviso | aggravated_branch | mitigating_branch",\n'
        '      "applicability": "supported | uncertain | not_supported",\n'
        '      "statutory_structure": {\n'
        '        "structural_unit_type": "core_definition | conditional_proviso | aggravated_branch | mitigating_branch",\n'
        '        "core_elements": ["string"],\n'
        '        "conditional_elements": ["string"],\n'
        '        "aggravated_elements": ["string"],\n'
        '        "mitigating_elements": ["string"]\n'
        '      },\n'
        '      "prerequisite_evidence": [\n'
        '        {\n'
        '          "requirement": "string",\n'
        '          "requirement_type": "core | conditional | aggravated | mitigating",\n'
        '          "evidence_status": "satisfied | missing | contradicted | not_applicable",\n'
        '          "incident_evidence": "string",\n'
        '          "reason": "string"\n'
        '        }\n'
        '      ],\n'
        '      "core_elements": ["string"],\n'
        '      "conditional_elements": ["string"],\n'
        '      "satisfied_elements": ["string"],\n'
        '      "missing_elements": ["string"],\n'
        '      "contradicted_elements": ["string"],\n'
        '      "relationship_analysis": {\n'
        '        "relationship_type": "none | specific_over_general | ancillary_conduct | mutually_exclusive | alternative_branch | independent_concurrent",\n'
        '        "related_candidate": "string",\n'
        '        "reason": "string"\n'
        '      },\n'
        '      "reasoning": "string",\n'
        '      "explanation": "string"\n'
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
        clean_group_offence = group_offence if group_offence and group_offence != "reranked_candidates" else ""
        offence_name = sched_1.get("offence") or clean_group_offence or doc_info.get("title", "")
        punishment_val = sched_1.get("punishment") or "Not available in retrieved source"
        bailable_val = sched_1.get("bailable") or "Not available in retrieved source"
        cognizable_val = sched_1.get("cognizable") or "Not available in retrieved source"
        court_val = sched_1.get("court") or "Not available in retrieved source"

        applicability = item.get("applicability", "uncertain")
        if applicability not in ["supported", "uncertain", "not_supported"]:
            applicability = "uncertain"

        unit_type = item.get("unit_type", "core_definition")
        if unit_type not in ["core_definition", "conditional_proviso", "aggravated_branch", "mitigating_branch"]:
            unit_type = "core_definition"

        core_elements = item.get("core_elements")
        if not isinstance(core_elements, list):
            core_elements = []
        cond_elements = item.get("conditional_elements")
        if not isinstance(cond_elements, list):
            cond_elements = []

        sat_elements = item.get("satisfied_elements")
        if not isinstance(sat_elements, list):
            sat_elements = []
        miss_elements = item.get("missing_elements")
        if not isinstance(miss_elements, list):
            miss_elements = []
        contra_elements = item.get("contradicted_elements")
        if not isinstance(contra_elements, list):
            contra_elements = []

        # Parse statutory_structure
        stat_struct = item.get("statutory_structure")
        if not isinstance(stat_struct, dict):
            stat_struct = {
                "structural_unit_type": unit_type,
                "core_elements": core_elements,
                "conditional_elements": cond_elements,
                "aggravated_elements": [],
                "mitigating_elements": []
            }
        else:
            if "structural_unit_type" not in stat_struct:
                stat_struct["structural_unit_type"] = unit_type
            if "core_elements" not in stat_struct or not isinstance(stat_struct["core_elements"], list):
                stat_struct["core_elements"] = core_elements
            if "conditional_elements" not in stat_struct or not isinstance(stat_struct["conditional_elements"], list):
                stat_struct["conditional_elements"] = cond_elements
            if "aggravated_elements" not in stat_struct or not isinstance(stat_struct["aggravated_elements"], list):
                stat_struct["aggravated_elements"] = []
            if "mitigating_elements" not in stat_struct or not isinstance(stat_struct["mitigating_elements"], list):
                stat_struct["mitigating_elements"] = []

        # Parse prerequisite_evidence
        prereq_ev = item.get("prerequisite_evidence")
        if not isinstance(prereq_ev, list):
            prereq_ev = []
            for el in sat_elements:
                prereq_ev.append({
                    "requirement": el,
                    "requirement_type": "core",
                    "evidence_status": "satisfied",
                    "incident_evidence": "Directly established by incident facts.",
                    "reason": "Supported by facts."
                })
            for el in miss_elements:
                prereq_ev.append({
                    "requirement": el,
                    "requirement_type": "conditional" if unit_type == "conditional_proviso" else "core",
                    "evidence_status": "missing",
                    "incident_evidence": "Unstated in incident facts.",
                    "reason": "Statutory prerequisite not established."
                })
            for el in contra_elements:
                prereq_ev.append({
                    "requirement": el,
                    "requirement_type": "core",
                    "evidence_status": "contradicted",
                    "incident_evidence": "Contradicted by incident facts.",
                    "reason": "Statutory prerequisite explicitly contradicted."
                })

        # Parse relationship_analysis
        rel_analysis = item.get("relationship_analysis")
        if not isinstance(rel_analysis, dict):
            rel_analysis = {
                "relationship_type": "none",
                "related_candidate": "",
                "reason": "Independent candidate analysis; no conflict or suppression."
            }
        else:
            rel_type = rel_analysis.get("relationship_type", "none")
            if rel_type not in ["none", "specific_over_general", "ancillary_conduct", "mutually_exclusive", "alternative_branch", "independent_concurrent"]:
                rel_type = "none"
            rel_analysis["relationship_type"] = rel_type
            rel_analysis["related_candidate"] = str(rel_analysis.get("related_candidate", ""))
            rel_analysis["reason"] = str(rel_analysis.get("reason", "No relationship action taken."))

        reasoning_text = item.get("reasoning") or item.get("explanation") or ""
        explanation_text = item.get("explanation") or reasoning_text

        grounded_item = {
            "offence_type": offence_name,
            "section": str(doc_info.get("section", "")),
            "clause": doc_info.get("clause", ""),
            "title": doc_info.get("title", ""),
            "unit_type": unit_type,
            "applicability": applicability,
            "statutory_structure": stat_struct,
            "prerequisite_evidence": prereq_ev,
            "core_elements": core_elements,
            "conditional_elements": cond_elements,
            "statutory_elements": core_elements + cond_elements,
            "satisfied_elements": sat_elements,
            "missing_elements": miss_elements,
            "contradicted_elements": contra_elements,
            "relationship_analysis": rel_analysis,
            "reasoning": reasoning_text,
            "explanation": explanation_text,
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
        llm_client = MultiProviderLLMFailoverClient()

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

    # Attempt 2 (Retry on JSON parse failure if single client is passed directly)
    if parsed_json is None and not isinstance(llm_client, MultiProviderLLMFailoverClient):
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
            parse_error = str(err2)

    if parsed_json is None:
        print(f"[Legal Analyzer LLM Offline/Error] LLM generation unavailable: {parse_error}")
        provider_trace = getattr(llm_client, "last_execution_trace", [])
        return {
            "status": "analysis_unavailable",
            "analysis": [],
            "limitations": [
                "AI legal analysis is temporarily unavailable. The legal knowledge base was reached successfully, but the reasoning service is currently unavailable. Please try again shortly."
            ],
            "provider_trace": provider_trace
        }

    # Ground analysis against actual retrieved evidence
    result = validate_and_ground_analysis(parsed_json, context_obj)
    if hasattr(llm_client, "active_provider_info") and llm_client.active_provider_info:
        result["provider_used"] = llm_client.active_provider_info
    if hasattr(llm_client, "last_execution_trace") and llm_client.last_execution_trace:
        result["provider_trace"] = llm_client.last_execution_trace

    return result


