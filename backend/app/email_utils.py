import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from app.config import settings


class EmailNotConfigured(Exception):
    pass


def send_invoice_email(
    to_email: str, subject: str, body: str, pdf_path: str, pdf_filename: str
) -> str:
    if not settings.smtp_host or not settings.smtp_from:
        raise EmailNotConfigured(
            "SMTP ist nicht konfiguriert (SMTP_HOST/SMTP_FROM fehlen)."
        )
    if bool(settings.smtp_user) != bool(settings.smtp_password):
        raise EmailNotConfigured(
            "SMTP-Benutzer und SMTP-Passwort müssen gemeinsam konfiguriert sein."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    message_id = make_msgid(domain="essentials-freelancer.invalid")
    msg["Message-ID"] = message_id
    msg.set_content(body)

    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=pdf_filename,
        )

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=settings.smtp_timeout_seconds,
    ) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
    return message_id
