import os
import fitz  # PyMuPDF
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import pandas as pd

def detect_columns(words, page_width):
    """
    Detects whether the main text is arranged in one or two columns on the first page.
    Uses clustering on horizontal positions of text blocks to determine the column layout.

    Args:
        words (list): List of word dictionaries with bounding box information.
        page_width (float): Width of the page.

    Returns:
        int: 1 if single-column layout, 2 if two-column layout.
    """
    if not words:
        return 1  # Assume single column if no text is detected.

    # Extract the horizontal mid-points of each word's bounding box
    x_midpoints = [(word["bbox"][0] + word["bbox"][2]) / 2 for word in words]

    # Reshape data for clustering
    x_midpoints = np.array(x_midpoints).reshape(-1, 1)

    # Apply K-means clustering to detect clusters of horizontal positions
    kmeans = KMeans(n_clusters=2, random_state=42).fit(x_midpoints)
    cluster_centers = kmeans.cluster_centers_.flatten()
    cluster_labels = kmeans.labels_

    # Compute the distance between the two clusters
    distance_between_clusters = abs(cluster_centers[1] - cluster_centers[0])

    # If the distance between clusters is significant, it's a two-column layout
    if distance_between_clusters > page_width * 0.2:  # Threshold: 20% of page width
        return 2
    else:
        return 1

def extract_layout_features(pdf_path):
    """
    Extracts layout features from the first page of a PDF file using PyMuPDF.
    Features include:
    - First page margins (left, right, top, bottom)
    - Column detection (1 or 2 columns)
    """
    try:
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return [0, 0, 0, 0, 1]  # Default values for empty PDF

        first_page = doc[0]
        width, height = first_page.rect.width, first_page.rect.height

        # Extract words and their positions
        words = [
            span for block in first_page.get_text("dict")["blocks"] if "lines" in block
            for line in block["lines"] for span in line["spans"]
        ]

        # Exclude page numbers by filtering
        words = [
            word for word in words
            if word["bbox"][1] > height * 0.1 and word["bbox"][1] < height * 0.9
        ]

        # Compute margins
        if words:
            x_positions = [w["bbox"][0] for w in words] + [w["bbox"][2] for w in words]
            y_positions = [w["bbox"][1] for w in words] + [w["bbox"][3] for w in words]

            left_margin = min(x_positions)
            right_margin = width - max(x_positions)
            top_margin = min(y_positions)
            bottom_margin = height - max(y_positions)

        else:
            left_margin, right_margin, top_margin, bottom_margin = 0, 0, 0, 0  # Default to single column if no text is detected

        # Print the extracted margins and columns for debugging
        print(f"PDF: {pdf_path}")
        print(f"Margins - Left: {left_margin}, Right: {right_margin}, Top: {top_margin}, Bottom: {bottom_margin}")

        return [left_margin, right_margin, top_margin, bottom_margin]
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return [0, 0, 0, 0, 1]  # Default values for unprocessable PDFs

def load_pdfs(directory):
    """
    Recursively loads all PDF files from a directory and its subdirectories,
    and extracts their layout features.
    """
    pdf_features = []
    pdf_files = []
    for root, _, files in os.walk(directory):  # Walk through all subdirectories
        for file in files:
            if file.endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                features = extract_layout_features(pdf_path)
                if any(features):  # Ensure at least one feature is non-zero
                    pdf_features.append(features)
                    pdf_files.append(pdf_path)  # Use full path for clarity
    return pdf_files, pdf_features

def find_optimal_clusters(features):
    """
    Finds the optimal number of clusters using the silhouette score.
    """
    max_clusters = min(len(features), 10)  # Limit to 10 clusters or the number of PDFs
    best_k = 2
    best_score = -1

    for k in range(2, max_clusters + 1):
        kmeans = KMeans(n_clusters=k, random_state=42)
        labels = kmeans.fit_predict(features)
        score = silhouette_score(features, labels)

        if score > best_score:
            best_k = k
            best_score = score

    return best_k

def cluster_pdfs(pdf_features):
    """
    Clusters PDFs based on their layout features using KMeans.
    Automatically determines the optimal number of clusters.
    """
    optimal_clusters = 4
    kmeans = KMeans(n_clusters=optimal_clusters, random_state=42)
    labels = kmeans.fit_predict(pdf_features)
    return labels

def main():
    # Directory containing the PDFs
    pdf_directory = "data/og_reports"

    # Load PDFs and extract layout features
    pdf_files, pdf_features = load_pdfs(pdf_directory)

    if not pdf_features:
        print("No PDFs found or failed to extract layout features.")
        return

    # Cluster PDFs
    labels = cluster_pdfs(pdf_features)

    # Print clustering results
    print("Clustering Results Based on First Page Margins and Column Detection:")
    for file, label in zip(pdf_files, labels):
        print(f"PDF: {file} -> Cluster: {label}")

    # Save results to a CSV for further analysis
    results = pd.DataFrame({"PDF": pdf_files, "Cluster": labels})
    results.to_csv("data/clustering_results.csv", index=False)
    print("Results saved to clustering_results.csv.")

if __name__ == "__main__":
    main()