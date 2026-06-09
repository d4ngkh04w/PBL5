"""
Count images per class in waste_dataset_v1/splits/{train,val,test}
and print a CSV table: class_name,train_count,val_count,test_count
"""
import os
from pathlib import Path

SPLITS_DIR = Path("waste_dataset_v1/splits")
CLASSES = [
    "Battery", "Biological", "Cardboard", "Clothes", "E_Waste",
    "Glass", "Metal", "Paper", "Plastic", "Other"
]

def count_images(folder: Path) -> dict:
    counts = {}
    for cls in CLASSES:
        cls_path = folder / cls
        if cls_path.is_dir():
            counts[cls] = len(list(cls_path.glob("*")))
        else:
            counts[cls] = 0
    return counts

def main():
    train_counts = count_images(SPLITS_DIR / "train")
    val_counts   = count_images(SPLITS_DIR / "val")
    test_counts  = count_images(SPLITS_DIR / "test")

    print("class_name,train_count,val_count,test_count")
    for cls in CLASSES:
        print(f"{cls},{train_counts[cls]},{val_counts[cls]},{test_counts[cls]}")

    total_train = sum(train_counts.values())
    total_val   = sum(val_counts.values())
    total_test  = sum(test_counts.values())
    print(f"\nTotal: train={total_train}, val={total_val}, test={total_test}, all={total_train+total_val+total_test}")

if __name__ == "__main__":
    main()
