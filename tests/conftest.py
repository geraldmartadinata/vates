"""Test fixtures bersama — digunakan di semua modul test."""

import pytest


@pytest.fixture
def sample_ticker() -> str:
    """Ticker IHSG untuk testing."""
    return "BBCA.JK"
