import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.utils.email import send_email_html
import os


class TestSendEmailHtml:
    def test_send_email_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                send_email_html(
                    to_email="recipient@example.com",
                    subject="Test Subject",
                    html_body="<h1>Test</h1>",
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "RESEND_API_KEY no configurada"

    def test_send_email_requires_resend_library(self):
        env_vars = {"RESEND_API_KEY": "re_test_key"}
        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.utils.email.resend", None):
                with pytest.raises(HTTPException) as exc_info:
                    send_email_html(
                        to_email="recipient@example.com",
                        subject="Test Subject",
                        html_body="<h1>Test</h1>",
                    )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Librería resend no instalada"

    def test_send_email_success_uses_default_sender_and_default_text(self):
        env_vars = {"RESEND_API_KEY": "re_test_key"}
        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.utils.email.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email_123"}

                send_email_html(
                    to_email="recipient@example.com",
                    subject="Test Subject",
                    html_body="<h1>Test</h1>",
                )

        assert mock_resend.api_key == "re_test_key"
        mock_resend.Emails.send.assert_called_once_with(
            {
                "from": "onboarding@resend.dev",
                "to": "recipient@example.com",
                "subject": "Test Subject",
                "html": "<h1>Test</h1>",
                "text": "Tu cliente de correo no soporta HTML.",
            }
        )

    def test_send_email_success_uses_custom_sender_and_text_fallback(self):
        env_vars = {
            "RESEND_API_KEY": "re_test_key",
            "EMAIL_FROM": "noreply@bazaar.test",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.utils.email.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email_123"}

                send_email_html(
                    to_email="recipient@example.com",
                    subject="Test Subject",
                    html_body="<h1>Test</h1>",
                    text_fallback="Texto alternativo",
                )

        mock_resend.Emails.send.assert_called_once_with(
            {
                "from": "noreply@bazaar.test",
                "to": "recipient@example.com",
                "subject": "Test Subject",
                "html": "<h1>Test</h1>",
                "text": "Texto alternativo",
            }
        )

    def test_send_email_fails_when_provider_returns_no_id(self):
        env_vars = {"RESEND_API_KEY": "re_test_key"}
        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.utils.email.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {
                    "message": "provider error",
                }

                with pytest.raises(HTTPException) as exc_info:
                    send_email_html(
                        to_email="recipient@example.com",
                        subject="Test Subject",
                        html_body="<h1>Test</h1>",
                    )

        assert exc_info.value.status_code == 502
        assert "Error enviando email:" in exc_info.value.detail

    def test_send_email_fails_when_provider_raises_exception(self):
        env_vars = {"RESEND_API_KEY": "re_test_key"}
        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.utils.email.resend") as mock_resend:
                mock_resend.Emails.send.side_effect = RuntimeError("connection down")

                with pytest.raises(HTTPException) as exc_info:
                    send_email_html(
                        to_email="recipient@example.com",
                        subject="Test Subject",
                        html_body="<h1>Test</h1>",
                    )

        assert exc_info.value.status_code == 502
        assert "connection down" in exc_info.value.detail
