import os
import torch
import json
import csv

base_dir = "model/output/outputs_resnet50_continue_10class_mapped"

required_files = [
    "tables/model_metrics.csv",
    "tables/classification_report.csv",
    "tables/bin4_model_metrics.csv",
    "tables/bin4_classification_report.csv",
    "tables/bin4_confusion_matrix.csv",
    "tables/test_predictions.csv",
    "tables/training_history.csv",
    "tables/training_history_continue_only.csv",
    "figures/loss_curve.png",
    "figures/accuracy_f1_curve.png",
    "figures/confusion_matrix.png",
    "figures/confusion_matrix_normalized.png",
    "figures/per_class_f1_score.png",
    "figures/bin4_confusion_matrix.png",
    "logs/test_summary.json",
    "logs/worklog.md",
    "checkpoints/best_checkpoint.pth",
    "checkpoints/last_model.pth"
]

missing_files = []
for f in required_files:
    if not os.path.exists(os.path.join(base_dir, f)):
        missing_files.append(f)

print(f"Missing files: {missing_files}")

checkpoint_path = os.path.join(base_dir, "checkpoints/best_checkpoint.pth")
model_path = os.path.join(base_dir, "checkpoints/best_model.pth")

if os.path.exists(checkpoint_path) and not os.path.exists(model_path):
    print("best_model.pth not found. Attempting to extract from best_checkpoint.pth...")
    try:
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        if 'model_state_dict' in checkpoint:
            torch.save(checkpoint['model_state_dict'], model_path)
            print(f"Successfully created {model_path}")
        else:
            print("No 'model_state_dict' in checkpoint.")
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
elif os.path.exists(model_path):
    print("best_model.pth already exists.")
else:
    print("best_checkpoint.pth not found, cannot create best_model.pth.")

# Extract metrics
metrics = {}
try:
    with open(os.path.join(base_dir, "tables/model_metrics.csv"), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics['test_accuracy'] = row.get('accuracy', row.get('Accuracy'))
            metrics['test_macro_f1'] = row.get('macro_f1', row.get('Macro F1'))
            metrics['test_weighted_f1'] = row.get('weighted_f1', row.get('Weighted F1'))
            break
except Exception as e:
    print(f"Error reading model_metrics: {e}")

try:
    with open(os.path.join(base_dir, "tables/bin4_model_metrics.csv"), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics['bin4_accuracy'] = row.get('accuracy', row.get('Accuracy'))
            metrics['bin4_macro_f1'] = row.get('macro_f1', row.get('Macro F1'))
            break
except Exception as e:
    print(f"Error reading bin4 metrics: {e}")

print("Extracted metrics:", json.dumps(metrics, indent=2))
