"""
Evaluate Waste Classification ResNet50 checkpoint on the test split.

This script loads an existing checkpoint and evaluates it locally.
It does NOT train or fine-tune the model.

Default paths are intentionally placed near the top for easy editing.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

DATA_ROOT = "waste_dataset_v1/splits"
BEST_MODEL_PATH = "model/output/outputs_waste_resnet50_v2/checkpoints/best_model.pth"
HISTORY_PATH = "model/output/training_history.csv"
OUTPUT_DIR = "model/output/outputs_waste_resnet50_eval"

EXPECTED_CLASSES = [
    "Battery",
    "Biological",
    "Cardboard",
    "Clothes",
    "E_Waste",
    "Glass",
    "Metal",
    "Other",
    "Paper",
    "Plastic",
]

plt = None
np = None
pd = None
torch = None
nn = None
Image = None
classification_report = None
confusion_matrix = None
f1_score = None
DataLoader = None
datasets = None
models = None
transforms = None
DEVICE = None


def import_runtime_dependencies() -> None:
    """Import heavy ML dependencies after argparse handles --help."""
    global plt, np, pd, torch, nn, Image
    global classification_report, confusion_matrix, f1_score
    global DataLoader, datasets, models, transforms, DEVICE

    try:
        import matplotlib.pyplot as _plt
        import numpy as _np
        import pandas as _pd
        import torch as _torch
        import torch.nn as _nn
        from PIL import Image as _Image
        from sklearn.metrics import classification_report as _classification_report
        from sklearn.metrics import confusion_matrix as _confusion_matrix
        from sklearn.metrics import f1_score as _f1_score
        from torch.utils.data import DataLoader as _DataLoader
        from torchvision import datasets as _datasets
        from torchvision import models as _models
        from torchvision import transforms as _transforms
    except ModuleNotFoundError as exc:
        missing = exc.name or str(exc)
        raise ModuleNotFoundError(
            f"Missing required Python package: {missing}\n"
            "Install the evaluation dependencies in the active environment before running evaluation.\n"
            "Common packages required: torch, torchvision, numpy, pandas, matplotlib, pillow, scikit-learn."
        ) from exc

    plt = _plt
    np = _np
    pd = _pd
    torch = _torch
    nn = _nn
    Image = _Image
    classification_report = _classification_report
    confusion_matrix = _confusion_matrix
    f1_score = _f1_score
    DataLoader = _DataLoader
    datasets = _datasets
    models = _models
    transforms = _transforms
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a Waste Classification ResNet50 checkpoint on DATA_ROOT/test. "
            "No training is performed."
        )
    )
    parser.add_argument("--data-root", default=DATA_ROOT, help="Dataset root containing train/val/test folders.")
    parser.add_argument("--checkpoint", default=BEST_MODEL_PATH, help="Path to best_model.pth checkpoint.")
    parser.add_argument("--history", default=HISTORY_PATH, help="Path to training_history.csv.")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Directory where evaluation outputs are written.")
    parser.add_argument("--batch-size", type=int, default=64, help="Evaluation batch size.")
    parser.add_argument("--num-workers", type=int, default=2, help="DataLoader worker count.")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def append_worklog(worklog_path: Path, message: str) -> None:
    with worklog_path.open("a", encoding="utf-8") as f:
        f.write(message.rstrip() + "\n")


def validate_paths(data_root: Path, checkpoint_path: Path) -> None:
    if not data_root.exists():
        raise FileNotFoundError(
            f"DATA_ROOT does not exist: {data_root}\n"
            f"Expected dataset structure: {data_root}/train, {data_root}/val, {data_root}/test"
        )
    if not data_root.is_dir():
        raise NotADirectoryError(f"DATA_ROOT is not a directory: {data_root}")

    for split in ["train", "val", "test"]:
        split_dir = data_root / split
        if not split_dir.exists():
            raise FileNotFoundError(f"Missing required dataset split folder: {split_dir}")
        if not split_dir.is_dir():
            raise NotADirectoryError(f"Dataset split path is not a directory: {split_dir}")
        for class_name in EXPECTED_CLASSES:
            class_dir = split_dir / class_name
            if not class_dir.exists():
                raise FileNotFoundError(f"Missing required class folder: {class_dir}")
            if not class_dir.is_dir():
                raise NotADirectoryError(f"Class path is not a directory: {class_dir}")

    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"Checkpoint does not exist: {checkpoint_path}\n"
            f"Place best_model.pth at: {BEST_MODEL_PATH} or pass --checkpoint PATH"
        )
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Checkpoint path is not a file: {checkpoint_path}")


def get_test_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )


def get_preview_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
        ]
    )


def validate_imagefolder_classes(dataset: datasets.ImageFolder, split_name: str) -> None:
    if dataset.classes != EXPECTED_CLASSES:
        raise AssertionError(
            f"{split_name} class order mismatch.\n"
            f"Expected: {EXPECTED_CLASSES}\n"
            f"Found:    {dataset.classes}\n"
            "ImageFolder orders classes alphabetically; check folder names exactly."
        )


def build_resnet50(head_type: str) -> nn.Module:
    model = models.resnet50(weights=None)
    in_features = model.fc.in_features

    if head_type == "dropout":
        model.fc = nn.Sequential(
            nn.Dropout(p=0.4),
            nn.Linear(in_features, len(EXPECTED_CLASSES)),
        )
    elif head_type == "linear":
        model.fc = nn.Linear(in_features, len(EXPECTED_CLASSES))
    else:
        raise ValueError(f"Unsupported head_type: {head_type}")

    return model


def strip_module_prefix(state_dict: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    if any(key.startswith("module.") for key in state_dict.keys()):
        return {key.replace("module.", "", 1): value for key, value in state_dict.items()}
    return state_dict


def extract_state_dict(checkpoint: Any) -> Dict[str, torch.Tensor]:
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
    else:
        state_dict = checkpoint

    if not isinstance(state_dict, dict):
        raise TypeError("Checkpoint is not a state_dict and does not contain key 'model_state_dict'.")

    return strip_module_prefix(state_dict)


def extract_checkpoint_metadata(checkpoint: Any) -> Tuple[Optional[Any], Optional[Any], Optional[Any]]:
    if not isinstance(checkpoint, dict):
        return None, None, None

    checkpoint_epoch = checkpoint.get("epoch")
    checkpoint_metric = None
    for key in ["metric", "val_metric", "val_acc", "val_macro_f1", "score"]:
        if key in checkpoint:
            checkpoint_metric = checkpoint.get(key)
            break

    best_metric = checkpoint.get("best_metric")
    return checkpoint_epoch, checkpoint_metric, best_metric


def load_model_from_checkpoint(checkpoint_path: Path) -> Tuple[nn.Module, Dict[str, Any]]:
    checkpoint = torch.load(checkpoint_path, map_location=DEVICE)
    state_dict = extract_state_dict(checkpoint)

    checkpoint_epoch, checkpoint_metric, best_metric = extract_checkpoint_metadata(checkpoint)

    load_errors: List[str] = []
    for head_type in ["dropout", "linear"]:
        model = build_resnet50(head_type)
        try:
            model.load_state_dict(state_dict, strict=True)
            model.to(DEVICE)
            model.eval()
            metadata = {
                "checkpoint_epoch": checkpoint_epoch,
                "checkpoint_metric": checkpoint_metric,
                "best_metric": best_metric,
                "loaded_head": head_type,
            }
            print(f"checkpoint epoch: {checkpoint_epoch}")
            print(f"checkpoint metric: {checkpoint_metric}")
            print(f"best_metric: {best_metric}")
            print(f"loaded classifier head: {head_type}")
            return model, metadata
        except RuntimeError as exc:
            load_errors.append(f"{head_type}: {exc}")

    raise RuntimeError(
        "Failed to load checkpoint with both classifier heads.\n\n"
        + "\n\n".join(load_errors)
    )


def make_weighted_criterion(train_dataset: datasets.ImageFolder) -> nn.CrossEntropyLoss:
    train_counts = np.bincount(train_dataset.targets, minlength=len(EXPECTED_CLASSES))
    class_weights = train_counts.sum() / (len(EXPECTED_CLASSES) * np.maximum(train_counts, 1))
    class_weights_tensor = torch.tensor(class_weights, dtype=torch.float32, device=DEVICE)
    return nn.CrossEntropyLoss(weight=class_weights_tensor, label_smoothing=0.1)


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    dataset: datasets.ImageFolder,
) -> Dict[str, Any]:
    all_true: List[int] = []
    all_pred: List[int] = []
    all_conf: List[float] = []
    all_paths: List[str] = []
    total_loss = 0.0
    total_samples = 0

    offset = 0
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(DEVICE, non_blocking=True)
            labels = labels.to(DEVICE, non_blocking=True)

            logits = model(images)
            loss = criterion(logits, labels)
            probs = torch.softmax(logits, dim=1)
            confs, preds = torch.max(probs, dim=1)

            batch_size = labels.size(0)
            total_loss += float(loss.item()) * batch_size
            total_samples += batch_size

            all_true.extend(labels.cpu().numpy().tolist())
            all_pred.extend(preds.cpu().numpy().tolist())
            all_conf.extend(confs.cpu().numpy().tolist())

            for idx in range(offset, offset + batch_size):
                all_paths.append(dataset.samples[idx][0])
            offset += batch_size

    y_true = np.array(all_true, dtype=int)
    y_pred = np.array(all_pred, dtype=int)
    confidences = np.array(all_conf, dtype=float)

    test_loss = total_loss / max(total_samples, 1)
    test_acc = float((y_true == y_pred).mean()) if total_samples else 0.0
    test_macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    test_weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    return {
        "test_loss": test_loss,
        "test_acc": test_acc,
        "test_macro_f1": test_macro_f1,
        "test_weighted_f1": test_weighted_f1,
        "num_test_samples": total_samples,
        "y_true": y_true,
        "y_pred": y_pred,
        "confidences": confidences,
        "paths": all_paths,
    }


def save_training_curves(history_path: Path, tables_dir: Path, figures_dir: Path, worklog_path: Path) -> List[str]:
    created: List[str] = []
    if not history_path.exists():
        warning = f"WARNING: HISTORY_PATH does not exist, skipping training curves: {history_path}"
        print(warning)
        append_worklog(worklog_path, warning)
        return created

    shutil.copy2(history_path, tables_dir / "training_history.csv")
    created.append(str(tables_dir / "training_history.csv"))

    history = pd.read_csv(history_path)

    if {"train_loss", "val_loss"}.issubset(history.columns):
        plt.figure(figsize=(8, 5))
        plt.plot(history["train_loss"], label="train_loss")
        plt.plot(history["val_loss"], label="val_loss")
        plt.xlabel("Epoch")
        plt.ylabel("Loss")
        plt.title("Training and Validation Loss")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        out_path = figures_dir / "loss_curve.png"
        plt.savefig(out_path, dpi=200)
        plt.close()
        created.append(str(out_path))
    else:
        append_worklog(worklog_path, "WARNING: train_loss/val_loss columns not found; skipped loss_curve.png.")

    acc_cols = [col for col in ["train_acc", "val_acc", "train_macro_f1", "val_macro_f1"] if col in history.columns]
    if acc_cols:
        plt.figure(figsize=(8, 5))
        for col in acc_cols:
            plt.plot(history[col], label=col)
        plt.xlabel("Epoch")
        plt.ylabel("Score")
        plt.title("Training and Validation Accuracy/F1")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        out_path = figures_dir / "accuracy_curve.png"
        plt.savefig(out_path, dpi=200)
        plt.close()
        created.append(str(out_path))
    else:
        append_worklog(worklog_path, "WARNING: accuracy/F1 columns not found; skipped accuracy_curve.png.")

    return created


def save_classification_outputs(
    eval_result: Dict[str, Any],
    tables_dir: Path,
    figures_dir: Path,
) -> List[str]:
    created: List[str] = []
    y_true = eval_result["y_true"]
    y_pred = eval_result["y_pred"]
    confidences = eval_result["confidences"]
    paths = eval_result["paths"]

    report_dict = classification_report(
        y_true,
        y_pred,
        target_names=EXPECTED_CLASSES,
        output_dict=True,
        zero_division=0,
    )
    report_df = pd.DataFrame(report_dict).transpose()
    report_path = tables_dir / "classification_report.csv"
    report_df.to_csv(report_path, index=True)
    created.append(str(report_path))

    predictions_path = tables_dir / "test_predictions.csv"
    with predictions_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_path", "true_label", "pred_label", "confidence", "correct"])
        for image_path, true_idx, pred_idx, conf in zip(paths, y_true, y_pred, confidences):
            writer.writerow(
                [
                    image_path,
                    EXPECTED_CLASSES[int(true_idx)],
                    EXPECTED_CLASSES[int(pred_idx)],
                    float(conf),
                    bool(int(true_idx) == int(pred_idx)),
                ]
            )
    created.append(str(predictions_path))

    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(EXPECTED_CLASSES))))
    save_confusion_matrix(cm, figures_dir / "confusion_matrix.png", normalized=False)
    created.append(str(figures_dir / "confusion_matrix.png"))

    with np.errstate(divide="ignore", invalid="ignore"):
        cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
        cm_norm = np.nan_to_num(cm_norm)
    save_confusion_matrix(cm_norm, figures_dir / "confusion_matrix_normalized.png", normalized=True)
    created.append(str(figures_dir / "confusion_matrix_normalized.png"))

    per_class_f1 = f1_score(y_true, y_pred, average=None, labels=list(range(len(EXPECTED_CLASSES))), zero_division=0)
    save_per_class_f1(per_class_f1, figures_dir / "per_class_f1_score.png")
    created.append(str(figures_dir / "per_class_f1_score.png"))

    return created


def save_confusion_matrix(matrix: np.ndarray, out_path: Path, normalized: bool) -> None:
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(matrix, interpolation="nearest", cmap="Blues")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set(
        xticks=np.arange(len(EXPECTED_CLASSES)),
        yticks=np.arange(len(EXPECTED_CLASSES)),
        xticklabels=EXPECTED_CLASSES,
        yticklabels=EXPECTED_CLASSES,
        ylabel="True label",
        xlabel="Predicted label",
        title="Normalized Confusion Matrix" if normalized else "Confusion Matrix",
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    fmt = ".2f" if normalized else "d"
    threshold = matrix.max() / 2.0 if matrix.size else 0
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            ax.text(
                j,
                i,
                format(value, fmt),
                ha="center",
                va="center",
                color="white" if value > threshold else "black",
                fontsize=8,
            )

    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def save_per_class_f1(per_class_f1: np.ndarray, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(EXPECTED_CLASSES, per_class_f1, color="#4C78A8")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("F1-score")
    ax.set_title("Per-class F1-score")
    ax.grid(True, axis="y", alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    for bar, value in zip(bars, per_class_f1):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            min(value + 0.02, 0.98),
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def save_prediction_examples(
    eval_result: Dict[str, Any],
    figures_dir: Path,
    worklog_path: Path,
) -> List[str]:
    created: List[str] = []
    y_true = eval_result["y_true"]
    y_pred = eval_result["y_pred"]
    confidences = eval_result["confidences"]
    paths = eval_result["paths"]

    correct_indices = [idx for idx, (t, p) in enumerate(zip(y_true, y_pred)) if int(t) == int(p)][:9]
    wrong_indices = [idx for idx, (t, p) in enumerate(zip(y_true, y_pred)) if int(t) != int(p)][:9]

    correct_path = figures_dir / "prediction_examples_correct.png"
    wrong_path = figures_dir / "prediction_examples_wrong.png"

    if correct_indices:
        save_examples_grid(correct_indices, paths, y_true, y_pred, confidences, correct_path, "Correct Predictions")
        created.append(str(correct_path))
    else:
        append_worklog(worklog_path, "WARNING: No correct predictions found; prediction_examples_correct.png not created.")
        print("WARNING: No correct predictions found; prediction_examples_correct.png not created.")

    if wrong_indices:
        save_examples_grid(wrong_indices, paths, y_true, y_pred, confidences, wrong_path, "Wrong Predictions")
        created.append(str(wrong_path))
    else:
        append_worklog(worklog_path, "WARNING: No wrong predictions found; prediction_examples_wrong.png not created.")
        print("WARNING: No wrong predictions found; prediction_examples_wrong.png not created.")

    return created


def save_examples_grid(
    indices: Sequence[int],
    paths: Sequence[str],
    y_true: np.ndarray,
    y_pred: np.ndarray,
    confidences: np.ndarray,
    out_path: Path,
    title: str,
) -> None:
    n = len(indices)
    cols = 3
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
    axes_array = np.array(axes).reshape(-1)

    preview_transform = get_preview_transform()

    for ax_idx, sample_idx in enumerate(indices):
        ax = axes_array[ax_idx]
        image = Image.open(paths[sample_idx]).convert("RGB")
        image = preview_transform(image)
        ax.imshow(image)
        ax.axis("off")
        ax.set_title(
            f"True: {EXPECTED_CLASSES[int(y_true[sample_idx])]}\n"
            f"Pred: {EXPECTED_CLASSES[int(y_pred[sample_idx])]}\n"
            f"Conf: {float(confidences[sample_idx]):.3f}",
            fontsize=10,
        )

    for ax in axes_array[n:]:
        ax.axis("off")

    fig.suptitle(title, fontsize=14)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def save_metrics_and_summary(
    eval_result: Dict[str, Any],
    metadata: Dict[str, Any],
    checkpoint_path: Path,
    output_dir: Path,
    tables_dir: Path,
    logs_dir: Path,
    created_files: List[str],
) -> List[str]:
    created: List[str] = []
    created_at = now_iso()

    metrics = {
        "model_name": "resnet50",
        "weights": "None",
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_epoch": metadata.get("checkpoint_epoch"),
        "checkpoint_metric": metadata.get("checkpoint_metric"),
        "test_loss": eval_result["test_loss"],
        "test_acc": eval_result["test_acc"],
        "test_macro_f1": eval_result["test_macro_f1"],
        "test_weighted_f1": eval_result["test_weighted_f1"],
        "num_test_samples": eval_result["num_test_samples"],
        "created_at": created_at,
    }

    metrics_path = tables_dir / "model_metrics.csv"
    pd.DataFrame([metrics]).to_csv(metrics_path, index=False)
    created.append(str(metrics_path))

    summary = {
        **metrics,
        "best_metric": metadata.get("best_metric"),
        "loaded_head": metadata.get("loaded_head"),
        "device": str(DEVICE),
        "output_dir": str(output_dir),
        "created_files": created_files + created,
    }

    summary_path = logs_dir / "test_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    created.append(str(summary_path))

    return created


def initialize_worklog(worklog_path: Path, args: argparse.Namespace) -> None:
    content = [
        "# Waste Classification Checkpoint Evaluation Worklog",
        "",
        f"- Created at: {now_iso()}",
        f"- Device: {DEVICE}",
        f"- Data root: {args.data_root}",
        f"- Checkpoint: {args.checkpoint}",
        f"- History: {args.history}",
        f"- Output dir: {args.output_dir}",
        "",
        "## Notes",
        "- No training was performed.",
        "- Model architecture: torchvision.models.resnet50(weights=None).",
        "- Primary classifier head: Dropout(p=0.4) + Linear(in_features, 10).",
        "- Fallback classifier head: Linear(in_features, 10).",
        "",
    ]
    worklog_path.write_text("\n".join(content), encoding="utf-8")


def main() -> int:
    args = parse_args()

    try:
        import_runtime_dependencies()
    except ModuleNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    data_root = Path(args.data_root)
    checkpoint_path = Path(args.checkpoint)
    history_path = Path(args.history)
    output_dir = Path(args.output_dir)
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    logs_dir = output_dir / "logs"
    checkpoints_dir = output_dir / "checkpoints"

    for directory in [figures_dir, tables_dir, logs_dir, checkpoints_dir]:
        ensure_dir(directory)

    worklog_path = logs_dir / "eval_worklog.md"
    initialize_worklog(worklog_path, args)
    created_files: List[str] = [str(worklog_path)]

    try:
        validate_paths(data_root, checkpoint_path)

        test_transform = get_test_transform()
        train_dataset = datasets.ImageFolder(data_root / "train", transform=test_transform)
        val_dataset = datasets.ImageFolder(data_root / "val", transform=test_transform)
        test_dataset = datasets.ImageFolder(data_root / "test", transform=test_transform)

        validate_imagefolder_classes(train_dataset, "train")
        validate_imagefolder_classes(val_dataset, "val")
        validate_imagefolder_classes(test_dataset, "test")

        append_worklog(worklog_path, f"- Train samples: {len(train_dataset)}")
        append_worklog(worklog_path, f"- Val samples: {len(val_dataset)}")
        append_worklog(worklog_path, f"- Test samples: {len(test_dataset)}")

        if len(test_dataset) == 0:
            raise ValueError(f"Test dataset has zero images: {data_root / 'test'}")

        created_files.extend(save_training_curves(history_path, tables_dir, figures_dir, worklog_path))

        model, metadata = load_model_from_checkpoint(checkpoint_path)
        append_worklog(worklog_path, f"- Checkpoint epoch: {metadata.get('checkpoint_epoch')}")
        append_worklog(worklog_path, f"- Checkpoint metric: {metadata.get('checkpoint_metric')}")
        append_worklog(worklog_path, f"- Best metric: {metadata.get('best_metric')}")
        append_worklog(worklog_path, f"- Loaded classifier head: {metadata.get('loaded_head')}")

        criterion = make_weighted_criterion(train_dataset)
        test_loader = DataLoader(
            test_dataset,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.num_workers,
            pin_memory=torch.cuda.is_available(),
        )

        eval_result = evaluate(model, test_loader, criterion, test_dataset)

        created_files.extend(save_classification_outputs(eval_result, tables_dir, figures_dir))
        created_files.extend(save_prediction_examples(eval_result, figures_dir, worklog_path))
        created_files.extend(
            save_metrics_and_summary(
                eval_result,
                metadata,
                checkpoint_path,
                output_dir,
                tables_dir,
                logs_dir,
                created_files,
            )
        )

        append_worklog(worklog_path, "")
        append_worklog(worklog_path, "## Final Metrics")
        append_worklog(worklog_path, f"- test_loss: {eval_result['test_loss']:.6f}")
        append_worklog(worklog_path, f"- test_acc: {eval_result['test_acc']:.6f}")
        append_worklog(worklog_path, f"- test_macro_f1: {eval_result['test_macro_f1']:.6f}")
        append_worklog(worklog_path, f"- test_weighted_f1: {eval_result['test_weighted_f1']:.6f}")

        print("\nEvaluation complete.")
        print(f"test_acc: {eval_result['test_acc']:.6f}")
        print(f"test_macro_f1: {eval_result['test_macro_f1']:.6f}")
        print(f"test_weighted_f1: {eval_result['test_weighted_f1']:.6f}")
        print(f"OUTPUT_DIR: {output_dir}")
        print("Created files:")
        for file_path in created_files:
            print(f"- {file_path}")

        return 0

    except Exception as exc:
        error_message = f"ERROR: {exc}"
        append_worklog(worklog_path, error_message)
        print(error_message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())