"""fir_pdf_generator.py — PyMuPDF Overlay PDF Generator for IF1 FIR Template.

Located at: ai/fir_engine/fir_pdf_generator.py
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List

import fitz  # PyMuPDF

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "fir" / "IF1_FIR_Template.pdf"


def _draw_text_point(page: fitz.Page, text: str, x: float, y: float, fontname: str = "helv", fontsize: float = 7.5, color=(0, 0, 0)):
    """Draws a single-line text string anchored at exact point (x, y) baseline."""
    if not text:
        return
    page.insert_text(fitz.Point(x, y), str(text).strip(), fontname=fontname, fontsize=fontsize, color=color)


def _draw_textbox_rect(page: fitz.Page, text: str, x0: float, y0: float, x1: float, y1: float, fontname: str = "helv", fontsize: float = 7.5, color=(0, 0, 0)):
    """Draws multiline wrapped text strictly bounded inside rectangle (x0, y0, x1, y1)."""
    if not text:
        return
    rect = fitz.Rect(x0, y0, x1, y1)
    page.insert_textbox(rect, str(text).strip(), fontname=fontname, fontsize=fontsize, color=color, align=0)


def generate_fir_pdf(fir_data: Dict[str, Any]) -> bytes:
    """
    Overlays structured FIR JSON fields (1-15) directly onto the official 2-page IF1 PDF template.

    Args:
        fir_data (dict): Structured FIR data dictionary matching IF1 schema.

    Returns:
        bytes: Binary PDF content with populated text overlay.
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"IF1 FIR Template not found at: {TEMPLATE_PATH}")

    doc = fitz.open(str(TEMPLATE_PATH))
    if len(doc) < 2:
        raise ValueError(f"Expected 2-page template, but got {len(doc)} pages.")

    page0 = doc[0]
    page1 = doc[1]

    # Shared styling
    FN = "helv"
    FS = 7.5  # Compact 7.5pt font to fit dotted line fields cleanly without label collisions
    COLOR = (0, 0, 0)  # Pure black text for form fidelity

    # Helper getters with default fallbacks
    def g(parent: dict, *keys: str, default: str = "") -> str:
        if not isinstance(parent, dict):
            return default
        for k in keys:
            val = parent
            for part in k.split('.'):
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                    break
            if val is not None and str(val).strip() != "":
                res = str(val).strip()
                if res.lower() not in ["not provided", "n/a", "unknown", "none", "null"]:
                    return res
        return default

    # =========================================================================
    # PAGE 0 OVERLAY
    # =========================================================================

    # ITEM 1: FIR Identifiers (y=119.0 baseline)
    _draw_text_point(page0, g(fir_data, "district"), 105.0, 119.0, fontname=FN, fontsize=7.0, color=COLOR)
    _draw_text_point(page0, g(fir_data, "policeStation", "police_station"), 225.0, 119.0, fontname=FN, fontsize=7.0, color=COLOR)
    _draw_text_point(page0, g(fir_data, "year", default="2026"), 330.0, 119.0, fontname=FN, fontsize=FS, color=COLOR)
    
    # FIR No - compact string to fit dotted box (x=447 to 490)
    fir_no = g(fir_data, "firNo", "fir_number", default="Draft")
    if "Draft" in fir_no:
        fir_no = "Draft"
    _draw_text_point(page0, fir_no, 450.0, 119.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "firDate", "fir_date"), 525.0, 119.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 2: Act(s) & Section(s) - Render form.actEntries directly as authoritative officer state
    raw_entries = fir_data.get("actEntries")
    if not isinstance(raw_entries, list) or len(raw_entries) == 0:
        raw_entries = fir_data.get("acts_sections")
    if not isinstance(raw_entries, list) or len(raw_entries) == 0:
        raw_entries = []
        if g(fir_data, "section1") != "":
            raw_entries.append({"act": g(fir_data, "act1", default="Bharatiya Nyaya Sanhita, 2023"), "section": g(fir_data, "section1")})
        if g(fir_data, "section2") != "":
            raw_entries.append({"act": g(fir_data, "act2", default="Bharatiya Nyaya Sanhita, 2023"), "section": g(fir_data, "section2")})
        if g(fir_data, "section3") != "":
            raw_entries.append({"act": g(fir_data, "act3", default="Bharatiya Nyaya Sanhita, 2023"), "section": g(fir_data, "section3")})

    if isinstance(raw_entries, list):
        row_y = [146.0, 166.0, 186.0]
        row_act_x = [125.0, 135.0, 135.0]
        
        valid_entries = []
        for e in raw_entries:
            if isinstance(e, dict):
                sec_val = g(e, "section", "sections")
                if sec_val != "":
                    valid_entries.append(e)
            elif isinstance(e, str) and e.strip() != "":
                valid_entries.append(e.strip())
        
        # Populate rows (i) to (iii) for first 3 entries
        for idx, item in enumerate(valid_entries[:3]):
            y_pos = row_y[idx]
            act_x = row_act_x[idx]
            
            if isinstance(item, dict):
                act_str = g(item, "act", default="Bharatiya Nyaya Sanhita, 2023")
                sec_raw = item.get("section") or item.get("sections") or ""
                if isinstance(sec_raw, list):
                    sec_str = ", ".join([str(s) for s in sec_raw if s])
                else:
                    sec_str = str(sec_raw).strip()
            else:
                act_str = "Bharatiya Nyaya Sanhita, 2023"
                sec_str = str(item).strip()

            _draw_text_point(page0, act_str, act_x, y_pos, fontname=FN, fontsize=FS, color=COLOR)
            _draw_text_point(page0, sec_str, 370.0, y_pos, fontname=FN, fontsize=FS, color=COLOR)

        # Handle remaining entries (> 3) for Item 2(iv)
        overflow_entries = valid_entries[3:]
        continuation_entries = []
        if overflow_entries:
            overflow_strings = []
            for item in overflow_entries:
                if isinstance(item, dict):
                    act_s = g(item, "act", default="BNS 2023")
                    sec_s = g(item, "section", "sections")
                    overflow_strings.append(f"{act_s} {sec_s}".strip())
                else:
                    overflow_strings.append(str(item).strip())
            
            combined_overflow = "; ".join(overflow_strings)
            
            # Max readable chars in single-line 2(iv) area: ~55 chars
            if len(combined_overflow) <= 55 and len(overflow_entries) <= 2:
                _draw_text_point(page0, combined_overflow, 310.0, 206.0, fontname=FN, fontsize=FS, color=COLOR)
            else:
                _draw_text_point(page0, "See Attached Continuation Sheet (Item 2)", 310.0, 206.0, fontname=FN, fontsize=FS, color=COLOR)
                continuation_entries = overflow_entries

    # ITEM 3: Occurrence of Offence & Info Received & GD Entry
    occ_date = g(fir_data, "occurrenceDate", "occurrence.date_from", "occurrence.date", "occurrence_date")
    occ_time = g(fir_data, "occurrenceTime", "occurrence.time_from", "occurrence.time", "occurrence_time")
    occ_day = g(fir_data, "occurrenceDay", "occurrence.day", "occurrence_day")

    _draw_text_point(page0, occ_day, 258.0, 240.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, occ_date, 365.0, 240.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, occ_time, 485.0, 240.0, fontname=FN, fontsize=FS, color=COLOR)

    info_date = g(fir_data, "informationDate", "information_received.date", "information_date")
    info_time = g(fir_data, "informationTime", "information_received.time", "information_time")
    _draw_text_point(page0, info_date, 248.0, 267.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, info_time, 430.0, 267.0, fontname=FN, fontsize=FS, color=COLOR)

    gd_entry = g(fir_data, "gdEntry", "general_diary.entry_numbers", "gd_entry")
    gd_time = g(fir_data, "gdTime", "general_diary.time", "gd_time")
    _draw_text_point(page0, gd_entry, 295.0, 294.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, gd_time, 460.0, 294.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 4: Type of Information
    _draw_text_point(page0, g(fir_data, "informationType", "type_of_information", default="Written"), 365.0, 321.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 5: Place of Occurrence
    _draw_text_point(page0, g(fir_data, "placeDirection", "place_of_occurrence.direction_distance_from_ps"), 345.0, 347.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "beatNo", "place_of_occurrence.beat_no"), 500.0, 347.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "placeAddress", "place_of_occurrence.address", "place_address", "location"), 155.0, 374.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "outsidePoliceStation", "place_of_occurrence.outside_police_station"), 440.0, 401.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "outsideDistrict", "place_of_occurrence.district"), 150.0, 414.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 6: Complainant / Informant
    _draw_text_point(page0, g(fir_data, "complainantName", "complainant.name"), 140.0, 468.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "fatherHusbandName", "complainant.father_husband_name"), 250.0, 489.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "dob", "complainant.date_year_of_birth"), 225.0, 509.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "nationality", "complainant.nationality"), 455.0, 509.0, fontname=FN, fontsize=FS, color=COLOR)

    _draw_text_point(page0, g(fir_data, "passportNo", "complainant.passport_no"), 165.0, 529.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "passportDate", "complainant.passport_date_of_issue"), 325.0, 529.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "passportPlace", "complainant.passport_place_of_issue"), 472.0, 529.0, fontname=FN, fontsize=FS, color=COLOR)

    _draw_text_point(page0, g(fir_data, "occupation", "complainant.occupation"), 162.0, 550.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "complainantAddress", "complainant.address"), 148.0, 570.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 7: Details of Accused (Multiline Rect starting at y=626 cleanly on dotted line at y=634)
    accused_text = g(fir_data, "accusedDetails", "accused_details", "accused")
    _draw_textbox_rect(page0, accused_text, 69.0, 626.0, 540.0, 654.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 8: Reasons for Delay
    _draw_text_point(page0, g(fir_data, "delayReason", "delay_reason"), 372.0, 664.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 9: Particulars of Properties Stolen / Involved (Line 1 on Page 0)
    prop_text = g(fir_data, "propertyDetails", "property_details", "property")
    _draw_text_point(page0, prop_text[:40], 442.0, 704.0, fontname=FN, fontsize=FS, color=COLOR)

    # =========================================================================
    # PAGE 1 OVERLAY
    # =========================================================================

    # ITEM 9 (Continued on Page 1 if text is long)
    if len(prop_text) > 40:
        _draw_textbox_rect(page1, prop_text[40:], 69.0, 44.0, 540.0, 82.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 10: Total Value of Property Stolen / Involved
    _draw_text_point(page1, g(fir_data, "propertyValue", "property_value", "value"), 295.0, 107.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 11: Inquest Report / U.D. Case No.
    _draw_text_point(page1, g(fir_data, "inquestDetails", "inquest_ud_case"), 265.0, 134.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 12: F.I.R. Contents (Multiline Rect starting at y=188 cleanly below header)
    fir_contents = g(fir_data, "firContents", "fir_contents", "statement")
    _draw_textbox_rect(page1, fir_contents, 69.0, 188.0, 540.0, 355.0, fontname=FN, fontsize=8.0, color=COLOR)

    # ITEM 13: Action Taken & Officer Details
    off_name = g(fir_data, "officerName", "officer.name")
    off_rank = g(fir_data, "officerRank", "officer.rank")
    off_no = g(fir_data, "officerNo", "officer.number")

    # Draw officer name cleanly on 1st dotted line after 'direction /' at x=370, y=388
    _draw_text_point(page1, off_name, 370.0, 388.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page1, off_rank, 496.0, 388.0, fontname=FN, fontsize=FS, color=COLOR)

    # OFFICER DETAILS (Item 13 Footer block)
    _draw_text_point(page1, off_name, 356.0, 482.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page1, off_rank, 348.0, 496.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page1, off_no, 470.0, 496.0, fontname=FN, fontsize=7.0, color=COLOR)

    # ITEM 14: Complainant Signature area (Left intentionally clean / un-overlapped)

    # ITEM 15: Date & Time of Despatch to Court
    dt_date = g(fir_data, "dispatchDate", "dispatch_to_court.date")
    dt_time = g(fir_data, "dispatchTime", "dispatch_to_court.time")
    disp_str = f"{dt_date} {dt_time}".strip()
    _draw_text_point(page1, disp_str, 242.0, 550.0, fontname=FN, fontsize=FS, color=COLOR)

    # =========================================================================
    # CONTINUATION SHEET (If > 3 Acts & Sections)
    # =========================================================================
    if continuation_entries:
        cont_page = doc.new_page(width=595.0, height=841.0)
        _draw_text_point(cont_page, "FORM F.I.R. (IF1) - CONTINUATION SHEET", 40.0, 45.0, fontname="hebo", fontsize=12.0, color=COLOR)
        _draw_text_point(cont_page, "Item 2: Acts & Sections (Continued)", 40.0, 62.0, fontname="hebo", fontsize=10.0, color=COLOR)
        
        fir_ref = f"FIR No: {fir_no} | P.S.: {g(fir_data, 'policeStation', 'police_station')} | Date: {g(fir_data, 'firDate', 'fir_date')}"
        _draw_text_point(cont_page, fir_ref, 40.0, 78.0, fontname=FN, fontsize=8.0, color=(0.3, 0.3, 0.3))
        
        cont_page.draw_line(fitz.Point(40.0, 88.0), fitz.Point(555.0, 88.0), color=COLOR, width=0.8)
        
        cont_page.draw_rect(fitz.Rect(40.0, 98.0, 555.0, 116.0), color=(0.7, 0.7, 0.7), fill=(0.93, 0.95, 0.98))
        _draw_text_point(cont_page, "#", 48.0, 110.0, fontname="hebo", fontsize=8.5, color=COLOR)
        _draw_text_point(cont_page, "Act / Statute", 75.0, 110.0, fontname="hebo", fontsize=8.5, color=COLOR)
        _draw_text_point(cont_page, "Section(s) & Offence Description", 270.0, 110.0, fontname="hebo", fontsize=8.5, color=COLOR)
        
        curr_y = 132.0
        for c_idx, item in enumerate(continuation_entries):
            if curr_y > 780.0:
                cont_page = doc.new_page(width=595.0, height=841.0)
                curr_y = 50.0
            
            entry_no = f"{c_idx + 4}."
            if isinstance(item, dict):
                act_str = g(item, "act", default="Bharatiya Nyaya Sanhita, 2023")
                sec_str = g(item, "section", "sections")
            else:
                act_str = "Bharatiya Nyaya Sanhita, 2023"
                sec_str = str(item).strip()

            cont_page.draw_rect(fitz.Rect(40.0, curr_y - 12.0, 555.0, curr_y + 8.0), color=(0.85, 0.85, 0.85), width=0.5)
            _draw_text_point(cont_page, entry_no, 48.0, curr_y, fontname=FN, fontsize=8.0, color=COLOR)
            _draw_text_point(cont_page, act_str, 75.0, curr_y, fontname=FN, fontsize=8.0, color=COLOR)
            _draw_text_point(cont_page, sec_str, 270.0, curr_y, fontname=FN, fontsize=8.0, color=COLOR)
            
            curr_y += 24.0

    # Write output to bytes
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes
