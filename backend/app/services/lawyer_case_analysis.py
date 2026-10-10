"""Conservative, source-grounded extraction for the lawyer workflow.

This intentionally extracts only text present in uploaded documents.  It is a
review aid, not a finding of fact or legal conclusion.
"""
import re
from collections import defaultdict
from datetime import datetime


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


def extract_case_information(documents):
    parties, locations, evidence, financial, facts, sections, timeline = [], [], [], [], [], [], []
    seen = defaultdict(set)
    for document in documents:
        text = document.extracted_text or ""
        if not text.strip():
            continue
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
            title = "Date mentioned in document"
            nearby = text[max(0, match.start()-100):match.end()+160]
            kind = "Incident" if re.search(r"incident|occurred|happened|assault|theft|complaint", nearby, re.I) else "Investigation"
            timeline.append({"date": _normalized_date(match.group(0)), "time": (TIME_RE.search(nearby).group(0) if TIME_RE.search(nearby) else None), "title": title, "description": nearby.strip(), "event_type": kind, "source_document_id": document.id, "source_document_name": document.original_filename, "source_reference": _source(document, match), "confidence": "needs_review"})
        for line in (line.strip() for line in text.splitlines()):
            if line and re.search(r"evidence|seized|photograph|video|medical|weapon|receipt", line, re.I) and line.lower() not in seen["evidence"]:
                seen["evidence"].add(line.lower()); evidence.append({"name": line[:500], "source_document_id": document.id, "source_document_name": document.original_filename, "confidence": "needs_review"})
        for line in (line.strip() for line in text.splitlines()):
            if len(line) >= 30 and re.search(r"incident|accused|complainant|witness|stolen|assault|fraud", line, re.I):
                if line.lower() not in seen["fact"]:
                    seen["fact"].add(line.lower()); facts.append({"text": line[:1000], "source": {"document_id": document.id, "document_name": document.original_filename, "excerpt": line[:1000]}, "confidence": "needs_review"})
    return {"parties": parties, "locations": locations, "bns_sections": sections, "evidence": evidence, "financial_details": financial, "key_facts": facts, "timeline_candidates": timeline, "offence_type": None,
            "limitations": ["All extracted values require lawyer review. Fields not supported by uploaded text are left blank."]}
