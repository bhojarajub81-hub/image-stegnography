import os
import pickle

import cv2
import numpy as np
import pandas as pd
from cryptography.fernet import Fernet

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(ROOT, "stego_model.pkl")
IMAGE_PATH = os.path.join(os.path.expanduser("~"), "Downloads", "stego.png")
FERNET_KEY = b"6I_-mh53g0BqoCEzGpen9-FJwtpjt_onta-Ejeo5NHg="


def load_model():
    with open(MODEL_PATH, "rb") as model_file:
        return pickle.load(model_file)


def extract_features(image_path):
    image = cv2.imread(image_path)
    if image is None:
        print(f"Image not found: {image_path}")
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    variance = float(np.var(gray))
    edges = cv2.Canny(gray, 100, 200)
    edge_count = int(np.sum(edges > 0))
    mean_intensity = float(np.mean(gray))
    return [variance, edge_count, mean_intensity]


def detect_stego(image_path, model):
    features = extract_features(image_path)
    if features is None:
        return False

    features_frame = pd.DataFrame(
        [features],
        columns=["variance", "edge_count", "mean_intensity"],
    )
    return int(model.predict(features_frame)[0]) == 1


def decode_message_from_bits(image_path):
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        return None

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    flat = image_rgb.reshape(-1)
    bits = (flat & 1).astype(np.uint8)
    if bits.size < 32:
        return None

    total_bytes = bits.size // 8
    packed = np.packbits(bits[: total_bytes * 8].reshape(-1, 8), axis=1, bitorder="big")
    extracted = packed.flatten().tobytes()
    payload_length = int.from_bytes(extracted[:4], byteorder="big", signed=False)
    if payload_length <= 0 or payload_length > len(extracted) - 4:
        return None

    encrypted = extracted[4:4 + payload_length]
    try:
        return Fernet(FERNET_KEY).decrypt(encrypted).decode("utf-8")
    except Exception:
        return None


if __name__ == "__main__":
    try:
        model = load_model()
    except Exception as error:
        print(f"Could not load model: {error}")
        model = None

    if model is None:
        print("Model not available; trying direct decoder...")
    else:
        is_stego = detect_stego(IMAGE_PATH, model)
        print(f"Stego image detected by model: {is_stego}")

    hidden_message = decode_message_from_bits(IMAGE_PATH)
    if hidden_message:
        print(f"Hidden message: {hidden_message}")
    else:
        print("No hidden message found.")
