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
    def g(parent: dict, key: str, default: str = "Not provided") -> str:
        val = parent.get(key)
        if val is None or str(val).strip() == "":
            return default
        return str(val).strip()

    # =========================================================================
    # PAGE 0 OVERLAY
    # =========================================================================

    # ITEM 1: FIR Identifiers (y=119.0 baseline)
    _draw_text_point(page0, g(fir_data, "district"), 105.0, 119.0, fontname=FN, fontsize=7.0, color=COLOR)
    _draw_text_point(page0, g(fir_data, "police_station"), 225.0, 119.0, fontname=FN, fontsize=7.0, color=COLOR)
    _draw_text_point(page0, g(fir_data, "year", "2026"), 330.0, 119.0, fontname=FN, fontsize=FS, color=COLOR)
    
    # FIR No - compact string to fit dotted box (x=447 to 490)
    fir_no = g(fir_data, "fir_number", "Draft")
    if "Draft" in fir_no:
        fir_no = "Draft"
    _draw_text_point(page0, fir_no, 450.0, 119.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(fir_data, "fir_date", "09/09/2026"), 525.0, 119.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 2: Act(s) & Section(s)
    # Grounded acts_sections format: list of dicts [{"act": "...", "sections": "..."}, ...]
    acts_sections = fir_data.get("acts_sections", [])
    if isinstance(acts_sections, list):
        row_y = [146.0, 166.0, 186.0]
        row_act_x = [125.0, 135.0, 135.0]
        
        for idx, item in enumerate(acts_sections[:3]):
            y_pos = row_y[idx]
            act_x = row_act_x[idx]
            
            if isinstance(item, dict):
                act_str = g(item, "act", "Bharatiya Nyaya Sanhita, 2023")
                sec_raw = item.get("sections", "")
                if isinstance(sec_raw, list):
                    sec_str = ", ".join([str(s) for s in sec_raw])
                else:
                    sec_str = str(sec_raw)
            else:
                act_str = "Bharatiya Nyaya Sanhita, 2023"
                sec_str = str(item)

            _draw_text_point(page0, act_str, act_x, y_pos, fontname=FN, fontsize=FS, color=COLOR)
            _draw_text_point(page0, sec_str, 370.0, y_pos, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 3: Occurrence of Offence & Info Received & GD Entry
    occ = fir_data.get("occurrence", {}) if isinstance(fir_data.get("occurrence"), dict) else {}
    occ_date = g(occ, "date_from") if occ.get("date_from") else g(occ, "date")
    occ_time = g(occ, "time_from") if occ.get("time_from") else g(occ, "time")
    _draw_text_point(page0, g(occ, "day"), 258.0, 240.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, occ_date, 365.0, 240.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, occ_time, 485.0, 240.0, fontname=FN, fontsize=FS, color=COLOR)

    info_rec = fir_data.get("information_received", {}) if isinstance(fir_data.get("information_received"), dict) else {}
    _draw_text_point(page0, g(info_rec, "date"), 248.0, 267.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(info_rec, "time"), 430.0, 267.0, fontname=FN, fontsize=FS, color=COLOR)

    gd = fir_data.get("general_diary", {}) if isinstance(fir_data.get("general_diary"), dict) else {}
    _draw_text_point(page0, g(gd, "entry_numbers"), 295.0, 294.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(gd, "time"), 460.0, 294.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 4: Type of Information
    _draw_text_point(page0, g(fir_data, "type_of_information"), 365.0, 321.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 5: Place of Occurrence
    poc = fir_data.get("place_of_occurrence", {}) if isinstance(fir_data.get("place_of_occurrence"), dict) else {}
    _draw_text_point(page0, g(poc, "direction_distance_from_ps"), 345.0, 347.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(poc, "beat_no"), 500.0, 347.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(poc, "address"), 155.0, 374.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(poc, "outside_police_station", "N/A"), 440.0, 401.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(poc, "district"), 150.0, 414.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 6: Complainant / Informant
    comp = fir_data.get("complainant", {}) if isinstance(fir_data.get("complainant"), dict) else {}
    _draw_text_point(page0, g(comp, "name"), 140.0, 468.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(comp, "father_husband_name"), 250.0, 489.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(comp, "date_year_of_birth"), 225.0, 509.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(comp, "nationality"), 455.0, 509.0, fontname=FN, fontsize=FS, color=COLOR)

    _draw_text_point(page0, g(comp, "passport_no", "N/A"), 165.0, 529.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(comp, "passport_date_of_issue", "N/A"), 325.0, 529.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(comp, "passport_place_of_issue", "N/A"), 472.0, 529.0, fontname=FN, fontsize=FS, color=COLOR)

    _draw_text_point(page0, g(comp, "occupation"), 162.0, 550.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page0, g(comp, "address"), 148.0, 570.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 7: Details of Accused (Multiline Rect starting at y=626 cleanly on dotted line at y=634)
    accused_text = g(fir_data, "accused_details", "Unknown male accused; identity not known at this stage.")
    _draw_textbox_rect(page0, accused_text, 69.0, 626.0, 540.0, 654.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 8: Reasons for Delay
    _draw_text_point(page0, g(fir_data, "delay_reason"), 372.0, 664.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 9: Particulars of Properties Stolen / Involved (Line 1 on Page 0)
    prop_text = g(fir_data, "property_details", "N/A")
    _draw_text_point(page0, prop_text[:40], 442.0, 704.0, fontname=FN, fontsize=FS, color=COLOR)

    # =========================================================================
    # PAGE 1 OVERLAY
    # =========================================================================

    # ITEM 9 (Continued on Page 1 if text is long)
    if len(prop_text) > 40:
        _draw_textbox_rect(page1, prop_text[40:], 69.0, 44.0, 540.0, 82.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 10: Total Value of Property Stolen / Involved
    _draw_text_point(page1, g(fir_data, "property_value", "Unknown"), 295.0, 107.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 11: Inquest Report / U.D. Case No.
    _draw_text_point(page1, g(fir_data, "inquest_ud_case", "N/A"), 265.0, 134.0, fontname=FN, fontsize=FS, color=COLOR)

    # ITEM 12: F.I.R. Contents (Multiline Rect starting at y=188 cleanly below header)
    fir_contents = g(fir_data, "fir_contents", "Statement of incident.")
    _draw_textbox_rect(page1, fir_contents, 69.0, 188.0, 540.0, 355.0, fontname=FN, fontsize=8.0, color=COLOR)

    # ITEM 13: Action Taken & Officer Details
    # The official template contains printed prose. Only populate dynamic officer fields on dotted lines.
    officer = fir_data.get("officer", {}) if isinstance(fir_data.get("officer"), dict) else {}
    off_name = g(officer, "name", "Not provided")
    off_rank = g(officer, "rank", "Not provided")

    # Draw officer name cleanly on 1st dotted line after 'direction /' at x=370, y=388
    if off_name != "Not provided":
        _draw_text_point(page1, off_name, 370.0, 388.0, fontname=FN, fontsize=FS, color=COLOR)
    else:
        _draw_text_point(page1, "Not provided", 370.0, 388.0, fontname=FN, fontsize=FS, color=COLOR)

    # Draw officer rank on 2nd dotted line after 'Rank' at x=496, y=388
    if off_rank != "Not provided":
        _draw_text_point(page1, off_rank, 496.0, 388.0, fontname=FN, fontsize=FS, color=COLOR)

    # OFFICER DETAILS (Item 13 Footer block)
    _draw_text_point(page1, g(officer, "name"), 356.0, 482.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page1, g(officer, "rank"), 348.0, 496.0, fontname=FN, fontsize=FS, color=COLOR)
    _draw_text_point(page1, g(officer, "number", "N/A"), 470.0, 496.0, fontname=FN, fontsize=7.0, color=COLOR)


    # ITEM 14: Complainant Signature area (Left intentionally clean / un-overlapped)

    # ITEM 15: Date & Time of Despatch to Court
    dt_court = fir_data.get("dispatch_to_court", {}) if isinstance(fir_data.get("dispatch_to_court"), dict) else {}
    if isinstance(dt_court, dict):
        d_val = g(dt_court, 'date', 'To be dispatched')
        t_val = g(dt_court, 'time', '')
        if d_val == t_val or not t_val or t_val in d_val:
            disp_str = d_val
        else:
            disp_str = f"{d_val} {t_val}".strip()
    else:
        disp_str = str(dt_court)
    _draw_text_point(page1, disp_str, 242.0, 550.0, fontname=FN, fontsize=FS, color=COLOR)

    # Write output to bytes
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes
