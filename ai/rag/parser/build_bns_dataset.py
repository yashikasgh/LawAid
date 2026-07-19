"""build_bns_dataset.py — Download, parse, and structure the Bharatiya Nyaya Sanhita (BNS)
PDF into a JSON dataset suitable for RAG embeddings.

Located at: ai/rag/parser/build_bns_dataset.py
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

import requests
import fitz  # PyMuPDF

# ---------------------------------------------------------------------------
# Project-relative paths (BASE_DIR = ai/rag/)
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent

SOURCE_URL: str = "https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf"
RAW_PDF_PATH: Path = BASE_DIR / "data" / "raw" / "bns_raw.pdf"
OUTPUT_JSON_PATH: Path = BASE_DIR / "data" / "processed" / "bns_sections.json"
REVIEW_LOG_PATH: Path = BASE_DIR / "data" / "logs" / "bns_review.txt"

CHAPTER_HEADER_RE: re.Pattern[str] = re.compile(r"^\s*CHAPTER\s+[IVXLCDM]+\s*$", re.MULTILINE)


def download_pdf() -> None:
    """Download the BNS PDF from *SOURCE_URL* if it is not already cached locally."""
    if RAW_PDF_PATH.exists():
        print(f"[skip] {RAW_PDF_PATH} already downloaded.")
        return
    print(f"[fetch] downloading {SOURCE_URL} ...")
    resp = requests.get(SOURCE_URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    RAW_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PDF_PATH.write_bytes(resp.content)
    print(f"[fetch] saved {len(resp.content):,} bytes to {RAW_PDF_PATH}")


def extract_full_text() -> str:
    """Extract the full plain-text content of every page in the downloaded PDF."""
    doc = fitz.open(RAW_PDF_PATH)
    pages: list[str] = [page.get_text("text") for page in doc]
    doc.close()
    full_text: str = "\n".join(pages)
    print(f"[extract] {len(pages)} pages, {len(full_text):,} characters extracted")
    return full_text


def parse_toc(full_text: str) -> tuple[list[dict[str, Any]], str]:
    """
    Parses the ARRANGEMENT OF SECTIONS block into a list of
    {"number": int, "title": str, "chapter": str}.
    This block appears once, before the main Act body starts (which is
    marked by the repeated "CHAPTER I / PRELIMINARY" + "1. Short title...").
    """
    marker = "ARRANGEMENT OF SECTIONS"
    idx = full_text.find(marker)
    if idx == -1:
        raise ValueError("Could not locate 'ARRANGEMENT OF SECTIONS' — check PDF format hasn't changed.")

    # Body starts at the SECOND occurrence of the "CHAPTER I / PRELIMINARY" heading
    # pair (first is in the TOC, second is the real chapter heading in the body).
    # NOTE: a naive substring search for "CHAPTER I" is unsafe — it also matches
    # inside "CHAPTER II", "CHAPTER III", "CHAPTER IV", "CHAPTER IX", "CHAPTER XI",
    # etc. (anything starting with "I"), so we anchor on the unique "PRELIMINARY"
    # heading that only follows the real Chapter I.
    heading_re = re.compile(r"CHAPTER\s+I\s*\n\s*PRELIMINARY")
    matches = list(heading_re.finditer(full_text))
    if len(matches) < 2:
        raise ValueError(
            f"Expected 2 occurrences of 'CHAPTER I / PRELIMINARY' (TOC + body), found {len(matches)}. "
            "PDF structure may have changed — inspect manually."
        )
    body_start = matches[1].start()

    toc_text = full_text[idx:body_start]

    # TOC lines look like: "4. Punishments." or wrap across lines.
    # Track current chapter as we walk through.
    entries: list[dict[str, Any]] = []
    current_chapter: str | None = None
    line_pattern = re.compile(r"^(\d+)\.\s+(.+)$")

    # Collapse to logical lines (join wrapped continuation lines heuristically:
    # a new entry always starts with "<number>." at line start).
    raw_lines = [l.strip() for l in toc_text.splitlines() if l.strip()]
    buffer: str = ""
    buffered_num: int | None = None

    def flush() -> None:
        nonlocal buffer, buffered_num
        if buffered_num is not None:
            entries.append({
                "number": buffered_num,
                "title": buffer.strip().rstrip(".") + ".",
                "chapter": current_chapter,
            })
        buffer, buffered_num = "", None

    # Sub-group headings inside a chapter, e.g. "Of sexual offences", "of abetment",
    # "Of right of private defence" — these are NOT section titles and must not be
    # glued onto the previous entry's title as if it were a wrapped continuation line.
    subheading_re = re.compile(r"^of\s+[a-z]", re.IGNORECASE)

    for line in raw_lines:
        line_upper = line.upper()
        # Defensive stop condition for obvious document boilerplate after final TOC entry
        if (
            "THE BHARATIYA NYAYA SANHITA" in line_upper
            or "ACT NO." in line_upper
            or line_upper.startswith("AN ACT")
            or line_upper.startswith("BE IT ENACTED")
            or line_upper.strip() == "PART"
            or line_upper.strip() == "CHAPTER"
        ):
            break

        if line.upper().startswith("CHAPTER"):
            flush()
            current_chapter = line
            continue
        if line.upper() == "SECTIONS":
            continue
        if line.strip().isdigit():
            # bare page-number artifact from PDF extraction (running header/footer)
            continue
        if subheading_re.match(line) and not any(ch.isdigit() for ch in line):
            # sub-group heading like "Of sexual offences" — track but don't merge into a title
            continue
        m = line_pattern.match(line)
        if m:
            flush()
            buffered_num = int(m.group(1))
            buffer = m.group(2)
        else:
            # continuation of previous title (wrapped line)
            buffer += " " + line
    flush()

    print(f"[toc] parsed {len(entries)} section entries from TOC "
          f"(numbers {entries[0]['number']}–{entries[-1]['number']})")
    return entries, full_text[body_start:]


def slice_sections(toc_entries: list[dict[str, Any]], body_text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Uses each TOC title as an anchor into body_text to slice per-section
    chunks. Falls back to number-based anchor if exact title match fails
    (titles can differ slightly in whitespace/hyphenation between TOC and body).
    """
    sections: list[dict[str, Any]] = []
    review_notes: list[str] = []

    # Build anchor regexes: "<num>. <title-ish>" allowing flexible dash
    # ("––", "—", "-") between title and body per the Act's typesetting.
    anchors: list[tuple[int, re.Pattern[str]]] = []
    for entry in toc_entries:
        num = entry["number"]
        # Use just the number + first few words of title as an anchor —
        # more robust than the full title, which sometimes truncates in TOC.
        # Use 15 chars to avoid hitting broken hyphenation from PDF line-wrap
        # artifacts in the TOC (e.g. "hous-ebreaking" vs "house-breaking").
        title_start = re.escape(entry["title"].split(",")[0].split(".")[0][:15])
        # Allow optional em-dash / en-dash between section number and title
        # (the Act's typesetting often uses "255.—Title" instead of "255. Title").
        pattern = re.compile(rf"(?m)^\s*{num}\.\s*[—–\-]?\s*{title_start}")
        anchors.append((num, pattern))

    positions: list[tuple[int, int | None]] = []
    for num, pattern in anchors:
        m = pattern.search(body_text)
        if m:
            positions.append((num, m.start()))
        else:
            review_notes.append(f"Section {num}: anchor not found in body text — needs manual extraction.")
            positions.append((num, None))

    # Slice using consecutive found positions
    found = [(n, p) for n, p in positions if p is not None]
    for i, (num, start) in enumerate(found):
        end = found[i + 1][1] if i + 1 < len(found) else len(body_text)
        raw_chunk = body_text[start:end].strip()
        
        # Clean obvious PDF artefacts (isolated page numbers)
        lines = raw_chunk.splitlines()
        cleaned_lines = []
        for line in lines:
            if line.strip().isdigit():
                continue
            cleaned_lines.append(line)
        cleaned_text = "\n".join(cleaned_lines).strip()
        
        # Remove chapter headings accidentally appended to the end
        match = CHAPTER_HEADER_RE.search(cleaned_text)
        if match:
            cleaned_text = cleaned_text[:match.start()].strip()
            
        sections.append({"number": num, "raw_text": cleaned_text})

    return sections, review_notes


