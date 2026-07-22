"""Optional email delivery of the run report.

No-op unless SMTP env vars are configured — never an error when unset. The
manual CLI does not email; this is here for the later scheduled version (or if
you set --email plus SMTP_* env vars).

Env vars: SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
SMTP_FROM (default SMTP_USER), SMTP_TO, SMTP_TLS (default "1").
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

_REQUIRED = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_TO")


def is_configured() -> bool:
    return all(os.environ.get(k) for k in _REQUIRED)


def send(subject: str, text_body: str, html_body: str) -> tuple[bool, str]:
    """Send the report. Returns (sent, message)."""
    if not is_configured():
        missing = [k for k in _REQUIRED if not os.environ.get(k)]
        return False, f"email not configured, skipping (missing: {', '.join(missing)})"

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.environ.get("SMTP_FROM", user)
    recipients = [r.strip() for r in os.environ["SMTP_TO"].split(",") if r.strip()]
    use_tls = os.environ.get("SMTP_TLS", "1") not in ("0", "false", "False")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
        return True, f"email sent to {', '.join(recipients)}"
    except Exception as exc:  # noqa: BLE001
        return False, f"email failed: {type(exc).__name__}: {exc}"
