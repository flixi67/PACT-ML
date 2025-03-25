import logging
from pathlib import Path
from docling.document_converter import DocumentConverter  

def parse_reports(input_folder: Path, output_folder: Path):
    logging.basicConfig(level=logging.INFO)

    if not input_folder.exists():
        logging.error(f"Input folder does not exist: {input_folder}")
        return

    output_folder.mkdir(parents=True, exist_ok=True)

    pdf_paths = list(input_folder.glob("*.pdf"))
    if not pdf_paths:
        logging.warning(f"No PDF files found in: {input_folder}")
        return

    logging.info(f"Found {len(pdf_paths)} PDF files to process.")

    converter = DocumentConverter()

    for pdf_path in pdf_paths:
        try:
            logging.info(f"Processing: {pdf_path.name}")
            result = converter.convert(str(pdf_path))

            markdown_content = result.document.export

            output_path = output_folder / f"{pdf_path.stem}.md"
            with output_path.open("w", encoding="utf-8") as f:
                f.write(markdown_content)

            logging.info(f"✓ Saved to: {output_path.name}")

        except Exception as e:
            logging.error(f"Failed to process {pdf_path.name}: {e}")

def main():
    input_folder = Path("./data/")         # Change to your actual folder
    output_folder = Path("./data/parsed/")   # Where .md files will be saved
    convert_pdfs_to_markdown(input_folder, output_folder)

if __name__ == "__main__":
    main()
