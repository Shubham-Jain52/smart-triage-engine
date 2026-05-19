"""Text preprocessing and vectorization module."""

import string
import logging

logger = logging.getLogger(__name__)


class TextPreprocessor:
    @staticmethod
    def preprocess(title: str, description: str) -> str:
        combined_text = f"{title} {description}"
        combined_text = combined_text.lower()
        translator = str.maketrans('', '', string.punctuation)
        combined_text = combined_text.translate(translator)
        combined_text = ' '.join(combined_text.split())
        logger.debug(f"Preprocessed text: {combined_text[:100]}...")
        return combined_text
