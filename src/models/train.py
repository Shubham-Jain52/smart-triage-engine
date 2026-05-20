"""Optional offline training: TF-IDF + Logistic Regression to pickle artifacts.

The FastAPI runtime classifies tickets with ``MLClassifier`` (Hugging Face zero-shot) by default.
Run this module only if you want ``MODEL_PATH`` / ``VECTORIZER_PATH`` pickles for experiments
or a future sklearn-based ``MLClassifier`` swap.

    python -m src.models.train
"""

import pickle
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from src.config import get_settings
from src.models.preprocessor import TextPreprocessor

settings = get_settings()


def create_synthetic_dataset():
    return pd.DataFrame([
        {
            "title": "Cannot connect to VPN",
            "description": "VPN authentication fails after entering correct password",
            "assigned_team": "Network Support",
        },
        {
            "title": "Email delivery error",
            "description": "Outgoing messages are bouncing back with error code 550",
            "assigned_team": "Email Support",
        },
        {
            "title": "Forgot password",
            "description": "User cannot log in because password reset link expired",
            "assigned_team": "Identity & Access",
        },
        {
            "title": "Printer not printing",
            "description": "Office printer is showing a paper jam even after clearing it",
            "assigned_team": "Hardware Support",
        },
        {
            "title": "Application crash",
            "description": "Business application crashes when saving a record",
            "assigned_team": "Application Support",
        },
        {
            "title": "Database timeout",
            "description": "Queries are timing out when accessing the customer database",
            "assigned_team": "Database Support",
        },
    ])


def train_model():
    data = create_synthetic_dataset()
    preprocessor = TextPreprocessor()
    text_series = data.apply(
        lambda row: preprocessor.preprocess(row["title"], row["description"]), axis=1
    )

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(text_series)
    y = data["assigned_team"]

    classifier = LogisticRegression(max_iter=500)
    classifier.fit(X, y)

    model_dir = Path(settings.MODEL_PATH).parent
    model_dir.mkdir(parents=True, exist_ok=True)

    with open(settings.MODEL_PATH, "wb") as f:
        pickle.dump(classifier, f)

    with open(settings.VECTORIZER_PATH, "wb") as f:
        pickle.dump(vectorizer, f)

    print(f"Trained and saved model to {settings.MODEL_PATH}")
    print(f"Trained and saved vectorizer to {settings.VECTORIZER_PATH}")


if __name__ == "__main__":
    train_model()
