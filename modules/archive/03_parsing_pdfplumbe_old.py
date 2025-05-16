import pdfplumber
import re

def extract_clean_paragraphs(pdf_path, margins, minujusth_margins=None):
    paragraphs_all_pages = []

    # Determine if the file is a "MINUJUSTH" report
    is_minujusth = "MINUJUSTH" in pdf_path.upper()

    # Select margins based on the file type
    selected_margins = minujusth_margins if is_minujusth and minujusth_margins else margins

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages):
            # Determine the top margin based on the page number
            if page_number == 0:
                top_margin = selected_margins["first_page_top"]
            else:
                top_margin = selected_margins["other_pages_top"]

            # Crop the page to the specified margins
            cropped_page = page.within_bbox((
                selected_margins["left"],
                selected_margins["bottom"],
                selected_margins["right"],
                top_margin
            ))
            
            words = cropped_page.extract_words()

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
                para_text = "\n".join(current_para)
                if re.match(r"^\d+\.\s.*", para_text):
                    paragraphs.append(" ".join(current_para))
        


            paragraphs_all_pages.extend(paragraphs)

    return paragraphs_all_pages

if __name__ == "__main__":
    pdf_files = [
        "data/pdfs/UNIKOM_S_2003_393.pdf"
    ]

    margins = {
        "first_page_top": 575,  # Top margin for the first page in points
        "other_pages_top": 720,  # Top margin for all other pages in points
        "left": 50,   # Left margin in points
        "right": 495,  # Right margin in points
        "bottom": 92  # Bottom margin in points
    }

    # Specific margins for "MINUJUSTH" reports
    minujusth_margins = {
        "first_page_top": 582,  # Top margin for the first page in points
        "other_pages_top": 727,  # Top margin for all other pages in points
        "left": 50,   # Left margin in points
        "right": 495,  # Right margin in points
        "bottom": 57  # Bottom margin in points
    }

    for pdf_file in pdf_files:
        paragraphs = extract_clean_paragraphs(pdf_file, margins, minujusth_margins)

        # Print the extracted paragraphs
        print("Extracted Paragraphs:")
        for paragraph in paragraphs:
            print(paragraph)
            print("-" * 80)
