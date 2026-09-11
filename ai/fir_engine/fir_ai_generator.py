"""fir_ai_generator.py — Grounded AI FIR Generator Service for LawAid.

Located at: ai/fir_engine/fir_ai_generator.py
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ANALYSIS_DIR = PROJECT_ROOT / "ai" / "rag" / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from ai.rag.analysis.legal_analyzer import GroqLLMClient, MultiProviderLLMFailoverClient, LLMClient


STRUCTURED_FIR_SCHEMA = {
    "district": "string (e.g. 'Not provided' or stated district)",
    "police_station": "string (e.g. 'Not provided' or stated police station)",
    "year": "string (e.g. '2026')",
    "fir_number": "string (e.g. 'Draft')",
    "fir_date": "string (e.g. '09/09/2026')",
    "acts_sections": [
        {
            "act": "Bharatiya Nyaya Sanhita, 2023",
            "sections": "string (e.g. '303' or 'Not provided')"
        }
    ],
    "occurrence": {
        "day": "string (e.g. 'Tuesday' or 'Not provided')",
        "date": "string (e.g. '08/09/2026' or 'Not provided')",
        "time": "string (e.g. '7:30 PM' or '19:30' or 'Not provided')"
    },
    "information_received": {
        "date": "string ('Not provided')",
        "time": "string ('Not provided')"
    },
    "general_diary": {
        "entry_numbers": "string ('Not provided')",
        "time": "string ('Not provided')"
    },
    "type_of_information": "string ('Not provided' or 'Written' or 'Oral')",
    "place_of_occurrence": {
        "direction_distance_from_ps": "string ('Not provided')",
        "beat_no": "string ('Not provided')",
        "address": "string (stated address/location or 'Not provided')",
        "outside_police_station": "string ('N/A')",
        "district": "string ('Not provided')"
    },
    "complainant": {
        "name": "string (stated name or 'Not provided')",
        "father_husband_name": "string ('Not provided')",
        "date_year_of_birth": "string ('Not provided')",
        "nationality": "string ('Not provided')",
        "passport_no": "string ('N/A')",
        "passport_date_of_issue": "string ('N/A')",
        "passport_place_of_issue": "string ('N/A')",
        "occupation": "string ('Not provided')",
        "address": "string ('Not provided')"
    },
    "accused_details": "string (e.g. 'Unknown male accused; identity not known at this stage.')",
    "delay_reason": "string ('Not provided')",
    "property_details": "string (stated stolen items, e.g. 'One mobile phone', or 'N/A')",
    "property_value": "string ('Unknown')",
    "inquest_ud_case": "string ('N/A')",
    "fir_contents": "string (formal, faithful narrative summary of stated incident facts)",
    "action_taken": "string ('To be verified by officer')",
    "officer": {
        "name": "string ('Not provided')",
        "rank": "string ('Not provided')",
        "number": "string ('Not provided')"
    },
    "complainant_signature": "string ('Not provided')",
    "dispatch_to_court": {
        "date": "string ('To be dispatched')",
        "time": "string ('To be dispatched')"
    }
}


def _extract_factual_heuristics(
    incident_text: str,
    reference_date: Optional[Any] = None
) -> Dict[str, str]:
    """Extracts factual incident attributes deterministically from statement text, including relative dates."""
    import datetime
    text = incident_text or ""

    if reference_date is None:
        reference_date = datetime.date.today()
    elif isinstance(reference_date, datetime.datetime):
        reference_date = reference_date.date()

    # 1. Date & Day extraction (explicit date or relative date expressions)
    date_str = "Not provided"
    day_str = "Not provided"

    # Check for explicit date strings (e.g. "8 September 2026" or "08/09/2026")
    m_date = re.search(r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b', text, re.I)
    if m_date:
        try:
            d_val = int(m_date.group(1))
            m_val = m_date.group(2)[:3]
            y_val = int(m_date.group(3))
            dt = datetime.datetime.strptime(f"{d_val} {m_val} {y_val}", "%d %b %Y").date()
            date_str = dt.strftime("%d/%m/%Y")
            day_str = dt.strftime("%A")
        except ValueError:
            date_str = m_date.group(0)
    else:
        m_slash = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b', text)
        if m_slash:
            try:
                dt = datetime.datetime.strptime(m_slash.group(0), "%d/%m/%Y").date()
                date_str = dt.strftime("%d/%m/%Y")
                day_str = dt.strftime("%A")
            except ValueError:
                date_str = m_slash.group(0)

    # Relative date expressions if no explicit date matched
    if date_str == "Not provided":
        lower_text = text.lower()
        target_dt = None
        if re.search(r'\b(day before yesterday)\b', lower_text):
            target_dt = reference_date - datetime.timedelta(days=2)
        elif re.search(r'\b(yesterday|last night)\b', lower_text):
            target_dt = reference_date - datetime.timedelta(days=1)
        elif re.search(r'\b(today|this morning|this afternoon|this evening)\b', lower_text):
            target_dt = reference_date

        if target_dt:
            date_str = target_dt.strftime("%d/%m/%Y")
            day_str = target_dt.strftime("%A")

    # 2. Time extraction (e.g. "7:30 PM" or "19:30")
    time_str = "Not provided"
    m_time = re.search(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\b', text)
    if m_time:
        time_str = m_time.group(1).strip()

    # 3. Location extraction (e.g. "near the local market")
    loc_str = "Not provided"
    m_loc = re.search(
        r'\b(?:near|at|around|in)\s+(?:the\s+)?([a-z0-9\s]+(?:market|road|street|station|bus stand|park|shop|colony|nagar|area|house|store|mall|place|junction|cross|village|city|bazaar))\b',
        text,
        re.I
    )
    if m_loc:
        loc_str = m_loc.group(0).strip()
    else:
        m_near = re.search(r'\b(?:near|in|at)\s+([a-zA-Z0-9\s]{3,30}?)(?=\s*(?:when|where|and|stole|punched|demanded|threatened|\.|\,|$))', text, re.I)
        if m_near:
            cand_loc = m_near.group(0).strip()
            if not re.search(r'\b(\d{1,2}:\d{2}|AM|PM|today|yesterday)\b', cand_loc, re.I):
                loc_str = cand_loc

    # 4. Stolen property extraction
    prop_str = "N/A"
    lower_text = text.lower()
    if "phone" in lower_text or "mobile" in lower_text:
        prop_str = "One mobile phone"
    elif "wallet" in lower_text or "purse" in lower_text:
        prop_str = "One wallet/purse"
    elif "vehicle" in lower_text or "motorcycle" in lower_text or "car" in lower_text:
        prop_str = "Vehicle"
    elif "stole" in lower_text or "took" in lower_text:
        prop_str = "Stolen property"

    # 5. Accused details extraction
    accused_str = "Unknown accused person(s)"
    if "unknown man" in lower_text or "unknown male" in lower_text:
        accused_str = "Unknown male accused; identity not known at this stage."
    elif "unknown woman" in lower_text or "unknown female" in lower_text:
        accused_str = "Unknown female accused; identity not known at this stage."

    return {
        "date": date_str,
        "day": day_str,
        "time": time_str,
        "location": loc_str,
        "property": prop_str,
        "accused": accused_str
    }


def generate_structured_fir(
    sanitized_incident: str,
    grounded_analysis: List[Dict[str, Any]],
    llm_client: Optional[LLMClient] = None,
    reference_date: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Generates structured IF1 FIR JSON grounded in incident facts and BNS legal analysis.

    Args:
        sanitized_incident (str): Incident description text.
        grounded_analysis (list): Grounded legal analysis items from run_pipeline().
        llm_client (LLMClient, optional): Client instance for LLM generation.
        reference_date (date/datetime, optional): Reference date context for relative date resolution.

    Returns:
        dict: Structured FIR JSON matching IF1 fields 1-15.
    """
    import datetime

    if llm_client is None:
        llm_client = MultiProviderLLMFailoverClient()

    # Extract ONLY supported BNS section numbers from grounded analysis
    raw_supported_sections = []
    for item in grounded_analysis:
        if item.get("applicability") == "supported":
            sec_num = str(item.get("section", "")).strip()
            m = re.search(r'\d+', sec_num)
            clean_sec = m.group(0) if m else sec_num
            if clean_sec and clean_sec not in raw_supported_sections:
                raw_supported_sections.append(clean_sec)

    if raw_supported_sections:
        acts_sections_grounded = [
            {
                "act": "Bharatiya Nyaya Sanhita, 2023",
                "sections": sec
            }
            for sec in raw_supported_sections
        ]
    else:
        # Zero grounded provisions from RAG — NEVER emit "Under Investigation"
        acts_sections_grounded = [
            {
                "act": "Bharatiya Nyaya Sanhita, 2023",
                "sections": "Not provided"
            }
        ]

    prompt = (
        "You are LawAid's official Police AI FIR Generation Assistant.\n"
        "Generate a structured First Information Report (IF1 FIR format) based strictly on the provided INCIDENT STATEMENT.\n\n"
        "STRICT ANTI-HALLUCINATION & GROUNDING CONSTRAINTS:\n"
        "1. Base all fields ONLY on facts explicitly stated in the INCIDENT STATEMENT.\n"
        "2. NEVER invent or fabricate names, dates, times, addresses, police stations, districts, accused identities, property values, weapons, or injuries that were not explicitly stated.\n"
        "3. For unstated or missing facts, use 'Not provided', 'Unknown', or 'N/A' as defined in the JSON schema. Do NOT fabricate fake names, GD numbers, beat numbers, or officer details.\n"
        "4. If the incident mentions property taken (e.g. mobile phone), put it in 'property_details' (e.g. 'One mobile phone'). Do NOT say 'N/A' if property was stolen.\n"
        "5. In the 'acts_sections' array, output the grounded sections provided below. If no section is provided, use 'Not provided'. NEVER output 'Under Investigation'.\n"
        "6. The 'fir_contents' field must be a formal, detailed narrative statement of the incident, strictly faithful to the provided text.\n"
        "7. Output ONLY valid JSON matching the exact schema below without markdown framing or commentary.\n\n"
        f"GROUNDED BNS SECTIONS:\n{json.dumps(acts_sections_grounded, indent=2)}\n\n"
        f"INCIDENT STATEMENT:\n{sanitized_incident}\n\n"
        "JSON OUTPUT SCHEMA:\n"
        f"{json.dumps(STRUCTURED_FIR_SCHEMA, indent=2)}\n"
    )

    fir_data = {}
    try:
        raw_out = llm_client.generate(prompt)
        cleaned = raw_out.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        fir_data = json.loads(cleaned)
    except Exception as e:
        print(f"[FIR Generator LLM Offline/Error] Using deterministic factual extraction: {e}")
        fir_data = {}

    # Heuristic extraction fallback when LLM is unavailable/offline or for post-processing relative dates
    heuristics = _extract_factual_heuristics(sanitized_incident, reference_date=reference_date)

    # Ensure required structure fallback
    if not isinstance(fir_data, dict) or not fir_data:
        fir_date_val = "09/09/2026"
        if isinstance(reference_date, (datetime.date, datetime.datetime)):
            fir_date_val = reference_date.strftime("%d/%m/%Y")

        fir_data = {
            "district": "Not provided",
            "police_station": "Not provided",
            "year": "2026",
            "fir_number": "Draft",
            "fir_date": fir_date_val,
            "acts_sections": acts_sections_grounded,
            "occurrence": {
                "day": heuristics["day"],
                "date": heuristics["date"],
                "date_from": heuristics["date"],
                "time": heuristics["time"],
                "time_from": heuristics["time"]
            },
            "information_received": {"date": "Not provided", "time": "Not provided"},
            "general_diary": {"entry_numbers": "Not provided", "time": "Not provided"},
            "type_of_information": "Not provided",
            "place_of_occurrence": {
                "direction_distance_from_ps": "Not provided",
                "beat_no": "Not provided",
                "address": heuristics["location"],
                "outside_police_station": "N/A",
                "district": "Not provided"
            },
            "complainant": {
                "name": "Not provided",
                "father_husband_name": "Not provided",
                "date_year_of_birth": "Not provided",
                "nationality": "Not provided",
                "passport_no": "N/A",
                "passport_date_of_issue": "N/A",
                "passport_place_of_issue": "N/A",
                "occupation": "Not provided",
                "address": "Not provided"
            },
            "accused_details": heuristics["accused"],
            "delay_reason": "Not provided",
            "property_details": heuristics["property"],
            "property_value": "Unknown",
            "inquest_ud_case": "N/A",
            "fir_contents": sanitized_incident,
            "action_taken": "Registered the case and took up the investigation",
            "officer": {"name": "Not provided", "rank": "Not provided", "number": "Not provided"},
            "complainant_signature": "Not provided",
            "dispatch_to_court": {"date": "To be dispatched", "time": "To be dispatched"}
        }
    else:
        # Enforce grounded acts_sections strictly (never allow 'Under Investigation')
        fir_data["acts_sections"] = acts_sections_grounded

        # Post-process occurrence fields if LLM emitted 'Not provided' or empty
        if isinstance(fir_data.get("occurrence"), dict):
            if fir_data["occurrence"].get("date") in ["Not provided", None, ""] and heuristics["date"] != "Not provided":
                fir_data["occurrence"]["date"] = heuristics["date"]
            if fir_data["occurrence"].get("date_from") in ["Not provided", None, ""] and heuristics["date"] != "Not provided":
                fir_data["occurrence"]["date_from"] = heuristics["date"]
            if fir_data["occurrence"].get("day") in ["Not provided", None, ""] and heuristics["day"] != "Not provided":
                fir_data["occurrence"]["day"] = heuristics["day"]
            if fir_data["occurrence"].get("time") in ["Not provided", None, ""] and heuristics["time"] != "Not provided":
                fir_data["occurrence"]["time"] = heuristics["time"]
            if fir_data["occurrence"].get("time_from") in ["Not provided", None, ""] and heuristics["time"] != "Not provided":
                fir_data["occurrence"]["time_from"] = heuristics["time"]


        # Post-process place_of_occurrence address if LLM emitted 'Not provided' or empty
        if isinstance(fir_data.get("place_of_occurrence"), dict):
            if fir_data["place_of_occurrence"].get("address") in ["Not provided", None, ""] and heuristics["location"] != "Not provided":
                fir_data["place_of_occurrence"]["address"] = heuristics["location"]

        # Post-process property_details if LLM emitted 'N/A' / 'Not provided' when property was stolen
        if fir_data.get("property_details") in ["N/A", "Not provided", None, ""] and heuristics["property"] != "N/A":
            fir_data["property_details"] = heuristics["property"]

    return fir_data
