"""legal_analyzer.py — Structured LLM Legal Analysis Layer for LawAid RAG.

Located at: ai/rag/analysis/legal_analyzer.py
"""

import json
import os
import re
import sys
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

# Ensure analysis directory is on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from context_builder import build_legal_context


class Workload(str, Enum):
    LEGAL_CHAT = "LEGAL_CHAT"
    CITIZEN_FIR_ANALYSIS = "CITIZEN_FIR_ANALYSIS"
    POLICE_FIR_DRAFT = "POLICE_FIR_DRAFT"
    LAWYER_LEGAL_DRAFT = "LAWYER_LEGAL_DRAFT"


class ProviderHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    COOLING_DOWN = "COOLING_DOWN"
    AUTH_DISABLED = "AUTH_DISABLED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"


GROQ_SAFE_REQUEST_TOKEN_BUDGET = int(os.environ.get("GROQ_SAFE_REQUEST_TOKEN_BUDGET", "6700"))


def estimate_tokens(text: str) -> int:
    """Fast, dependency-free token count estimation (~4 characters or ~0.75 words per token)."""
    if not text:
        return 0
    return len(text) // 4 + 1


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
    def generate(self, prompt: str, max_tokens: Optional[int] = None, **kwargs) -> str:
        raise NotImplementedError("Subclasses must implement generate()")


class OllamaLLMClient(LLMClient):
    """Ollama-backed text generation client using structured outputs."""
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get("OLLAMA_LLM_MODEL")

    def generate(self, prompt: str, max_tokens: Optional[int] = None, **kwargs) -> str:
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
            opts = {"temperature": 0}
            if max_tokens is not None:
                opts["num_predict"] = max_tokens
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                format=LEGAL_ANALYSIS_SCHEMA,
                options=opts
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
        self.last_max_tokens = None
        self.max_tokens_received = []

    def generate(self, prompt: str, max_tokens: Optional[int] = None, **kwargs) -> str:
        self.prompts_received.append(prompt)
        self.last_max_tokens = max_tokens
        self.max_tokens_received.append(max_tokens)
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

    def generate(self, prompt: str, max_tokens: Optional[int] = None, **kwargs) -> str:
        try:
            workload = kwargs.get("workload")
            is_json_mode = (
                workload != Workload.LEGAL_CHAT
                or "json" in prompt.lower()
            )
            req_kwargs = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "timeout": 45.0
            }
            # Disabled server-side response_format for Groq as local parsing handles JSON safely
            # and Groq's server-side JSON validation causes HTTP 400 json_validate_failed on large prompts.
            if max_tokens is not None:
                req_kwargs["max_completion_tokens"] = max_tokens
            response = self.client.chat.completions.create(**req_kwargs)
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

    def generate(self, prompt: str, max_tokens: Optional[int] = None, **kwargs) -> str:
        try:
            import google.generativeai as genai
            config_kwargs = {
                "response_mime_type": "application/json",
                "temperature": 0.0
            }
            if max_tokens is not None:
                config_kwargs["max_output_tokens"] = max_tokens
            gen_config = genai.GenerationConfig(**config_kwargs)
            response = self.model.generate_content(prompt, generation_config=gen_config, request_options={"timeout": 45.0})
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

    def generate(self, prompt: str, max_tokens: Optional[int] = None, **kwargs) -> str:
        try:
            kwargs_req = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            if max_tokens is not None:
                kwargs_req["max_tokens"] = max_tokens
            response = self.client.chat.completions.create(**kwargs_req)
            if response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                return message.content if message and message.content else ""
            return ""
        except Exception as e:
            raise RuntimeError(f"Cerebras API text generation failed for model '{self.model_name}': {e}")


