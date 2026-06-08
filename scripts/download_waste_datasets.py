import os
import subprocess
import argparse
from pathlib import Path

def run_command(command):
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
    return True

def download_dataset(slug, dest_dir, force=False):
    dest_path = Path(dest_dir)
    if dest_path.exists() and any(dest_path.iterdir()) and not force:
        print(f"Dataset {slug} already exists in {dest_dir}. Skipping download.")
        return True
    
    os.makedirs(dest_dir, exist_ok=True)
    print(f"Downloading dataset {slug} to {dest_dir}...")
    
    # Check if kaggle is installed
    kaggle_cmd = "venv310\\Scripts\\kaggle" if os.name == 'nt' else "kaggle"
    if not run_command(f"{kaggle_cmd} --version"):
        print("Kaggle CLI not found or not configured. Please ensure kaggle.json is in ~/.kaggle/ or KAGGLE_USERNAME/KAGGLE_KEY are set.")
        return False

    cmd = f"{kaggle_cmd} datasets download -d {slug} -p {dest_dir} --unzip"
    if run_command(cmd):
        print(f"Successfully downloaded and unzipped {slug}")
        return True
    return False

def count_images(directory):
    path = Path(directory)
    extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    count = sum(1 for p in path.rglob('*') if p.suffix.lower() in extensions)
    return count

def main():
    parser = argparse.ArgumentParser(description="Download waste datasets from Kaggle.")
    parser.add_argument("--force", action="store_true", help="Force download even if dataset exists.")
    args = parser.parse_args()

    datasets = [
        {"slug": "thanhngnguyn/vietnam-domestic-solid-waste", "dest": "waste_dataset_v1/downloads/vietnam_domestic_solid_waste"},
        {"slug": "mostafaabla/garbage-classification", "dest": "waste_dataset_v1/downloads/garbage_classification_12"}
    ]

    for ds in datasets:
        success = download_dataset(ds["slug"], ds["dest"], force=args.force)
        if success:
            img_count = count_images(ds["dest"])
            print(f"Dataset {ds['slug']}: {img_count} images found.")
        else:
            print(f"Failed to process {ds['slug']}. Please check your Kaggle API key or connection.")

if __name__ == "__main__":
    main()