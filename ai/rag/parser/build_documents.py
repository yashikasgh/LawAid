"""build_documents.py — Reads bns_sections_enriched.json and generates documents.json
optimized for the RAG pipeline.

Located at: ai/rag/parser/build_documents.py
"""

import json
import re
import argparse
import unittest
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENRICHED_JSON_PATH = BASE_DIR / "data" / "processed" / "bns_sections_enriched.json"
DOCUMENTS_JSON_PATH = BASE_DIR / "data" / "processed" / "documents.json"

def clean_lines(field_value):
    if not field_value:
        return []
    return [line.strip() for line in field_value.split("\n") if line.strip()]

def parse_prefixed_line(line):
    # Matches "[clause_marker] text"
    m = re.match(r"^\[([^\]]+)\]\s*(.*)$", line)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", line.strip()

def build_documents():
    if not ENRICHED_JSON_PATH.exists():
        raise FileNotFoundError(f"Enriched JSON file not found at {ENRICHED_JSON_PATH}")

    with open(ENRICHED_JSON_PATH, "r", encoding="utf-8") as f:
        sections = json.load(f)

    documents = []
    generated_ids = set()

    for sec in sections:
        sec_num = sec["number"]
        sec_id = sec["section_id"]
        title = sec["title"]
        chapter = sec["chapter"]
        legal_text = sec["text"]
        
        # Split fields by newline
        offence_lines = clean_lines(sec["offence"])
        punishment_lines = clean_lines(sec["punishment"])
        cognizable_lines = clean_lines(sec["cognizable"])
        bailable_lines = clean_lines(sec["bailable"])
        court_lines = clean_lines(sec["court"])

        # Determine the number of clauses/entries
        num_clauses = max(
            len(offence_lines),
            len(punishment_lines),
            len(cognizable_lines),
            len(bailable_lines),
            len(court_lines)
        )

        if num_clauses <= 1:
            # Normal section (0 or 1 entry)
            offence_val = offence_lines[0] if offence_lines else ""
            punishment_val = punishment_lines[0] if punishment_lines else ""
            cognizable_val = cognizable_lines[0] if cognizable_lines else ""
            bailable_val = bailable_lines[0] if bailable_lines else ""
            court_val = court_lines[0] if court_lines else ""

            # Strip clause prefix if accidentally present
            _, offence_val = parse_prefixed_line(offence_val)
            _, punishment_val = parse_prefixed_line(punishment_val)
            _, cognizable_val = parse_prefixed_line(cognizable_val)
            _, bailable_val = parse_prefixed_line(bailable_val)
            _, court_val = parse_prefixed_line(court_val)

            doc_id = f"bns_{sec_num}"
            
            # Format clean human-readable text for embeddings
            emb_text = f"Bharatiya Nyaya Sanhita (BNS), 2023\n\n"
            emb_text += f"Section: {sec_num}\n"
            emb_text += f"Title: {title}\n"
            emb_text += f"Chapter: {chapter}\n\n"
            emb_text += f"Legal Text:\n{legal_text}\n\n"
            emb_text += f"Schedule I Classification\n\n"
            if offence_val:
                emb_text += f"Offence:\n{offence_val}\n\n"
                emb_text += f"Punishment:\n{punishment_val}\n\n"
                emb_text += f"Cognizable:\n{cognizable_val}\n\n"
                emb_text += f"Bailable:\n{bailable_val}\n\n"
                emb_text += f"Court:\n{court_val}"
            else:
                emb_text += "Not applicable."

            doc = {
                "id": doc_id,
                "text": emb_text.strip(),
                "metadata": {
                    "id": doc_id,
                    "section": sec_num,
                    "clause": "",
                    "title": title,
                    "chapter": chapter,
                    "bailable": bailable_val,
                    "cognizable": cognizable_val
                }
            }
            documents.append(doc)
            generated_ids.add(doc_id)
        else:
            # Multi-clause section
            for i in range(num_clauses):
                off_line = offence_lines[i] if i < len(offence_lines) else ""
                pun_line = punishment_lines[i] if i < len(punishment_lines) else ""
                cog_line = cognizable_lines[i] if i < len(cognizable_lines) else ""
                bai_line = bailable_lines[i] if i < len(bailable_lines) else ""
                crt_line = court_lines[i] if i < len(court_lines) else ""

                clause_marker_off, offence_val = parse_prefixed_line(off_line)
                clause_marker_pun, punishment_val = parse_prefixed_line(pun_line)
                clause_marker_cog, cognizable_val = parse_prefixed_line(cog_line)
                clause_marker_bai, bailable_val = parse_prefixed_line(bai_line)
                clause_marker_crt, court_val = parse_prefixed_line(crt_line)

                # Determine clause marker
                clause = clause_marker_off or clause_marker_pun or clause_marker_cog or clause_marker_bai or clause_marker_crt or ""
                
                # Check for duplicates of clause marker and create unique ID
                base_id = f"bns_{sec_num}_{clause}" if clause else f"bns_{sec_num}_row_{i+1}"
                doc_id = base_id
                suffix = 2
                while doc_id in generated_ids:
                    doc_id = f"{base_id}-{suffix}"
                    suffix += 1

                # If the clause marker is just the section number and there are multiple entries,
                # suffix it with its row index to keep it descriptive and unique (e.g. "55-1")
                display_clause = clause
                if clause == str(sec_num):
                    display_clause = f"{clause}-{i+1}"

                # Format clean human-readable text for embeddings
                emb_text = f"Bharatiya Nyaya Sanhita (BNS), 2023\n\n"
                emb_text += f"Section: {sec_num} (Clause {display_clause})\n"
                emb_text += f"Title: {title}\n"
                emb_text += f"Chapter: {chapter}\n\n"
                emb_text += f"Legal Text:\n{legal_text}\n\n"
                emb_text += f"Schedule I Classification\n\n"
                emb_text += f"Offence:\n{offence_val}\n\n"
                emb_text += f"Punishment:\n{punishment_val}\n\n"
                emb_text += f"Cognizable:\n{cognizable_val}\n\n"
                emb_text += f"Bailable:\n{bailable_val}\n\n"
                emb_text += f"Court:\n{court_val}"

                doc = {
                    "id": doc_id,
                    "text": emb_text.strip(),
                    "metadata": {
                        "id": doc_id,
                        "section": sec_num,
                        "clause": display_clause,
                        "title": title,
                        "chapter": chapter,
                        "bailable": bailable_val,
                        "cognizable": cognizable_val
                    }
                }
                documents.append(doc)
                generated_ids.add(doc_id)

    # Save to documents.json
    DOCUMENTS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DOCUMENTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(documents)} documents in {DOCUMENTS_JSON_PATH}")
    return documents

