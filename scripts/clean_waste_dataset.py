import os
import csv
import shutil
import hashlib
import argparse
from pathlib import Path
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

def generate_hash(filepath, chunk_size=8192):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""

def is_valid_image(filepath):
    try:
        with Image.open(filepath) as img:
            img.verify()
        return True
    except Exception:
        return False

def process_image_worker(task):
    source_path_str, dest_path_str, class_name, file_hash = task
    try:
        # We open and save the image
        with Image.open(source_path_str) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(dest_path_str, 'JPEG', quality=95)
            width, height = img.size
            return {
                'class_name': class_name,
                'clean_path': dest_path_str,
                'width': width,
                'height': height,
                'source_path': source_path_str,
                'md5': file_hash,
                'status': 'clean'
            }
    except Exception as e:
        return {
            'class_name': class_name,
            'clean_path': '',
            'width': '',
            'height': '',
            'source_path': source_path_str,
            'md5': file_hash,
            'status': 'corrupt_processing'
        }

def main():
    parser = argparse.ArgumentParser(description="Clean waste dataset in parallel.")
    parser.add_argument("--limit-per-class", type=int, default=None, help="Limit number of images per class for testing.")
    args = parser.parse_args()

    raw_mapped_dir = Path("waste_dataset_v1/raw_mapped")
    clean_dir = Path("waste_dataset_v1/clean")
    rejected_corrupt_dir = Path("waste_dataset_v1/rejected/corrupt")
    rejected_duplicate_dir = Path("waste_dataset_v1/rejected/duplicate")
    clean_manifest_path = "waste_dataset_v1/metadata/clean_manifest.csv"
    
    if not raw_mapped_dir.exists():
        print(f"Error: {raw_mapped_dir} not found. Run map script first.")
        return

    # Create directories
    os.makedirs(clean_dir, exist_ok=True)
    os.makedirs(rejected_corrupt_dir, exist_ok=True)
    os.makedirs(rejected_duplicate_dir, exist_ok=True)

    seen_hashes = set()
    tasks = []
    corrupt_records = []
    duplicate_records = []
    
    print("Scanning and verifying images sequentially...")
    
    for class_dir in raw_mapped_dir.iterdir():
        if not class_dir.is_dir():
            continue
            
        class_name = class_dir.name
        os.makedirs(clean_dir / class_name, exist_ok=True)
        
        class_files = list(class_dir.iterdir())
        class_files_count = 0
        
        for p in class_files:
            if not p.is_file():
                continue
                
            if args.limit_per_class and class_files_count >= args.limit_per_class:
                break
                
            if not is_valid_image(p):
                corrupt_records.append({
                    'class_name': class_name,
                    'clean_path': '',
                    'width': '',
                    'height': '',
                    'source_path': str(p),
                    'md5': '',
                    'status': 'corrupt'
                })
                continue
                
            file_hash = generate_hash(p)
            if not file_hash:
                corrupt_records.append({
                    'class_name': class_name,
                    'clean_path': '',
                    'width': '',
                    'height': '',
                    'source_path': str(p),
                    'md5': '',
                    'status': 'corrupt'
                })
                continue
                
            if file_hash in seen_hashes:
                duplicate_records.append({
                    'class_name': class_name,
                    'clean_path': '',
                    'width': '',
                    'height': '',
                    'source_path': str(p),
                    'md5': file_hash,
                    'status': 'duplicate'
                })
                continue
                
            seen_hashes.add(file_hash)
            class_files_count += 1
            
            dest_path = clean_dir / class_name / f"{p.stem}.jpg"
            tasks.append((str(p), str(dest_path), class_name, file_hash))
            
    print(f"Scan complete.")
    print(f"  Valid unique tasks to process: {len(tasks)}")
    print(f"  Corrupt files found: {len(corrupt_records)}")
    print(f"  Duplicate files found: {len(duplicate_records)}")
    
    results = []
    total_tasks = len(tasks)
    
    if total_tasks > 0:
        workers = min(os.cpu_count() or 4, 16)
        print(f"Processing images using ProcessPoolExecutor with {workers} workers...")
        
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_image_worker, task): task for task in tasks}
            
            completed = 0
            for future in as_completed(futures):
                res = future.result()
                results.append(res)
                completed += 1
                if completed % 1000 == 0 or completed == total_tasks:
                    print(f"Processed {completed}/{total_tasks} clean images...")

    print("Writing manifests and moving rejected files...")
    
    class_counts = {cls: 0 for cls in class_counts_summary(raw_mapped_dir)}
    
    with open(clean_manifest_path, 'w', newline='', encoding='utf-8') as outfile:
        fieldnames = ['class_name', 'clean_path', 'width', 'height', 'source_path', 'md5', 'status']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write clean and processed corrupt
        for res in results:
            if res['status'] == 'clean':
                class_counts[res['class_name']] = class_counts.get(res['class_name'], 0) + 1
            elif res['status'] == 'corrupt_processing':
                # Move to rejected corrupt
                p = Path(res['source_path'])
                shutil.copy2(p, rejected_corrupt_dir / p.name)
            writer.writerow(res)
            
        # Write and copy corrupt
        for rec in corrupt_records:
            p = Path(rec['source_path'])
            try:
                shutil.copy2(p, rejected_corrupt_dir / p.name)
            except Exception as e:
                print(f"Error copying corrupt file {p}: {e}")
            writer.writerow(rec)
            
        # Write and copy duplicates
        for rec in duplicate_records:
            p = Path(rec['source_path'])
            try:
                shutil.copy2(p, rejected_duplicate_dir / p.name)
            except Exception as e:
                print(f"Error copying duplicate file {p}: {e}")
            writer.writerow(rec)

    print("\nCleaning complete. Summary of clean images:")
    for cls in sorted(class_counts.keys()):
        print(f"  {cls}: {class_counts[cls]}")

def class_counts_summary(raw_mapped_dir):
    classes = []
    for d in raw_mapped_dir.iterdir():
        if d.is_dir():
            classes.append(d.name)
    return classes

if __name__ == "__main__":
    main()