"""ner_extractor.py — Hybrid legal-domain Named Entity Recognition system for LawAid RAG.

Located at: ai/rag/ner/ner_extractor.py
"""

import re
import sys
from typing import Dict, List, Any
import spacy

# Controlled BNS-aligned offence categories
CONTROLLED_OFFENCES = {
    "assault": [
        "assault", "assaulted", "assaulting", "physical assault", "physically attacked",
        "physically assault", "hit", "punched", "beat", "beaten", "struck", "slapped", "battered"
    ],
    "theft": [
        "theft", "stole", "stolen", "thief", "snatched", "snatching", "robbed", "robbery",
        "pilfered", "burglary"
    ],
    "criminal trespass": [
        "criminal trespass", "trespass", "trespassed", "trespassing", "house-breaking",
        "house breaking", "unlawfully entered", "illegal entry", "illegally entered",
        "illegally enter", "illegally entering"
    ],
    "murder": [
        "murder", "murdered", "killing", "killed", "homicide", "slain", "stabbed to death",
        "shot dead", "culpable homicide"
    ],
    "cheating": [
        "cheating", "cheated", "fraud", "defrauded", "scammed", "swindled", "impersonated",
        "impersonation"
    ],
    "criminal intimidation": [
        "criminal intimidation", "intimidation", "threatened", "threatened to kill",
        "extortion", "extorted"
    ]
}

# Reverse mapping from expression to controlled category
EXPRESSION_TO_OFFENCE = {}
for category, exprs in CONTROLLED_OFFENCES.items():
    for expr in exprs:
        EXPRESSION_TO_OFFENCE[expr.lower()] = category

LOCATION_KEYWORDS = [
    "place", "nagar", "chowk", "road", "street", "bagh", "market", "p.s.",
    "station", "park", "vihar", "colony", "sector", "block", "rohani", "rohini",
    "delhi", "noida", "mumbai"
]

DAYS_MONTHS = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "yesterday", "today", "tomorrow"
}

STOP_HONORIFICS_UNITS = {
    "the", "on", "sub", "inspector", "sub-inspector", "mr", "mrs", "dr", "sir",
    "lakhs", "lakh", "crores", "crore", "rupees", "inr", "something", "somewhere"
}


