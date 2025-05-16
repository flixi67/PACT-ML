import pdfplumber
import re
import glob
import os
import pandas as pd
from modules.helpers.validity_check import check_paragraphs, load_expected_counts, fuzzy_match_report_key

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
            # Skip pages that don't have standard dimensions (612 x 792 points)
            if abs(page.width) != 612 or abs(page.height) != 792:
                print(f"Skipping non-standard page {page_number+1} in {os.path.basename(pdf_path)} (dimensions: {page.width} x {page.height})")
                full_text.append(None)  # Add None to maintain page count
                continue

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
    regex = r"(?m)^\d{1,3}\.\s.*(?:\n(?!\d+\.).*)*"
    roman_header_pattern = r"^[IVXLCDM]+\.\s+[A-Z]"
    numbered_para_pattern = r"^(\d+)\.\s+(.*)"

    # Split the text into lines
    lines = text.split("\n")

    paragraphs = []
    current_paragraph = ""
    current_number = None
    started = False  # Flag to start collecting after the first numbered paragraph

    for line in lines:
        line = line.strip()

        # Skip Roman numeral section headers
        if re.match(roman_header_pattern, line):
            continue

        # If the line starts a numbered paragraph
        match = re.match(numbered_para_pattern, line)
        if re.match(regex, line):
            if started and current_paragraph and current_number is not None:
                paragraphs.append((current_number, current_paragraph.strip()))
            current_paragraph = line
            started = True

            # Start new paragraph with detected number
            current_number = int(match.group(1))
            current_paragraph = line
            started = True
        else:
            if started:  # Only collect text after numbered paragraphs begin
                current_paragraph += " " + line

    # Add the last paragraph if it exists
    if current_paragraph and current_number is not None:
        paragraphs.append((current_number, current_paragraph.strip()))

    consecutive_paragraphs = []
    expected_number = 1
    
    for num, para in paragraphs:
        if num >= expected_number:
            consecutive_paragraphs.append((num, para))
            expected_number = num
        else:
            # Skip non-consecutive paragraphs
            print(f"Skipping non-consecutive paragraph: {num} (expected {expected_number})")
    
    return consecutive_paragraphs

def print_paragraphs_debug(numbered_paragraphs):
    """
    Prints a debug representation of the extracted paragraphs.
    
    Args:
        numbered_paragraphs: List of tuples (paragraph_number, paragraph_text)
    """
    print("\n===== Extracted Paragraphs =====")
    print(f"Total paragraphs: {len(numbered_paragraphs)}")
    
    for i, (num, paragraph) in enumerate(numbered_paragraphs):
        # Get the first 80 characters of the paragraph for preview
        preview = paragraph[:80].replace('\n', ' ') + ("..." if len(paragraph) > 80 else "")
        print(f"[{i+1}/{len(numbered_paragraphs)}] #{num}: {preview}")
    
    # Print consecutive number check
    if numbered_paragraphs:
        expected_sequence = list(range(1, len(numbered_paragraphs) + 1))
        actual_sequence = [num for num, _ in numbered_paragraphs]
        is_consecutive = (actual_sequence == expected_sequence)
        
        print(f"\nConsecutive numbering: {'✓ YES' if is_consecutive else '✗ NO'}")
        if not is_consecutive:
            print(f"Expected sequence: {expected_sequence}")
            print(f"Actual sequence:   {actual_sequence}")
    
    print("================================\n")

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
    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    # pdf_files = [f for f in glob.glob(os.path.join(pdf_folder, "*.pdf")) if "UNMIK" in os.path.basename(f)]

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
        # Load expected counts
        expected_counts = load_expected_counts()
        # Get the keys from the dictionary
        keys = list(expected_counts.keys())
        # Get filename from path
        pdf_filename = os.path.basename(pdf_path)
        # Find the best matching key
        matching_key = fuzzy_match_report_key(pdf_filename, keys)

        # print_paragraphs_debug(paragraphs)

        if matching_key is not None:
            expected = expected_counts[matching_key]
            min_acceptable = expected * 0.9  # 10% lower threshold
            max_acceptable = expected * 1.1  # 10% upper threshold
            
            is_valid = min_acceptable <= actual_paragraphs <= max_acceptable
            
            if is_valid:
                # Add each paragraph to the data with consecutive numbering
                for num, paragraph in paragraphs:
                    data.append({
                        'paragraph': paragraph,
                        'paragraphNumber': num,
                        'filePath': pdf_path,  # Store original file path
                        'fileName': pdf_filename, # Store just the filename
                        'matchingKey': matching_key # add maching key for traceability
                    })
                print(f"Added {len(paragraphs)} paragraphs from {pdf_path} (matched to {matching_key})")
            else:
                print(f"Paragraph count outside 10% threshold for {pdf_filename}. Expected: {expected}, Got: {actual_paragraphs} (matched to {matching_key})")
        else:
            print(f"No matching key found for {pdf_filename}")

    df = pd.DataFrame(data)

    df.to_csv("data/PACT_paragraphs_training.csv", index=False)        


if __name__ == "__main__":
    main()