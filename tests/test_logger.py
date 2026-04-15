from unittest.mock import patch

from app import logger as logger_module


def test_setup_logger_development_configures_debug_format(monkeypatch):
    monkeypatch.setattr(logger_module.settings, "ENVIRONMENT", "development")

    with patch.object(logger_module.logger, "remove") as mock_remove, patch.object(logger_module.logger, "add") as mock_add:
        returned = logger_module.setup_logger()

    mock_remove.assert_called_once()
    mock_add.assert_called_once()
    kwargs = mock_add.call_args.kwargs
    assert kwargs["level"] == "DEBUG"
    assert "<green>{time}</green>" in kwargs["format"]
    assert returned is logger_module.logger


def test_setup_logger_production_configures_info_format(monkeypatch):
    monkeypatch.setattr(logger_module.settings, "ENVIRONMENT", "production")

    with patch.object(logger_module.logger, "remove") as mock_remove, patch.object(logger_module.logger, "add") as mock_add:
        returned = logger_module.setup_logger()

    mock_remove.assert_called_once()
    mock_add.assert_called_once()
    kwargs = mock_add.call_args.kwargs
    assert kwargs["level"] == "INFO"
    assert kwargs["format"] == "{time} | {level} | {message}"
    assert returned is logger_module.logger
