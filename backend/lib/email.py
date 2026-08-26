from __future__ import annotations

import re
from pathlib import Path

import structlog

from litestar_email import ConsoleBackend, EmailMessage, SMTPBackend
from litestar_email.config import SMTPConfig

from config import settings

logger = structlog.get_logger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"

HTML_TAG_PATTERN = re.compile(r"<[^<]+?>")


def _render_template(template_name: str, **context: str) -> str:
    path = TEMPLATES_DIR / f"{template_name}.html"
    html = path.read_text(encoding="utf-8")
    for key, val in context.items():
        html = html.replace(f"{{{{ {key} }}}}", val)
    return html


def render_footer() -> str:
    path = TEMPLATES_DIR / "_footer.html"
    html = path.read_text(encoding="utf-8")
    return html.replace("{{ frontend_url }}", settings.frontend_url)


def _html_to_text(html: str) -> str:
    """Convert an HTML email body to a readable plain-text version.

    Strips tags, decodes common HTML entities, and collapses whitespace so the
    `text/plain` MIME part is clean instead of raw HTML.
    """
    text = HTML_TAG_PATTERN.sub("", html)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def send_email(to: str, subject: str, template_name: str, **context: str) -> None:
    html_body = _render_template(template_name, **context)
    footer = render_footer()
    if "{{ footer }}" in html_body:
        html_body = html_body.replace("{{ footer }}", footer, 1)
    elif "</body>" in html_body:
        html_body = html_body.replace("</body>", footer + "</body>", 1)
    else:
        html_body = html_body + footer
    message = EmailMessage(
        subject=subject,
        body=_html_to_text(html_body),
        to=[to],
        from_email=settings.from_email,
    )
    message.alternatives.append((html_body, "text/html"))

    if settings.smtp_host:


        backend = SMTPBackend(
            config=SMTPConfig(
                host=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=settings.smtp_use_tls,
                use_ssl=settings.smtp_use_ssl,
            )
        )
    else:
        backend = ConsoleBackend()

    sent = await backend.send_messages([message])
    if sent != 1:
        raise Exception("failed to send email")
    logger.info("email sent", to=to, subject=subject, template=template_name)
