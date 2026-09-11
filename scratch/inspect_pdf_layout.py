import fitz  # PyMuPDF
import json

doc = fitz.open("templates/fir/IF1_FIR_Template.pdf")

print(f"Total pages: {len(doc)}")

for page_num in range(len(doc)):
    page = doc[page_num]
    rect = page.rect
    print(f"\n--- PAGE {page_num} (width={rect.width}, height={rect.height}) ---")
    
    # Get all text words with bounding boxes: (x0, y0, x1, y1, word, block_no, line_no, word_no)
    words = page.get_text("words")
    lines = {}
    for w in words:
        # Group words by approximate vertical line (y0)
        y_approx = round(w[1] / 5) * 5
        lines.setdefault(y_approx, []).append(w)
    
    for y_approx in sorted(lines.keys()):
        line_words = sorted(lines[y_approx], key=lambda x: x[0])
        line_text = " ".join([w[4] for w in line_words])
        x0_min = line_words[0][0]
        x1_max = line_words[-1][2]
        y0 = line_words[0][1]
        y1 = line_words[0][3]
        print(f"y={y0:.1f}..{y1:.1f} | x={x0_min:.1f}..{x1_max:.1f} | Text: {line_text}")