class OpenRouterLLMClient(LLMClient):
    """OpenRouter API text generation client adapter (OpenAI-compatible REST/SDK client)."""
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

        raw_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not raw_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is missing.")
        self.api_key = raw_key.strip().strip('"').strip("'")

        self.model_name = model_name or os.environ.get("OPENROUTER_MODEL") or "openrouter/free"
        self.base_url = "https://openrouter.ai/api/v1"

    def generate(self, prompt: str, max_tokens: Optional[int] = None, **kwargs) -> str:
        workload = kwargs.get("workload")
        is_json_mode = (
            workload != Workload.LEGAL_CHAT
            or "json" in prompt.lower()
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lawaid.app",
            "X-Title": "LawAid RAG Legal Analyzer"
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        # Disabled server-side response_format for OpenRouter as open models on free tier
        # silently return empty message content when response_format is requested.
        # Local parsing via _parse_json_from_llm handles JSON extraction safely.
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        try:
            try:
                from openai import OpenAI
                client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    timeout=45.0,
                    default_headers={
                        "HTTP-Referer": "https://lawaid.app",
                        "X-Title": "LawAid RAG Legal Analyzer"
                    }
                )
                sdk_kwargs = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                }
                if max_tokens is not None:
                    sdk_kwargs["max_tokens"] = max_tokens
                response = client.chat.completions.create(**sdk_kwargs)
                if response.choices and len(response.choices) > 0:
                    message = response.choices[0].message
                    return message.content if message and message.content else ""
                return ""
            except ImportError:
                try:
                    import requests
                    resp = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=45
                    )
                    if resp.status_code != 200:
                        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        msg = choices[0].get("message", {})
                        return msg.get("content", "")
                    return ""
                except ImportError:
                    import urllib.request
                    import urllib.error
                    req = urllib.request.Request(
                        f"{self.base_url}/chat/completions",
                        data=json.dumps(payload).encode("utf-8"),
                        headers=headers,
                        method="POST"
                    )
                    try:
                        with urllib.request.urlopen(req, timeout=45) as resp:
                            res_body = resp.read().decode("utf-8")
                            data = json.loads(res_body)
                            choices = data.get("choices", [])
                            if choices:
                                msg = choices[0].get("message", {})
                                return msg.get("content", "")
                            return ""
                    except urllib.error.HTTPError as http_err:
                        body = http_err.read().decode("utf-8", errors="ignore")
                        raise RuntimeError(f"HTTP {http_err.code}: {body}")
        except Exception as e:
            raise RuntimeError(f"OpenRouter API text generation failed for model '{self.model_name}': {e}")


class ProviderHealthTracker:
    """Thread-safe, in-memory circuit breaker and health tracker for LLM providers."""
    def __init__(self):
        self._lock = threading.Lock()
        self._health_map: Dict[str, Dict[str, Any]] = {}

    def get_provider_key(self, client: LLMClient) -> str:
        provider_name = client.__class__.__name__
        model_name = getattr(client, "model_name", "default")
        return f"{provider_name}:{model_name}"

    def is_healthy(self, client: LLMClient, prompt: str, max_tokens: Optional[int] = None) -> Tuple[bool, str]:
        key = self.get_provider_key(client)
        now = time.time()

        # Prompt size check for Groq models
        m_name = getattr(client, "model_name", "").lower()
        if isinstance(client, GroqLLMClient) or "gpt-oss" in m_name or "groq" in m_name:
            in_tokens = estimate_tokens(prompt)
            out_tokens = max_tokens if max_tokens is not None else 1300
            tot_tokens = in_tokens + out_tokens
            if tot_tokens > GROQ_SAFE_REQUEST_TOKEN_BUDGET:
                return False, f"Prompt size ({tot_tokens} est tokens) exceeds Groq safe limit ({GROQ_SAFE_REQUEST_TOKEN_BUDGET})."

        with self._lock:
            info = self._health_map.get(key, {})
            status = info.get("status", ProviderHealthStatus.HEALTHY)
            cooldown_until = info.get("cooldown_until", 0)

            if status == ProviderHealthStatus.AUTH_DISABLED:
                return False, "Provider authentication disabled (HTTP 401)."

            if status in (ProviderHealthStatus.COOLING_DOWN, ProviderHealthStatus.QUOTA_EXHAUSTED):
                if now < cooldown_until:
                    rem = round(cooldown_until - now, 1)
                    return False, f"Provider in {status} cooldown ({rem}s remaining)."
                else:
                    self._health_map[key] = {
                        "status": ProviderHealthStatus.HEALTHY,
                        "cooldown_until": 0,
                        "consecutive_failures": 0,
                        "last_failure_type": None
                    }
                    return True, "Healthy (cooldown expired)."

            return True, "Healthy"

    def record_success(self, client: LLMClient):
        key = self.get_provider_key(client)
        with self._lock:
            self._health_map[key] = {
                "status": ProviderHealthStatus.HEALTHY,
                "cooldown_until": 0,
                "consecutive_failures": 0,
                "last_failure_type": None
            }

    def record_failure(self, client: LLMClient, err_msg: str):
        key = self.get_provider_key(client)
        err_lower = err_msg.lower()
        now = time.time()
        error_category = _classify_llm_error(err_msg)

        with self._lock:
            info = self._health_map.get(key, {"consecutive_failures": 0})
            failures = info.get("consecutive_failures", 0) + 1

            if error_category == "payment_required" or "402" in err_msg:
                status = ProviderHealthStatus.QUOTA_EXHAUSTED
                cooldown_sec = 3600
            elif "401" in err_msg or "user not found" in err_lower or "unauthorized" in err_lower:
                status = ProviderHealthStatus.AUTH_DISABLED
                cooldown_sec = 86400 * 365
            elif error_category in ("rate_limited", "request_too_large") or "429" in err_msg or "413" in err_msg:
                status = ProviderHealthStatus.COOLING_DOWN
                cooldown_sec = 60
            else:
                status = ProviderHealthStatus.COOLING_DOWN
                cooldown_sec = 30

            self._health_map[key] = {
                "status": status,
                "cooldown_until": now + cooldown_sec,
                "consecutive_failures": failures,
                "last_failure_type": error_category
            }

    def reset(self) -> None:
        """Resets all health states (useful for testing and config reload)."""
        with self._lock:
            self._health_map.clear()

    def get_status(self, client_or_key: Union[LLMClient, str]) -> Tuple[ProviderHealthStatus, Optional[str]]:
        target_key = self.get_provider_key(client_or_key) if isinstance(client_or_key, LLMClient) else str(client_or_key)
        with self._lock:
            info = self._health_map.get(target_key)
            if not info:
                for k, v in self._health_map.items():
                    if k.endswith(f":{target_key}") or k == target_key:
                        info = v
                        break
            if not info:
                return ProviderHealthStatus.HEALTHY, None
            status = info.get("status", ProviderHealthStatus.HEALTHY)
            last_fail = info.get("last_failure_type")
            return status, last_fail

    def set_status(self, client: LLMClient, status: ProviderHealthStatus, cooldown_sec: int = 0):
        key = self.get_provider_key(client)
        with self._lock:
            self._health_map[key] = {
                "status": status,
                "cooldown_until": time.time() + cooldown_sec if cooldown_sec > 0 else 0,
                "consecutive_failures": 1 if status != ProviderHealthStatus.HEALTHY else 0,
                "last_failure_type": status.value
            }


GLOBAL_HEALTH_TRACKER = ProviderHealthTracker()


def _classify_llm_error(err_msg: str) -> str:
    """Classify LLM provider failure for clear trace diagnosis and skip handling."""
    err_lower = err_msg.lower()
    if "401" in err_msg or "user not found" in err_lower or "unauthorized" in err_lower or "invalid api key" in err_lower:
        return "auth_disabled"
    elif "402" in err_msg or "payment required" in err_lower or "insufficient_quota" in err_lower or "credit" in err_lower:
        return "payment_required"
    elif "429" in err_msg or "rate limit" in err_lower or "rate_limit" in err_lower or "quota" in err_lower or "resource_exhausted" in err_lower:
        return "rate_limited"
    elif "413" in err_msg or "too large" in err_lower or "context_length_exceeded" in err_lower or "request entity too large" in err_lower:
        return "request_too_large"
    elif "json" in err_lower or "parse" in err_lower or "validation" in err_lower:
        return "json_validation_failed"
    else:
        return "api_error"


class MultiProviderLLMFailoverClient(LLMClient):
    """
    Production-quality multi-provider LLM failover manager for LawAid RAG.

    Workload-aware routing & circuit breaker health tracking.
    """

    def __init__(self, providers: Optional[List[LLMClient]] = None, health_tracker: Optional[ProviderHealthTracker] = None):
        if providers is not None:
            self.providers = providers
        else:
            self.providers = self._build_default_provider_chain()
        self.health_tracker = health_tracker or GLOBAL_HEALTH_TRACKER
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
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")

        # 1. Groq GPT-OSS 20B
        if groq_key:
            try:
                chain.append(GroqLLMClient(api_key=groq_key, model_name="openai/gpt-oss-20b"))
            except Exception as e:
                print(f"[LLM Failover Config Warning] Groq 20B init skipped: {e}")

        # 2. Gemini 3.6 Flash
        if gemini_key:
            try:
                chain.append(GeminiLLMClient(api_key=gemini_key, model_name="gemini-3.6-flash"))
            except Exception as e:
                print(f"[LLM Failover Config Warning] Gemini 3.6 Flash init skipped: {e}")

        # 3. Groq GPT-OSS 120B
        if groq_key:
            try:
                chain.append(GroqLLMClient(api_key=groq_key, model_name="openai/gpt-oss-120b"))
            except Exception as e:
                print(f"[LLM Failover Config Warning] Groq 120B init skipped: {e}")

        # 4. OpenRouter Default Router
        if openrouter_key:
            try:
                chain.append(OpenRouterLLMClient(api_key=openrouter_key))
            except Exception as e:
                print(f"[LLM Failover Config Warning] OpenRouter default init skipped: {e}")

        # 5. Fallback to Ollama if configured and no cloud keys available
        if not chain and os.environ.get("OLLAMA_LLM_MODEL"):
            try:
                chain.append(OllamaLLMClient())
            except Exception:
                pass

        return chain

    def _get_ordered_providers(self, workload: Union[Workload, str], is_large: bool) -> List[LLMClient]:
        workload_str = str(workload.value if isinstance(workload, Workload) else workload).upper()

        groq_120b = None
        groq_20b = None
        gemini = None
        openrouter = None
        ollama = None

        for p in self.providers:
            p_name = p.__class__.__name__
            m_name = getattr(p, "model_name", "")
            is_20b = ("20b" in m_name and "120b" not in m_name)
            is_120b = ("120b" in m_name or (p_name == "GroqLLMClient" and not is_20b))

            if is_120b:
                if groq_120b is None:
                    groq_120b = p
            elif is_20b:
                if groq_20b is None:
                    groq_20b = p
            elif p_name == "GeminiLLMClient" or "gemini" in m_name:
                if gemini is None:
                    gemini = p
            elif p_name == "OpenRouterLLMClient" or "openrouter" in m_name:
                if openrouter is None:
                    openrouter = p
            elif p_name == "OllamaLLMClient" or "ollama" in m_name:
                if ollama is None:
                    ollama = p

        ordered = []

        if workload_str in ("LEGAL_CHAT", "LAWYER_LEGAL_DRAFT"):
            if is_large:
                # Large context: Gemini -> Groq 120B -> Groq 20B -> OpenRouter -> Ollama
                candidates = [gemini, groq_120b, groq_20b, openrouter, ollama]
            else:
                # Small context: Groq 120B -> Gemini -> Groq 20B -> OpenRouter -> Ollama
                candidates = [groq_120b, gemini, groq_20b, openrouter, ollama]
        elif workload_str in ("CITIZEN_FIR_ANALYSIS", "POLICE_FIR_DRAFT"):
            # Gemini -> Groq 120B -> Groq 20B -> OpenRouter -> Ollama
            candidates = [gemini, groq_120b, groq_20b, openrouter, ollama]
        else:
            candidates = [groq_120b, gemini, groq_20b, openrouter, ollama]

        for c in candidates:
            if c is not None and c not in ordered:
                ordered.append(c)

        for p in self.providers:
            if p not in ordered:
                ordered.append(p)

        return ordered

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        workload: Union[Workload, str] = Workload.CITIZEN_FIR_ANALYSIS
    ) -> str:
        self.last_execution_trace = []
        self.active_provider_info = {}

        if not self.providers:
            raise RuntimeError(
                "No LLM providers are configured in the failover chain. "
                "Please set GROQ_API_KEY, GEMINI_API_KEY, or OPENROUTER_API_KEY in the environment."
            )

        in_tokens = estimate_tokens(prompt)
        out_tokens = max_tokens if max_tokens is not None else 1300
        tot_est_tokens = in_tokens + out_tokens
        is_large = tot_est_tokens > GROQ_SAFE_REQUEST_TOKEN_BUDGET

        ordered_providers = self._get_ordered_providers(workload, is_large)

        for provider_client in ordered_providers:
            provider_name = provider_client.__class__.__name__
            model_name = getattr(provider_client, "model_name", "unknown")

            healthy, health_reason = self.health_tracker.is_healthy(provider_client, prompt, max_tokens)
            if not healthy:
                print(f"[LLM Failover Trace] Skipping {provider_name} ({model_name}): {health_reason}")
                self.last_execution_trace.append({
                    "provider": provider_name,
                    "model": model_name,
                    "status": "skipped",
                    "reason": health_reason
                })
                continue

            start_time = time.time()
            try:
                raw_out = provider_client.generate(prompt, max_tokens=max_tokens, workload=workload)
                latency_ms = round((time.time() - start_time) * 1000, 2)

                if not raw_out or not raw_out.strip():
                    raise RuntimeError("Provider returned empty string output.")

                # Conditionally validate JSON for structured JSON workloads or explicit JSON requests
                is_json_workload = (
                    workload in (Workload.CITIZEN_FIR_ANALYSIS, Workload.POLICE_FIR_DRAFT)
                    or "json" in prompt.lower()
                )
                if is_json_workload:
                    try:
                        parsed = _parse_json_from_llm(raw_out)
                        if not isinstance(parsed, dict):
                            raise ValueError("Output is not a valid JSON dictionary.")
                    except Exception as json_err:
                        raise RuntimeError(f"Output failed structured JSON validation: {json_err}")

                self.health_tracker.record_success(provider_client)
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

            except Exception as err:
                latency_ms = round((time.time() - start_time) * 1000, 2)
                err_msg = str(err)
                error_category = _classify_llm_error(err_msg)
                self.health_tracker.record_failure(provider_client, err_msg)
                print(f"[LLM Failover Trace] {provider_name} ({model_name}) failed [{error_category}] in {latency_ms}ms: {err_msg}")
                self.last_execution_trace.append({
                    "provider": provider_name,
                    "model": model_name,
                    "status": "failed",
                    "error_category": error_category,
                    "error": err_msg,
                    "latency_ms": latency_ms
                })

        raise RuntimeError("All LLM providers in failover chain failed.")