PENALTY_RE: re.Pattern[str] = re.compile(
    r"[^.]*\b(?:imprisonment|fine|forfeiture|death|life imprisonment)\b[^.]*\.",
    re.IGNORECASE,
)


def extract_penalty(text: str) -> str:
    """Return the penalty clause(s) found in a section's text, if any."""
    matches = PENALTY_RE.findall(text)
    if not matches:
        return ""
    # Keep the last 1-2 matching sentences — punishment is usually stated
    # at the end of a section, not in illustrations earlier in the text.
    return " ".join(m.strip() for m in matches[-2:])


def build_dataset(toc_entries: list[dict[str, Any]], sliced_sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge TOC metadata with sliced body text into the final dataset records."""
    by_number: dict[int, str] = {s["number"]: s["raw_text"] for s in sliced_sections}
    titles_by_number: dict[int, str] = {e["number"]: e["title"] for e in toc_entries}
    chapters_by_number: dict[int, str] = {e["number"]: e["chapter"] for e in toc_entries}

    dataset: list[dict[str, Any]] = []
    body_title_count = 0
    toc_title_count = 0

    for num in sorted(titles_by_number):
        raw_text = by_number.get(num, "")
        
        # Extract title from body if possible
        title = titles_by_number[num]
        used_body_title = False
        if raw_text:
            match = re.match(
                rf"^\s*{num}\.\s*[\u2014\u2013\-]?\s*(.*?)\s*[\u2014\u2013]+",
                raw_text,
                re.DOTALL
            )
            if match:
                derived = match.group(1).strip()
                derived_clean = " ".join(derived.split())
                if len(derived_clean) >= 3:
                    title = derived_clean
                    used_body_title = True
                    
        if used_body_title:
            body_title_count += 1
        else:
            toc_title_count += 1

        dataset.append({
            "section_id": f"bns_{num}",
            "number": num,
            "title": title,
            "chapter": chapters_by_number[num],
            "text": raw_text,
            "penalty": extract_penalty(raw_text),
        })

    print(f"[build] titles derived from body: {body_title_count} | fallback to TOC: {toc_title_count}")
    return dataset


def validate(toc_entries: list[dict[str, Any]], dataset: list[dict[str, Any]], review_notes: list[str]) -> None:
    """Check for missing or suspiciously short sections and write a review log if needed."""
    expected_numbers: set[int] = {e["number"] for e in toc_entries}
    actual_numbers: set[int] = {d["number"] for d in dataset}
    missing: list[int] = sorted(expected_numbers - actual_numbers)
    empty_text: list[int] = [d["number"] for d in dataset if len(d["text"]) < 20]

    if missing:
        review_notes.append(f"Missing sections entirely: {missing}")
    if empty_text:
        review_notes.append(f"Sections with suspiciously short/empty text: {empty_text}")

    print(f"[validate] TOC sections: {len(expected_numbers)} | "
          f"Extracted: {len(actual_numbers)} | "
          f"Flagged for review: {len(review_notes)}")

    if review_notes:
        REVIEW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        REVIEW_LOG_PATH.write_text("\n".join(review_notes), encoding="utf-8")
        print(f"[validate] see {REVIEW_LOG_PATH} — fix these manually before trusting the dataset.")
    else:
        # Clean up stale review log from a previous run
        if REVIEW_LOG_PATH.exists():
            REVIEW_LOG_PATH.unlink()
            print(f"[validate] removed stale {REVIEW_LOG_PATH}")


def main() -> None:
    """Entry point: download → extract → parse → slice → build → validate → write."""
    download_pdf()
    full_text = extract_full_text()
    toc_entries, body_text = parse_toc(full_text)
    sliced_sections, review_notes = slice_sections(toc_entries, body_text)
    dataset = build_dataset(toc_entries, sliced_sections)
    validate(toc_entries, dataset, review_notes)

    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[done] wrote {len(dataset)} sections to {OUTPUT_JSON_PATH}")

    if review_notes:
        print("\n[WARNING] Some sections need manual review -- check bns_review.txt before using this "
              "dataset for embeddings. Do not skip this step; RAG accuracy depends on it.")
        sys.exit(1)


if __name__ == "__main__":
    main()
