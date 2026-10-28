"""
Global pytest fixtures (dùng chung cho toàn bộ test suite).
"""
import sys
from unittest.mock import MagicMock

try:
    import pymupdf
except Exception:
    mock_mupdf = MagicMock()
    sys.modules["pymupdf"] = mock_mupdf
    sys.modules["fitz"] = mock_mupdf

import pytest
import app.models  # noqa: F401