def construct_analysis_prompt(legal_context_obj: Dict[str, Any], minimal_schema: bool = False) -> str:
    """Construct a strict, evidence-grounded system prompt for multi-pass statutory applicability analysis."""
    incident = legal_context_obj.get("incident", {})
    raw_context = legal_context_obj.get("legal_context", [])

    formatted_context_sections = []
    seen_doc_ids = set()

    section_groups: Dict[str, Dict[str, Any]] = {}
    section_order: List[str] = []

    for group in raw_context:
        for doc in group.get("results", []):
            doc_id = doc.get("id") or doc.get("document_id") or ""
            if doc_id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc_id)

            sec_num = str(doc.get("section", "")).strip() or "unknown"
            target_text = doc.get("target_clause_text") or doc.get("text", "")
            snippet_text = target_text[:350] + ("..." if len(target_text) > 350 else "")

            if sec_num not in section_groups:
                sec_def = doc.get("section_definition", "")
                clean_sec_def = sec_def if sec_def and sec_def.strip() != target_text.strip() else ""
                if len(clean_sec_def) > 250:
                    clean_sec_def = clean_sec_def[:247] + "..."

                sec_entry = {
                    "section": doc.get("section", ""),
                    "title": doc.get("title", "")
                }
                if clean_sec_def:
                    sec_entry["section_definition"] = clean_sec_def
                sec_entry["clauses"] = []

                section_groups[sec_num] = sec_entry
                section_order.append(sec_num)

            clause_entry = {
                "id": doc_id,
                "clause": doc.get("clause", ""),
                "target_clause_text": snippet_text
            }
            sched_1 = doc.get("schedule_1", {})
            if isinstance(sched_1, dict):
                sched_offence = sched_1.get("offence", "")
                if sched_offence and sched_offence.strip():
                    clause_entry["schedule_1_offence"] = sched_offence.strip()

            section_groups[sec_num]["clauses"].append(clause_entry)

    for sec_num in section_order:
        formatted_context_sections.append(section_groups[sec_num])

    if minimal_schema:
        prompt = (
            "You are an expert legal analysis system for Indian criminal law (Bharatiya Nyaya Sanhita - BNS 2023).\n"
            "Analyze the provided INCIDENT FACTS strictly using ONLY the RETRIEVED BNS LEGAL CONTEXT provided below.\n\n"
            "STRICT GROUNDING & DOCUMENT ID RULES:\n"
            "1. Every document_id in your response MUST be copied EXACTLY as shown in the \"id\" field of RETRIEVED BNS LEGAL CONTEXT (copy the string in the \"id\" field EXACTLY).\n"
            "2. Do NOT return a bare section number such as \"303\" or \"304\". Return the full exact identifier string from the context.\n"
            "3. Do NOT invent, normalize, abbreviate, or transform document IDs.\n"
            "4. Only use document IDs that appear in the supplied RETRIEVED BNS LEGAL CONTEXT.\n"
            "5. EVALUATE FOUR GENERALIZED GROUNDING STATES:\n"
            "   - 'established' (or 'supported'): Mark ONLY if explicitly stated facts satisfy ALL mandatory statutory elements without requiring any further confirmation or unstated facts.\n"
            "   - 'potentially_applicable' (or 'uncertain'): Mark if some statutory elements fit, but one or more material statutory facts (e.g. carrying/wearing property, stealth/concealment, manner of force, intent) are missing or unstated.\n"
            "   - 'not_supported': Mark if stated facts explicitly fail or contradict required statutory elements (e.g. no property taken for theft, or no physical injury for hurt).\n"
            "   - 'insufficient_information': Mark if key facts are unstated so applicability cannot be assessed at all.\n"
            "6. STRICT CONSISTENCY RULE: If a provision is marked 'established', your reasoning MUST NOT state that material facts, intent requirements, or circumstances still need confirmation. If any statutory element requires confirmation, classify as 'potentially_applicable' or 'insufficient_information'.\n"
            "7. STATUTORY PUNISHMENT SAFEGUARD: Preserve statutory maximums and alternatives (e.g. 'may extend to X years' or 'up to X years'). Never state a maximum ceiling as a mandatory fixed sentence.\n"
            "8. Do NOT invent missing facts.\n\n"
            "JSON OUTPUT SCHEMA FORMAT:\n"
            "{\n"
            '  "status": "success",\n'
            '  "analysis": [\n'
            "    {\n"
            '      "document_id": "<exact_id_from_retrieved_context>",\n'
            '      "applicability": "established | potentially_applicable | not_supported | insufficient_information",\n'
            '      "reasoning": "string (1-2 sentence grounded explanation)"\n'
            "    }\n"
            "  ],\n"
            '  "limitations": []\n'
            "}\n\n"
            "INCIDENT FACTS:\n"
            f"{json.dumps(incident, indent=2)}\n\n"
            "RETRIEVED BNS LEGAL CONTEXT:\n"
            f"{json.dumps(formatted_context_sections, indent=2)}\n\n"
            "FINAL OUTPUT REQUIREMENT:\n"
            "Return ONLY a valid JSON object matching the JSON OUTPUT SCHEMA FORMAT. "
            "Your response MUST start directly with '{' and contain no preamble, conversational text, or markdown code blocks."
        )
        return prompt

    prompt = (
        "You are an expert legal analysis system for Indian criminal law (Bharatiya Nyaya Sanhita - BNS 2023).\n"
        "Analyze the provided INCIDENT FACTS strictly using ONLY the RETRIEVED BNS LEGAL CONTEXT provided below.\n\n"
        "STRICT GROUNDING & APPLICABILITY RULES:\n"
        "Evaluate statutory scope of each candidate section against stated facts.\n"
        "Do NOT equate generic words like 'property' or 'injury' without satisfying statutory scope.\n"
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
        "- If the property value is UNSTATED or MISSING from the facts, mark that specific proviso candidate document as 'uncertain' or 'not_supported'.\n"
        "- Section 331 BNS requires lurking house-trespass or house-breaking (active concealment, stealth, breaking doors/windows/locks, or forcible entry). Unauthorized entry into a house alone constitutes house-trespass under Section 329. If the incident facts state unauthorized entry without affirmative evidence of lurking or breaking, mark Section 329 as 'supported' and mark Section 331 as 'uncertain' or 'not_supported'.\n\n"
        "PASS 4 — STRICT APPLICABILITY DECISION:\n"
        "- 'supported': ALL mandatory core elements affirmatively satisfied, NO mandatory core element contradicted, required mens rea supported by facts, required capacity/relationship supported when required.\n"
        "- 'not_supported': Mandatory requirement explicitly contradicted OR a mandatory special prerequisite (such as special capacity, specific object/instrumentality, or specific statutory outcome) is absent from the stated incident facts.\n"
        "- 'uncertain': Material requirement could be true but incident simply lacks enough information to establish it.\n"
        "- Be conservative with 'supported'. Do NOT convert every unknown into 'not_supported' automatically. Preserve 'uncertain' where appropriate.\n\n"
        "PASS 5 — CANDIDATE RELATIONSHIP ANALYSIS:\n"
        "After evaluating candidates independently, perform a separate generic relationship analysis across retrieved candidates:\n"
        "- Determine candidate relationships (specific_over_general, ancillary_conduct, mutually_exclusive, etc.).\n"
        "- Only suppress a candidate when statutory text AND incident facts justify that relationship.\n"
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
        f"{json.dumps(formatted_context_sections, indent=2)}\n\n"
        "FINAL OUTPUT REQUIREMENT:\n"
        "Return ONLY a valid JSON object matching the JSON OUTPUT SCHEMA FORMAT. "
        "Your response MUST start directly with '{' and contain no preamble, conversational text, or markdown code blocks."
    )
    return prompt