class TestDocumentBuilder(unittest.TestCase):
    def setUp(self):
        if not DOCUMENTS_JSON_PATH.exists():
            build_documents()
        with open(DOCUMENTS_JSON_PATH, "r", encoding="utf-8") as f:
            self.docs = json.load(f)

    def test_section_55(self):
        sec_docs = [d for d in self.docs if d["metadata"]["section"] == 55]
        self.assertEqual(len(sec_docs), 2)
        self.assertIn("Whoever abets the \ncommission of an offence", sec_docs[0]["text"])
        self.assertIn("Whoever abets the \ncommission of an offence", sec_docs[1]["text"])
        self.assertEqual(sec_docs[0]["id"], "bns_55_55")
        self.assertEqual(sec_docs[1]["id"], "bns_55_55-2")
        self.assertEqual(sec_docs[0]["metadata"]["clause"], "55-1")
        self.assertEqual(sec_docs[1]["metadata"]["clause"], "55-2")

    def test_section_58(self):
        sec_docs = [d for d in self.docs if d["metadata"]["section"] == 58]
        self.assertEqual(len(sec_docs), 2)
        self.assertEqual(sec_docs[0]["metadata"]["clause"], "58(a)")
        self.assertEqual(sec_docs[1]["metadata"]["clause"], "58(b)")
        self.assertEqual(sec_docs[0]["id"], "bns_58_58(a)")
        self.assertEqual(sec_docs[1]["id"], "bns_58_58(b)")
        self.assertEqual(sec_docs[0]["metadata"]["bailable"], "Non-bailable.")
        self.assertEqual(sec_docs[1]["metadata"]["bailable"], "Bailable.")

    def test_section_64(self):
        sec_docs = [d for d in self.docs if d["metadata"]["section"] == 64]
        self.assertEqual(len(sec_docs), 2)
        self.assertEqual(sec_docs[0]["metadata"]["clause"], "64(1)")
        self.assertEqual(sec_docs[1]["metadata"]["clause"], "64(2)")

    def test_section_103(self):
        sec_docs = [d for d in self.docs if d["metadata"]["section"] == 103]
        self.assertEqual(len(sec_docs), 2)
        self.assertEqual(sec_docs[0]["metadata"]["clause"], "103(1)")
        self.assertEqual(sec_docs[1]["metadata"]["clause"], "103(2)")

    def test_section_302(self):
        sec_docs = [d for d in self.docs if d["metadata"]["section"] == 302]
        self.assertEqual(len(sec_docs), 1)
        self.assertEqual(sec_docs[0]["metadata"]["clause"], "")
        self.assertEqual(sec_docs[0]["id"], "bns_302")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    args = parser.parse_args()

    if args.test:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDocumentBuilder)
        runner = unittest.TextTestRunner()
        runner.run(suite)
    else:
        build_documents()
        # Automatically run tests on the generated output
        print("Running verification tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDocumentBuilder)
        runner = unittest.TextTestRunner()
        runner.run(suite)
