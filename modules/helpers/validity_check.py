import json
import re
import os

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
    name_without_extension = pdf_filename.replace('.pdf', '')
    
    # Remove numeric suffixes at the end (like _1, _4)
    clean_name = re.sub(r'_\d+$', '', name_without_extension)
    
    # Special case for rev.1
    if "rev.1" in clean_name:
        clean_name = clean_name.replace("rev.1", "rev1")
    
    # Create normalized versions for comparison (treat _ and / the same)
    normalized_name = clean_name.replace('_', '.').replace('/', '.')
    
    # Special case for UNMIK without S
    if normalized_name.startswith("UNMIK.") and ".S." not in normalized_name:
        normalized_name = normalized_name.replace("UNMIK.", "UNMIK.S.")
    
    best_match = None
    best_score = 0
    
    for key in expected_keys:
        # Normalize the dictionary key too
        normalized_key = key.replace('_', '.').replace('/', '.')
        
        # Calculate similarity score (simple method - shared prefix length)
        prefix_length = 0
        for i in range(min(len(normalized_name), len(normalized_key))):
            if normalized_name[i] == normalized_key[i]:
                prefix_length += 1
            else:
                break
        
        # Bias score toward complete matches of segments
        segments_name = normalized_name.split('.')
        segments_key = normalized_key.split('.')
        shared_segments = sum(1 for a, b in zip(segments_name, segments_key) if a == b)
        
        # Calculate total score
        score = prefix_length + shared_segments * 5  # Weight segment matches higher
        
        if score > best_score:
            best_score = score
            best_match = key
    
    # Set a minimum threshold for considering it a match
    min_threshold = max(10, min(len(normalized_name), len(normalized_key)) / 2)
    if best_score < min_threshold:
        return None
    
    return best_match


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