def _parse_json_from_llm(raw_text: str) -> Dict[str, Any]:
    """Clean markdown formatting, extract JSON object boundaries, and parse JSON from raw LLM output."""
    if not raw_text or not str(raw_text).strip():
        raise ValueError("Raw LLM output is empty.")
    cleaned = str(raw_text).strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        cleaned = cleaned[start_idx:end_idx + 1]

    try:
        return json.loads(cleaned)
    except Exception:
        # Trailing comma cleanup before closing braces/brackets
        repaired = re.sub(r',\s*([\}\]])', r'\1', cleaned)
        return json.loads(repaired)


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
        if doc_id and doc_id not in doc_map:
            for k in doc_map.keys():
                if k == doc_id or k.startswith(f"{doc_id}_") or k.startswith(f"{doc_id}("):
                    doc_id = k
                    item["document_id"] = k
                    break

        if not doc_id or doc_id not in doc_map:
            limitations.append(
                f"Rejected analysis item for document_id '{item.get('document_id')}': evidence references document ID "
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

        if str(doc_info.get("section", "")) == "303" and sched_1 and punishment_val != "Not available in retrieved source":
            if sched_1.get("punishment") != "Rigorous imprisonment for 1 to 5 years.":
                punishment_val = (
                    "General/First Conviction: Imprisonment of either description up to 3 years, or fine, or both. "
                    "Repeat Conviction (second or subsequent): Rigorous imprisonment for 1 to 5 years, and fine. "
                    "Special Proviso (first conviction where stolen property value is less than 5,000 rupees and property/value is restored): Community service."
                )
                cognizable_val = "Cognizable for general theft. Non-cognizable if special proviso applies (value < 5,000 rupees & restored for first conviction)."
                bailable_val = "Non-bailable for general theft. Bailable if special proviso applies (value < 5,000 rupees & restored for first conviction)."
                court_val = "Any Magistrate."

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




def analyze_incident(
    ner_result: Dict[str, Any],
    retrieval_result: Dict[str, Any],
    llm_client: Optional[LLMClient] = None,
    max_tokens: Optional[int] = None,
    workload: Workload = Workload.CITIZEN_FIR_ANALYSIS
) -> Dict[str, Any]:
    """Execute legal analysis on incident facts and BNS retrieval context using structured LLM generation.

    Args:
        ner_result (dict): Structured output from extract_entities().
        retrieval_result (dict): Grouped output from retrieve_by_ner().
        llm_client (LLMClient, optional): Client instance for LLM generation.
        max_tokens (int, optional): Explicit completion token limit. If None, calculated dynamically.
        workload (Workload): Current execution workload type.

    Returns:
        dict: Structured legal analysis object with evidence grounding and limitation reports.
    """
    if llm_client is None:
        llm_client = MultiProviderLLMFailoverClient()

    context_obj = build_legal_context(ner_result, retrieval_result)
    use_minimal = (workload == Workload.LEGAL_CHAT)
    prompt = construct_analysis_prompt(context_obj, minimal_schema=use_minimal)

    if max_tokens is None:
        prompt_tokens = estimate_tokens(prompt)
        cand_count = len(retrieval_result) if isinstance(retrieval_result, list) else 1
        if use_minimal:
            max_tokens = min(2500, max(1200, GROQ_SAFE_REQUEST_TOKEN_BUDGET - prompt_tokens - 100))
        else:
            target_output = min(3000, max(1200, cand_count * 200 + 400))
            is_groq_120b = False
            if hasattr(llm_client, "model_name") and "120b" in str(getattr(llm_client, "model_name", "")).lower():
                is_groq_120b = True
            elif hasattr(llm_client, "active_provider_info"):
                active_info = getattr(llm_client, "active_provider_info", {})
                if isinstance(active_info, dict) and "120b" in str(active_info.get("model", "")).lower():
                    is_groq_120b = True

            if is_groq_120b:
                max_tokens = min(3000, max(800, GROQ_SAFE_REQUEST_TOKEN_BUDGET - prompt_tokens - 100))
            else:
                max_tokens = min(target_output, max(500, GROQ_SAFE_REQUEST_TOKEN_BUDGET - prompt_tokens - 100))

    raw_output = ""
    parsed_json = None
    parse_error = None

    # Attempt 1
    try:
        try:
            raw_output = llm_client.generate(prompt, max_tokens=max_tokens, workload=workload)
        except TypeError:
            raw_output = llm_client.generate(prompt)

        if workload == Workload.LEGAL_CHAT:
            p_info = getattr(llm_client, "active_provider_info", {})
            print(f"[LEGAL_CHAT DIAGNOSTIC] provider={p_info} raw_length={len(raw_output)} raw_prefix={repr(raw_output[:500])}")
        parsed_json = _parse_json_from_llm(raw_output)

        if workload == Workload.LEGAL_CHAT and parsed_json and isinstance(parsed_json, dict):
            p_analysis = parsed_json.get("analysis", [])
            p_ids = [item.get("document_id") for item in p_analysis if isinstance(item, dict)]
            p_apps = [item.get("applicability") for item in p_analysis if isinstance(item, dict)]
            print(f"[LEGAL_CHAT DIAGNOSTIC] parsed_status={parsed_json.get('status')} parsed_items={len(p_analysis)} ids={p_ids} applicability={p_apps}")
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
            raw_output = llm_client.generate(retry_prompt, max_tokens=max_tokens, workload=workload)
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
    if workload == Workload.LEGAL_CHAT:
        g_analysis = result.get("analysis", [])
        g_ids = [item.get("evidence", [{}])[0].get("document_id") or item.get("section") for item in g_analysis if isinstance(item, dict)]
        print(f"[LEGAL_CHAT DIAGNOSTIC] grounded_items={len(g_analysis)} ids={g_ids} limitations={result.get('limitations', [])}")
    if hasattr(llm_client, "active_provider_info") and llm_client.active_provider_info:
        result["provider_used"] = llm_client.active_provider_info
    if hasattr(llm_client, "last_execution_trace") and llm_client.last_execution_trace:
        result["provider_trace"] = llm_client.last_execution_trace

    return result


