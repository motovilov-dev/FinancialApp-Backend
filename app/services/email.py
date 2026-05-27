from __future__ import annotations

import logging
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib

from ..config import get_settings
from .email_templates import verify_email as tpl_verify
from .email_templates import welcome_email as tpl_welcome
from .email_templates import workspace_invite as tpl_invite

log = logging.getLogger(__name__)
settings = get_settings()


async def send_email(
    *,
    to: str,
    subject: str,
    text: str,
    html: str | None = None,
) -> None:
    """Отправка письма. В dev — пишем .eml в ./var/mail.
    Если html задан — формируем multipart/alternative (text + html).
    """
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    if settings.use_real_smtp and settings.smtp_host:
        use_tls = settings.smtp_implicit_tls
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=use_tls,
            start_tls=not use_tls,
        )
        log.info(
            "smtp sent to=%s subject=%r via %s:%d tls=%s",
            to, subject, settings.smtp_host, settings.smtp_port,
            "implicit" if use_tls else "starttls",
        )
        return

    out_dir = Path("var/mail")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    safe_to = to.replace("@", "_at_").replace("/", "_")
    out_path = out_dir / f"{ts}-{safe_to}.eml"
    out_path.write_bytes(bytes(msg))
    log.warning("DEV email -> %s\n  TO: %s\n  SUBJECT: %s", out_path, to, subject)


# ---------- высокоуровневые письма ----------

async def send_verify_email(*, to: str, display_name: str, verify_url: str) -> None:
    subject, html, text = tpl_verify(display_name=display_name, verify_url=verify_url)
    await send_email(to=to, subject=subject, text=text, html=html)


async def send_welcome_email(*, to: str, display_name: str, app_url: str | None = None) -> None:
    subject, html, text = tpl_welcome(
        display_name=display_name,
        app_url=app_url or settings.public_base_url,
    )
    await send_email(to=to, subject=subject, text=text, html=html)


async def send_workspace_invite(
    *, to: str, inviter_name: str, workspace_name: str, accept_url: str
) -> None:
    subject, html, text = tpl_invite(
        inviter_name=inviter_name, workspace_name=workspace_name, accept_url=accept_url
    )
    await send_email(to=to, subject=subject, text=text, html=html)
