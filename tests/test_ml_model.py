"""ML model and preprocessing tests."""

from src.models.ml_classifier import MLClassifier
from src.models.preprocessor import TextPreprocessor


def test_text_preprocessor_combines_and_normalizes_text():
    result = TextPreprocessor.preprocess("Password reset", "User cannot log in.")
    assert "password reset" in result
    assert "." not in result
    assert result == "password reset user cannot log in"


def test_ml_classifier_zero_shot_returns_label_and_score(monkeypatch):
    def fake_load(self):
        self._pipeline = lambda text, candidate_labels: {
            "labels": [candidate_labels[0]],
            "scores": [0.91],
        }

    monkeypatch.setattr(MLClassifier, "_load_pipeline", fake_load)
    classifier = MLClassifier()

    assigned_team, confidence_score = classifier.classify(
        "VPN issue",
        "My VPN disconnects after login",
    )

    assert isinstance(assigned_team, str)
    assert 0.0 <= confidence_score <= 1.0
    assert assigned_team != ""
