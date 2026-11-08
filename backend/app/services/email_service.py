"""Resend delivery for account OTPs and SMTP delivery for notifications."""
import json
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app

from app.services.email_templates import render_notification_email, render_otp_email


class EmailDeliveryError(RuntimeError):
    """Raised when an account email cannot be delivered."""


def send_account_token(user, purpose, code):
    """Send an account OTP through Resend, or use the configured test sender."""
    test_sender = current_app.config.get("AUTH_EMAIL_SENDER")
    if test_sender is not None:
        test_sender(user.email, purpose, code)
        return

    subject, text, html = render_otp_email(user.display_name, purpose, code)
    _send_resend_message(user.email, subject, text, html)


def send_account_notification(user, notification):
    """Send a non-OTP account notification."""
    subject, text, html = render_notification_email(
        user.display_name, notification
    )
    _send_message(user.email, subject, text, html)


def _send_message(recipient, subject, text, html):
    config = current_app.config
    server = config.get("MAIL_SERVER")
    sender_address = config.get("MAIL_DEFAULT_SENDER") or config.get("MAIL_FROM")
    if not server or not sender_address:
        raise EmailDeliveryError("SMTP server and sender address must be configured.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((config.get("MAIL_SENDER_NAME", "STEER"), sender_address))
    message["To"] = recipient
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    context = ssl.create_default_context()
    try:
        if config.get("MAIL_USE_SSL"):
            with smtplib.SMTP_SSL(
                server, config.get("MAIL_PORT", 587), context=context, timeout=15
            ) as connection:
                _authenticate(connection, config)
                connection.send_message(message)
        else:
            with smtplib.SMTP(
                server, config.get("MAIL_PORT", 587), timeout=15
            ) as connection:
                if config.get("MAIL_USE_TLS"):
                    connection.starttls(context=context)
                    connection.ehlo()
                _authenticate(connection, config)
                connection.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError("SMTP could not deliver the account email.") from error


def _send_resend_message(recipient, subject, text, html):
    config = current_app.config
    api_key = config.get("RESEND_API_KEY")
    sender_address = config.get("MAIL_DEFAULT_SENDER") or config.get("MAIL_FROM")
    if not api_key or not sender_address:
        raise EmailDeliveryError(
            "Resend API key and verified sender address must be configured."
        )

    message = {
        "from": formataddr((config.get("MAIL_SENDER_NAME", "STEER"), sender_address)),
        "to": [recipient],
        "subject": subject,
        "text": text,
        "html": html,
    }
    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(message).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            if response.status >= 400:
                raise EmailDeliveryError("Resend could not deliver the account email.")
    except (HTTPError, URLError, OSError, TimeoutError) as error:
        raise EmailDeliveryError("Resend could not deliver the account email.") from error


def _authenticate(connection, config):
    username = config.get("MAIL_USERNAME")
    password = config.get("MAIL_PASSWORD")
    if username and password:
        connection.login(username, password)
