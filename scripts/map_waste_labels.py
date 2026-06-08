import os
import csv
import shutil
import hashlib
import argparse
from pathlib import Path

# Mapping rules
LABEL_MAPPING = {
    "Battery": ["battery", "batteries", "pin"],
    "Biological": ["biological", "organic", "food", "kitchen", "fruit", "vegetable", "leftover"],
    "Cardboard": ["cardboard", "carton"],
    "Clothes": ["clothes", "clothing", "textile", "fabric", "cloth", "leather"],
    "E_Waste": ["e-waste", "ewaste", "electronic", "electrical", "electronics", "device", "mobile", "cable", "charger"],
    "Glass": ["glass", "bottle_glass"],
    "Metal": ["metal", "can", "aluminum", "aluminium", "steel"],
    "Paper": ["paper", "newspaper", "book", "notebook"],
    "Plastic": ["plastic", "bottle_plastic", "nylon", "bag", "cup"],
    "Other": ["trash", "other", "miscellaneous", "residual", "non-recyclable", "non_recyclable", "wood", "rubber", "hazardous", "medical", "light"]
}

def get_target_class(original_label):
    label_lower = original_label.lower()
    for target_class, keywords in LABEL_MAPPING.items():
        if any(keyword in label_lower for keyword in keywords):
            return target_class
    return None

def generate_hash(filepath, chunk_size=8192):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()[:8]

def main():
    parser = argparse.ArgumentParser(description="Map waste labels to target classes.")
    parser.add_argument("--limit-per-class", type=int, default=None, help="Limit number of images per class for testing.")
    args = parser.parse_args()

    source_manifest_path = "waste_dataset_v1/metadata/source_manifest.csv"
    mapped_manifest_path = "waste_dataset_v1/metadata/mapped_manifest.csv"
    raw_mapped_dir = Path("waste_dataset_v1/raw_mapped")
    rejected_dir = Path("waste_dataset_v1/rejected/unmapped")
    
    if not os.path.exists(source_manifest_path):
        print(f"Error: {source_manifest_path} not found. Run inspect script first.")
        return

    # Create directories
    for target_class in LABEL_MAPPING.keys():
        os.makedirs(raw_mapped_dir / target_class, exist_ok=True)
    os.makedirs(rejected_dir, exist_ok=True)

    class_counts = {target_class: 0 for target_class in LABEL_MAPPING.keys()}
    
    print("Mapping labels and copying files...")
    
    with open(source_manifest_path, 'r', encoding='utf-8') as infile, \
         open(mapped_manifest_path, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(infile)
        fieldnames = ['source_dataset', 'original_label', 'target_class', 'source_path', 'mapped_path', 'status']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            source_path = Path(row['filepath'])
            if not source_path.exists():
                continue
                
            original_label = row['original_label']
            source_dataset = row['source_dataset']
            extension = row['extension']
            
            target_class = get_target_class(original_label)
            
            if target_class:
                if args.limit_per_class and class_counts[target_class] >= args.limit_per_class:
                    continue
                
                file_hash = generate_hash(source_path)
                new_filename = f"{source_dataset}_{original_label}_{file_hash}{extension}"
                mapped_path = raw_mapped_dir / target_class / new_filename
                
                try:
                    shutil.copy2(source_path, mapped_path)
                    status = "mapped"
                    class_counts[target_class] += 1
                except Exception as e:
                    print(f"Error copying {source_path}: {e}")
                    status = "error"
                    mapped_path = ""
            else:
                file_hash = generate_hash(source_path)
                new_filename = f"{source_dataset}_{original_label}_{file_hash}{extension}"
                mapped_path = rejected_dir / new_filename
                
                try:
                    shutil.copy2(source_path, mapped_path)
                    status = "unmapped"
                except Exception as e:
                    print(f"Error copying to rejected {source_path}: {e}")
                    status = "error"
                    mapped_path = ""
            
            writer.writerow({
                'source_dataset': source_dataset,
                'original_label': original_label,
                'target_class': target_class if target_class else "None",
                'source_path': str(source_path),
                'mapped_path': str(mapped_path),
                'status': status
            })

    print("\nMapping complete. Summary:")
    for cls, count in class_counts.items():
        print(f"  {cls}: {count}")

if __name__ == "__main__":
    main()