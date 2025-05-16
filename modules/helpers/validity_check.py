import json

def load_expected_counts(json_path="data/paragraph_numbers.json"):
    with open(json_path, "r") as f:
        return json.load(f)

def pdf_filename_to_dict_key(pdf_filename):
    """
    Convert a PDF filename to the corresponding dictionary key format.
    
    Args:
        pdf_filename (str): The PDF filename (e.g., "MINUJUSTH_S_2018_1059.pdf")
    
    Returns:
        str: The dictionary key format (e.g., "MINUJUSTH_S/2018/1059")
    """
    # Remove .pdf extension
    name_without_extension = pdf_filename.replace('.pdf', '')
    
    # Special case for UNMIK_2011_514.pdf (missing the "S")
    if name_without_extension == "UNMIK_2011_514":
        return "UNMIK_S/2011/514"
    
    # Handle special case where UNMISET_S2004/888 is missing an underscore
    if name_without_extension == "UNMISET_S_2004_888":
        return "UNMISET_S2004/888"
    
    # Handle special case for rev.1
    if "rev.1" in name_without_extension:
        name_without_extension = name_without_extension.replace("rev.1", "rev1")
    
    # Handle numeric suffixes (like _1, _4) at the end
    name = re.sub(r'_\d+$', '', name_without_extension)
    
    # Find the positions of the underscores
    underscores = [i for i, char in enumerate(name) if char == '_']
    
    if len(underscores) >= 3:
        # Replace 2nd and 3rd underscores with slashes
        result = list(name)
        result[underscores[1]] = '/'
        result[underscores[2]] = '/'
        return ''.join(result)
    
    # If there aren't enough underscores, return as is
    return name


def check_paragraphs(pdf_path, actual_count):
    report_name = pdf_filename_to_dict_key(pdf_path)
    expected_counts = load_expected_counts()
    expected = expected_counts.get(report_name)
    if expected is None:
        return False  # unknown report
    return actual_count == expected