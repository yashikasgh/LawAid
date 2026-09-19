import re
from typing import Dict, Any

def clean_ocr_text(raw_text: str) -> str:
    """
    Normalizes common OCR spacing and layout anomalies without altering legal meaning.
    Splits concatenated words like 'InspectorofroadaccidentinAngul' -> 'Inspector of road accident in Angul'.
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text.strip()

    # 1. Known FIR header & label concatenations
    known_replacements = [
        (r'\bINFORMATIONREPORT\b', 'INFORMATION REPORT'),
        (r'\bFIRNo\b', 'FIR No.'),
        (r'\bPoliceStation\b', 'Police Station'),
        (r'\bDistrict\b', 'District: '),
        (r'\bDateof\b', 'Date of '),
        (r'\bTimeof\b', 'Time of '),
        (r'\bPlaceof\b', 'Place of '),
        (r'\bOdishaPolice\b', 'Odisha Police'),
        (r'\bDelhiPolice\b', 'Delhi Police'),
        (r'\bUPPolice\b', 'UP Police'),
        (r'\bInspectorof\b', 'Inspector of '),
    ]
    for pattern, repl in known_replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    # 2. Generic OCR word concatenation splitters (e.g., Inspectorofroad, roadaccident, inAngul)
    text = re.sub(r'\b([A-Za-z]+)of([a-z]+)', r'\1 of \2', text)
    text = re.sub(r'\b([a-z]+)road([a-z]+)', r'\1 road \2', text, flags=re.IGNORECASE)
    text = re.sub(r'\b([a-z]+)accident([a-z]+)', r'\1 accident \2', text, flags=re.IGNORECASE)
    text = re.sub(r'\b([a-z]+)in([A-Z][a-z]+)', r'\1 in \2', text)

    # 3. Insert space between lowercase letter and uppercase letter (e.g. Inspectorofroad -> Inspector of road)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

    # 4. Insert space between digit and uppercase letter (e.g. 2022Odisha -> 2022 Odisha)
    text = re.sub(r'([0-9]{2,4})([A-Z][a-z]+)', r'\1 \2', text)

    # 5. Insert space between letter/digit and colon if concatenated
    text = re.sub(r'([a-zA-Z0-9])(:)([a-zA-Z0-9])', r'\1: \3', text)

    # 4. Clean multiple spaces and normalize line breaks
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.splitlines()]
    return "\n".join([l for l in lines if l])


def extract_fir_metadata(cleaned_text: str) -> Dict[str, str]:
    """
    Extracts structured FIR metadata fields from text if present.
    If a field is not present or cannot be extracted with high confidence,
    explicitly returns 'Not stated in the FIR'.
    """
    if not cleaned_text or len(cleaned_text.strip()) < 10:
        return {
            "fir_number": "Not stated in the FIR",
            "police_station": "Not stated in the FIR",
            "district": "Not stated in the FIR",
            "date_of_report": "Not stated in the FIR",
            "date_time_of_occurrence": "Not stated in the FIR",
            "informant": "Not stated in the FIR",
            "accused_details": "Not stated in the FIR",
            "place_of_occurrence": "Not stated in the FIR",
            "injuries_damage": "Not stated in the FIR",
            "witnesses": "Not stated in the FIR"
        }

    known_headers = [
        "police station", "district", "fir", "date", "time", "place of occurrence",
        "informant", "complainant", "accused", "witness", "injuries", "property", "place"
    ]

    def _extract_regex(patterns: list) -> str:
        for pat in patterns:
            m = re.search(pat, cleaned_text, re.IGNORECASE)
            if m and m.group(1).strip():
                val = m.group(1).strip()
                # Clean leading and trailing punctuation and quotes
                val = re.sub(r'^[,\s.:;\-\'\"\(\)]+', '', val).strip()
                val = re.sub(r'[,\s.:;\-\'\"\(\)]+$', '', val).strip()

                val_lower = val.lower()
                invalid_phrases = ["details", "'s details", "information", "particulars", "n/a", "nil", "none", "not known", "not specified", "unknown"]
                if val_lower in invalid_phrases or val_lower.startswith("'s ") or len(val) < 3:
                    continue

                # Reject matches that bleed into subsequent section headers
                if any(val_lower.startswith(h + ":") or val_lower.startswith(h + " :") for h in known_headers):
                    continue

                return val
        return "Not stated in the FIR"

    fir_number = _extract_regex([
        r'FIR\s*(?:No\.?|Number)\s*[:\-]?\s*([0-9]+/[0-9]{2,4}(?=[A-Za-z\s]|$)|[A-Za-z0-9/\-]+?\b)',
        r'FIR\s*[:\-]\s*([0-9]+/[0-9]{2,4}(?=[A-Za-z\s]|$)|[A-Za-z0-9/\-]+?\b)',
    ])

    police_station = _extract_regex([
        r'Police\s*Station\s*(?:\'s\s*Name|\'s\s*Details|Name|Details)?\s*[:\-]?\s*([A-Za-z0-9\s,]+?)(?=\n|District|FIR|Date|Time|$)',
        r'P\.S\.?\s*[:\-]?\s*([A-Za-z0-9\s,]+?)(?=\n|District|FIR|Date|Time|$)',
    ])

    district = _extract_regex([
        r'District\s*[:\-]?\s*([A-Za-z0-9\s]+?)(?=\n|State|P\.S|FIR|Date|$)',
        r'Dist\.?\s*[:\-]?\s*([A-Za-z0-9\s]+?)(?=\n|State|P\.S|FIR|Date|$)',
    ])

    date_of_report = _extract_regex([
        r'(?:Date\s*of\s*FIR|Date\s*of\s*Report|FIR\s*Date)\s*[:\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4})',
        r'Dated?\s*[:\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4})',
        r'\b([0-9]{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+[0-9]{2,4})\b',
    ])

    date_time_of_occurrence = _extract_regex([
        r'(?:Date\s*(?:and|&)?\s*Time\s*of\s*Occurrence|Occurrence\s*Date\s*and\s*Time)\s*(?:Details)?\s*[:\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4}[^\n]*)',
        r'Occurrence\s*[:\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4}[^\n]*)',
    ])

    informant = _extract_regex([
        r'(?:Informant|Complainant)\s*(?:\'s\s*Details|\'s\s*Name|Details|Name)?\s*[:\-]?\s*([^\n]+?)(?=\n|Place|Police|District|FIR|Date|Time|$)',
    ])

    accused_details = _extract_regex([
        r'Accused\s*(?:Details|Person)?\s*[:\-]?\s*([^\n]+?)(?=\n|Place|Police|District|FIR|Date|Time|$)',
        r'Suspect\s*[:\-]?\s*([^\n]+?)(?=\n|Place|Police|District|FIR|Date|Time|$)',
    ])

    place_of_occurrence = _extract_regex([
        r'Place\s*of\s*Occurrence\s*[:\-]?\s*([^\n]+)',
        r'P\.O\.?\s*[:\-]?\s*([^\n]+)',
    ])

    injuries_damage = _extract_regex([
        r'(?:Injuries|Damage|Stolen\s*Property|Property)\s*[:\-]?\s*([^\n]+)',
    ])

    witnesses = _extract_regex([
        r'Witness(?:es)?\s*[:\-]?\s*([^\n]+)',
    ])

    return {
        "fir_number": fir_number,
        "police_station": police_station,
        "district": district,
        "date_of_report": date_of_report,
        "date_time_of_occurrence": date_time_of_occurrence,
        "informant": informant,
        "accused_details": accused_details,
        "place_of_occurrence": place_of_occurrence,
        "injuries_damage": injuries_damage,
        "witnesses": witnesses
    }
