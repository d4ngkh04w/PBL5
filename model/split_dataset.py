import splitfolders
import os
import shutil

if os.path.exists("dataset/output"):
    shutil.rmtree("dataset/output")

splitfolders.ratio(
    "dataset/input",
    output="dataset/output",
    seed=1303,
    ratio=(0.8, 0.1, 0.1),
)
