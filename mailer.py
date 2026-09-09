# -*- coding: utf-8 -*-
"""온다(ONDA) 일정관리 - Gmail(SMTP 앱 비밀번호) 발송 유틸리티"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "njb.official.connect@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def mail_configured():
    return bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)


def send_email(to_email, subject, body, sender_display_name=""):
    """SMTP(SSL)로 메일을 보냅니다. 성공하면 (True, None), 실패하면 (False, 에러메시지)."""

    if not mail_configured():
        return False, "GMAIL_APP_PASSWORD가 설정되어 있지 않습니다. .env를 확인하세요."

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    from_label = f"{sender_display_name} (ONDA)" if sender_display_name else "ONDA"
    msg["From"] = f"{from_label} <{GMAIL_ADDRESS}>"
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, [to_email], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


def send_email_with_attachment(to_email, subject, body, filename, file_bytes, sender_display_name=""):
    """SMTP(SSL)로 첨부파일이 있는 메일을 보냅니다. 성공하면 (True, None), 실패하면 (False, 에러메시지)."""

    if not mail_configured():
        return False, "GMAIL_APP_PASSWORD가 설정되어 있지 않습니다. .env를 확인하세요."

    msg = MIMEMultipart()
    msg["Subject"] = subject
    from_label = f"{sender_display_name} (ONDA)" if sender_display_name else "ONDA"
    msg["From"] = f"{from_label} <{GMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg.attach(MIMEText(body, _charset="utf-8"))

    attachment = MIMEApplication(file_bytes, Name=filename)
    attachment["Content-Disposition"] = f'attachment; filename="{filename}"'
    msg.attach(attachment)

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, [to_email], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)
