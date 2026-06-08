"""
generate_waste_report_assets.py

Generates report figures, tables, and a worklog from real dataset counts.
Reads ONLY from waste_dataset_v1/clean and waste_dataset_v1/splits.
Does NOT modify, move or delete any images.

Output:
  reports/figures/class_distribution.png
  reports/figures/train_val_test_distribution.png
  reports/figures/class_to_bin_mapping.png
  reports/figures/data_pipeline.png
  reports/tables/dataset_summary.csv
  reports/tables/class_distribution.csv
  reports/logs/report_assets_worklog.md
"""

import csv
import sys
import datetime
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyArrowPatch
except ImportError:
    print("[ERROR] matplotlib is not installed. Run: pip install matplotlib")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("[ERROR] pandas is not installed. Run: pip install pandas")
    sys.exit(1)

# ─────────────────────────── constants ───────────────────────────
BASE_DIR = Path("waste_dataset_v1")
CLEAN_DIR = BASE_DIR / "clean"
SPLITS_DIR = BASE_DIR / "splits"

REPORTS_DIR = Path("reports")
FIG_DIR = REPORTS_DIR / "figures"
TABLE_DIR = REPORTS_DIR / "tables"
LOG_DIR = REPORTS_DIR / "logs"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

CLASSES = [
    "Battery", "Biological", "Cardboard", "Clothes", "E_Waste",
    "Glass", "Metal", "Paper", "Plastic", "Other"
]

# class -> bin group mapping
CLASS_TO_BIN = {
    "Battery": "Hazardous",
    "E_Waste": "Hazardous",
    "Biological": "Organic",
    "Cardboard": "Recyclable",
    "Glass": "Recyclable",
    "Metal": "Recyclable",
    "Paper": "Recyclable",
    "Plastic": "Recyclable",
    "Clothes": "Other",
    "Other": "Other",
}

BIN_COLORS = {
    "Hazardous":  "#e74c3c",
    "Organic":    "#27ae60",
    "Recyclable": "#2980b9",
    "Other":      "#8e44ad",
}

# ─────────────────────────── helpers ─────────────────────────────

def count_images(directory: Path) -> int:
    """Count image files (by extension) in a directory (non-recursive)."""
    d = Path(directory)
    if not d.exists():
        return 0
    return sum(1 for f in d.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS)


