import fitz  # PyMuPDF
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = PROJECT_ROOT / "scratch" / "test_output_demo_fir.pdf"

doc = fitz.open(str(PDF_PATH))
print(f"Opening PDF: {PDF_PATH} ({len(doc)} pages)")

zoom = 2.0  # 2.0 = 144 DPI, clear resolution
mat = fitz.Matrix(zoom, zoom)

out_images = []
for i in range(len(doc)):
    page = doc[i]
    pix = page.get_pixmap(matrix=mat)
    out_img_path = PROJECT_ROOT / "scratch" / f"page_{i+1}_demo.png"
    pix.save(str(out_img_path))
    out_images.append(str(out_img_path))
    print(f"Rendered Page {i+1} -> {out_img_path}")

print("Done rendering pages to PNG.")
