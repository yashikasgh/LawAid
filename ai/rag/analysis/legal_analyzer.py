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
                "timeout": 15.0
            }
            if is_json_mode:
                req_kwargs["response_format"] = {"type": "json_object"}

            # Give reasoning models (like gpt-oss-120b) sufficient room for reasoning + content
            if max_tokens is not None:
                req_kwargs["max_completion_tokens"] = max(max_tokens, 2500)
            else:
                req_kwargs["max_completion_tokens"] = 2500

            response = self.client.chat.completions.create(**req_kwargs)
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                message = choice.message
                content = message.content or ""
                finish_reason = getattr(choice, "finish_reason", None)

                # Keep message.content as the only user-facing final answer.
                if content and content.strip():
                    return content.strip()

                # Diagnostic check for empty content (do NOT fallback to or expose internal reasoning)
                has_reasoning = bool(getattr(message, "reasoning", None))
                has_tool_calls = bool(getattr(message, "tool_calls", None))
                print(f"[GroqLLMClient] Empty final content for {self.model_name}: finish_reason='{finish_reason}', has_reasoning={has_reasoning}, has_tool_calls={has_tool_calls}")

            return ""
        except Exception as e:
            raise RuntimeError(f"Groq API text generation failed for model '{self.model_name}': {e}")


