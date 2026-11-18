import math
import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent
FEATURE_COLUMNS = ["variance", "edge_count", "mean_intensity"]


def train_model(data_path=ROOT / "training_data.csv", model_path=ROOT / "stego_model.pkl"):
    frame = pd.read_csv(data_path)
    missing = set(FEATURE_COLUMNS + ["label"]) - set(frame.columns)
    if missing:
        raise ValueError(f"Training data is missing columns: {', '.join(sorted(missing))}")
    if frame.empty or set(frame["label"].dropna().unique()) != {0, 1}:
        raise ValueError("Training data must contain rows labeled 0 and 1.")

    label_counts = frame["label"].value_counts()
    if label_counts.min() < 2:
        raise ValueError("Training data needs at least two rows for each label.")

    features = frame[FEATURE_COLUMNS]
    labels = frame["label"]
    test_count = max(2, math.ceil(len(frame) * 0.2))
    if test_count >= len(frame):
        raise ValueError("Training data has too few rows for a train/test split.")

    train_features, test_features, train_labels, test_labels = train_test_split(
        features,
        labels,
        test_size=test_count,
        random_state=42,
        stratify=labels,
    )
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(train_features, train_labels)
    prediction = model.predict(test_features)
    print("Accuracy:", accuracy_score(test_labels, prediction))

    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as model_file:
        pickle.dump(model, model_file)
    print(f"Model saved to {model_path}")
    return model


def main():
    train_model()


if __name__ == "__main__":
    main()
