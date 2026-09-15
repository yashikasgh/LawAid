import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.rag.pipeline import run_pipeline, LEGAL_DISCLAIMER
from ai.rag.analysis.legal_analyzer import GroqLLMClient

def test_chat_flow(user_msg: str):
    print(f"\n--- USER MSG: {user_msg} ---")
    
    # 1. Run standard pipeline
    pipeline_res = run_pipeline(user_msg)
    print("Pipeline Status:", pipeline_res.get("status"))
    print("Analysis Items Count:", len(pipeline_res.get("analysis", [])))
    for a in pipeline_res.get("analysis", []):
        print(f"  Section: {a.get('section')}, Title: {a.get('title')}, Applicability: {a.get('applicability')}")
    
    # 2. Conversational Synthesis
    client = GroqLLMClient()
    analysis_items = pipeline_res.get("analysis", [])
    sanitized_incident = pipeline_res.get("sanitized_incident", user_msg)
    
    prompt = (
        "You are LawAid's compassionate, plain-language Legal AI Assistant specializing in Indian criminal law "
        "(Bharatiya Nyaya Sanhita, BNS 2023 & Bharatiya Nagarik Suraksha Sanhita, BNSS 2023).\n"
        "Summarize the grounded legal analysis below for the user in a clear, empathetic conversational response.\n\n"
        "STRICT CONSTRAINTS:\n"
        "1. Base your legal explanations ONLY on the provided GROUNDED BNS ANALYSIS data.\n"
        "2. Refer to BNS sections strictly as 'Section <section>' or 'BNS Section <section>'. NEVER mention or introduce Indian Penal Code (IPC) sections.\n"
        "3. Expand BNS strictly as 'Bharatiya Nyaya Sanhita, 2023' and BNSS strictly as 'Bharatiya Nagarik Suraksha Sanhita, 2023'. NEVER expand BNS as 'Bihar National Security'.\n"
        "4. Do NOT invent or hallucinate section numbers, punishments, or bailable/cognizable classifications not present in the grounded analysis.\n"
        "5. If applicability is marked 'uncertain' or 'not_supported', or if no grounded sections are available, state clearly that the provided information is insufficient or uncertain to confirm specific BNS section applicability.\n"
        "6. Do NOT present yourself as a lawyer or provide formal legal representation.\n"
        "7. Return ONLY valid JSON matching this schema:\n"
        '{\n  "reply": "string (conversational response text)"\n}\n\n'
        f"USER QUERY: {sanitized_incident}\n\n"
        f"GROUNDED BNS ANALYSIS:\n{pipeline_res.get('analysis')}\n"
    )
    
    raw = client.generate(prompt)
    import json
    parsed = json.loads(raw)
    reply = parsed.get("reply", "")
    print("\nSynthesized Conversational Reply:\n", reply)
    
    # Verification checks
    assert "Bihar National Security" not in reply, "BNS expanded incorrectly!"
    assert "IPC" not in reply and "Indian Penal Code" not in reply, "IPC leakage detected!"

if __name__ == "__main__":
    test_chat_flow("Someone stole my phone.")
    test_chat_flow("A man suddenly punched me in the face and caused my nose to bleed.")
