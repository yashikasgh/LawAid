import fitz
import json
import re
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_JSON_PATH = PROCESSED_DIR / "schedule1.json"

def locate_pdf() -> Path:
    # Look for the BNSS First Schedule PDF
    pdf_path_1 = RAW_DIR / "bnss_schedule1.pdf"
    pdf_path_2 = RAW_DIR / "bnss_schedule1.pdf.pdf"
    
    if pdf_path_1.exists():
        return pdf_path_1
    elif pdf_path_2.exists():
        return pdf_path_2
    else:
        print(f"[ERROR] Could not find bnss_schedule1.pdf or bnss_schedule1.pdf.pdf in {RAW_DIR}")
        sys.exit(1)

def group_words_into_lines(page):
    words = page.get_text("words")
    # Filter out header and footer areas to exclude page headers and page numbers
    # Headers are usually at y < 80, page numbers are at y > 720
    words = [w for w in words if w[1] > 80 and w[3] < 720]
    if not words:
        return []
    words.sort(key=lambda w: (w[1], w[0]))
    
    lines = []
    current_line = [words[0]]
    for w in words[1:]:
        avg_y0 = sum(x[1] for x in current_line) / len(current_line)
        if abs(w[1] - avg_y0) < 3.0:
            current_line.append(w)
        else:
            lines.append(sorted(current_line, key=lambda x: x[0]))
            current_line = [w]
    lines.append(sorted(current_line, key=lambda x: x[0]))
    return lines

def get_page_boundaries(page, p_num):
    words = page.get_text("words")
    limit_y = 350 if p_num == 0 else 120
    candidates = [w for w in words if w[1] < limit_y and w[4] in ["1", "2", "3", "4", "5", "6"]]
    
    lines = {}
    for w in candidates:
        y = round(w[1], 1)
        found = False
        for ly in lines:
            if abs(ly - y) < 2.0:
                lines[ly].append(w)
                found = True
                break
        if not found:
            lines[y] = [w]
            
    header_line = None
    for ly in lines:
        line_words = sorted(lines[ly], key=lambda x: x[0])
        vals = [w[4] for w in line_words]
        if "1" in vals and "2" in vals and "3" in vals and "4" in vals and "5" in vals and "6" in vals:
            header_line = line_words
            break
            
    if header_line:
        header_map = {w[4]: w[0] for w in header_line}
        x2 = header_map.get("2", 107.0)
        x3 = header_map.get("3", 224.9)
        x4 = header_map.get("4", 294.4)
        x5 = header_map.get("5", 371.7)
        
        B1 = 100
        B5 = 445
        
        if x2 < 120:
            # Layout A
            B2 = x3 - 10
            B3 = x4 - 10
            B4 = x5 - 10
        else:
            # Layout B/C (centered column numbers header)
            B2 = (x2 + x3) / 2
            B3 = (x3 + x4) / 2
            B4 = (x4 + x5) / 2
            
        return [B1, B2, B3, B4, B5]
    else:
        # Fallback if header is not found on a page
        if p_num + 1 < 19:
            return [100, 215, 285, 360, 445]
        else:
            return [100, 215, 320, 380, 445]

