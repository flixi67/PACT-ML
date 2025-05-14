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

    # Split the text into lines
    lines = text.split("\n")

    paragraphs = []
    current_paragraph = ""

    for line in lines:
        # Check if the line starts a new numbered paragraph
        if re.match(regex, line):
            # Save the current paragraph if it exists
            if current_paragraph:
                paragraphs.append(current_paragraph.strip())
            # Start a new paragraph with the current line
            current_paragraph = line
        else:
            # Append the line to the current paragraph if it doesn't start a new one
            current_paragraph += " " + line

    # Add the last paragraph if it exists
    if current_paragraph:
        paragraphs.append(current_paragraph.strip())

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
    text = extract_text_within_margins(pdf_path, margins, minujusth_margins)

    # Join the list into a single string
    text = "\n".join(text)

    paragraphs = extract_paragraphs(text)

    # Print the extracted paragraphs
    print("Extracted Paragraphs:")
    for paragraph in paragraphs:
        print(paragraph)
        print("-" * 80)


if __name__ == "__main__":
    main()