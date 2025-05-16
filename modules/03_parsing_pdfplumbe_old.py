from pathlib import Path
import pdfplumber

def extract_clean_paragraphs(pdf_path):
    paragraphs_all_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()

            # Remove likely headers/footers
            words = [w for w in words if 70 < w['top'] < 750]

            # Sort top to bottom, left to right
            words = sorted(words, key=lambda w: (round(w['top'], 1), w['x0']))

            # Group into lines
            lines_dict = {}
            for w in words:
                key = round(w['top'], 1)
                if key not in lines_dict:
                    lines_dict[key] = []
                lines_dict[key].append(w)
            lines = list(lines_dict.values())

            # Group into paragraphs
            paragraphs = []
            current_para = []
            last_y = None
            for line in lines:
                y = min(w['top'] for w in line)
                line_text = " ".join(w['text'] for w in line)
                if last_y is not None and abs(y - last_y) > 15:
                    if current_para:
                        paragraphs.append(" ".join(current_para))
                        current_para = []
                current_para.append(line_text)
                last_y = y
            if current_para:
                paragraphs.append(" ".join(current_para))

            paragraphs_all_pages.extend(paragraphs)

    return paragraphs_all_pages

def convert_pdf_to_markdown(pdf_path):
    paragraphs = extract_clean_paragraphs(pdf_path)
    output_path = Path(pdf_path).with_suffix(".md")
    with open(output_path, "w", encoding="utf-8") as f:
        for para in paragraphs:
            f.write(para + "\n\n")
    print(f"Saved: {output_path}")

if __name__ == "__main__":
    pdf_files = [
        "data/pdfs/UNIKOM_S_2003_393.pdf"
    ]

    for pdf_file in pdf_files:
        paragraphs = extract_clean_paragraphs(pdf_file)

        # Print the extracted paragraphs
        print("Extracted Paragraphs:")
        for paragraph in paragraphs:
            print(paragraph)
            print("-" * 80)