class GeminiLLMClient(LLMClient):
    """Google Gemini API text generation client adapter using the official google.genai SDK."""
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

        self.model_name = model_name or os.environ.get("GEMINI_MODEL") or "gemini-3.6-flash"

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini client for model '{self.model_name}': {e}")

    def generate(self, prompt: str, max_tokens: Optional[int] = None, **kwargs) -> str:
        try:
            from google import genai
            from google.genai import types
            from google.genai.errors import APIError

            effective_max_tokens = max(max_tokens or 8192, 8192)
            config_kwargs = {
                "response_mime_type": "application/json",
                "temperature": 0.0,
                "max_output_tokens": effective_max_tokens,
                "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True)
            }

            gen_config = types.GenerateContentConfig(**config_kwargs)

            # Candidate model list bounded to active valid models
            candidate_models = [self.model_name]
            if "gemini-flash-latest" not in candidate_models:
                candidate_models.append("gemini-flash-latest")

            last_error = None
            for model_id in candidate_models:
                try:
                    response = self.client.models.generate_content(
                        model=model_id,
                        contents=prompt,
                        config=gen_config
                    )
                    
                    if response and response.candidates and len(response.candidates) > 0:
                        cand = response.candidates[0]
                        finish_reason = getattr(cand, "finish_reason", None)
                        finish_str = str(finish_reason).upper()
                        if "MAX_TOKENS" in finish_str or "LENGTH" in finish_str:
                            raise RuntimeError(f"Gemini generation for {model_id} hit output token limit ({finish_reason}).")

                    text = getattr(response, "text", "") or ""
                    if text and text.strip():
                        return text.strip()
                except APIError as api_err:
                    last_error = api_err
                    if getattr(api_err, "code", None) in (503, 404) or "503" in str(api_err) or "404" in str(api_err):
                        continue
                    raise api_err
                except Exception as ex:
                    last_error = ex
                    if "503" in str(ex) or "404" in str(ex):
                        continue
                    raise ex

            if last_error:
                raise last_error
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
                    timeout=30.0,
                    max_retries=0,
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
                    content = message.content or ""
                    if content and content.strip():
                        return content.strip()
                    return ""
                return ""
            except ImportError:
                try:
                    import requests
                    resp = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    if resp.status_code != 200:
                        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        msg = choices[0].get("message", {})
                        content = msg.get("content", "")
                        return content.strip() if content else ""
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
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            res_body = resp.read().decode("utf-8")
                            data = json.loads(res_body)
                            choices = data.get("choices", [])
                            if choices:
                                msg = choices[0].get("message", {})
                                content = msg.get("content", "")
                                return content.strip() if content else ""
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
            elif error_category in ("rate_limited", "request_too_large") or "429" in err_msg or "413" in err_msg or "tpd" in err_lower or "tokens per day" in err_lower:
                status = ProviderHealthStatus.COOLING_DOWN
                cooldown_sec = 15
            else:
                status = ProviderHealthStatus.COOLING_DOWN
                cooldown_sec = 15

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

        # 1. Groq GPT-OSS 120B
        if groq_key:
            try:
                chain.append(GroqLLMClient(api_key=groq_key, model_name="openai/gpt-oss-120b"))
            except Exception as e:
                print(f"[LLM Failover Config Warning] Groq 120B init skipped: {e}")

        # 2. Gemini
        if gemini_key:
            try:
                chain.append(GeminiLLMClient(api_key=gemini_key, model_name="gemini-3.6-flash"))
            except Exception as e:
                print(f"[LLM Failover Config Warning] Gemini init skipped: {e}")

        # 3. Groq GPT-OSS 20B
        if groq_key:
            try:
                chain.append(GroqLLMClient(api_key=groq_key, model_name="openai/gpt-oss-20b"))
            except Exception as e:
                print(f"[LLM Failover Config Warning] Groq 20B init skipped: {e}")

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

        # Fallback pass: If no provider actually executed because all were skipped on health check, force attempt on active non-disabled providers
        attempted_any = any(t.get("status") in ("success", "failed") for t in self.last_execution_trace)
        if not attempted_any:
            print("[LLM Failover Trace] All providers were skipped on health check. Forcing attempt on available providers...")
            for provider_client in ordered_providers:
                provider_name = provider_client.__class__.__name__
                model_name = getattr(provider_client, "model_name", "unknown")
                status, _ = self.health_tracker.get_status(provider_client)
                if status == ProviderHealthStatus.AUTH_DISABLED:
                    continue

                start_time = time.time()
                try:
                    raw_out = provider_client.generate(prompt, max_tokens=max_tokens, workload=workload)
                    latency_ms = round((time.time() - start_time) * 1000, 2)

                    if not raw_out or not raw_out.strip():
                        raise RuntimeError("Provider returned empty string output.")

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
                    print(f"[LLM Failover Trace] Forced fallback {provider_name} ({model_name}) failed [{error_category}] in {latency_ms}ms: {err_msg}")
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

            act_code = doc.get("act", "BNS")
            act_full = doc.get("act_name", "Bharatiya Nyaya Sanhita (BNS), 2023")
            sec_num = str(doc.get("section", "")).strip() or "unknown"
            sec_key = f"{act_code}_{sec_num}"
            target_text = doc.get("target_clause_text") or doc.get("text", "")
            snippet_text = target_text[:350] + ("..." if len(target_text) > 350 else "")

            if sec_key not in section_groups:
                sec_def = doc.get("section_definition", "")
                clean_sec_def = sec_def if sec_def and sec_def.strip() != target_text.strip() else ""
                if len(clean_sec_def) > 250:
                    clean_sec_def = clean_sec_def[:247] + "..."

                sec_entry = {
                    "act": act_code,
                    "act_name": act_full,
                    "section": doc.get("section", ""),
                    "title": doc.get("title", "")
                }
                if clean_sec_def:
                    sec_entry["section_definition"] = clean_sec_def
                sec_entry["clauses"] = []

                section_groups[sec_key] = sec_entry
                section_order.append(sec_key)

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

            section_groups[sec_key]["clauses"].append(clause_entry)

    for sec_key in section_order:
        formatted_context_sections.append(section_groups[sec_key])

    if minimal_schema:
        prompt = (
            "You are an expert legal analysis system for Indian criminal law (Bharatiya Nyaya Sanhita - BNS 2023 and Bharatiya Nagarik Suraksha Sanhita - BNSS 2023).\n"
            "Analyze the provided INCIDENT FACTS strictly using ONLY the RETRIEVED BNS LEGAL CONTEXT provided below.\n\n"
            "STRICT GROUNDING & DOCUMENT ID RULES:\n"
            "1. Indian criminal law strictly separates Substantive Offences (BNS) from Criminal Procedure (BNSS).\n"
            "   - BNS (Bharatiya Nyaya Sanhita) defines criminal offences, elements, and punishments (e.g. BNS Section 303 for Theft, BNS Section 173 for Bribery).\n"
            "   - BNSS (Bharatiya Nagarik Suraksha Sanhita) governs procedure, FIR registration, investigation, arrest, and bail (e.g. BNSS Section 173 for FIR filing/registration, BNSS Section 35/41 for arrest, BNSS Section 480 for bail).\n"
            "2. DO NOT mislabel procedural provisions as BNS offences. Use the explicit 'act' metadata field in RETRIEVED BNS LEGAL CONTEXT.\n"
            "3. Every document_id in your response MUST be copied EXACTLY as shown in the \"id\" field of RETRIEVED BNS LEGAL CONTEXT (copy the string in the \"id\" field EXACTLY).\n"
            "4. Do NOT return a bare section number such as \"303\" or \"304\". Return the full exact identifier string from the context.\n"
            "5. Do NOT invent, normalize, abbreviate, or transform document IDs.\n"
            "6. Only use document IDs that appear in the supplied RETRIEVED BNS LEGAL CONTEXT.\n"
            "7. EVALUATE FOUR GENERALIZED GROUNDING STATES:\n"
            "   - 'established' (or 'supported'): Mark ONLY if explicitly stated facts satisfy ALL mandatory statutory elements without requiring any further confirmation or unstated facts.\n"
            "   - 'potentially_applicable' (or 'uncertain'): Mark if some statutory elements fit, but one or more material statutory facts are missing or unstated.\n"
            "   - 'not_supported': Mark if stated facts explicitly fail or contradict required statutory elements.\n"
            "   - 'insufficient_information': Mark if key facts are unstated so applicability cannot be assessed at all.\n"
            "8. STRICT CONSISTENCY RULE: If a provision is marked 'established', your reasoning MUST NOT state that material facts, intent requirements, or circumstances still need confirmation.\n"
            "9. STATUTORY PUNISHMENT SAFEGUARD: Preserve statutory maximums and alternatives (e.g. 'may extend to X years' or 'up to X years'). Never state a maximum ceiling as a mandatory fixed sentence.\n"
            "10. Do NOT invent missing facts.\n\n"
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
        "You are an expert legal analysis system for Indian criminal law (Bharatiya Nyaya Sanhita - BNS 2023 and Bharatiya Nagarik Suraksha Sanhita - BNSS 2023).\n"
        "Analyze the provided INCIDENT FACTS strictly using ONLY the RETRIEVED BNS LEGAL CONTEXT provided below.\n\n"
        "STRICT GROUNDING & APPLICABILITY RULES:\n"
        "1. Indian criminal law strictly separates Substantive Offences (BNS) from Criminal Procedure (BNSS).\n"
        "   - BNS defines offences and punishments (e.g. Theft, Bribery, Assault).\n"
        "   - BNSS defines procedure, FIR registration, investigation, arrest, and bail rights (e.g. BNSS Section 173 for FIR registration upon information of a cognizable offence).\n"
        "2. DO NOT describe FIR registration or procedural rights as offences under BNS.\n"
        "3. STRICTLY DISTINGUISH ALLEGATIONS FROM PROVEN GUILT:\n"
        "   - An FIR contains allegations/claims filed with law enforcement. Never state that a person is guilty or that offences are conclusively proved.\n"
        "   - Use phrases such as 'Why Section X may apply' and 'relevant for consideration'.\n"
        "   - End plain_summary with: 'These are allegations/facts recorded in the FIR. They are not, by themselves, a final determination that an offence has been proved.'\n\n"
        "4. CONDITIONAL SECTIONS & STATUTORY SCOPE GATING:\n"
        "   - Section 134 BNS: Concerns assault/criminal force in an attempt to commit theft of property carried by a person. Mark conditional/uncertain unless facts show property was carried on person AND assault/force was used in theft attempt.\n"
        "   - Section 309 BNS (Robbery): Requires voluntary causing or attempting to cause death, hurt, wrongful restraint, or fear of instant death/hurt/restraint in connection with theft. Generic physical force alone does not automatically make theft robbery unless statutory tests are met.\n"
        "   - Section 307 BNS: Require statutory preparation for hurt/death/restraint/fear supported by facts.\n"
        "   - Section 317 BNS: Requires receiving, retaining, or concealing stolen property with knowledge or dishonest belief. Surface ONLY if FIR facts state receiving/retaining/concealing.\n"
        "   - Section 306 BNS: Surface ONLY if FIR facts show clerk or servant relationship.\n"
        "   - Section 329 BNS: Require statutory intent for criminal trespass.\n"
        "   - Section 330 BNS: Distinguish definition from punishment provisions.\n\n"
        "5. PUNISHMENT GROUNDING:\n"
        "   - Preserve statutory maximums and alternatives ('up to', 'or', 'and').\n"
        "   - For Section 303 (Theft), preserve all 3 branches: ordinary theft (up to 3 years/fine), repeat conviction (1 to 5 years/fine), and petty theft proviso (value < 5000 INR & restored for 1st conviction -> community service).\n\n"
        "6-PASS GENERIC STATUTORY APPLICABILITY REASONING:\n"
        "==================================================\n"
        "PASS 1 — STATUTORY REQUIREMENT EXTRACTION:\n"
        "Derive core legal elements, conditional elements, aggravated elements, and capacity requirements from the supplied statutory text.\n\n"
        "PASS 2 — EVIDENCE STATUS:\n"
        "Classify requirement evidence as SATISFIED, MISSING, CONTRADICTED, or NOT_APPLICABLE based strictly on stated facts.\n\n"
        "PASS 3 — CORE VS CONDITIONAL STRUCTURE:\n"
        "Preserve core vs conditional architecture. Do not invalidate core definition if conditional proviso is missing.\n\n"
        "PASS 4 — STRICT APPLICABILITY DECISION:\n"
        "Mark 'supported' ONLY if all mandatory core elements are satisfied. Mark 'uncertain' if material facts are unstated.\n\n"
        "PASS 5 — CANDIDATE RELATIONSHIP ANALYSIS:\n"
        "Analyze candidate relationships (specific_over_general, ancillary_conduct, etc.).\n\n"
        "PASS 6 — FINAL CLASSIFICATION & STRUCTURED OUTPUT:\n"
        "Return structured JSON matching the schema.\n\n"
        "JSON OUTPUT SCHEMA FORMAT:\n"
        "{\n"
        '  "status": "success",\n'
        '  "plain_summary": "Natural factual summary based specifically on uploaded FIR facts, ending with mandatory disclaimer: These are allegations/facts recorded in the FIR. They are not, by themselves, a final determination that an offence has been proved.",\n'
        '  "what_fir_alleges": "Plain-language summary of specific allegations recorded in the FIR.",\n'
        '  "analysis": [\n'
        "    {\n"
        '      "document_id": "string",\n'
        '      "section": "string",\n'
        '      "title": "string",\n'
        '      "unit_type": "core_definition | conditional_proviso | aggravated_branch | mitigating_branch",\n'
        '      "applicability": "supported | uncertain | not_supported",\n'
        '      "law_requires": ["Statutory requirement 1", "Statutory requirement 2"],\n'
        '      "fir_states": ["Corresponding fact from FIR"],\n'
        '      "why_may_apply": "Specific factual-legal explanation why Section X may apply",\n'
        '      "what_remains_uncertain": ["Missing or unverified fact 1"],\n'
        '      "assessment": "The allegations recorded in the FIR make Section X relevant for consideration; the FIR itself does not establish guilt.",\n'
        '      "reasoning": "string",\n'
        '      "explanation": "string"\n'
        "    }\n"
        "  ],\n"
        '  "unestablished_facts": [\n'
        '    "Whether the allegations are ultimately proved in court",\n'
        '    "Whether the accused possessed the required criminal intent"\n'
        '  ],\n'
        '  "clarifying_details": [\n'
        '    "Was the stolen property being carried on the victim\'s person?",\n'
        '    "Was physical force or weapon used during the incident?"\n'
        '  ],\n'
        '  "rights": [\n'
        '    "Under Section 173(2) BNSS, right to a free copy of the recorded FIR immediately.",\n'
        '    "Under Article 22(1) of the Constitution and Section 47 BNSS, right to consult legal counsel."\n'
        '  ],\n'
        '  "next_steps": [\n'
        '    "Preserve physical and digital FIR copies.",\n'
        '    "Verify dates, times, vehicle/person details in the FIR."\n'
        '  ],\n'
        '  "bottom_line": "Concise summary answering what FIR alleges, which provisions are relevant vs conditional, what is uncertain, and what to do next without declaring guilt.",\n'
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
    """Clean markdown wrappers and parse structured JSON. Fails boundedly on malformed text."""
    if not raw_text or not str(raw_text).strip():
        raise ValueError("Raw LLM output is empty.")

    cleaned = str(raw_text).strip()

    # Strip markdown code fences if present
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Extract JSON substring between outer braces
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        cleaned = cleaned[start_idx:end_idx + 1]

    # 1. Direct JSON parsing
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 2. Minor safe trailing comma repair
    try:
        repaired = re.sub(r',\s*([\}\]])', r'\1', cleaned)
        return json.loads(repaired)
    except Exception as err:
        raise ValueError(f"Could not parse valid JSON from LLM response: {err}")


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
            doc_id_lower = str(doc_id).lower().strip()
            for k in doc_map.keys():
                k_lower = k.lower()
                sec_in_k = str(doc_map[k][0].get("section", "")).strip()
                if (
                    k_lower == doc_id_lower
                    or k_lower == f"bns_{doc_id_lower}"
                    or doc_id_lower == f"bns_{k_lower}"
                    or k_lower.startswith(f"{doc_id_lower}_")
                    or k_lower.startswith(f"{doc_id_lower}(")
                    or (sec_in_k and sec_in_k in doc_id_lower)
                ):
                    doc_id = k
                    item["document_id"] = k
                    break

        if not doc_id or doc_id not in doc_map:
            # Fallback section number matching
            item_sec = str(item.get("section", "")).strip()
            sec_search = re.search(r'\b\d+\b', str(doc_id or item_sec))
            if sec_search:
                target_sec = sec_search.group()
                for k, (d_info, g_off) in doc_map.items():
                    if str(d_info.get("section", "")).strip() == target_sec:
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
        act_code = doc_info.get("act", "BNS")
        act_name = doc_info.get("act_name", "Bharatiya Nyaya Sanhita (BNS), 2023")

        reasoning_text = item.get("reasoning") or item.get("explanation") or ""
        explanation_text = item.get("explanation") or reasoning_text

        sec_num = str(doc_info.get("section", ""))
        law_requires = item.get("law_requires") or item.get("core_elements") or [doc_info.get("title", "Statutory requirement")]
        fir_states = item.get("fir_states") or item.get("satisfied_elements") or ["Facts stated in the FIR."]
        why_may_apply = item.get("why_may_apply") or reasoning_text or f"The allegations in the FIR correspond to the statutory scope of Section {sec_num}."
        what_remains_uncertain = item.get("what_remains_uncertain") or miss_elements or ["Further investigation and legal proceedings required."]
        raw_assessment = str(item.get("assessment") or "").strip()
        if not raw_assessment or "directly satisfies" in raw_assessment.lower() or "conclusively proves" in raw_assessment.lower() or "establishes guilt" in raw_assessment.lower():
            assessment = f"The allegations recorded in the FIR make Section {sec_num} relevant for consideration; the FIR itself does not establish guilt."
        else:
            assessment = raw_assessment

        grounded_item = {
            "offence_type": offence_name,
            "act": act_code,
            "act_name": act_name,
            "section": sec_num,
            "clause": doc_info.get("clause", ""),
            "title": doc_info.get("title", ""),
            "unit_type": unit_type,
            "applicability": applicability,
            "law_requires": law_requires,
            "fir_states": fir_states,
            "why_may_apply": why_may_apply,
            "what_remains_uncertain": what_remains_uncertain,
            "assessment": assessment,
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
                    "section": sec_num,
                    "clause": doc_info.get("clause", ""),
                    "rank": doc_info.get("rank")
                }
            ]
        }
        valid_analysis_items.append(grounded_item)

    res_dict = {
        "status": "success",
        "analysis": valid_analysis_items,
        "limitations": limitations
    }

    if parsed_data.get("plain_summary"):
        res_dict["plain_summary"] = parsed_data["plain_summary"]
    if parsed_data.get("what_fir_alleges"):
        res_dict["what_fir_alleges"] = parsed_data["what_fir_alleges"]
    if parsed_data.get("unestablished_facts"):
        res_dict["unestablished_facts"] = parsed_data["unestablished_facts"]
    if parsed_data.get("clarifying_details"):
        res_dict["clarifying_details"] = parsed_data["clarifying_details"]
    if parsed_data.get("rights"):
        res_dict["rights"] = parsed_data["rights"]
    if parsed_data.get("next_steps"):
        res_dict["next_steps"] = parsed_data["next_steps"]
    if parsed_data.get("bottom_line"):
        res_dict["bottom_line"] = parsed_data["bottom_line"]

    return res_dict




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


