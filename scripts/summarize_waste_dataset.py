import os
import csv
from pathlib import Path

def count_images(directory):
    path = Path(directory)
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob('*') if p.is_file())

def main():
    base_dir = Path("waste_dataset_v1")
    metadata_dir = base_dir / "metadata"
    
    if not metadata_dir.exists():
        print(f"Error: {metadata_dir} not found.")
        return

    classes = [
        "Battery", "Biological", "Cardboard", "Clothes", "E_Waste",
        "Glass", "Metal", "Paper", "Plastic", "Other"
    ]

    summary_data = []
    total_raw = 0
    total_clean = 0
    total_train = 0
    total_val = 0
    total_test = 0

    print("Generating summary...")

    for cls in classes:
        raw_count = count_images(base_dir / "raw_mapped" / cls)
        clean_count = count_images(base_dir / "clean" / cls)
        train_count = count_images(base_dir / "splits" / "train" / cls)
        val_count = count_images(base_dir / "splits" / "val" / cls)
        test_count = count_images(base_dir / "splits" / "test" / cls)

        total_raw += raw_count
        total_clean += clean_count
        total_train += train_count
        total_val += val_count
        total_test += test_count

        summary_data.append({
            'class_name': cls,
            'raw_mapped': raw_count,
            'clean': clean_count,
            'train': train_count,
            'val': val_count,
            'test': test_count
        })

    # Write CSV
    csv_path = metadata_dir / "dataset_summary.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['class_name', 'raw_mapped', 'clean', 'train', 'val', 'test'])
        writer.writeheader()
        writer.writerows(summary_data)

    # Count rejected
    corrupt_count = count_images(base_dir / "rejected" / "corrupt")
    duplicate_count = count_images(base_dir / "rejected" / "duplicate")
    unmapped_count = count_images(base_dir / "rejected" / "unmapped")

    # Write README
    readme_path = metadata_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("# Waste Dataset v1\n\n")
        f.write("## Objective\n")
        f.write("Dataset prepared for training a ResNet model for Smart Trash Bin / Waste Classification in Vietnam.\n\n")
        
        f.write("## Sources\n")
        f.write("- Primary: Vietnam Domestic Solid Waste (Kaggle)\n")
        f.write("- Secondary: Garbage Classification 12 classes (Kaggle)\n\n")
        
        f.write("## Classes and Mapping\n")
        f.write("10 standard classes mapped to 4 bin types:\n")
        f.write("- **Hazardous**: Battery, E_Waste\n")
        f.write("- **Organic**: Biological\n")
        f.write("- **Recyclable**: Cardboard, Glass, Metal, Paper, Plastic\n")
        f.write("- **Other**: Clothes, Other\n\n")
        
        f.write("## Split Ratio\n")
        f.write("Train / Val / Test = 70% / 15% / 15%\n\n")
        
        f.write("## Summary Statistics\n")
        f.write(f"- Total Raw Mapped: {total_raw}\n")
        f.write(f"- Total Clean: {total_clean}\n")
        f.write(f"- Total Train: {total_train}\n")
        f.write(f"- Total Val: {total_val}\n")
        f.write(f"- Total Test: {total_test}\n\n")
        
        f.write("### Rejected Images\n")
        f.write(f"- Corrupt: {corrupt_count}\n")
        f.write(f"- Duplicate: {duplicate_count}\n")
        f.write(f"- Unmapped: {unmapped_count}\n\n")
        
        f.write("### Class Breakdown\n")
        f.write("| Class | Raw | Clean | Train | Val | Test |\n")
        f.write("|---|---|---|---|---|---|\n")
        for row in summary_data:
            f.write(f"| {row['class_name']} | {row['raw_mapped']} | {row['clean']} | {row['train']} | {row['val']} | {row['test']} |\n")
            
        f.write("\n## Warnings\n")
        for row in summary_data:
            if row['clean'] < 500:
                f.write(f"- **Warning**: Class '{row['class_name']}' has less than 500 clean images ({row['clean']}).\n")
                
        f.write("\n## Note\n")
        f.write("Image files are not committed to git. Only metadata and scripts are tracked.\n")

    print(f"\nSummary generated at {csv_path} and {readme_path}")
    
    print("\nFinal Report:")
    print(f"Total Raw Mapped: {total_raw}")
    print(f"Total Clean: {total_clean}")
    print(f"Total Train: {total_train}")
    print(f"Total Val: {total_val}")
    print(f"Total Test: {total_test}")
    print(f"Corrupt: {corrupt_count}")
    print(f"Duplicate: {duplicate_count}")
    print(f"Unmapped: {unmapped_count}")
    
    print("\nClass Breakdown:")
    for row in summary_data:
        print(f"  {row['class_name']}: {row['clean']} clean images")
        if row['clean'] < 500:
            print(f"    -> WARNING: Less than 500 images!")

if __name__ == "__main__":
    main()