def extract_schedule():
    pdf_path = locate_pdf()
    print(f"[fetch] opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    
    # 1. Dynamically detect start page of THE FIRST SCHEDULE
    start_page_idx = None
    for idx in range(len(doc)):
        text = doc[idx].get_text("text")
        if "THE FIRST SCHEDULE" in text:
            start_page_idx = idx
            break
            
    if start_page_idx is None:
        print("[ERROR] Could not find the start of THE FIRST SCHEDULE in the PDF.")
        sys.exit(1)
        
    print(f"[parse] detected THE FIRST SCHEDULE starting at Page {start_page_idx + 1}")
    
    rows = []
    active_row = None
    started = False
    
    # Regex to identify case-sensitive row-start words in classification columns
    row_start_keywords = re.compile(r"^(Cognizable|Non-|Non\s|According|Same|Bailable)")
    
    for p_num in range(start_page_idx, len(doc)):
        page = doc[p_num]
        text = page.get_text("text")
        
        # 2. Stop parsing when THE SECOND SCHEDULE begins or Part II begins
        if "THE SECOND SCHEDULE" in text or "II.--CLASSIFICATION OF OFFENCES" in text or "II.—CLASSIFICATION OF OFFENCES" in text or "OFFENCES AGAINST OTHER LAWS" in text:
            print(f"[parse] stop condition encountered on Page {p_num + 1}. Ending parser loop.")
            break
            
        boundaries = get_page_boundaries(page, p_num - start_page_idx)
        lines = group_words_into_lines(page)
        
        for line in lines:
            cols = [""] * 6
            for w in line:
                x0 = w[0]
                col_idx = 0
                while col_idx < len(boundaries) and x0 >= boundaries[col_idx]:
                    col_idx += 1
                cols[col_idx] = (cols[col_idx] + " " + w[4]).strip()
                
            # Skip column header numbers line "1 2 3 4 5 6"
            if cols[0] == "1" and cols[1] == "2":
                continue
                
            # Wait for first digit-starting Section on the start page
            if p_num == start_page_idx and not started:
                if cols[0] and cols[0][0].isdigit():
                    started = True
                else:
                    continue
                    
            digit_start = bool(cols[0] and cols[0][0].isdigit())
            keyword_start = bool((cols[3] and row_start_keywords.match(cols[3])) or 
                                 (cols[4] and row_start_keywords.match(cols[4])))
            
            # Calculate current line y0
            line_y = sum(w[1] for w in line) / len(line)
            
            # Determine if this line starts a new row
            is_row_start = False
            if digit_start:
                # Prevent splitting if the section number is just vertically centered and on a new line
                if active_row and not active_row["section"] and active_row["page"] == p_num + 1:
                    prev_y = active_row.get("start_y", 0)
                    if line_y - prev_y < 20.0 and not keyword_start:
                        is_row_start = False
                    else:
                        is_row_start = True
                else:
                    is_row_start = True
            elif keyword_start and bool(cols[1]):
                is_row_start = True
                
            if is_row_start:
                if active_row:
                    rows.append(active_row)
                active_row = {
                    "section": cols[0],
                    "offence": cols[1],
                    "punishment": cols[2],
                    "cognizable": cols[3],
                    "bailable": cols[4],
                    "court": cols[5],
                    "page": p_num + 1,
                    "start_y": line_y
                }
            else:
                if active_row:
                    if cols[0]:
                        active_row["section"] = (active_row["section"] + " " + cols[0]).strip()
                    if cols[1]:
                        active_row["offence"] = (active_row["offence"] + " " + cols[1]).strip()
                    if cols[2]:
                        active_row["punishment"] = (active_row["punishment"] + " " + cols[2]).strip()
                    if cols[3]:
                        active_row["cognizable"] = (active_row["cognizable"] + " " + cols[3]).strip()
                    if cols[4]:
                        active_row["bailable"] = (active_row["bailable"] + " " + cols[4]).strip()
                    if cols[5]:
                        active_row["court"] = (active_row["court"] + " " + cols[5]).strip()

    if active_row:
        rows.append(active_row)
        
    print(f"[parse] extracted {len(rows)} raw rows before propagation and normalization")
    
    # 3. Propagate section numbers for empty section fields
    last_section = ""
    for r in rows:
        if r["section"].strip():
            last_section = r["section"]
        else:
            r["section"] = last_section
            
    # 4. Clean up spaces and format records exactly
    cleaned_records = []
    for r in rows:
        rec = {
            "section": " ".join(r["section"].split()),
            "offence": " ".join(r["offence"].split()),
            "punishment": " ".join(r["punishment"].split()),
            "cognizable": " ".join(r["cognizable"].split()),
            "bailable": " ".join(r["bailable"].split()),
            "court": " ".join(r["court"].split())
        }
        cleaned_records.append(rec)
        
    # 4b. Post-processing pass for leftover tokens in cognizable fields
    # and normalization of spacing around hyphens case-insensitively
    for r in cleaned_records:
        # Spacing, duplicate word, and prefix fixes across all fields
        for field in ["offence", "punishment", "cognizable", "bailable", "court"]:
            val = r[field]
            val = re.sub(r"\bNon-\s+cognizable\b", "Non-cognizable", val, flags=re.IGNORECASE)
            val = re.sub(r"\bnon-\s+cognizable\b", "non-cognizable", val, flags=re.IGNORECASE)
            val = re.sub(r"\bNon-\s+bailable\b", "Non-bailable", val, flags=re.IGNORECASE)
            val = re.sub(r"\bnon-\s+bailable\b", "non-bailable", val, flags=re.IGNORECASE)
            val = re.sub(r"\bone-\s+fourth\b", "one-fourth", val, flags=re.IGNORECASE)
            val = re.sub(r"\bone-\s+eighth\b", "one-eighth", val, flags=re.IGNORECASE)
            val = re.sub(r"\bone-\s+half\b", "one-half", val, flags=re.IGNORECASE)
            val = re.sub(r"\bsub-\s+section\b", "sub-section", val, flags=re.IGNORECASE)
            val = re.sub(r"\bbank-\s+notes\b", "bank-notes", val, flags=re.IGNORECASE)
            val = re.sub(r"\bVice-\s+President\b", "Vice-President", val, flags=re.IGNORECASE)
            
            # Clean duplicate words
            val = re.sub(r"\bto to\b", "to", val, flags=re.IGNORECASE)
            val = re.sub(r"\bis is\b", "is", val, flags=re.IGNORECASE)
            
            # Clean stray words
            val = re.sub(r"\bthe men offence\b", "the offence", val, flags=re.IGNORECASE)
            
            # Clean double spaces
            val = re.sub(r"\s+", " ", val).strip()
            r[field] = val
            
        token = None
        rest = None
        
        # Check for numeric token inside parenthetical notes in cognizable (e.g., Section 67)
        m_paren_num = re.search(r"\b(\d+)\s+complaint\b", r["cognizable"], re.IGNORECASE)
        if m_paren_num:
            token = m_paren_num.group(1)
            r["cognizable"] = r["cognizable"].replace(f"{token} complaint", "complaint")
        else:
            # Check for leading leftover token
            m_lead = re.match(r"^\s*(to|of|or|the|a|\d+)\s+(Cognizable|Non-cognizable|According)", r["cognizable"], re.IGNORECASE)
            if m_lead:
                token = m_lead.group(1)
                rest = r["cognizable"][m_lead.end(1):].strip()
                r["cognizable"] = rest
            else:
                # Check for trailing leftover token
                m_trail = re.search(r"\b(Cognizable|Non-cognizable|According)[\s.]+(to|of|or|the|a|\d+)\.?$", r["cognizable"], re.IGNORECASE)
                if m_trail:
                    token = m_trail.group(2)
                    rest = r["cognizable"][:m_trail.start(2)].strip()
                    if not rest.endswith("."):
                        rest += "."
                    r["cognizable"] = rest
                else:
                    # Check for infixed token in Non-cognizable
                    m_infix = re.match(r"^Non-[\s.]+(to|of|or|the|a|\d+)[\s.]+cognizable\.?$", r["cognizable"], re.IGNORECASE)
                    if m_infix:
                        token = m_infix.group(1)
                        r["cognizable"] = "Non-cognizable."
            
        if token is not None:
            pun = r["punishment"]
            
            # Smart placement rules
            if token.lower() == "to":
                if "extend imprisonment for life" in pun:
                    pun = pun.replace("extend imprisonment for life", "extend to imprisonment for life")
                elif pun.endswith(". to"):
                    pun = pun[:-4].strip() + " to."
                elif not pun.endswith("to") and not pun.endswith("to."):
                    pun = pun.rstrip(".") + " to."
            elif token == "7":
                if "extend to years" in pun:
                    pun = pun.replace("extend to years", "extend to 7 years")
                elif "imprisonment for years" in pun:
                    pun = pun.replace("imprisonment for years", "imprisonment for 7 years")
                elif pun.endswith(". 7"):
                    pun = pun[:-3].strip() + " 7."
                elif not pun.endswith("7") and not pun.endswith("7."):
                    pun = pun.rstrip(".") + " 7."
            elif token == "3":
                if "extend to years" in pun:
                    pun = pun.replace("extend to years", "extend to 3 years")
                elif pun.endswith(". 3"):
                    pun = pun[:-3].strip() + " 3."
                elif not pun.endswith("3") and not pun.endswith("3."):
                    pun = pun.rstrip(".") + " 3."
            elif token.lower() == "of":
                if "fine 5,000" in pun:
                    pun = pun.replace("fine 5,000", "fine of 5,000")
                elif "fine 2,500" in pun:
                    pun = pun.replace("fine 2,500", "fine of 2,500")
                elif pun.endswith(". of"):
                    pun = pun[:-4].strip() + " of."
                elif not pun.endswith("of") and not pun.endswith("of."):
                    pun = pun.rstrip(".") + " of."
            else:
                pun = pun.rstrip(".") + " " + token + "."
                
            r["punishment"] = pun
        
    # Write to schedule1.json
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, indent=4, ensure_ascii=False)
    print(f"[write] saved {len(cleaned_records)} records to {OUTPUT_JSON_PATH}")
    
    # 5. Validation and Anomalies Reporting
    section_counts = {}
    missing_fields_rows = 0
    anomalies = []
    
    for idx, r in enumerate(cleaned_records):
        sec = r["section"]
        section_counts[sec] = section_counts.get(sec, 0) + 1
        
        # Check for missing fields
        has_missing = False
        for field in ["section", "offence", "punishment", "cognizable", "bailable", "court"]:
            if not r[field].strip():
                if field in ["cognizable", "bailable", "court", "punishment"]:
                    has_missing = True
                elif field in ["section", "offence"]:
                    has_missing = True
                    
        if has_missing:
            # Legally empty container rows have no punishment, cognizable, bailable, or court
            is_container = not r["punishment"].strip() and not r["cognizable"].strip() and not r["bailable"].strip() and not r["court"].strip()
            if not is_container:
                missing_fields_rows += 1
            
        # Check for anomalies
        cog_clean = r["cognizable"].lower()
        bai_clean = r["bailable"].lower()
        
        # Don't check classification for container rows
        is_container = not r["punishment"].strip() and not r["cognizable"].strip() and not r["bailable"].strip() and not r["court"].strip()
        if not is_container:
            if "cognizable" not in cog_clean and "same" not in cog_clean and "according" not in cog_clean:
                anomalies.append(f"Row {idx+1} (Sec {sec}): Unexpected cognizable classification: '{r['cognizable']}'")
            if "bailable" not in bai_clean and "same" not in bai_clean and "according" not in bai_clean:
                anomalies.append(f"Row {idx+1} (Sec {sec}): Unexpected bailable classification: '{r['bailable']}'")
            
    duplicate_sections = {sec: count for sec, count in section_counts.items() if count > 1}
    
    print("\n" + "="*40)
    print("VALIDATION REPORT")
    print("="*40)
    print(f"Total rows extracted         : {len(cleaned_records)}")
    print(f"Rows with missing fields     : {missing_fields_rows}")
    print(f"Unique section identifiers   : {len(section_counts)}")
    print(f"Duplicate section identifiers: {len(duplicate_sections)}")
    print(f"Total parsing anomalies      : {len(anomalies)}")
    
    if duplicate_sections:
        print("\nDuplicate Section Identifiers Details:")
        for sec, count in sorted(duplicate_sections.items()):
            print(f"  - Section '{sec}': appears {count} times")
            
    if anomalies:
        print("\nParsing Anomalies Details:")
        for anomaly in anomalies[:15]:
            print(f"  - {anomaly}")
        if len(anomalies) > 15:
            print(f"  ... and {len(anomalies) - 15} more anomalies")
    print("="*40)

if __name__ == "__main__":
    extract_schedule()
