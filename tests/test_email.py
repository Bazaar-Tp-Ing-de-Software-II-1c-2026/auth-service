import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.utils.email import send_email_html, _smtp_config
import os


class TestSmtpConfig:
    def test_smtp_config_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            host, port, user, password, starttls, ssl, sender, timeout = _smtp_config()
            assert host == "smtp.gmail.com"
            assert port == 465
            assert starttls is False
            assert ssl is True
            assert timeout == 10

    def test_smtp_config_custom_values(self):
        env_vars = {
            "SMTP_HOST": "mail.example.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@example.com",
            "SMTP_PASSWORD": "password",
            "SMTP_STARTTLS": "True",
            "SMTP_SSL": "False",
            "SMTP_SENDER": "sender@example.com",
            "SMTP_TIMEOUT": "20"
        }
        with patch.dict(os.environ, env_vars):
            host, port, user, password, starttls, ssl, sender, timeout = _smtp_config()
            assert host == "mail.example.com"
            assert port == 587
            assert starttls is True
            assert ssl is False
            assert timeout == 20
            assert sender == "sender@example.com"


class TestSendEmailHtml:
    @patch('app.utils.email.smtplib.SMTP_SSL')
    def test_send_email_ssl_success(self, mock_smtp_ssl):
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server

        env_vars = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "465",
            "SMTP_USER": "test@gmail.com",
            "SMTP_PASSWORD": "password",
            "SMTP_SSL": "True"
        }
        
        with patch.dict(os.environ, env_vars):
            send_email_html(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_body="<h1>Test</h1>",
                text_fallback="Test"
            )
        
        mock_server.ehlo.assert_called()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

    @patch('app.utils.email.smtplib.SMTP')
    def test_send_email_starttls_success(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        env_vars = {
            "SMTP_HOST": "mail.example.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "test@example.com",
            "SMTP_PASSWORD": "password",
            "SMTP_STARTTLS": "True",
            "SMTP_SSL": "False"
        }
        
        with patch.dict(os.environ, env_vars):
            send_email_html(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_body="<h1>Test</h1>"
            )
        
        mock_server.starttls.assert_called()
        mock_server.login.assert_called_once()

    @patch('app.utils.email.smtplib.SMTP_SSL')
    def test_send_email_with_html(self, mock_smtp_ssl):
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server

        env_vars = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_USER": "test@gmail.com",
            "SMTP_PASSWORD": "password"
        }
        
        with patch.dict(os.environ, env_vars):
            send_email_html(
                to_email="test@example.com",
                subject="HTML Test",
                html_body="<p>Hello</p>"
            )
        
        assert mock_server.send_message.called

    @patch('app.utils.email.smtplib.SMTP_SSL')
    def test_send_email_with_text_fallback(self, mock_smtp_ssl):
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server

        env_vars = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_USER": "test@gmail.com",
            "SMTP_PASSWORD": "password"
        }
        
        with patch.dict(os.environ, env_vars):
            send_email_html(
                to_email="test@example.com",
                subject="Test",
                html_body="<p>HTML</p>",
                text_fallback="Plain text"
            )
        
        assert mock_server.send_message.called

    @patch('app.utils.email.smtplib.SMTP_SSL')
    def test_send_email_timeout_error(self, mock_smtp):
        import socket
        mock_smtp.side_effect = socket.timeout("Connection timeout")

        env_vars = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_USER": "test@gmail.com",
            "SMTP_PASSWORD": "password"
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(HTTPException):
                send_email_html(
                    to_email="test@example.com",
                    subject="Test",
                    html_body="<p>Test</p>"
                )
