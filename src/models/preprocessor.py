"""Text preprocessing and vectorization module."""

import string
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """Handles text preprocessing for ML classifier."""
    
    @staticmethod
    def preprocess(title: str, description: str) -> str:
        """
        Preprocess ticket title and description.
        
        Steps:
        1. Concatenate title and description
        2. Convert to lowercase
        3. Remove punctuation
        """
        # Concatenate
        combined_text = f"{title} {description}"
        
        # Convert to lowercase
        combined_text = combined_text.lower()
        
        # Remove punctuation
        translator = str.maketrans('', '', string.punctuation)
        combined_text = combined_text.translate(translator)
        
        # Remove extra whitespace
        combined_text = ' '.join(combined_text.split())
        
        logger.debug(f"Preprocessed text: {combined_text[:100]}...")
        return combined_text
