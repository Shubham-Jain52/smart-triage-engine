"""ML classifier wrapper for ticket classification."""

import pickle
import logging
from typing import Optional, Tuple
from pathlib import Path

from src.config import get_settings
from src.models.preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)
settings = get_settings()


class MLClassifier:
    """Wrapper for ML classifier and vectorizer."""
    
    def __init__(self):
        """Initialize classifier and vectorizer from serialized files."""
        self.classifier = None
        self.vectorizer = None
        self.preprocessor = TextPreprocessor()
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained classifier and vectorizer from disk."""
        try:
            model_path = Path(settings.MODEL_PATH)
            vectorizer_path = Path(settings.VECTORIZER_PATH)
            
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    self.classifier = pickle.load(f)
                logger.info(f"Loaded classifier from {model_path}")
            else:
                logger.warning(f"Classifier not found at {model_path}")
            
            if vectorizer_path.exists():
                with open(vectorizer_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                logger.info(f"Loaded vectorizer from {vectorizer_path}")
            else:
                logger.warning(f"Vectorizer not found at {vectorizer_path}")
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def classify(self, title: str, description: str) -> Tuple[str, float]:
        """
        Classify ticket and return team assignment and confidence score.
        
        Args:
            title: Ticket title
            description: Ticket description
        
        Returns:
            Tuple of (assigned_team, confidence_score)
        """
        if not self.classifier or not self.vectorizer:
            logger.error("Classifier or vectorizer not loaded")
            raise RuntimeError("ML models not available")
        
        try:
            # Preprocess text
            preprocessed_text = self.preprocessor.preprocess(title, description)
            
            # Vectorize
            vectorized_text = self.vectorizer.transform([preprocessed_text])
            
            # Predict
            predicted_class = self.classifier.predict(vectorized_text)[0]
            predicted_proba = self.classifier.predict_proba(vectorized_text)[0]
            confidence_score = float(max(predicted_proba))
            
            logger.info(f"Classification: {predicted_class} (confidence: {confidence_score:.2f})")
            
            return predicted_class, confidence_score
        except Exception as e:
            logger.error(f"Classification error: {e}")
            raise
