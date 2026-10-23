import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    SMTP Email Client for Chitties.
    Handles email verification, password reset, and transactional notifications.
    """

    @classmethod
    def _create_smtp_client(cls) -> Optional[smtplib.SMTP]:
        """Establish connected and authenticated SMTP session."""
        try:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            return server
        except Exception as exc:
            logger.error(f"Failed to connect to SMTP server ({settings.SMTP_HOST}:{settings.SMTP_PORT}): {exc}")
            return None

    @classmethod
    def send_email(
        cls,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email via SMTP.
        Returns True on success, False if delivery failed.
        """
        server = cls._create_smtp_client()
        if not server:
            logger.warning(f"SMTP unavailable; skipping email dispatch to {to_email}")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
            msg["To"] = to_email

            part1 = MIMEText(text_content, "plain")
            msg.attach(part1)

            if html_content:
                part2 = MIMEText(html_content, "html")
                msg.attach(part2)

            server.sendmail(settings.EMAILS_FROM_EMAIL, [to_email], msg.as_string())
            server.quit()
            logger.info(f"Email successfully delivered to {to_email} via SMTP")
            return True
        except Exception as exc:
            logger.error(f"Failed to send email to {to_email}: {exc}")
            try:
                server.quit()
            except Exception:
                pass
            return False

    @classmethod
    def send_verification_email(cls, to_email: str, full_name: str, token: str) -> bool:
        """Send account email verification token/link."""
        subject = "Verify Your Chitties Account"
        text_body = (
            f"Hello {full_name},\n\n"
            f"Welcome to Chitties Chit Fund Management Platform!\n"
            f"Please verify your email address by submitting this token:\n\n"
            f"Token: {token}\n\n"
            f"This verification token expires in 24 hours.\n\n"
            f"Best regards,\n"
            f"Chitties Team"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 580px; margin: 0 auto; padding: 20px; background-color: #f8fafc; border-radius: 8px;">
            <div style="background-color: #064e3b; padding: 20px; border-radius: 6px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Chitties Platform</h1>
            </div>
            <div style="background-color: #ffffff; padding: 30px; border-radius: 6px; margin-top: 15px; border: 1px solid #e2e8f0;">
                <h2 style="color: #1e293b; font-size: 18px;">Welcome, {full_name}!</h2>
                <p style="color: #475569; font-size: 14px; line-height: 1.6;">
                    Thank you for signing up with Chitties. Please use the verification token below to verify your account:
                </p>
                <div style="background-color: #f1f5f9; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 16px; font-weight: bold; color: #0f172a; text-align: center; word-break: break-all; margin: 20px 0;">
                    {token}
                </div>
                <p style="color: #64748b; font-size: 12px;">This token is valid for 24 hours.</p>
            </div>
            <div style="text-align: center; margin-top: 20px; color: #94a3b8; font-size: 11px;">
                &copy; 2026 Chitties Platform. Enterprise Chit Fund Management.
            </div>
        </div>
        """
        return cls.send_email(to_email, subject, text_body, html_body)

    @classmethod
    def send_password_reset_email(cls, to_email: str, full_name: str, token: str) -> bool:
        """Send password recovery token/link."""
        subject = "Reset Your Chitties Password"
        text_body = (
            f"Hello {full_name},\n\n"
            f"We received a request to reset your password for your Chitties account.\n"
            f"Please submit this token with your new password:\n\n"
            f"Reset Token: {token}\n\n"
            f"This reset token will expire in 1 hour.\n\n"
            f"If you did not request this, please disregard this email.\n\n"
            f"Best regards,\n"
            f"Chitties Security Team"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 580px; margin: 0 auto; padding: 20px; background-color: #f8fafc; border-radius: 8px;">
            <div style="background-color: #1e293b; padding: 20px; border-radius: 6px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Chitties Security</h1>
            </div>
            <div style="background-color: #ffffff; padding: 30px; border-radius: 6px; margin-top: 15px; border: 1px solid #e2e8f0;">
                <h2 style="color: #1e293b; font-size: 18px;">Password Reset Request</h2>
                <p style="color: #475569; font-size: 14px; line-height: 1.6;">
                    Hello {full_name}, we received a request to reset your Chitties password. Use the token below to set your new password:
                </p>
                <div style="background-color: #fee2e2; border: 1px solid #fca5a5; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 16px; font-weight: bold; color: #991b1b; text-align: center; word-break: break-all; margin: 20px 0;">
                    {token}
                </div>
                <p style="color: #64748b; font-size: 12px;">This token expires in 1 hour. If you didn't request this change, you can safely ignore this email.</p>
            </div>
            <div style="text-align: center; margin-top: 20px; color: #94a3b8; font-size: 11px;">
                &copy; 2026 Chitties Platform. Enterprise Chit Fund Management.
            </div>
        </div>
        """
        return cls.send_email(to_email, subject, text_body, html_body)