def _init_nlp_pipeline():
    """Initialize spaCy pipeline with EntityRuler placed before statistical ner."""
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' is missing. "
            "Please run 'python -m spacy download en_core_web_sm' to install it."
        )

    # Insert custom EntityRuler BEFORE statistical ner component
    if "entity_ruler" in nlp.pipe_names:
        nlp.remove_pipe("entity_ruler")

    ruler = nlp.add_pipe("entity_ruler", before="ner")

    ruler_patterns = []

    # 1. Controlled Offence Patterns
    for expr, category in EXPRESSION_TO_OFFENCE.items():
        pattern_tokens = []
        for word in expr.split():
            pattern_tokens.append({"LOWER": word})
        ruler_patterns.append({
            "label": "OFFENCE_TYPE",
            "pattern": pattern_tokens,
            "id": category
        })

    # 2. Location Span Patterns (e.g. "Patel Nagar", "Karol Bagh", "Chandni Chowk")
    ruler_patterns.append({
        "label": "LOCATION_SPAN",
        "pattern": [{"IS_TITLE": True, "OP": "+"}, {"LOWER": {"IN": LOCATION_KEYWORDS}}]
    })

    # 3. Explicit Victim Patterns ("victim X", "X, the victim", "victim was X", "victim is X")
    ruler_patterns.extend([
        {"label": "VICTIM", "pattern": [{"LOWER": "victim"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "VICTIM", "pattern": [{"IS_TITLE": True, "OP": "+"}, {"IS_PUNCT": True, "OP": "?"}, {"LOWER": "the"}, {"LOWER": "victim"}]},
        {"label": "VICTIM", "pattern": [{"LOWER": "victim"}, {"LOWER": "was"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "VICTIM", "pattern": [{"LOWER": "victim"}, {"LOWER": "is"}, {"IS_TITLE": True, "OP": "+"}]},
    ])

    # 4. Explicit Accused Patterns ("accused X", "X, the accused", "assaulted by X", "attacked by X", "X assaulted", etc.)
    ruler_patterns.extend([
        {"label": "ACCUSED", "pattern": [{"LOWER": "accused"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "ACCUSED", "pattern": [{"IS_TITLE": True, "OP": "+"}, {"IS_PUNCT": True, "OP": "?"}, {"LOWER": "the"}, {"LOWER": "accused"}]},
        {"label": "ACCUSED", "pattern": [{"LOWER": "accused"}, {"LOWER": "was"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "ACCUSED", "pattern": [{"LOWER": "accused"}, {"LOWER": "is"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "ACCUSED", "pattern": [{"LOWER": "assaulted"}, {"LOWER": "by"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "ACCUSED", "pattern": [{"LOWER": "attacked"}, {"LOWER": "by"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "ACCUSED", "pattern": [{"LOWER": "beaten"}, {"LOWER": "by"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "ACCUSED", "pattern": [{"LOWER": "threatened"}, {"LOWER": "by"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "ACCUSED", "pattern": [{"LOWER": "robbed"}, {"LOWER": "by"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "ACCUSED", "pattern": [{"LOWER": "killed"}, {"LOWER": "by"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "ACCUSED", "pattern": [{"LOWER": "cheated"}, {"LOWER": "by"}, {"IS_TITLE": True, "OP": "+"}]},
        {"label": "ACCUSED", "pattern": [{"IS_TITLE": True, "OP": "+"}, {"LOWER": "assaulted"}]},
    ])

    ruler.add_patterns(ruler_patterns)
    return nlp


# Global pipeline instance
_NLP = _init_nlp_pipeline()


def _clean_person_name(span_text: str, role_type: str) -> str:
    """Extract clean person name from a role entity span."""
    stopwords = {"victim", "accused", "the", "was", "is", "by", "assaulted", "attacked", "beaten", "threatened", "robbed", "killed", "cheated"}
    tokens = [t.strip(",. ") for t in span_text.split()]
    cleaned = [t for t in tokens if t.lower() not in stopwords and t]
    res = " ".join(cleaned).strip(",. ")
    return res if res else span_text


def extract_entities(text: str) -> Dict[str, Any]:
    """Extract legal entities and general entities into structured representation.

    Args:
        text (str): Input text paragraph describing incident.

    Returns:
        Dict[str, Any]: Structured entity representation.
    """
    if not text or not text.strip():
        return {
            "victims": [],
            "accused": [],
            "persons": [],
            "dates": [],
            "times": [],
            "locations": [],
            "organizations": [],
            "offence_types": [],
            "raw_text": text
        }

    doc = _NLP(text)

    victims = []
    accused = []
    persons = []
    dates = []
    times = []
    locations = []
    organizations = []
    offence_types = []

    # First pass: collect entities tagged by spaCy / EntityRuler
    for ent in doc.ents:
        lbl = ent.label_
        raw_val = ent.text.strip()

        if lbl == "VICTIM":
            cleaned_name = _clean_person_name(raw_val, "VICTIM")
            if cleaned_name and cleaned_name not in victims:
                victims.append(cleaned_name)
        elif lbl == "ACCUSED":
            cleaned_name = _clean_person_name(raw_val, "ACCUSED")
            if cleaned_name and cleaned_name not in accused:
                accused.append(cleaned_name)
        elif lbl == "OFFENCE_TYPE":
            category = ent.ent_id_ if ent.ent_id_ else EXPRESSION_TO_OFFENCE.get(raw_val.lower())
            if category and category not in offence_types:
                offence_types.append(category)
        elif lbl in ("LOCATION_SPAN", "GPE", "LOC"):
            if raw_val not in locations:
                locations.append(raw_val)
        elif lbl in ("ORG", "FAC"):
            if any(kw in raw_val.lower() for kw in LOCATION_KEYWORDS):
                if raw_val not in locations:
                    locations.append(raw_val)
            else:
                if raw_val not in organizations:
                    organizations.append(raw_val)
        elif lbl == "PERSON":
            if raw_val not in persons and raw_val not in victims and raw_val not in accused:
                persons.append(raw_val)
        elif lbl == "DATE":
            if raw_val not in dates:
                dates.append(raw_val)
        elif lbl == "TIME":
            if raw_val not in times:
                times.append(raw_val)

    # Secondary scan: Date pattern matching (e.g. "15th August 2026")
    date_regex = r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b'
    date_matches = re.findall(date_regex, text, re.IGNORECASE)
    for m in date_matches:
        if m not in dates:
            dates.append(m)

    # Secondary scan: Controlled offences regex fallback
    for expr, category in EXPRESSION_TO_OFFENCE.items():
        pattern = r'\b' + re.escape(expr) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            if category not in offence_types:
                offence_types.append(category)

    # Build token sets for location words and role names
    location_words = set(w.lower() for loc in locations for w in loc.split())
    role_names = set(victims + accused)

    # Secondary scan: Extract proper noun names for generic persons if missed by statistical NER
    for token in doc:
        txt = token.text.strip(",. ")
        if token.is_title and len(txt) > 2:
            txt_lower = txt.lower()
            if (txt_lower not in DAYS_MONTHS and
                txt_lower not in LOCATION_KEYWORDS and
                txt_lower not in STOP_HONORIFICS_UNITS and
                txt_lower not in location_words and
                txt not in locations and
                txt not in role_names and
                not any(txt in r for r in role_names)):
                if token.pos_ in ("PROPN", "NOUN"):
                    if txt not in persons:
                        persons.append(txt)

    # Clean up persons list ensuring no location words, location spans, or role names leak into persons
    filtered_persons = []
    for p in persons:
        p_lower = p.lower()
        if (p not in locations and
            p_lower not in location_words and
            p_lower not in STOP_HONORIFICS_UNITS and
            not any(p_lower in loc.lower() for loc in locations) and
            not any(loc.lower() in p_lower for loc in locations) and
            not any(p in r for r in role_names)):
            filtered_persons.append(p)

    # Clean up locations list ensuring no person names mislabeled as locations
    all_people = set(victims + accused + filtered_persons)
    filtered_locations = [loc for loc in locations if loc not in all_people]

    return {
        "victims": victims,
        "accused": accused,
        "persons": filtered_persons,
        "dates": dates,
        "times": times,
        "locations": filtered_locations,
        "organizations": organizations,
        "offence_types": offence_types,
        "raw_text": text
    }
