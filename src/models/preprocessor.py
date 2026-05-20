"""Preprocessor for ticket text.

Combines title and description for NLP models: lowercase, strip punctuation (TRD),
normalize whitespace, then optional character truncation before tokenization.
"""

import logging
import string

logger = logging.getLogger(__name__)


class TextPreprocessor:
    @staticmethod
    def preprocess(title: str, description: str, max_length_chars: int = 1000) -> str:
        """Combine `title` and `description` into a single string suitable for classifiers.

        - Lowercases the combined text
        - Replaces punctuation with spaces, then collapses repeated whitespace
        - Truncates to `max_length_chars` characters (keeps tokenization fast)
        """
        if not title:
            title = ""
        if not description:
            description = ""

        combined = f"{title} {description}".strip()
        combined = combined.lower()
        combined = "".join(ch if ch not in string.punctuation else " " for ch in combined)
        combined = " ".join(combined.split())

        if len(combined) > max_length_chars:
            combined = combined[:max_length_chars]

        logger.debug(f"Preprocessed text (len={len(combined)}): {combined[:120]}...")
        return combined
