"""HTML‑шаблоны писем. Минимальный inline‑CSS, тёмная/светлая совместимость,
рендерится в Gmail / Apple Mail / Outlook без сюрпризов.
"""
from __future__ import annotations

from datetime import datetime


_BRAND = "FinanceMac"
_ACCENT = "#3E7BFA"
_BG = "#F5F6F8"
_CARD = "#FFFFFF"
_TEXT = "#1B1F24"
_MUTED = "#6B7380"
_BORDER = "#E6E8EC"


def _layout(*, preheader: str, body_html: str) -> str:
    """Базовый wrapper. preheader — невидимый текст-превью в инбоксе."""
    year = datetime.utcnow().year
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <title>{_BRAND}</title>
</head>
<body style="margin:0;padding:0;background:{_BG};font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:{_TEXT};">
  <span style="display:none!important;opacity:0;color:transparent;height:0;width:0;font-size:1px;line-height:1px;max-height:0;max-width:0;overflow:hidden;mso-hide:all;">{preheader}</span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:{_CARD};border:1px solid {_BORDER};border-radius:16px;overflow:hidden;">
        <tr><td style="padding:28px 32px 8px 32px;">
          <table role="presentation" cellpadding="0" cellspacing="0">
            <tr>
              <td style="vertical-align:middle;padding-right:10px;">
                <div style="width:36px;height:36px;border-radius:9px;background:linear-gradient(135deg,{_ACCENT},#7A4BFA);display:inline-block;text-align:center;line-height:36px;color:#fff;font-weight:700;font-size:15px;">₽</div>
              </td>
              <td style="vertical-align:middle;">
                <div style="font-weight:600;font-size:15px;letter-spacing:.2px;color:{_TEXT};">{_BRAND}</div>
                <div style="font-size:12px;color:{_MUTED};">Бюджет в стиле приложения</div>
              </td>
            </tr>
          </table>
        </td></tr>
        <tr><td style="padding:8px 32px 32px 32px;">
          {body_html}
        </td></tr>
      </table>
      <div style="max-width:560px;margin:14px auto 0;color:{_MUTED};font-size:11px;text-align:center;line-height:1.5;">
        © {year} {_BRAND}. Это автоматическое письмо, отвечать на него не нужно.<br>
        Если вы не запрашивали действие — просто проигнорируйте письмо.
      </div>
    </td></tr>
  </table>
</body>
</html>"""


def _button(href: str, label: str) -> str:
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:18px 0 6px;">'
        f'  <tr><td bgcolor="{_ACCENT}" style="border-radius:10px;">'
        f'    <a href="{href}" target="_blank" style="display:inline-block;padding:12px 22px;'
        f'           font-size:14px;font-weight:600;color:#ffffff;text-decoration:none;'
        f'           border-radius:10px;">{label}</a>'
        f'  </td></tr>'
        f'</table>'
    )


def _link_fallback(href: str) -> str:
    return (
        f'<div style="margin-top:14px;font-size:12px;color:{_MUTED};line-height:1.6;">'
        f'Если кнопка не открывается, перейдите по ссылке вручную:<br>'
        f'<a href="{href}" target="_blank" style="color:{_ACCENT};word-break:break-all;">{href}</a>'
        f'</div>'
    )


# ---------- конкретные письма ----------

def verify_email(*, display_name: str, verify_url: str) -> tuple[str, str, str]:
    """Возвращает (subject, html, text)."""
    subject = "Подтверждение email — FinanceMac"
    safe_name = display_name or "Привет"
    body = f"""
      <h1 style="margin:18px 0 6px;font-size:22px;font-weight:600;color:{_TEXT};">Подтвердите email</h1>
      <p style="margin:0 0 6px;font-size:14px;line-height:1.55;color:{_TEXT};">
        Здравствуйте, {safe_name}! Чтобы активировать аккаунт, подтвердите этот адрес.
      </p>
      {_button(verify_url, "Подтвердить email")}
      <p style="margin:8px 0 0;font-size:12px;color:{_MUTED};">Ссылка действует 48 часов.</p>
      {_link_fallback(verify_url)}
    """
    html = _layout(preheader="Подтвердите email, чтобы активировать аккаунт FinanceMac.", body_html=body)
    text = (
        f"Здравствуйте, {safe_name}!\n\n"
        f"Подтвердите email, перейдя по ссылке (действует 48 часов):\n{verify_url}\n\n"
        f"Если вы не регистрировались — проигнорируйте письмо."
    )
    return subject, html, text


def welcome_email(*, display_name: str, app_url: str) -> tuple[str, str, str]:
    subject = "Добро пожаловать в FinanceMac"
    safe_name = display_name or "друг"
    body = f"""
      <h1 style="margin:18px 0 6px;font-size:22px;font-weight:600;color:{_TEXT};">Привет, {safe_name}!</h1>
      <p style="margin:0 0 8px;font-size:14px;line-height:1.55;color:{_TEXT};">
        Аккаунт создан. Можно подключаться из приложения и начинать вести бюджет —
        категории, лимиты, операции и общий обзор синхронизируются между устройствами.
      </p>
      {_button(app_url, "Открыть FinanceMac")}
      <ul style="margin:14px 0 0;padding-left:18px;font-size:13px;color:{_TEXT};line-height:1.7;">
        <li>Создайте группы и категории с лимитами на месяц.</li>
        <li>Заносите операции — вручную или импортом.</li>
        <li>Пригласите второго пользователя в свой workspace.</li>
      </ul>
    """
    html = _layout(preheader="Аккаунт создан. Подключитесь из приложения и начинайте.", body_html=body)
    text = (
        f"Привет, {safe_name}!\n\n"
        f"Аккаунт FinanceMac создан. Подключайтесь: {app_url}"
    )
    return subject, html, text


def workspace_invite(*, inviter_name: str, workspace_name: str, accept_url: str) -> tuple[str, str, str]:
    subject = f"{inviter_name} приглашает вас в «{workspace_name}»"
    body = f"""
      <h1 style="margin:18px 0 6px;font-size:22px;font-weight:600;color:{_TEXT};">Вас пригласили</h1>
      <p style="margin:0 0 8px;font-size:14px;line-height:1.55;color:{_TEXT};">
        <b>{inviter_name}</b> приглашает вас в рабочее пространство
        <b>«{workspace_name}»</b> в FinanceMac.
      </p>
      {_button(accept_url, "Принять приглашение")}
      {_link_fallback(accept_url)}
    """
    html = _layout(preheader=f"{inviter_name} пригласил вас в «{workspace_name}».", body_html=body)
    text = (
        f"{inviter_name} приглашает вас в workspace «{workspace_name}».\n"
        f"Принять: {accept_url}"
    )
    return subject, html, text
