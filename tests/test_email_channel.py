import ssl
from datetime import date
from email.message import EmailMessage
from typing import Callable

import pytest

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.email import EmailChannel
from nanobot.config.schema import EmailConfig


class _FakeSMTPClient:
    def __init__(
        self,
        _host: str,
        _port: int,
        timeout: int = 30,
        context: ssl.SSLContext | None = None,
        on_init: Callable[[], None] | None = None,
    ) -> None:
        self.timeout = timeout
        self.context = context
        self.started_tls = False
        self.starttls_context: ssl.SSLContext | None = None
        self.logged_in = False
        self.sent_messages: list[EmailMessage] = []
        if on_init:
            on_init()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self, context=None):
        self.started_tls = True
        self.starttls_context = context

    def login(self, _user: str, _pw: str):
        self.logged_in = True

    def send_message(self, msg: EmailMessage):
        self.sent_messages.append(msg)


def _make_config() -> EmailConfig:
    return EmailConfig(
        enabled=True,
        consent_granted=True,
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="bot@example.com",
        imap_password="secret",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="bot@example.com",
        smtp_password="secret",
        mark_seen=True,
    )


def _make_raw_email(
    from_addr: str = "alice@example.com",
    subject: str = "Hello",
    body: str = "This is the body.",
) -> bytes:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = "bot@example.com"
    msg["Subject"] = subject
    msg["Message-ID"] = "<m1@example.com>"
    msg.set_content(body)
    return msg.as_bytes()


def test_fetch_new_messages_parses_unseen_and_marks_seen(monkeypatch) -> None:
    raw = _make_raw_email(subject="Invoice", body="Please pay")

    class FakeIMAP:
        def __init__(self) -> None:
            self.store_calls: list[tuple[bytes, str, str]] = []

        def login(self, _user: str, _pw: str):
            return "OK", [b"logged in"]

        def select(self, _mailbox: str):
            return "OK", [b"1"]

        def search(self, *_args):
            return "OK", [b"1"]

        def fetch(self, _imap_id: bytes, _parts: str):
            return "OK", [(b"1 (UID 123 BODY[] {200})", raw), b")"]

        def store(self, imap_id: bytes, op: str, flags: str):
            self.store_calls.append((imap_id, op, flags))
            return "OK", [b""]

        def logout(self):
            return "BYE", [b""]

    fake = FakeIMAP()
    captured: dict[str, ssl.SSLContext | None] = {"ssl_context": None}

    def _imap_factory(_host: str, _port: int, ssl_context: ssl.SSLContext | None = None):
        captured["ssl_context"] = ssl_context
        return fake

    monkeypatch.setattr("nanobot.channels.email.imaplib.IMAP4_SSL", _imap_factory)

    channel = EmailChannel(_make_config(), MessageBus())
    items = channel._fetch_new_messages()

    assert len(items) == 1
    assert items[0]["sender"] == "alice@example.com"
    assert items[0]["subject"] == "Invoice"
    assert "Please pay" in items[0]["content"]
    assert fake.store_calls == [(b"1", "+FLAGS", "\\Seen")]
    assert captured["ssl_context"] is not None
    assert captured["ssl_context"].verify_mode == ssl.CERT_REQUIRED
    assert captured["ssl_context"].check_hostname is True

    # Same UID should be deduped in-process.
    items_again = channel._fetch_new_messages()
    assert items_again == []


def test_extract_text_body_falls_back_to_html() -> None:
    msg = EmailMessage()
    msg["From"] = "alice@example.com"
    msg["To"] = "bot@example.com"
    msg["Subject"] = "HTML only"
    msg.add_alternative("<p>Hello<br>world</p>", subtype="html")

    text = EmailChannel._extract_text_body(msg)
    assert "Hello" in text
    assert "world" in text


@pytest.mark.asyncio
async def test_start_returns_immediately_without_consent(monkeypatch) -> None:
    cfg = _make_config()
    cfg.consent_granted = False
    channel = EmailChannel(cfg, MessageBus())

    called = {"fetch": False}

    def _fake_fetch():
        called["fetch"] = True
        return []

    monkeypatch.setattr(channel, "_fetch_new_messages", _fake_fetch)
    await channel.start()
    assert channel.is_running is False
    assert called["fetch"] is False


