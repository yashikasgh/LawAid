import re
import json

def generate_benchmark_mock_queries(prompt: str) -> str:
    """
    Generates a deterministic JSON string containing adaptive, multi-perspective queries
    for query-generator prompts in BenchmarkLLMClient.
    
    Fully section-agnostic, generic, and derived purely from the incident text in the prompt.
    Does NOT use case IDs, section numbers, section maps, or invented facts.
    """
    # Extract raw text from prompt
    raw_text_match = re.search(r"INCIDENT RAW TEXT:\s*(.*?)(?=\n\nNER OFFENCE TYPES:|\Z)", prompt, re.DOTALL)
    if not raw_text_match:
        raw_text = prompt
    else:
        raw_text = raw_text_match.group(1).strip()
        
    text_lower = raw_text.lower()
    
    # Strip leading date/time phrase
    clean_text = re.sub(r"^on\s+\d{1,2}\s+[a-z]+\s+\d{4},?\s*", "", raw_text, flags=re.IGNORECASE).strip()
    if not clean_text:
        clean_text = raw_text

    # Replace numeric digits and commas cleanly
    clean_text_safe = re.sub(r"[\d,]+", " ", clean_text)
    clean_text_safe = re.sub(r"\s+", " ", clean_text_safe).strip()
    clean_text_lower = clean_text_safe.lower()
    
    queries = []
    
    # 1. Incident Context Query (Sanitized lowercase incident text)
    queries.append({
        "query_type": "incident_context",
        "query": clean_text_lower
    })
    
    # 2. Derive Grounded Statutory Legal Concepts using patterns explicitly matching query_generator.py regexes
    legal_concepts = []
    
    if any(w in text_lower for w in ["stole", "took", "taking", "theft", "bicycle", "watch", "phone", "wallet", "ring", "cash", "jewel"]):
        legal_concepts.append("dishonest taking of movable property without consent")
    if any(w in text_lower for w in ["snatch", "snatched", "grabbing", "grabbed", "chain", "neck"]):
        legal_concepts.append("theft committed by sudden snatching of property")
    if any(w in text_lower for w in ["house", "residence", "dwelling", "shop", "building", "window", "door", "room", "storage", "lock"]):
        legal_concepts.append("house trespass or breaking into building")
    if any(w in text_lower for w in ["slapped", "punched", "hit", "hurt", "pain", "injured", "injuries", "fist", "shoved"]):
        legal_concepts.append("voluntarily causing hurt or bodily pain")
    if any(w in text_lower for w in ["threatened", "threat", "demanded", "alarm", "kill", "burn", "knifepoint", "knife"]):
        legal_concepts.append("criminal intimidation by threatening injury")
    if any(w in text_lower for w in ["drove", "driving", "speeding", "car", "vehicle", "truck", "road", "motorcycle", "recklessly"]):
        legal_concepts.append("rash or negligent driving on public road endangering human life")
    if any(w in text_lower for w in ["induced", "promised", "fake", "job", "bank transfer", "cheated", "fraudulent"]):
        legal_concepts.append("cheating by fraudulent inducement to deliver property")
    if any(w in text_lower for w in ["entrusted", "warehouse", "manager", "laptop", "misappropriated"]):
        legal_concepts.append("dishonest misappropriation or breach of trust")
        
    if not legal_concepts:
        legal_concepts.append("dishonest taking of movable property")
        
    # Query 2: Primary Legal Concept
    queries.append({
        "query_type": "legal_concept",
        "query": legal_concepts[0]
    })
    
    # Query 3: Action Context (Distinct action phrase derived from incident text)
    words = clean_text_lower.split()
    if len(words) > 6:
        action_phrase = " ".join(words[:6])
    else:
        action_phrase = clean_text_lower

    queries.append({
        "query_type": "action_context",
        "query": action_phrase
    })
    
    # Adaptive Queries 4 & 5 for multi-concept / complex incidents
    if len(legal_concepts) > 1:
        queries.append({
            "query_type": "legal_concept",
            "query": legal_concepts[1]
        })
        
    if len(legal_concepts) > 2:
        queries.append({
            "query_type": "legal_concept",
            "query": legal_concepts[2]
        })

    # Ensure max 5 queries
    if len(queries) > 5:
        queries = queries[:5]

    return json.dumps({"queries": queries})

