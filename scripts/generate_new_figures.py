"""
Generate new class_distribution.png and train_val_test_distribution.png
for waste_dataset_v1 splits.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# ── Data ──────────────────────────────────────────────────────────────────────
CLASSES = [
    "Battery", "Biological", "Cardboard", "Clothes", "E_Waste",
    "Glass", "Metal", "Paper", "Plastic", "Other"
]

DATA = {
    "Battery":   {"train": 3571, "val": 765,  "test": 767},
    "Biological":{"train": 2956, "val": 633,  "test": 635},
    "Cardboard": {"train": 6098, "val": 1306, "test": 1308},
    "Clothes":   {"train": 3726, "val": 798,  "test": 800},
    "E_Waste":   {"train": 3698, "val": 792,  "test": 794},
    "Glass":     {"train": 3565, "val": 764,  "test": 765},
    "Metal":     {"train": 3726, "val": 798,  "test": 799},
    "Paper":     {"train": 3818, "val": 818,  "test": 819},
    "Plastic":   {"train": 3822, "val": 819,  "test": 820},
    "Other":     {"train": 7675, "val": 1644, "test": 1646},
}

# Bin colour mapping
BIN_COLORS = {
    "Battery":  "#e74c3c",   # Hazardous – red
    "E_Waste":  "#e74c3c",
    "Biological": "#2ecc71", # Organic – green
    "Cardboard": "#3498db",  # Recyclable – blue
    "Glass":    "#3498db",
    "Metal":    "#3498db",
    "Paper":    "#3498db",
    "Plastic":  "#3498db",
    "Clothes":  "#95a5a6",  # Other – grey
    "Other":    "#95a5a6",
}

LABEL_COLORS = {
    "Hazardous":  "#e74c3c",
    "Organic":    "#2ecc71",
    "Recyclable": "#3498db",
    "Other":      "#95a5a6",
}

OUT_DIR = Path("reports/figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Figure 1: class_distribution.png ─────────────────────────────────────────
def plot_class_distribution():
    totals = [DATA[c]["train"] + DATA[c]["val"] + DATA[c]["test"] for c in CLASSES]
    colors = [BIN_COLORS[c] for c in CLASSES]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(CLASSES, totals, color=colors, edgecolor="white", linewidth=0.8)

    # Add value labels on top of bars
    for bar, val in zip(bars, totals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 80,
                f"{val:,}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    total_all = sum(totals)
    ax.text(0.98, 0.95, f"Tổng: {total_all:,} ảnh", transform=ax.transAxes,
            ha="right", va="top", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", edgecolor="gray"))

    ax.set_xlabel("Lớp", fontsize=12)
    ax.set_ylabel("Số lượng ảnh", fontsize=12)
    ax.set_title("Phân bố số lượng ảnh theo lớp (Dataset mới)", fontsize=14, fontweight="bold")
    ax.set_ylim(0, max(totals) * 1.12)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
    plt.xticks(rotation=30, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Legend
    legend_patches = [
        mpatches.Patch(color=LABEL_COLORS["Hazardous"],  label="Hazardous (Nguy hại)"),
        mpatches.Patch(color=LABEL_COLORS["Organic"],    label="Organic (Hữu cơ)"),
        mpatches.Patch(color=LABEL_COLORS["Recyclable"], label="Recyclable (Tái chế)"),
        mpatches.Patch(color=LABEL_COLORS["Other"],      label="Other (Khác)"),
    ]
    ax.legend(handles=legend_patches, loc="upper left", fontsize=9)

    plt.tight_layout()
    out = OUT_DIR / "class_distribution.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ── Figure 2: train_val_test_distribution.png ─────────────────────────────────
def plot_split_distribution():
    x = np.arange(len(CLASSES))
    width = 0.25

    train_vals = [DATA[c]["train"] for c in CLASSES]
    val_vals   = [DATA[c]["val"]   for c in CLASSES]
    test_vals  = [DATA[c]["test"]  for c in CLASSES]

    fig, ax = plt.subplots(figsize=(14, 7))

    b_train = ax.bar(x - width, train_vals, width, label="Train", color="#2ecc71", edgecolor="white")
    b_val   = ax.bar(x,         val_vals,   width, label="Validation", color="#f39c12", edgecolor="white")
    b_test  = ax.bar(x + width, test_vals,  width, label="Test", color="#3498db", edgecolor="white")

    # Value labels
    for bars in [b_train, b_val, b_test]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 30,
                    f"{int(h):,}", ha="center", va="bottom", fontsize=7, fontweight="bold")

    # Summary box
    total_train = sum(train_vals)
    total_val   = sum(val_vals)
    total_test  = sum(test_vals)
    summary = (f"Train: {total_train:,}  |  Val: {total_val:,}  |  Test: {total_test:,}\n"
               f"Tổng: {total_train+total_val+total_test:,} ảnh")
    ax.text(0.98, 0.95, summary, transform=ax.transAxes,
            ha="right", va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", edgecolor="gray"))

    ax.set_xlabel("Lớp", fontsize=12)
    ax.set_ylabel("Số lượng ảnh", fontsize=12)
    ax.set_title("Phân bố Train / Validation / Test theo từng lớp (Dataset mới)", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(CLASSES, rotation=30, ha="right")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_ylim(0, max(max(train_vals), max(val_vals), max(test_vals)) * 1.15)
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    out = OUT_DIR / "train_val_test_distribution.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


if __name__ == "__main__":
    plot_class_distribution()
    plot_split_distribution()
    print("Done.")
