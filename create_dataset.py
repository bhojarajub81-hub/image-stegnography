import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
COLUMNS = ["variance", "edge_count", "mean_intensity", "label"]


def extract_image_features(folder, label):
    rows = []
    if not folder.is_dir():
        raise FileNotFoundError(f"Dataset folder not found: {folder}")

    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        image = cv2.imread(str(path))
        if image is None:
            continue

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        rows.append([
            float(np.var(gray)),
            int(np.sum(edges > 0)),
            float(np.mean(gray)),
            label,
        ])
    return rows


def main():
    rows = extract_image_features(ROOT / "dataset" / "cover", 0)
    rows.extend(extract_image_features(ROOT / "dataset" / "stego", 1))
    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame.to_csv(ROOT / "training_data.csv", index=False)
    print("Dataset created successfully")
    print(frame["label"].value_counts())


if __name__ == "__main__":
    main()
