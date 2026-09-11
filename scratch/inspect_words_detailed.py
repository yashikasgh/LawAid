import fitz

doc = fitz.open("templates/fir/IF1_FIR_Template.pdf")

for page_num in range(len(doc)):
    page = doc[page_num]
    print(f"\n==================== PAGE {page_num} ====================")
    words = page.get_text("words")
    # Sort words by y0, then x0
    # Group into lines
    y_lines = {}
    for w in words:
        y_approx = round(w[1] / 3) * 3
        y_lines.setdefault(y_approx, []).append(w)
    
    for y_val in sorted(y_lines.keys()):
        line_w = sorted(y_lines[y_val], key=lambda x: x[0])
        print(f"\n--- Y approx ~ {y_val} (actual y0 min={line_w[0][1]:.1f}, y1 max={line_w[0][3]:.1f}) ---")
        for w in line_w:
            print(f"  x0={w[0]:.1f}, x1={w[2]:.1f} | '{w[4]}'")
