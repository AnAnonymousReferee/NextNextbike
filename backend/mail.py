"""Mail support for the BonnBike backend."""

import os
import smtplib
from email.message import EmailMessage


class ConsoleMailSender:
    """Send mail output to the console for development."""

    def send_password_reset(self, *, email, token):
        reset_url_template = os.environ.get(
            "PASSWORD_RESET_URL_TEMPLATE",
            "http://localhost:8000/api/password-reset/confirm?token={token}",
        )
        reset_url = reset_url_template.format(token=token)
        print("--- Password reset email ---")
        print(f"To: {email}")
        print(f"Subject: BonnBike password reset")
        print("")
        print(f"Hello,\n\nTo reset your password, please visit the following link:\n{reset_url}\n\nIf you did not request this, ignore this message.\n")
        print("--- End email ---")


class PasswordResetMailSender:
    """Send password reset mail via SMTP."""

    def __init__(
        self,
        smtp_host,
        smtp_port,
        from_address,
        username=None,
        password=None,
        use_tls=True,
        reset_url_template=None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_address = from_address
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.reset_url_template = reset_url_template or (
            "http://localhost:8000/api/password-reset/confirm?token={token}"
        )

    def send_password_reset(self, *, email, token):
        reset_url = self.reset_url_template.format(token=token)
        message = EmailMessage()
        message["From"] = self.from_address
        message["To"] = email
        message["Subject"] = "BonnBike password reset"
        message.set_content(
            f"Hello,\n\n"
            f"To reset your BonnBike password, please open the following link:\n"
            f"{reset_url}\n\n"
            f"If you did not request this change, please ignore this email.\n"
        )

        if self.use_tls:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as smtp:
                smtp.starttls()
                if self.username and self.password:
                    smtp.login(self.username, self.password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as smtp:
                if self.username and self.password:
                    smtp.login(self.username, self.password)
                smtp.send_message(message)
