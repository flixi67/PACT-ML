import pdfplumber
import re
import glob
import os
from modules.helpers.validity_check import check_paragraphs, load_expected_counts, pdf_filename_to_dict_key

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
    full_text = []

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

            # Extract text from the cropped region
            text = cropped_page.extract_text()

            # if text:
            #     # Split the text into paragraphs
            #     lines = text.split("\n")
                
            #     for line in lines:
            #         # paragraphs.append(paragraph.strip())
            #         # Check if the paragraph starts with a numbered line (e.g., "1.    ")
            #         if re.match(r"(?m)^\d+\.\s.*(?:\n(?!\d+\.).*)*", paragraph.strip()):
            #             paragraphs.append(line.strip())

            full_text.append(text)

    return full_text

def extract_paragraphs(text):
    """
    Extracts paragraphs starting with Arabic numbers (e.g., 1., 2., 3.) and appends
    subsequent lines that do not start a new numbered paragraph.

    Args:
        text (str): The text to process.

    Returns:
        list: A list of extracted paragraphs.
    """
    # Define the regex for numbered paragraphs
    regex = r"(?m)^\d+\.\s.*(?:\n(?!\d+\.).*)*"
    roman_header_pattern = r"^[IVXLCDM]+\.\s+[A-Z]"

    # Split the text into lines
    lines = text.split("\n")

    paragraphs = []
    current_paragraph = ""
    started = False  # Flag to start collecting after the first numbered paragraph

    for line in lines:
        line = line.strip()

        # Skip Roman numeral section headers
        if re.match(roman_header_pattern, line):
            continue

        # If the line starts a numbered paragraph
        if re.match(regex, line):
            if started and current_paragraph:
                paragraphs.append(current_paragraph.strip())
            current_paragraph = line
            started = True
        else:
            if started:  # Only collect text after numbered paragraphs begin
                current_paragraph += " " + line

    # Add the last paragraph if it exists
    if current_paragraph:
        paragraphs.append(current_paragraph.strip())

    return paragraphs


def main():
    # Path to the folder containing PDFs
    pdf_folder = "data/pdfs"
    
    # General margins for most reports
    margins = {
        "first_page_top": 575,
        "other_pages_top": 720,
        "left": 50,
        "right": 495,
        "bottom": 92
    }

    # Specific margins for "MINUJUSTH" reports
    minujusth_margins = {
        "first_page_top": 582,
        "other_pages_top": 727,
        "left": 50,
        "right": 495,
        "bottom": 57
    }

    # Get a list of all PDF files in the folder
    # pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    pdf_files = [f for f in glob.glob(os.path.join(pdf_folder, "*.pdf")) if "MINUJUSTH" in os.path.basename(f)]

    data = []

    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path}")
        
        # Extract text from each PDF
        text = extract_text_within_margins(pdf_path, margins, minujusth_margins)
        text = "\n".join(filter(None, text))  # Join and skip None pages

        # Extract paragraphs
        paragraphs = extract_paragraphs(text)

        # Validity check and only write to training data if it passes
        actual_paragraphs = len(paragraphs)
        if check_paragraphs(pdf_path, actual_paragraphs):
            # Add each paragraph to the data with consecutive numbering
            for i, paragraph in enumerate(paragraphs, 1):
                data.append({
                    'paragraph': paragraph,
                    'paragraphNumber': i,
                    'filePath': pdf_path,  # Store original file path
                    'fileName': os.path.basename(pdf_path)  # Store just the filename
                })
            print(f"Added {len(paragraphs)} paragraphs from {pdf_path}")
        else:
            expected_counts = load_expected_counts()
            report_name = pdf_filename_to_dict_key(os.path.basename(pdf_path))
            expected = expected_counts.get(report_name, "unknown")
            print(f"Paragraph count mismatch for {pdf_path}. Expected: {expected}, Got: {actual_paragraphs}")


if __name__ == "__main__":
    main()