@pytest.mark.asyncio
async def test_send_uses_smtp_and_reply_subject(monkeypatch) -> None:
    fake_instances: list[_FakeSMTPClient] = []

    def _smtp_factory(host: str, port: int, timeout: int = 30):
        instance = _FakeSMTPClient(host, port, timeout=timeout)
        fake_instances.append(instance)
        return instance

    monkeypatch.setattr("nanobot.channels.email.smtplib.SMTP", _smtp_factory)

    channel = EmailChannel(_make_config(), MessageBus())
    channel._last_subject_by_chat["alice@example.com"] = "Invoice #42"
    channel._last_message_id_by_chat["alice@example.com"] = "<m1@example.com>"

    await channel.send(
        OutboundMessage(
            channel="email",
            chat_id="alice@example.com",
            content="Acknowledged.",
        )
    )

    assert len(fake_instances) == 1
    smtp = fake_instances[0]
    assert smtp.started_tls is True
    assert smtp.starttls_context is not None
    assert smtp.starttls_context.verify_mode == ssl.CERT_REQUIRED
    assert smtp.starttls_context.check_hostname is True
    assert smtp.logged_in is True
    assert len(smtp.sent_messages) == 1
    sent = smtp.sent_messages[0]
    assert sent["Subject"] == "Re: Invoice #42"
    assert sent["To"] == "alice@example.com"
    assert sent["In-Reply-To"] == "<m1@example.com>"


@pytest.mark.asyncio
async def test_send_skips_when_auto_reply_disabled(monkeypatch) -> None:
    fake_instances: list[_FakeSMTPClient] = []

    def _smtp_factory(host: str, port: int, timeout: int = 30):
        instance = _FakeSMTPClient(host, port, timeout=timeout)
        fake_instances.append(instance)
        return instance

    monkeypatch.setattr("nanobot.channels.email.smtplib.SMTP", _smtp_factory)

    cfg = _make_config()
    cfg.auto_reply_enabled = False
    channel = EmailChannel(cfg, MessageBus())
    await channel.send(
        OutboundMessage(
            channel="email",
            chat_id="alice@example.com",
            content="Should not send.",
        )
    )
    assert fake_instances == []

    await channel.send(
        OutboundMessage(
            channel="email",
            chat_id="alice@example.com",
            content="Force send.",
            metadata={"force_send": True},
        )
    )
    assert len(fake_instances) == 1
    assert len(fake_instances[0].sent_messages) == 1


@pytest.mark.asyncio
async def test_send_skips_when_consent_not_granted(monkeypatch) -> None:
    fake_instances: list[_FakeSMTPClient] = []

    def _smtp_factory(host: str, port: int, timeout: int = 30):
        instance = _FakeSMTPClient(host, port, timeout=timeout)
        fake_instances.append(instance)
        return instance

    monkeypatch.setattr("nanobot.channels.email.smtplib.SMTP", _smtp_factory)

    cfg = _make_config()
    cfg.consent_granted = False
    channel = EmailChannel(cfg, MessageBus())
    await channel.send(
        OutboundMessage(
            channel="email",
            chat_id="alice@example.com",
            content="Should not send.",
            metadata={"force_send": True},
        )
    )
    assert fake_instances == []


def test_validate_config_rejects_plaintext_smtp() -> None:
    cfg = _make_config()
    cfg.smtp_use_ssl = False
    cfg.smtp_use_tls = False

    channel = EmailChannel(cfg, MessageBus())
    assert channel._validate_config() is False


@pytest.mark.asyncio
async def test_send_skips_when_smtp_tls_and_ssl_disabled(monkeypatch) -> None:
    fake_instances: list[_FakeSMTPClient] = []

    def _smtp_factory(host: str, port: int, timeout: int = 30):
        instance = _FakeSMTPClient(host, port, timeout=timeout)
        fake_instances.append(instance)
        return instance

    monkeypatch.setattr("nanobot.channels.email.smtplib.SMTP", _smtp_factory)

    cfg = _make_config()
    cfg.smtp_use_ssl = False
    cfg.smtp_use_tls = False
    channel = EmailChannel(cfg, MessageBus())
    await channel.send(
        OutboundMessage(
            channel="email",
            chat_id="alice@example.com",
            content="Should not send over plaintext SMTP.",
            metadata={"force_send": True},
        )
    )

    assert fake_instances == []


