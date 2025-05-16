import json
import re
import os
from thefuzz import process

def load_expected_counts(json_path="data/paragraph_numbers.json"):
    with open(json_path, "r") as f:
        return json.load(f)

def fuzzy_match_report_key(pdf_filename, expected_keys):
    """
    Find the best matching dictionary key for a PDF filename by treating _ and / as equivalent.
    
    Args:
        pdf_filename (str): The PDF filename (e.g., "MINUJUSTH_S_2018_1059.pdf")
        expected_keys (list): List of keys from the dictionary
    
    Returns:
        str: The best matching dictionary key, or None if no good match found
    """
    # Remove .pdf extension
    clean_name = pdf_filename.replace('.pdf', '')
    
    # Special case for rev.1
    if "rev.1" in clean_name:
        clean_name = clean_name.replace("rev.1", "rev1")
    
    special_cases = {
        "UNMIK_2011_514": "UNMIK_S_2011_514",
        "UNMISET_S_2004_888": "UNMISET_S2004_888",
    }
    
    if clean_name in special_cases:
        return special_cases[clean_name]
    
    # Use thefuzz to find the best match
    best_match, score = process.extractOne(clean_name, expected_keys)
    
    # Only return matches above a certain score threshold
    if score >= 85:  # You can adjust this threshold as needed
        return best_match
    
    return None


def check_paragraphs(pdf_path, actual_count):
    # Get filename from path
    pdf_filename = os.path.basename(pdf_path)
    
    # Load expected counts
    expected_counts = load_expected_counts()
    
    # Get the keys from the dictionary
    keys = list(expected_counts.keys())
    
    # Find the best matching key
    matching_key = fuzzy_match_report_key(pdf_filename, keys)
    
    if matching_key is None:
        print(f"No matching key found for {pdf_filename}")
        return False
    
    expected = expected_counts[matching_key]
    return actual_count == expected