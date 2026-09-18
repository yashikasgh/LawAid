import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ANALYSIS_DIR = PROJECT_ROOT / "ai" / "rag" / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from legal_analyzer import GeminiLLMClient, GroqLLMClient

print("==================================================")
print("TESTING API KEYS STATUS")
print("==================================================")

# 1. Test Gemini
try:
    gemini = GeminiLLMClient()
    print(f"Gemini Model initialized: {gemini.model_name}")
    resp = gemini.generate("Hello, reply with JSON: {\"status\": \"ok\"}")
    print("Gemini API Status: WORKING SUCCESSFUL!")
    print(f"Gemini Response: {resp[:200]}")
except Exception as e:
    print(f"Gemini API Status: EXHAUSTED / FAILED -> {e}")

print("--------------------------------------------------")

# 2. Test Groq
try:
    groq = GroqLLMClient()
    print(f"Groq Model initialized: {groq.model_name}")
    resp = groq.generate("Hello, reply with JSON: {\"status\": \"ok\"}")
    print("Groq API Status: WORKING SUCCESSFUL!")
    print(f"Groq Response: {resp[:200]}")
except Exception as e:
    print(f"Groq API Status: EXHAUSTED / FAILED -> {e}")

print("==================================================")