def test_fetch_messages_between_dates_uses_imap_since_before_without_mark_seen(monkeypatch) -> None:
    raw = _make_raw_email(subject="Status", body="Yesterday update")

    class FakeIMAP:
        def __init__(self) -> None:
            self.search_args = None
            self.store_calls: list[tuple[bytes, str, str]] = []

        def login(self, _user: str, _pw: str):
            return "OK", [b"logged in"]

        def select(self, _mailbox: str):
            return "OK", [b"1"]

        def search(self, *_args):
            self.search_args = _args
            return "OK", [b"5"]

        def fetch(self, _imap_id: bytes, _parts: str):
            return "OK", [(b"5 (UID 999 BODY[] {200})", raw), b")"]

        def store(self, imap_id: bytes, op: str, flags: str):
            self.store_calls.append((imap_id, op, flags))
            return "OK", [b""]

        def logout(self):
            return "BYE", [b""]

    fake = FakeIMAP()
    captured: dict[str, ssl.SSLContext | None] = {"ssl_context": None}

    def _imap_factory(_host: str, _port: int, ssl_context: ssl.SSLContext | None = None):
        captured["ssl_context"] = ssl_context
        return fake

    monkeypatch.setattr("nanobot.channels.email.imaplib.IMAP4_SSL", _imap_factory)

    channel = EmailChannel(_make_config(), MessageBus())
    items = channel.fetch_messages_between_dates(
        start_date=date(2026, 2, 6),
        end_date=date(2026, 2, 7),
        limit=10,
    )

    assert len(items) == 1
    assert items[0]["subject"] == "Status"
    # search(None, "SINCE", "06-Feb-2026", "BEFORE", "07-Feb-2026")
    assert fake.search_args is not None
    assert fake.search_args[1:] == ("SINCE", "06-Feb-2026", "BEFORE", "07-Feb-2026")
    assert fake.store_calls == []
    assert captured["ssl_context"] is not None
    assert captured["ssl_context"].verify_mode == ssl.CERT_REQUIRED
    assert captured["ssl_context"].check_hostname is True


@pytest.mark.asyncio
async def test_send_uses_smtp_ssl_with_verified_context_by_default(monkeypatch) -> None:
    fake_instances: list[_FakeSMTPClient] = []

    def _smtp_ssl_factory(
        host: str,
        port: int,
        timeout: int = 30,
        context: ssl.SSLContext | None = None,
    ):
        instance = _FakeSMTPClient(host, port, timeout=timeout, context=context)
        fake_instances.append(instance)
        return instance

    monkeypatch.setattr("nanobot.channels.email.smtplib.SMTP_SSL", _smtp_ssl_factory)

    cfg = _make_config()
    cfg.smtp_use_ssl = True
    cfg.smtp_use_tls = False
    channel = EmailChannel(cfg, MessageBus())
    await channel.send(
        OutboundMessage(
            channel="email",
            chat_id="alice@example.com",
            content="Secure SMTP SSL test.",
        )
    )

    assert len(fake_instances) == 1
    smtp = fake_instances[0]
    assert smtp.context is not None
    assert smtp.context.verify_mode == ssl.CERT_REQUIRED
    assert smtp.context.check_hostname is True
    assert smtp.logged_in is True
    assert len(smtp.sent_messages) == 1


def test_tls_verify_false_uses_unverified_context_and_logs_once(monkeypatch) -> None:
    warnings: list[str] = []

    def _warn(msg: str, *args):
        if args:
            warnings.append(msg.format(*args))
        else:
            warnings.append(msg)

    monkeypatch.setattr("nanobot.channels.email.logger.warning", _warn)

    cfg = _make_config()
    cfg.tls_verify = False
    channel = EmailChannel(cfg, MessageBus())

    context_one = channel._tls_context()
    context_two = channel._tls_context()

    assert context_one.verify_mode == ssl.CERT_NONE
    assert context_one.check_hostname is False
    assert context_two.verify_mode == ssl.CERT_NONE
    assert context_two.check_hostname is False
    assert len(warnings) == 1
    assert "tlsverify=false" in warnings[0].lower()
