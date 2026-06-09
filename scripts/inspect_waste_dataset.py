import os
import csv
from pathlib import Path

def list_structure(directory, max_depth=3):
    print(f"\nStructure of {directory}:")
    path = Path(directory)
    if not path.exists():
        print("Directory does not exist.")
        return

    prefix = "  "
    for p in path.rglob('*'):
        depth = len(p.relative_to(path).parts)
        if depth <= max_depth:
            indent = prefix * (depth - 1)
            if p.is_dir():
                print(f"{indent}+-- {p.name}/")
            elif depth == 1: # Only print files at top level to avoid clutter
                 print(f"{indent}+-- {p.name}")

def generate_source_manifest(downloads_dir, output_file):
    print(f"\nGenerating source manifest: {output_file}")
    downloads_path = Path(downloads_dir)
    fieldnames = ['source_dataset', 'original_label', 'filepath', 'filename', 'extension', 'file_size_bytes']
    
    os.makedirs(Path(output_file).parent, exist_ok=True)
    
    extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for ds_dir in downloads_path.iterdir():
            if ds_dir.is_dir():
                source_name = ds_dir.name
                print(f"Processing dataset: {source_name}")
                
                # Assume images are in subdirectories which are labels
                for p in ds_dir.rglob('*'):
                    if p.is_file() and p.suffix.lower() in extensions:
                        # Find original label (immediate parent folder name)
                        original_label = p.parent.name
                        
                        writer.writerow({
                            'source_dataset': source_name,
                            'original_label': original_label,
                            'filepath': str(p),
                            'filename': p.name,
                            'extension': p.suffix.lower(),
                            'file_size_bytes': p.stat().st_size
                        })

def main():
    downloads_dir = "waste_dataset_v1/downloads"
    output_file = "waste_dataset_v1/metadata/source_manifest.csv"
    
    if not os.path.exists(downloads_dir):
        print(f"Error: {downloads_dir} not found. Run download script first.")
        return

    for ds in os.listdir(downloads_dir):
        ds_path = os.path.join(downloads_dir, ds)
        if os.path.isdir(ds_path):
            list_structure(ds_path)
            
    generate_source_manifest(downloads_dir, output_file)
    print("\nInspection complete.")

if __name__ == "__main__":
    main()