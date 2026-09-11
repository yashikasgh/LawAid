import fitz
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "fir" / "IF1_FIR_Template.pdf"

doc = fitz.open(str(TEMPLATE_PATH))
page1 = doc[1]

text_instances = page1.get_text("words")
print("=== WORDS ON PAGE 1 AROUND ITEM 13 (y between 350 and 520) ===")
for word in text_instances:
    # word format: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
    if 350 <= word[1] <= 520:
        print(f"y={word[1]:.1f}, x={word[0]:.1f}: {word[4]}")
