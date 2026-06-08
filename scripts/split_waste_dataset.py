import os
import csv
import shutil
import random
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Split clean dataset into train/val/test.")
    parser.add_argument("--limit-per-class", type=int, default=None, help="Limit number of images per class for testing.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args()

    random.seed(args.seed)

    clean_dir = Path("waste_dataset_v1/clean")
    splits_dir = Path("waste_dataset_v1/splits")
    split_manifest_path = "waste_dataset_v1/metadata/split_manifest.csv"
    
    if not clean_dir.exists():
        print(f"Error: {clean_dir} not found. Run clean script first.")
        return

    # Create directories
    for split in ['train', 'val', 'test']:
        for class_dir in clean_dir.iterdir():
            if class_dir.is_dir():
                os.makedirs(splits_dir / split / class_dir.name, exist_ok=True)

    split_counts = {'train': {}, 'val': {}, 'test': {}}
    
    print("Splitting dataset...")
    
    with open(split_manifest_path, 'w', newline='', encoding='utf-8') as outfile:
        fieldnames = ['class_name', 'split', 'path', 'original_clean_path']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for class_dir in clean_dir.iterdir():
            if not class_dir.is_dir():
                continue
                
            class_name = class_dir.name
            split_counts['train'][class_name] = 0
            split_counts['val'][class_name] = 0
            split_counts['test'][class_name] = 0
            
            print(f"Processing class: {class_name}")
            
            images = [p for p in class_dir.iterdir() if p.is_file()]
            if args.limit_per_class:
                images = images[:args.limit_per_class]
                
            random.shuffle(images)
            
            n_total = len(images)
            n_train = int(n_total * 0.7)
            n_val = int(n_total * 0.15)
            
            train_imgs = images[:n_train]
            val_imgs = images[n_train:n_train+n_val]
            test_imgs = images[n_train+n_val:]
            
            splits = [('train', train_imgs), ('val', val_imgs), ('test', test_imgs)]
            
            for split_name, split_imgs in splits:
                for img_path in split_imgs:
                    dest_path = splits_dir / split_name / class_name / img_path.name
                    try:
                        try:
                            os.link(img_path, dest_path)
                        except OSError:
                            shutil.copy2(img_path, dest_path)
                        split_counts[split_name][class_name] += 1
                        
                        writer.writerow({
                            'class_name': class_name,
                            'split': split_name,
                            'path': str(dest_path),
                            'original_clean_path': str(img_path)
                        })
                    except Exception as e:
                        print(f"Error copying {img_path} to {split_name}: {e}")

    print("\nSplitting complete. Summary:")
    for split_name, counts in split_counts.items():
        print(f"\n{split_name.upper()}:")
        for cls, count in counts.items():
            print(f"  {cls}: {count}")

if __name__ == "__main__":
    main()