def ensure_dirs():
    for d in [FIG_DIR, TABLE_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ─────────────────────────── data collection ─────────────────────

def collect_counts():
    """Returns a dict: class_name -> {clean, train, val, test}"""
    data = {}
    warnings = []

    for cls in CLASSES:
        clean = count_images(CLEAN_DIR / cls)
        train = count_images(SPLITS_DIR / "train" / cls)
        val   = count_images(SPLITS_DIR / "val"   / cls)
        test  = count_images(SPLITS_DIR / "test"  / cls)

        data[cls] = {
            "clean": clean,
            "train": train,
            "val":   val,
            "test":  test,
        }

        if clean == 0:
            warnings.append(f"WARNING: Class '{cls}' has 0 images in clean/")
        if train == 0:
            warnings.append(f"WARNING: Class '{cls}' has 0 images in splits/train/")
        if val == 0:
            warnings.append(f"WARNING: Class '{cls}' has 0 images in splits/val/")
        if test == 0:
            warnings.append(f"WARNING: Class '{cls}' has 0 images in splits/test/")

        total_split = train + val + test
        if clean > 0 and total_split > 0 and abs(clean - total_split) > max(5, int(clean * 0.01)):
            warnings.append(
                f"WARNING: Class '{cls}' clean={clean} vs total_split={total_split} — mismatch > 1%"
            )

    return data, warnings


# ─────────────────────────── figure 1: class distribution ────────

def plot_class_distribution(data: dict, out_path: Path):
    classes = CLASSES
    counts = [data[c]["clean"] for c in classes]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(classes))
    bars = ax.bar(x, counts, color="#2980b9", edgecolor="white", linewidth=0.8)

    # label on top of each bar
    for bar, cnt in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.01,
            str(cnt),
            ha="center", va="bottom", fontsize=10, fontweight="bold"
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(classes, rotation=25, ha="right", fontsize=11)
    ax.set_ylabel("Number of Clean Images", fontsize=12)
    ax.set_xlabel("Class", fontsize=12)
    ax.set_title("Clean Image Distribution by Class", fontsize=14, fontweight="bold", pad=15)
    ax.set_ylim(0, max(counts) * 1.15 if max(counts) > 0 else 10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  [OK] {out_path}")


# ─────────────────────────── figure 2: train/val/test distribution

def plot_split_distribution(data: dict, out_path: Path):
    classes = CLASSES
    n = len(classes)
    train_counts = [data[c]["train"] for c in classes]
    val_counts   = [data[c]["val"]   for c in classes]
    test_counts  = [data[c]["test"]  for c in classes]

    x = range(n)
    width = 0.26

    fig, ax = plt.subplots(figsize=(14, 7))

    b1 = ax.bar([i - width for i in x], train_counts, width, label="Train", color="#2980b9", edgecolor="white")
    b2 = ax.bar([i         for i in x], val_counts,   width, label="Val",   color="#f39c12", edgecolor="white")
    b3 = ax.bar([i + width for i in x], test_counts,  width, label="Test",  color="#27ae60", edgecolor="white")

    def label_bars(bars):
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    h + 2,
                    str(int(h)),
                    ha="center", va="bottom", fontsize=7.5
                )

    label_bars(b1)
    label_bars(b2)
    label_bars(b3)

    ax.set_xticks(list(x))
    ax.set_xticklabels(classes, rotation=25, ha="right", fontsize=11)
    ax.set_ylabel("Number of Images", fontsize=12)
    ax.set_xlabel("Class", fontsize=12)
    ax.set_title("Train/Validation/Test Distribution by Class", fontsize=14, fontweight="bold", pad=15)
    ax.legend(fontsize=11)
    ax.yaxis.grid(True, linestyle="--", alpha=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  [OK] {out_path}")


# ─────────────────────────── figure 3: class to bin mapping ──────

def plot_class_to_bin_mapping(out_path: Path):
    """Draw class boxes on the left, bin boxes on the right, arrows between them."""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis("off")
    ax.set_title(
        "Mapping from Waste Classes to Smart Bin Groups",
        fontsize=14, fontweight="bold", pad=12
    )

    # class positions (left column, y from top)
    class_positions = {}
    for i, cls in enumerate(CLASSES):
        y = 10.5 - i * 1.05
        class_positions[cls] = (2.0, y)

    # bin positions (right column)
    bin_names = ["Hazardous", "Organic", "Recyclable", "Other"]
    bin_y = {"Hazardous": 9.5, "Organic": 7.0, "Recyclable": 4.5, "Other": 2.0}

    box_w_cls, box_h_cls = 2.6, 0.72
    box_w_bin, box_h_bin = 2.6, 0.72

    # draw class boxes
    for cls, (cx, cy) in class_positions.items():
        color = BIN_COLORS[CLASS_TO_BIN[cls]]
        rect = mpatches.FancyBboxPatch(
            (cx - box_w_cls / 2, cy - box_h_cls / 2),
            box_w_cls, box_h_cls,
            boxstyle="round,pad=0.08",
            linewidth=1.2, edgecolor=color, facecolor=color + "30"
        )
        ax.add_patch(rect)
        ax.text(cx, cy, cls, ha="center", va="center", fontsize=10, fontweight="bold", color="#333333")

    # draw bin boxes
    for bin_name in bin_names:
        bx, by = 8.0, bin_y[bin_name]
        color = BIN_COLORS[bin_name]
        rect = mpatches.FancyBboxPatch(
            (bx - box_w_bin / 2, by - box_h_bin / 2),
            box_w_bin, box_h_bin,
            boxstyle="round,pad=0.08",
            linewidth=2.0, edgecolor=color, facecolor=color + "55"
        )
        ax.add_patch(rect)
        ax.text(bx, by, bin_name, ha="center", va="center", fontsize=11, fontweight="bold", color=color)

    # draw arrows: class -> bin
    for cls, (cx, cy) in class_positions.items():
        bin_name = CLASS_TO_BIN[cls]
        bx, by = 8.0, bin_y[bin_name]
        color = BIN_COLORS[bin_name]
        ax.annotate(
            "",
            xy=(bx - box_w_bin / 2, by),
            xytext=(cx + box_w_cls / 2, cy),
            arrowprops=dict(
                arrowstyle="->",
                color=color,
                lw=1.2,
                connectionstyle="arc3,rad=0.0"
            )
        )

    # column labels
    ax.text(2.0, 11.35, "Waste Classes", ha="center", va="center",
            fontsize=11, fontweight="bold", color="#555555")
    ax.text(8.0, 11.35, "Bin Groups", ha="center", va="center",
            fontsize=11, fontweight="bold", color="#555555")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  [OK] {out_path}")


# ─────────────────────────── figure 4: data pipeline ─────────────

def plot_data_pipeline(out_path: Path):
    steps = [
        "Download Dataset",
        "Inspect Labels",
        "Map Labels",
        "Remove Corrupt /\nDuplicate Images",
        "Clean Dataset",
        "Train / Val / Test Split",
        "Ready for ResNet Training",
    ]

    colors = [
        "#2980b9", "#8e44ad", "#16a085", "#c0392b",
        "#27ae60", "#f39c12", "#2c3e50"
    ]

    fig, ax = plt.subplots(figsize=(10, 9))
    ax.set_xlim(0, 6)
    ax.set_ylim(-0.5, len(steps) - 0.5)
    ax.axis("off")
    ax.set_title("Waste Dataset Preparation Pipeline", fontsize=14, fontweight="bold", pad=14)

    box_w, box_h = 4.2, 0.72
    cx = 3.0

    y_positions = list(range(len(steps) - 1, -1, -1))  # top to bottom

    for i, (step, color, y) in enumerate(zip(steps, colors, y_positions)):
        rect = mpatches.FancyBboxPatch(
            (cx - box_w / 2, y - box_h / 2),
            box_w, box_h,
            boxstyle="round,pad=0.10",
            linewidth=1.8, edgecolor=color, facecolor=color + "28"
        )
        ax.add_patch(rect)
        ax.text(cx, y, step, ha="center", va="center",
                fontsize=11, fontweight="bold", color="#1a1a1a",
                multialignment="center")

        # arrow to next step
        if i < len(steps) - 1:
            next_y = y_positions[i + 1]
            ax.annotate(
                "",
                xy=(cx, next_y + box_h / 2 + 0.04),
                xytext=(cx, y - box_h / 2 - 0.04),
                arrowprops=dict(arrowstyle="->", color="#555555", lw=1.5)
            )

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  [OK] {out_path}")


# ─────────────────────────── CSV tables ──────────────────────────

def write_dataset_summary_csv(data: dict, out_path: Path):
    rows = []
    for cls in CLASSES:
        d = data[cls]
        rows.append({
            "class_name":        cls,
            "clean_count":       d["clean"],
            "train_count":       d["train"],
            "val_count":         d["val"],
            "test_count":        d["test"],
            "total_split_count": d["train"] + d["val"] + d["test"],
        })
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)
    print(f"  [OK] {out_path}")


