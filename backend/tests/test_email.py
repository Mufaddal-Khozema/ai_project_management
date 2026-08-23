import pytest

from lib import email as lib_email


@pytest.fixture
def frontend_url(monkeypatch):
    monkeypatch.setattr(lib_email.settings, "frontend_url", "https://coordinaai.test")
    return "https://coordinaai.test"


@pytest.fixture
def console_send(monkeypatch):
    """Force the ConsoleBackend path so the captured backend is used."""
    captured = {}
    monkeypatch.setattr(lib_email.settings, "smtp_host", "")
    monkeypatch.setattr(lib_email, "ConsoleBackend", lambda: _CapturedBackend(captured))
    return captured


def test_render_footer_contains_legal_links(frontend_url):
    html = lib_email.render_footer()
    assert f"{frontend_url}/terms" in html
    assert f"{frontend_url}/privacy" in html
    assert "{{ frontend_url }}" not in html


def test_render_footer_has_intro_line():
    html = lib_email.render_footer()
    assert "AI-powered project management" in html


async def test_send_email_uses_footer_placeholder(monkeypatch, console_send):
    body = "<html><body><table>{{ footer }}</table></body></html>"
    monkeypatch.setattr(lib_email, "_render_template", lambda name, **ctx: body)
    monkeypatch.setattr(lib_email, "render_footer", lambda: "<tr>FOOTER</tr>")
    await lib_email.send_email("a@b.com", "subj", "otp")
    assert "FOOTER" in console_send["html"]
    assert console_send["html"].count("FOOTER") == 1


async def test_send_email_injects_before_body_close(monkeypatch, console_send):
    body = "<html><body>CONTENT</body></html>"
    monkeypatch.setattr(lib_email, "_render_template", lambda name, **ctx: body)
    monkeypatch.setattr(lib_email, "render_footer", lambda: "FOOTER")
    await lib_email.send_email("a@b.com", "subj", "otp")
    assert console_send["html"] == "<html><body>CONTENTFOOTER</body></html>"


async def test_send_email_appends_when_no_marker(monkeypatch, console_send):
    body = "<html><body>CONTENT"
    monkeypatch.setattr(lib_email, "_render_template", lambda name, **ctx: body)
    monkeypatch.setattr(lib_email, "render_footer", lambda: "FOOTER")
    await lib_email.send_email("a@b.com", "subj", "otp")
    assert console_send["html"] == "<html><body>CONTENTFOOTER"


async def test_send_email_otp_template_renders_with_footer(frontend_url, console_send):
    await lib_email.send_email("a@b.com", "Your verification code", "otp", otp="123456", email="a@b.com")
    html = console_send["html"]
    assert "123456" in html
    assert f"{frontend_url}/terms" in html
    assert f"{frontend_url}/privacy" in html


def test_html_to_text_strips_tags_and_decodes_entities():
    html = "<p>Hello&nbsp;Ada &amp; Bob &lt;dev&gt;</p><br><strong>Team</strong>"
    text = lib_email._html_to_text(html)
    assert "<p>" not in text
    assert "<br>" not in text
    assert "<strong>" not in text
    assert "Hello Ada & Bob <dev>Team" in text


def test_html_to_text_collapses_whitespace():
    html = "<p>line1</p><p>line2</p>  <td> x </td>"
    text = lib_email._html_to_text(html)
    assert text == "line1line2 x"


async def test_send_email_body_is_plain_text_not_html(monkeypatch, console_send):
    html = "<html><body><p>Hello <strong>Ada</strong></p>{{ footer }}</body></html>"
    monkeypatch.setattr(lib_email, "_render_template", lambda name, **ctx: html)
    monkeypatch.setattr(lib_email, "render_footer", lambda: "<p>FOOTER</p>")
    await lib_email.send_email("a@b.com", "subj", "otp")
    body = console_send["message"].body
    assert "<" not in body
    assert "Hello Ada" in body
    assert "FOOTER" in body
    assert console_send["html"].startswith("<html>")


class _CapturedBackend:
    def __init__(self, store):
        self._store = store

    async def send_messages(self, messages):
        self._store["html"] = messages[0].alternatives[0][0]
        self._store["message"] = messages[0]
        return 1