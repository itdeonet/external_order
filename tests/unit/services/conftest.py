"""Shared fixtures for unit service tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def mock_emailer(mocker):
    """Automatically mock EmailSender for all tests in this directory."""
    mock_sender = Mock()
    mocker.patch("src.services.harman_stock_service.EmailSender", return_value=mock_sender)
