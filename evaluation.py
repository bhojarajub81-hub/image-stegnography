import pickle
from pathlib import Path

import pandas as pd
from sklearn.metrics import confusion_matrix, classification_report
from extract_message import decode_message_from_bits

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "stego_model.pkl"
DATASET_PATH = ROOT / "training_data.csv"
IMAGE_PATH = Path.home() / "Downloads" / "stego.png"


def main():
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    df = pd.read_csv(DATASET_PATH)
    X = df[["variance", "edge_count", "mean_intensity"]]
    y = df["label"]

    pred = model.predict(X)

    print("Confusion Matrix:")
    print(confusion_matrix(y, pred))

    print("\nClassification Report:")
    print(classification_report(y, pred))

    decoded = decode_message_from_bits(str(IMAGE_PATH))
    print(f"\nDecoded message from {IMAGE_PATH}:")
    if decoded:
        print(decoded)
    else:
        print("No hidden message found.")


if __name__ == "__main__":
    main()
