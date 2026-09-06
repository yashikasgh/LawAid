"""privacy_gateway.py — Lightweight Deterministic Privacy & Security Gateway for LawAid.

Located at: ai/security/privacy_gateway.py
"""

import re
from typing import Dict, List, Any, Optional, Tuple


# Regex patterns for sensitive identifiers
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
PAN_PATTERN = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b')
AADHAAR_PATTERN = re.compile(r'\b[2-9]\d{3}[\-\s]?\d{4}[\-\s]?\d{4}\b')
PHONE_PATTERN = re.compile(r'(?:\+?91[\-\s]?)?(?:0)?\b[6-9]\d{4}[\-\s]?\d{5}\b')


def detect_sensitive_data(text: str) -> List[Dict[str, Any]]:
    """
    Detect sensitive data occurrences in text using deterministic patterns.

    Returns list of metadata dicts (category, start, end) WITHOUT exposing raw PII text.
    """
    if not text or not isinstance(text, str):
        return []

    matches: List[Tuple[int, int, str]] = []

    # 1. Email matches
    for m in EMAIL_PATTERN.finditer(text):
        matches.append((m.start(), m.end(), "email"))

    # 2. PAN matches
    for m in PAN_PATTERN.finditer(text):
        matches.append((m.start(), m.end(), "pan"))

    # 3. Aadhaar matches
    for m in AADHAAR_PATTERN.finditer(text):
        # Ensure not overlapping with existing match
        if not any(start <= m.start() < end or start < m.end() <= end for start, end, _ in matches):
            matches.append((m.start(), m.end(), "aadhaar"))

    # 4. Phone matches
    for m in PHONE_PATTERN.finditer(text):
        # Ensure not overlapping with existing match
        if not any(start <= m.start() < end or start < m.end() <= end for start, end, _ in matches):
            matches.append((m.start(), m.end(), "phone"))

    # Sort matches by start position
    matches.sort(key=lambda x: x[0])

    detections = []
    for start, end, cat in matches:
        detections.append({
            "category": cat,
            "start": start,
            "end": end
        })

    return detections


def sanitize_text(text: str) -> Dict[str, Any]:
    """
    Sanitizes sensitive identifiers from text using deterministic local rules.

    Replaces detected sensitive values with consistent placeholders (e.g., EMAIL_1, PHONE_1).
    Guarantees that raw original sensitive values are NEVER returned in the output dictionary.

    Args:
        text (str): Input text string.

    Returns:
        dict:
            - sanitized_text (str): Text with sensitive identifiers replaced.
            - detections (list): List of category, placeholder, and match counts.
            - replacement_map (dict): Mapping of placeholder name -> category type metadata.
    """
    if not text or not isinstance(text, str):
        return {
            "sanitized_text": "" if text is None else str(text),
            "detections": [],
            "replacement_map": {}
        }

    # Find raw matches ordered by position
    raw_matches: List[Tuple[int, int, str, str]] = []  # (start, end, category, raw_val)

    for m in EMAIL_PATTERN.finditer(text):
        raw_matches.append((m.start(), m.end(), "email", m.group(0)))

    for m in PAN_PATTERN.finditer(text):
        raw_matches.append((m.start(), m.end(), "pan", m.group(0)))

    for m in AADHAAR_PATTERN.finditer(text):
        if not any(s <= m.start() < e or s < m.end() <= e for s, e, _, _ in raw_matches):
            raw_matches.append((m.start(), m.end(), "aadhaar", m.group(0)))

    for m in PHONE_PATTERN.finditer(text):
        if not any(s <= m.start() < e or s < m.end() <= e for s, e, _, _ in raw_matches):
            raw_matches.append((m.start(), m.end(), "phone", m.group(0)))

    if not raw_matches:
        return {
            "sanitized_text": text,
            "detections": [],
            "replacement_map": {}
        }

    # Sort matches by start position
    raw_matches.sort(key=lambda x: x[0])

    # Assign stable placeholders to unique sensitive strings
    category_counters: Dict[str, int] = {}
    val_to_placeholder: Dict[str, str] = {}
    placeholder_to_category: Dict[str, str] = {}
    placeholder_counts: Dict[str, int] = {}

    for _, _, category, raw_val in raw_matches:
        if raw_val not in val_to_placeholder:
            count = category_counters.get(category, 0) + 1
            category_counters[category] = count
            placeholder = f"{category.upper()}_{count}"
            val_to_placeholder[raw_val] = placeholder
            placeholder_to_category[placeholder] = category
            placeholder_counts[placeholder] = 1
        else:
            placeholder = val_to_placeholder[raw_val]
            placeholder_counts[placeholder] += 1

    # Perform replacements in sanitized text
    sanitized = text
    # Sort values to replace by length descending to prevent partial string replacement issues
    sorted_replacements = sorted(val_to_placeholder.items(), key=lambda x: len(x[0]), reverse=True)
    for raw_val, placeholder in sorted_replacements:
        sanitized = sanitized.replace(raw_val, placeholder)

    detections_summary = []
    for placeholder, category in placeholder_to_category.items():
        detections_summary.append({
            "category": category,
            "placeholder": placeholder,
            "count": placeholder_counts[placeholder]
        })

    return {
        "sanitized_text": sanitized,
        "detections": detections_summary,
        "replacement_map": placeholder_to_category
    }
