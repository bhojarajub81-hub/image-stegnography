import cv2
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def extract_features(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    if img is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    variance = float(np.var(img))
    edges = cv2.Canny(img, 100, 200)
    edge_count = int(np.sum(edges > 0))
    mean_intensity = float(np.mean(img))

    return [variance, edge_count, mean_intensity]


if __name__ == "__main__":
    image_path = ROOT / "stego_image.png"
    try:
        features = extract_features(image_path)
        print(f"Image: {image_path}")
        print(f"Variance: {features[0]}")
        print(f"Edge Count: {features[1]}")
        print(f"Mean Intensity: {features[2]}")
    except Exception as e:
        print(f"Error: {e}")