def write_class_distribution_csv(data: dict, out_path: Path):
    rows = [{"class_name": cls, "clean_count": data[cls]["clean"]} for cls in CLASSES]
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)
    print(f"  [OK] {out_path}")


# ─────────────────────────── worklog ─────────────────────────────

def write_worklog(data: dict, warnings: list, created_files: list, out_path: Path):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_clean = sum(data[c]["clean"] for c in CLASSES)
    total_train = sum(data[c]["train"] for c in CLASSES)
    total_val   = sum(data[c]["val"]   for c in CLASSES)
    total_test  = sum(data[c]["test"]  for c in CLASSES)

    lines = [
        "# Report Assets Worklog\n",
        f"**Generated at:** {now}\n",
        "\n## Dataset Paths Read\n",
        f"- `{CLEAN_DIR.resolve()}`\n",
        f"- `{(SPLITS_DIR / 'train').resolve()}`\n",
        f"- `{(SPLITS_DIR / 'val').resolve()}`\n",
        f"- `{(SPLITS_DIR / 'test').resolve()}`\n",
        "\n## Classes Found\n",
    ]
    for cls in CLASSES:
        lines.append(f"- {cls}\n")

    lines.append("\n## Image Counts\n")
    lines.append(f"- Total clean:  {total_clean}\n")
    lines.append(f"- Total train:  {total_train}\n")
    lines.append(f"- Total val:    {total_val}\n")
    lines.append(f"- Total test:   {total_test}\n")
    lines.append(f"- Total splits: {total_train + total_val + total_test}\n")

    lines.append("\n### Per-class breakdown\n")
    lines.append("| Class | Clean | Train | Val | Test |\n")
    lines.append("|-------|-------|-------|-----|------|\n")
    for cls in CLASSES:
        d = data[cls]
        lines.append(f"| {cls} | {d['clean']} | {d['train']} | {d['val']} | {d['test']} |\n")

    lines.append("\n## Files Created\n")
    for f in created_files:
        lines.append(f"- `{f}`\n")

    lines.append("\n## Warnings\n")
    if warnings:
        for w in warnings:
            lines.append(f"- {w}\n")
    else:
        lines.append("- None\n")

    lines.append("\n## Next Steps\n")
    lines.append("- Verify figures in `reports/figures/`\n")
    lines.append("- Verify tables in `reports/tables/`\n")
    lines.append("- Create ResNet training pipeline (`scripts/train_resnet.py`)\n")
    lines.append("- Configure hyperparameters, data augmentation, and model checkpointing\n")

    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"  [OK] {out_path}")


