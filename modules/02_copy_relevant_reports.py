import os
import shutil
import pandas as pd

def copy_cluster_pdfs(csv_path, destination_folder, target_cluster=2):
    """
    Copies PDFs from a given cluster to a destination folder.

    Args:
        csv_path (str): Path to the clustering results CSV file.
        destination_folder (str): Path to the folder where PDFs will be copied.
        target_cluster (int): Cluster number to filter and copy PDFs.
    """
    # Read the clustering results
    try:
        clustering_results = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_path}")
        return

    # Ensure the destination folder exists
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # Filter PDFs belonging to the target cluster
    target_pdfs = clustering_results[clustering_results["Cluster"] == target_cluster]["PDF"]

    # Copy each PDF to the destination folder
    for pdf in target_pdfs:
        if os.path.exists(pdf):
            shutil.copy(pdf, destination_folder)
            print(f"Copied: {pdf}")
        else:
            print(f"File not found, skipping: {pdf}")

    print(f"All PDFs from cluster {target_cluster} have been copied to {destination_folder}.")

if __name__ == "__main__":
    # Input paths
    csv_path = "data/clustering_results.csv"  # Path to the clustering results CSV file
    destination_folder = "data/pdfs"  # Folder where PDFs will be copied

    # Copy PDFs from cluster 2
    copy_cluster_pdfs(csv_path, destination_folder, target_cluster=1)