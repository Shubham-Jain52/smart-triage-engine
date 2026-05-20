"""Runtime ticket classifier: Hugging Face zero-shot classification.

Phase 1 uses a **local** pretrained NLI-style model (default ``valhalla/distilbart-mnli-12-1``)
via ``transformers.pipeline("zero-shot-classification", ...)``. Candidate team names come from
``Settings.CANDIDATE_LABELS`` (``CANDIDATE_LABELS`` env: comma-separated). No per-request HTTP
calls to an LLM API; weights load from disk/cache after the first download.

For a lighter TRD-style alternative (TF-IDF + Logistic Regression pickles), see
``src.models.train`` — not used by this class unless you replace the implementation.
"""

import logging
from typing import Tuple, Optional

from src.config import get_settings
from src.models.preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)


class MLClassifier:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or get_settings().ZS_MODEL_NAME
        self._pipeline = None
        self.preprocessor = TextPreprocessor()
        self._load_pipeline()

    def _load_pipeline(self):
        try:
            # Import here to keep import-time lightweight if transformers is not installed
            from transformers import pipeline

            self._pipeline = pipeline("zero-shot-classification", model=self.model_name)
            logger.info(f"Loaded zero-shot pipeline with model {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load Hugging Face pipeline: {e}")
            self._pipeline = None

    def classify(self, title: str, description: str) -> Tuple[str, float]:
        if not self._pipeline:
            raise RuntimeError("Zero-shot pipeline not available")

        text = self.preprocessor.preprocess(title, description)
        candidate_labels = get_settings().CANDIDATE_LABELS

        try:
            output = self._pipeline(text, candidate_labels)
            label = output.get("labels", [None])[0]
            score = float(output.get("scores", [0.0])[0])
            logger.info(f"Zero-shot predicted {label} with score {score:.2f}")
            return label, score
        except Exception as e:
            logger.error(f"Zero-shot classification error: {e}")
            raise
