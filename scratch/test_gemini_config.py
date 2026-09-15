import google.generativeai as genai
import os

print("Testing google.generativeai configuration...")
model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
print("Model name:", model_name)

config = genai.GenerationConfig(
    response_mime_type="application/json",
    temperature=0.0
)
print("GenerationConfig created successfully with response_mime_type='application/json'")
