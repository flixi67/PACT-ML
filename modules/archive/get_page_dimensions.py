import pdfplumber

def get_page_dimensions(pdf_path):
    """
    Prints the width and height of each page in a PDF.

    Args:
        pdf_path (str): Path to the PDF file.
    """
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            print(f"Page {page_number}:")
            print(f"  Width: {page.width} points")
            print(f"  Height: {page.height} points\n")

# Example usage
pdf_path = "data/pdfs/UNOMIG_S_2008_631.pdf"
get_page_dimensions(pdf_path)
