"""Preprocessor for ticket text.

BERT-style models perform their own tokenization and truncation, so
the preprocessor's responsibility is lightweight: safely combine the
ticket fields, normalize whitespace, lowercase, and optionally
truncate to a maximum character length to keep tokenization fast.
"""

import logging

logger = logging.getLogger(__name__)


class TextPreprocessor:
    @staticmethod
    def preprocess(title: str, description: str, max_length_chars: int = 1000) -> str:
        """Combine `title` and `description` into a single string suitable
        for model tokenizers.

        - Lowercases the combined text
        - Collapses repeated whitespace
        - Truncates to `max_length_chars` characters (safe for BERT inputs)

        The tokenizer (e.g. from Hugging Face) should be applied later
        so it can handle subword tokenization and exact max-token truncation.
        """
        if not title:
            title = ""
        if not description:
            description = ""

        combined = f"{title} {description}".strip()
        combined = " ".join(combined.split())
        combined = combined.lower()

        if len(combined) > max_length_chars:
            combined = combined[:max_length_chars]

        logger.debug(f"Preprocessed text (len={len(combined)}): {combined[:120]}...")
        return combined
