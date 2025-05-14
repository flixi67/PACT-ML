import pdfplumber
import re

def extract_text_within_margins(pdf_path, margins, minujusth_margins=None):
    """
    Extracts text from a PDF within specified margins, allowing for separate margins
    for reports containing "MINUJUSTH" in their name.

    Args:
        pdf_path (str): Path to the PDF file.
        margins (dict): Dictionary with general margins (first_page_top, other_pages_top, left, right, bottom).
        minujusth_margins (dict, optional): Margins specific to "MINUJUSTH" reports.

    Returns:
        list: List of paragraphs found within the specified margins.
    """
    paragraphs = []

    # Determine if the file is a "MINUJUSTH" report
    is_minujusth = "MINUJUSTH" in pdf_path.upper()

    # Select margins based on the file type
    selected_margins = minujusth_margins if is_minujusth and minujusth_margins else margins

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages):
            # Determine the top margin based on the page number
            top_margin = (
                selected_margins["first_page_top"] if page_number == 0 else selected_margins["other_pages_top"]
            )

            # Crop the page to the specified margins
            cropped_page = page.within_bbox((
                selected_margins["left"],
                top_margin,
                selected_margins["right"],
                selected_margins["bottom"]
            ))

            # Extract text from the cropped region
            text = cropped_page.extract_text()

            if text:
                # Split the text into paragraphs
                raw_paragraphs = text.split("\n\n")
                
                for paragraph in raw_paragraphs:
                    # Check if the paragraph starts with a numbered line (e.g., "1.    ")
                    if re.match(r"^\d+\.\s{2,}", paragraph.strip()):
                        paragraphs.append(paragraph.strip())

    return paragraphs


def main():
    # Path to the PDF file
    pdf_path = "data/pdfs/UNIKOM_S_2003_393.pdf"

    # General margins for most reports
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

    # Extract paragraphs within the margins
    paragraphs = extract_text_within_margins(pdf_path, margins, minujusth_margins)

    # Print the extracted paragraphs
    print("Extracted Paragraphs:")
    for paragraph in paragraphs:
        print(paragraph)
        print("-" * 80)


if __name__ == "__main__":
    main()