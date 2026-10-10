"""Deterministic, source-linked FIR form extraction; no legal inference."""
import re
from datetime import datetime

SECTION = re.compile(r"\b(?:(BNS|IPC|BNSS)\s*)?(?:u/s|section|sec\.?|s\.)\s*(\d{1,3}(?:\s*/\s*\d{1,3})*(?:\s*\(\s*\d+\s*\))?)", re.I)

def _norm(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value.replace("\u00a0", " ")).strip().strip(" :.-")

def _source(text: str, start: int, end: int, page: int | None = None):
    return {"page": page, "snippet": text[max(0, start-100):min(len(text), end+180)].strip()}

def _label(text: str, labels: list[str]):
    for label in labels:
        match = re.search(rf"(?:{label})\s*[:\-]?\s*([^\n]{{2,180}})", text, re.I)
        if match:
            return {"value": _norm(match.group(1)), "raw": match.group(1).strip(), "source": _source(text, match.start(), match.end()), "confidence": "explicit"}
    return None

def _date(value: str):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try: return datetime.strptime(value, fmt).date().isoformat()
        except ValueError: pass
    return None


def _attach_page(value: dict | None, page_texts: list[dict]) -> None:
    """Attach a page only when the captured text is actually present there."""
    if not value:
        return
    needle = str(value.get("raw") or value.get("value") or "").strip()
    for page in page_texts:
        if needle and needle.casefold() in str(page.get("text") or "").casefold():
            value.setdefault("source", {})["page"] = page.get("page")
            return

def extract_fir_fields(text: str, page_texts: list[dict] | None = None) -> dict:
    """Extract labels and explicit sections only; preserve missing/ambiguous fields."""
    normalized = re.sub(r"\n{3,}", "\n\n", text)
    document_type = "FIR" if re.search(r"FIRST\s+INFORMATION\s+REPORT|F\.I\.R\.|प्रथम\s+सूचना", normalized, re.I) else "unknown"
    page_texts = page_texts or []
    fields = {
        "document_type": document_type,
        "fir_number": _label(normalized, [r"FIR\s*(?:No|Number)\.?", r"क्रमांक"]),
        "district": _label(normalized, [r"District", r"जिला"]),
        "police_station": _label(normalized, [r"P\.?S\.?", r"Police\s+Station", r"थाना"]),
        "registration_date": _label(normalized, [r"FIR\s+Registration\s+Date", r"Date(?!\s+of\s+occurrence)", r"दिनांक"]),
        "occurrence_date": _label(normalized, [r"Date\s+(?:From|of\s+Occurrence)", r"घटना\s+की\s+तिथि"]),
        "occurrence_place": _label(normalized, [r"Place\s+of\s+Occurrence", r"Place\s+of\s+occurence", r"घटना\s+स्थल"]),
        "complainant": _label(normalized, [r"Name\s+of\s+(?:Complainant|Informant)", r"Complainant", r"सूचक"]),
        "investigating_officer": _label(normalized, [r"Name\s+of\s+I\.O\.?", r"Investigating\s+Officer", r"जांच\s+अधिकारी"]),
        "action_taken": _label(normalized, [r"Action\s+Taken", r"कार्रवाई"]),
    }
    for key in ("registration_date", "occurrence_date"):
        if fields[key]: fields[key]["normalized_date"] = _date(fields[key]["value"])
    for value in fields.values():
        if isinstance(value, dict):
            _attach_page(value, page_texts)
    sections = []
    for match in SECTION.finditer(normalized):
        section = {"act": (match.group(1) or "unspecified").upper(), "section": re.sub(r"\s+", "", match.group(2)), "raw": match.group(0), "source": _source(normalized, match.start(), match.end()), "confidence": "explicit"}
        _attach_page(section, page_texts)
        sections.append(section)
    narrative = re.search(r"(?:12\.?\s*F\.?I\.?R\.?\s*Contents|FIR\s+Contents)(.*?)(?=\n\s*13\.?\s*Action|\Z)", normalized, re.I | re.S)
    warnings = []
    if document_type == "unknown": warnings.append("Document type could not be confidently identified as an FIR.")
    if not fields["fir_number"]: warnings.append("FIR number was not found.")
    if not narrative: warnings.append("FIR narrative was not found under a recognized form label.")
    narrative_value = {"value": _norm(narrative.group(1)) if narrative else None, "source": _source(normalized, narrative.start(), narrative.end()) if narrative else None}
    _attach_page(narrative_value, page_texts)
    return {"raw_text": text, "normalized_text": normalized, "rule_fields": fields, "explicit_sections": sections,
            "incident_narrative": narrative_value, "page_texts": page_texts, "warnings": warnings, "quality": "needs_review"}
