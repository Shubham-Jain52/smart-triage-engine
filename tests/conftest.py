"""Pytest fixtures."""

import pytest

from src.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """So tests that change environment variables see fresh ``Settings``."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