# ─────────────────────────── main ────────────────────────────────

def main():
    print("=== generate_waste_report_assets.py ===\n")

    # Verify base dirs exist
    for d, label in [(CLEAN_DIR, "clean"), (SPLITS_DIR, "splits")]:
        if not d.exists():
            print(f"[ERROR] Required directory not found: {d}")
            sys.exit(1)

    ensure_dirs()
    print("[1/7] Collecting image counts ...")
    data, warnings = collect_counts()

    created_files = []

    # ── figures ──────────────────────────────────────
    print("[2/7] Generating class_distribution.png ...")
    out = FIG_DIR / "class_distribution.png"
    plot_class_distribution(data, out)
    created_files.append(str(out))

    print("[3/7] Generating train_val_test_distribution.png ...")
    out = FIG_DIR / "train_val_test_distribution.png"
    plot_split_distribution(data, out)
    created_files.append(str(out))

    print("[4/7] Generating class_to_bin_mapping.png ...")
    out = FIG_DIR / "class_to_bin_mapping.png"
    plot_class_to_bin_mapping(out)
    created_files.append(str(out))

    print("[5/7] Generating data_pipeline.png ...")
    out = FIG_DIR / "data_pipeline.png"
    plot_data_pipeline(out)
    created_files.append(str(out))

    # ── tables ────────────────────────────────────────
    print("[6/7] Writing CSV tables ...")
    out = TABLE_DIR / "dataset_summary.csv"
    write_dataset_summary_csv(data, out)
    created_files.append(str(out))

    out = TABLE_DIR / "class_distribution.csv"
    write_class_distribution_csv(data, out)
    created_files.append(str(out))

    # ── worklog ───────────────────────────────────────
    print("[7/7] Writing worklog ...")
    out = LOG_DIR / "report_assets_worklog.md"
    write_worklog(data, warnings, created_files, out)
    created_files.append(str(out))

    # ── verification ──────────────────────────────────
    print("\n=== VERIFICATION ===")
    required = [
        FIG_DIR / "class_distribution.png",
        FIG_DIR / "train_val_test_distribution.png",
        FIG_DIR / "class_to_bin_mapping.png",
        FIG_DIR / "data_pipeline.png",
        TABLE_DIR / "dataset_summary.csv",
        TABLE_DIR / "class_distribution.csv",
        LOG_DIR / "report_assets_worklog.md",
    ]
    all_ok = True
    for f in required:
        if f.exists():
            print(f"  [FOUND] {f}")
        else:
            print(f"  [MISSING] {f}")
            all_ok = False

    if not all_ok:
        print("\n[ERROR] Some output files are missing — check errors above.")
        sys.exit(1)

    # ── summary report ────────────────────────────────
    total_clean = sum(data[c]["clean"] for c in CLASSES)
    total_train = sum(data[c]["train"] for c in CLASSES)
    total_val   = sum(data[c]["val"]   for c in CLASSES)
    total_test  = sum(data[c]["test"]  for c in CLASSES)

    print("\n=== A. Files Created ===")
    for f in created_files:
        print(f"  {f}")

    print("\n=== B. Dataset Statistics ===")
    print(f"  Total clean : {total_clean}")
    print(f"  Total train : {total_train}")
    print(f"  Total val   : {total_val}")
    print(f"  Total test  : {total_test}")
    print("  Per-class:")
    for cls in CLASSES:
        d = data[cls]
        print(f"    {cls:12s}: clean={d['clean']}  train={d['train']}  val={d['val']}  test={d['test']}")

    print("\n=== C. Warnings ===")
    if warnings:
        for w in warnings:
            print(f"  {w}")
    else:
        print("  None")

    print("\n=== D. Next Command ===")
    print("  python scripts/train_resnet.py")
    print("  (Create ResNet training pipeline as next step)")
    print("\n[DONE]")


if __name__ == "__main__":
    main()