"""Conservative, source-grounded extraction for the lawyer workflow.

This intentionally extracts only text present in uploaded documents.  It is a
review aid, not a finding of fact or legal conclusion.
"""
import json
import re
from collections import defaultdict
from datetime import datetime

from app.services.fir_extractor import extract_fir_fields


DATE_RE = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b", re.I)
TIME_RE = re.compile(r"\b(?:\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?|\d{1,2}\s*(?:a\.?m\.?|p\.?m\.?))\b", re.I)
SECTION_RE = re.compile(r"\b(?:BNS\s*)?(?:Section|Sec\.?|S\.)\s*(\d{1,3}(?:\s*\(\s*\d+\s*\))?)\b", re.I)
MONEY_RE = re.compile(r"(?:₹|Rs\.?|INR)\s?([\d,]+(?:\.\d{1,2})?)", re.I)


def _source(document, match):
    start = max(0, match.start() - 140)
    end = min(len(document.extracted_text or ""), match.end() + 180)
    return {"document_id": document.id, "document_name": document.original_filename,
            "excerpt": (document.extracted_text or "")[start:end].strip()}


def _labelled(text, labels):
    for label in labels:
        match = re.search(rf"\b{label}\s*[:\-]\s*([^\n.]+)", text, re.I)
        if match:
            return match.group(1).strip(), match
    return None, None


def _normalized_date(value: str) -> str:
    """Store extractable dates in ISO form so event ordering is deterministic."""
    for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%d %B %Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    return value


def _structured_extraction(document, text: str) -> dict:
    """Use persisted FIR extraction when available, without making analysis depend on it."""
    try:
        saved = json.loads(document.structured_extraction or "")
        if isinstance(saved, dict):
            return saved
    except (TypeError, json.JSONDecodeError):
        pass
    return extract_fir_fields(text)


def _structured_source(document, value: dict | None) -> dict:
    return {
        "document_id": document.id,
        "document_name": document.original_filename,
        "page": (value or {}).get("source", {}).get("page"),
        "excerpt": (value or {}).get("source", {}).get("snippet", ""),
    }


def extract_case_information(documents):
    parties, locations, evidence, financial, facts, sections, timeline = [], [], [], [], [], [], []
    seen = defaultdict(set)
    for document in documents:
        text = document.extracted_text or ""
        if not text.strip():
            continue
            
        structured = _structured_extraction(document, text)
        fields = structured.get("rule_fields", {})
        complainant = fields.get("complainant")
        if complainant and complainant.get("value") and complainant["value"].lower() not in seen["complainant"]:
            seen["complainant"].add(complainant["value"].lower())
            parties.append({"role": "complainant", "name": complainant["value"], "source": _structured_source(document, complainant), "confidence": "explicit_in_document"})
        location = fields.get("occurrence_place")
        if location and location.get("value") and location["value"].lower() not in seen["location"]:
            seen["location"].add(location["value"].lower())
            locations.append({"text": location["value"], "source": _structured_source(document, location), "confidence": "explicit_in_document"})
        for section in structured.get("explicit_sections", []):
            number = section.get("section")
            if number and number not in seen["section"]:
                seen["section"].add(number)
                sections.append({"section_number": number, "title": section.get("act"), "confidence": "explicit_in_document", "source": _structured_source(document, section)})
        narrative = structured.get("incident_narrative", {})
        if narrative.get("value") and narrative["value"].lower() not in seen["fact"]:
            seen["fact"].add(narrative["value"].lower())
            facts.append({"text": narrative["value"][:1500], "source": _structured_source(document, narrative), "confidence": "explicit_in_document"})
        occurrence = fields.get("occurrence_date")
        if occurrence and occurrence.get("normalized_date"):
            timeline.append({"date": occurrence["normalized_date"], "time": None, "title": "Incident date recorded in FIR", "description": "Occurrence date explicitly labelled in the uploaded FIR.", "event_type": "Incident", "source_document_id": document.id, "source_document_name": document.original_filename, "source_reference": _structured_source(document, occurrence), "confidence": "explicit_in_document"})

        for role, labels in (("complainant", ["complainant", "informant"]), ("accused", ["accused", "respondent", "suspect"])):
            value, match = _labelled(text, labels)
            if value and value.lower() not in seen[role]:
                seen[role].add(value.lower()); parties.append({"role": role, "name": value, "source": _source(document, match), "confidence": "needs_review"})
        value, match = _labelled(text, ["place of occurrence", "incident location", "location", "place"])
        if value and value.lower() not in seen["location"]:
            seen["location"].add(value.lower()); locations.append({"text": value, "source": _source(document, match), "confidence": "needs_review"})
        for match in SECTION_RE.finditer(text):
            number = re.sub(r"\s+", "", match.group(1))
            if number not in seen["section"]:
                seen["section"].add(number); sections.append({"section_number": number, "title": None, "confidence": "explicit_in_document", "source": _source(document, match)})
        for match in MONEY_RE.finditer(text):
            raw = match.group(0)
            if raw not in seen["money"]:
                seen["money"].add(raw); financial.append({"label": "Amount mentioned in document", "raw_text": raw, "source": _source(document, match), "confidence": "needs_review"})
        for match in DATE_RE.finditer(text):
            nearby = text[max(0, match.start()-100):match.end()+160]
            if not re.search(r"incident|occurred|happened|assault|theft|complaint", nearby, re.I):
                continue
            normalized_date = _normalized_date(match.group(0))
            if any(event["date"] == normalized_date and event["source_document_id"] == document.id for event in timeline):
                continue
            timeline.append({"date": normalized_date, "time": (TIME_RE.search(nearby).group(0) if TIME_RE.search(nearby) else None), "title": "Incident date mentioned in document", "description": nearby.strip(), "event_type": "Incident", "source_document_id": document.id, "source_document_name": document.original_filename, "source_reference": _source(document, match), "confidence": "needs_review"})
        for line in (line.strip() for line in text.splitlines()):
            if line and re.search(r"evidence|seized|photograph|video|medical|weapon|receipt", line, re.I) and line.lower() not in seen["evidence"]:
                seen["evidence"].add(line.lower()); evidence.append({"name": line[:500], "source_document_id": document.id, "source_document_name": document.original_filename, "confidence": "needs_review"})
        for line in (line.strip() for line in text.splitlines()):
            if len(line) >= 30 and re.search(r"incident|accused|complainant|witness|stolen|assault|fraud", line, re.I):
                if line.lower() not in seen["fact"]:
                    seen["fact"].add(line.lower()); facts.append({"text": line[:1000], "source": {"document_id": document.id, "document_name": document.original_filename, "excerpt": line[:1000]}, "confidence": "needs_review"})
    return {"parties": parties, "locations": locations, "bns_sections": sections, "evidence": evidence, "financial_details": financial, "key_facts": facts, "timeline_candidates": timeline, "offence_type": None,
            "limitations": ["All extracted values require lawyer review. Fields not supported by uploaded text are left blank."]}
