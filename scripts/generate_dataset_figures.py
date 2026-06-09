"""
Script tạo 2 hình mới cho báo cáo:
1. class_distribution.png - phân bố tổng 60.945 ảnh theo 10 lớp
2. train_val_test_distribution.png - phân bố train/val/test theo từng class
"""

import matplotlib.pyplot as plt
import numpy as np

# Dữ liệu từ class_distribution_by_split.csv
classes = ['Battery', 'Biological', 'Cardboard', 'Clothes', 'E_Waste',
           'Glass', 'Metal', 'Other', 'Paper', 'Plastic']

train_counts = [3571, 2956, 6098, 3726, 3698, 3565, 3726, 7675, 3818, 3822]
val_counts = [765, 633, 1306, 798, 792, 764, 798, 1644, 818, 819]
test_counts = [767, 635, 1308, 800, 794, 765, 799, 1646, 819, 820]

# Màu sắc cho từng lớp
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
           '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']

# ============= HÌNH 1: class_distribution.png =============
fig1, ax1 = plt.subplots(figsize=(12, 7))

total_counts = [t + v + te for t, v, te in zip(train_counts, val_counts, test_counts)]
bars1 = ax1.bar(classes, total_counts, color=colors, edgecolor='white', linewidth=1.5)

# Thêm số liệu trên mỗi cột
for bar, count in zip(bars1, total_counts):
    height = bar.get_height()
    ax1.annotate(f'{count:,}',
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 5),
                textcoords="offset points",
                ha='center', va='bottom',
                fontsize=11, fontweight='bold')

ax1.set_xlabel('Lớp (Class)', fontsize=13, fontweight='bold')
ax1.set_ylabel('Số lượng ảnh', fontsize=13, fontweight='bold')
ax1.set_title('Phân bố tổng số ảnh theo 10 lớp\n(Tổng: 60,945 ảnh)',
              fontsize=15, fontweight='bold', pad=20)
ax1.set_ylim(0, max(total_counts) * 1.15)
ax1.tick_params(axis='x', rotation=30)
ax1.grid(axis='y', alpha=0.3, linestyle='--')

# Thêm annotation tổng
total = sum(total_counts)
ax1.text(0.98, 0.95, f'Tổng: {total:,} ảnh', transform=ax1.transAxes,
         fontsize=12, fontweight='bold', ha='right', va='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

plt.tight_layout()
fig1.savefig('reports/figures/class_distribution.png', dpi=150, bbox_inches='tight',
             facecolor='white', edgecolor='none')
plt.close(fig1)
print("Đã tạo: reports/figures/class_distribution.png")

# ============= HÌNH 2: train_val_test_distribution.png =============
fig2, ax2 = plt.subplots(figsize=(14, 8))

x = np.arange(len(classes))
width = 0.25

bars_train = ax2.bar(x - width, train_counts, width, label=f'Train (42,655)',
                     color='#3498DB', edgecolor='white', linewidth=1.2)
bars_val = ax2.bar(x, val_counts, width, label=f'Validation (9,137)',
                   color='#E74C3C', edgecolor='white', linewidth=1.2)
bars_test = ax2.bar(x + width, test_counts, width, label=f'Test (9,153)',
                     color='#2ECC71', edgecolor='white', linewidth=1.2)

# Thêm số liệu trên mỗi cột
def add_labels(bars):
    for bar in bars:
        height = bar.get_height()
        ax2.annotate(f'{int(height):,}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, fontweight='bold')

add_labels(bars_train)
add_labels(bars_val)
add_labels(bars_test)

ax2.set_xlabel('Lớp (Class)', fontsize=13, fontweight='bold')
ax2.set_ylabel('Số lượng ảnh', fontsize=13, fontweight='bold')
ax2.set_title('Phân bố Train/Validation/Test theo từng lớp\n(Train: 42,655 | Val: 9,137 | Test: 9,153)',
              fontsize=15, fontweight='bold', pad=20)
ax2.set_xticks(x)
ax2.set_xticklabels(classes, rotation=30, ha='right')
ax2.legend(loc='upper right', fontsize=11, framealpha=0.9)
ax2.grid(axis='y', alpha=0.3, linestyle='--')
ax2.set_ylim(0, max(train_counts) * 1.2)

# Thêm annotation
ax2.text(0.02, 0.98, f'Train: {sum(train_counts):,} ảnh\nVal: {sum(val_counts):,} ảnh\nTest: {sum(test_counts):,} ảnh',
         transform=ax2.transAxes, fontsize=10, fontweight='bold', va='top',
         bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

plt.tight_layout()
fig2.savefig('reports/figures/train_val_test_distribution.png', dpi=150, bbox_inches='tight',
             facecolor='white', edgecolor='none')
plt.close(fig2)
print("Đã tạo: reports/figures/train_val_test_distribution.png")

print("\nHoàn tất! Đã tạo 2 hình mới trong reports/figures/")
