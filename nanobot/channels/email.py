"""Email channel implementation using IMAP polling + SMTP replies."""

import asyncio
import html
import imaplib
import re
import smtplib
import ssl
from datetime import date
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr
from typing import Any

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import EmailConfig


class EmailChannel(BaseChannel):
    """
    Email channel.

    Inbound:
    - Poll IMAP mailbox for unread messages.
    - Convert each message into an inbound event.

    Outbound:
    - Send responses via SMTP back to the sender address.
    """

    name = "email"
    _IMAP_MONTHS = (
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    )

    def __init__(self, config: EmailConfig, bus: MessageBus):
        """
        Initialize the email channel and prepare internal state used for IMAP polling and SMTP sending.

        Parameters:
            config (EmailConfig): Channel configuration including IMAP/SMTP settings and behavior flags.
            bus (MessageBus): Message bus used to dispatch inbound events and receive outbound messages.

        Details:
            Sets up per-chat state for tracking the last seen subject and message-id, a bounded set for deduplicating processed IMAP UIDs, and cached SSL contexts and flags used for TLS handling.
        """
        super().__init__(config, bus)
        self.config: EmailConfig = config
        self._last_subject_by_chat: dict[str, str] = {}
        self._last_message_id_by_chat: dict[str, str] = {}
        self._processed_uids: set[str] = set()  # Capped to prevent unbounded growth
        self._MAX_PROCESSED_UIDS = 100000
        self._logged_insecure_tls_warning = False
        self._verified_tls_context: ssl.SSLContext | None = None
        self._insecure_tls_context: ssl.SSLContext | None = None

    async def start(self) -> None:
        """
        Begin polling IMAP for inbound email and dispatch received messages to the channel's message handler until stopped.

        This method starts a polling loop that retrieves new messages, updates per-sender last-seen subject and message-id, and forwards each message to the channel's message handler. The loop runs until stop() clears the running flag, or startup checks (consent and configuration validation) prevent polling from starting.
        """
        if not self.config.consent_granted:
            logger.warning(
                "Email channel disabled: consent_granted is false. "
                "Set channels.email.consentGranted=true after explicit user permission."
            )
            return

        if not self._validate_config():
            return

        self._running = True
        logger.info("Starting Email channel (IMAP polling mode)...")

        poll_seconds = max(5, int(self.config.poll_interval_seconds))
        while self._running:
            try:
                inbound_items = await asyncio.to_thread(self._fetch_new_messages)
                for item in inbound_items:
                    sender = item["sender"]
                    subject = item.get("subject", "")
                    message_id = item.get("message_id", "")

                    if subject:
                        self._last_subject_by_chat[sender] = subject
                    if message_id:
                        self._last_message_id_by_chat[sender] = message_id

                    await self._handle_message(
                        sender_id=sender,
                        chat_id=sender,
                        content=item["content"],
                        metadata=item.get("metadata", {}),
                    )
            except Exception as e:
                logger.error(f"Email polling error: {e}")

            await asyncio.sleep(poll_seconds)

    async def stop(self) -> None:
        """Stop polling loop."""
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        """
        Send an outbound email message using the channel's SMTP configuration.

        This operation respects channel consent and auto-reply settings (unless metadata["force_send"] is truthy), validates that an SMTP host is configured and that the transport is secure, and constructs the email using the message's content and recipient. The outgoing message's subject is derived from the last known subject for the recipient unless overridden via metadata["subject"]. If a last message-id exists for the recipient, it is attached to the outgoing message using In-Reply-To and References headers. The function attempts to deliver the message via the configured SMTP transport and logs any delivery error before re-raising it.

        Parameters:
            msg (OutboundMessage): Outbound message where
                - chat_id is the recipient email address,
                - content is the message body,
                - metadata may include:
                    - "force_send" (bool): bypass auto-reply gating,
                    - "subject" (str): explicit subject override.
        """
        if not self.config.consent_granted:
            logger.warning("Skip email send: consent_granted is false")
            return

        force_send = bool((msg.metadata or {}).get("force_send"))
        if not self.config.auto_reply_enabled and not force_send:
            logger.info("Skip automatic email reply: auto_reply_enabled is false")
            return

        if not self.config.smtp_host:
            logger.warning("Email channel SMTP host not configured")
            return
        if not self._smtp_transport_secure():
            logger.error(
                "Skip email send: insecure SMTP transport config "
                "(smtp_use_ssl=false and smtp_use_tls=false)"
            )
            return

        to_addr = msg.chat_id.strip()
        if not to_addr:
            logger.warning("Email channel missing recipient address")
            return

        base_subject = self._last_subject_by_chat.get(to_addr, "nanobot reply")
        subject = self._reply_subject(base_subject)
        if msg.metadata and isinstance(msg.metadata.get("subject"), str):
            override = msg.metadata["subject"].strip()
            if override:
                subject = override

        email_msg = EmailMessage()
        email_msg["From"] = self.config.from_address or self.config.smtp_username or self.config.imap_username
        email_msg["To"] = to_addr
        email_msg["Subject"] = subject
        email_msg.set_content(msg.content or "")

        in_reply_to = self._last_message_id_by_chat.get(to_addr)
        if in_reply_to:
            email_msg["In-Reply-To"] = in_reply_to
            email_msg["References"] = in_reply_to

        try:
            await asyncio.to_thread(self._smtp_send, email_msg)
        except Exception as e:
            logger.error(f"Error sending email to {to_addr}: {e}")
            raise

    def _validate_config(self) -> bool:
        """
        Validate that required IMAP/SMTP credentials are present and that SMTP transport is configured securely.

        Logs an error and returns False if any required IMAP or SMTP credential is missing, or if neither SSL nor STARTTLS is enabled for SMTP.

        Returns:
            bool: `True` if all required configuration fields are present and SMTP transport is secure, `False` otherwise.
        """
        missing = []
        if not self.config.imap_host:
            missing.append("imap_host")
        if not self.config.imap_username:
            missing.append("imap_username")
        if not self.config.imap_password:
            missing.append("imap_password")
        if not self.config.smtp_host:
            missing.append("smtp_host")
        if not self.config.smtp_username:
            missing.append("smtp_username")
        if not self.config.smtp_password:
            missing.append("smtp_password")

        if missing:
            logger.error(f"Email channel not configured, missing: {', '.join(missing)}")
            return False
        if not self._smtp_transport_secure():
            logger.error(
                "Email channel SMTP transport is insecure: both smtp_use_ssl and smtp_use_tls are false. "
                "Refusing plaintext SMTP. Enable at least one of them."
            )
            return False
        return True

    def _smtp_transport_secure(self) -> bool:
        """
        Check whether SMTP will use an encrypted transport.

        Returns:
            True if SMTP is configured for implicit SSL (smtp_use_ssl) or STARTTLS (smtp_use_tls), False otherwise.
        """
        return bool(self.config.smtp_use_ssl or self.config.smtp_use_tls)

    def _tls_context(self) -> ssl.SSLContext:
        """
        Create and return an SSLContext configured according to the channel's TLS verification setting.

        If tls_verify is true, returns a cached default (verified) SSLContext. If tls_verify is false,
        emits a one-time warning about increased MITM risk and returns a cached permissive SSLContext
        with hostname checking and certificate verification disabled.

        Returns:
            ssl.SSLContext: An SSL/TLS context appropriate for the configured verification behavior.
        """
        if self.config.tls_verify:
            if self._verified_tls_context is None:
                self._verified_tls_context = ssl.create_default_context()
            return self._verified_tls_context

        if not self._logged_insecure_tls_warning:
            logger.warning(
                "Email TLS verification is disabled (channels.email.tlsVerify=false). "
                "This increases MITM risk and may expose email credentials/content."
            )
            self._logged_insecure_tls_warning = True

        if self._insecure_tls_context is None:
            self._insecure_tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            self._insecure_tls_context.check_hostname = False
            self._insecure_tls_context.verify_mode = ssl.CERT_NONE
        return self._insecure_tls_context

    def _smtp_send(self, msg: EmailMessage) -> None:
        """
        Send the provided EmailMessage using the channel's SMTP configuration and TLS settings.

        This uses SMTP over SSL when `smtp_use_ssl` is enabled; otherwise it connects via plain SMTP and upgrades with STARTTLS if `smtp_use_tls` is enabled. Credentials from the channel configuration are used to authenticate and the channel's TLS context is applied. The operation uses a 30-second socket timeout.

        Parameters:
            msg (EmailMessage): The email message to send.
        """
        timeout = 30
        tls_context = self._tls_context()
        if self.config.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                self.config.smtp_host,
                self.config.smtp_port,
                timeout=timeout,
                context=tls_context,
            ) as smtp:
                smtp.login(self.config.smtp_username, self.config.smtp_password)
                smtp.send_message(msg)
            return

        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=timeout) as smtp:
            if self.config.smtp_use_tls:
                smtp.starttls(context=tls_context)
            smtp.login(self.config.smtp_username, self.config.smtp_password)
            smtp.send_message(msg)

    def _fetch_new_messages(self) -> list[dict[str, Any]]:
        """Poll IMAP and return parsed unread messages."""
        return self._fetch_messages(
            search_criteria=("UNSEEN",),
            mark_seen=self.config.mark_seen,
            dedupe=True,
            limit=0,
        )

    def fetch_messages_between_dates(
        self,
        start_date: date,
        end_date: date,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Fetch messages in [start_date, end_date) by IMAP date search.

        This is used for historical summarization tasks (e.g. "yesterday").
        """
        if end_date <= start_date:
            return []

        return self._fetch_messages(
            search_criteria=(
                "SINCE",
                self._format_imap_date(start_date),
                "BEFORE",
                self._format_imap_date(end_date),
            ),
            mark_seen=False,
            dedupe=False,
            limit=max(1, int(limit)),
        )

    def _fetch_messages(
        self,
        search_criteria: tuple[str, ...],
        mark_seen: bool,
        dedupe: bool,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Fetch messages from the configured IMAP mailbox that match the provided search criteria.

        Parameters:
            search_criteria (tuple[str, ...]): IMAP search tokens (e.g., ("UNSEEN",) or ("SINCE", "01-Jan-2024")).
            mark_seen (bool): If True, mark fetched messages as Seen on the server.
            dedupe (bool): If True, skip messages whose UID is already present in the channel's processed-UID set.
            limit (int): If greater than 0, restrict results to the last `limit` message IDs; if 0 or less, do not limit.

        Returns:
            list[dict[str, Any]]: A list of parsed message dictionaries. Each dictionary contains:
                - "sender" (str): Sender email address (lowercased).
                - "subject" (str): Decoded Subject header (may be empty).
                - "message_id" (str): Message-ID header value (may be empty).
                - "content" (str): Human-readable content including header lines and the extracted body (truncated to config.max_body_chars).
                - "metadata" (dict): Additional fields: "message_id", "subject", "date", "sender_email", and "uid".
        """
        messages: list[dict[str, Any]] = []
        mailbox = self.config.imap_mailbox or "INBOX"

        if self.config.imap_use_ssl:
            client = imaplib.IMAP4_SSL(
                self.config.imap_host,
                self.config.imap_port,
                ssl_context=self._tls_context(),
            )
        else:
            client = imaplib.IMAP4(self.config.imap_host, self.config.imap_port)

        try:
            client.login(self.config.imap_username, self.config.imap_password)
            status, _ = client.select(mailbox)
            if status != "OK":
                return messages

            status, data = client.search(None, *search_criteria)
            if status != "OK" or not data:
                return messages

            ids = data[0].split()
            if limit > 0 and len(ids) > limit:
                ids = ids[-limit:]
            for imap_id in ids:
                status, fetched = client.fetch(imap_id, "(BODY.PEEK[] UID)")
                if status != "OK" or not fetched:
                    continue

                raw_bytes = self._extract_message_bytes(fetched)
                if raw_bytes is None:
                    continue

                uid = self._extract_uid(fetched)
                if dedupe and uid and uid in self._processed_uids:
                    continue

                parsed = BytesParser(policy=policy.default).parsebytes(raw_bytes)
                sender = parseaddr(parsed.get("From", ""))[1].strip().lower()
                if not sender:
                    continue

                subject = self._decode_header_value(parsed.get("Subject", ""))
                date_value = parsed.get("Date", "")
                message_id = parsed.get("Message-ID", "").strip()
                body = self._extract_text_body(parsed)

                if not body:
                    body = "(empty email body)"

                body = body[: self.config.max_body_chars]
                content = (
                    f"Email received.\n"
                    f"From: {sender}\n"
                    f"Subject: {subject}\n"
                    f"Date: {date_value}\n\n"
                    f"{body}"
                )

                metadata = {
                    "message_id": message_id,
                    "subject": subject,
                    "date": date_value,
                    "sender_email": sender,
                    "uid": uid,
                }
                messages.append(
                    {
                        "sender": sender,
                        "subject": subject,
                        "message_id": message_id,
                        "content": content,
                        "metadata": metadata,
                    }
                )

                if dedupe and uid:
                    self._processed_uids.add(uid)
                    # mark_seen is the primary dedup; this set is a safety net
                    if len(self._processed_uids) > self._MAX_PROCESSED_UIDS:
                        self._processed_uids.clear()

                if mark_seen:
                    client.store(imap_id, "+FLAGS", "\\Seen")
        finally:
            try:
                client.logout()
            except Exception:
                pass

        return messages

    @classmethod
    def _format_imap_date(cls, value: date) -> str:
        """Format date for IMAP search (always English month abbreviations)."""
        month = cls._IMAP_MONTHS[value.month - 1]
        return f"{value.day:02d}-{month}-{value.year}"

    @staticmethod
    def _extract_message_bytes(fetched: list[Any]) -> bytes | None:
        for item in fetched:
            if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], (bytes, bytearray)):
                return bytes(item[1])
        return None

    @staticmethod
    def _extract_uid(fetched: list[Any]) -> str:
        for item in fetched:
            if isinstance(item, tuple) and item and isinstance(item[0], (bytes, bytearray)):
                head = bytes(item[0]).decode("utf-8", errors="ignore")
                m = re.search(r"UID\s+(\d+)", head)
                if m:
                    return m.group(1)
        return ""

    @staticmethod
    def _decode_header_value(value: str) -> str:
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except Exception:
            return value

    @classmethod
    def _extract_text_body(cls, msg: Any) -> str:
        """Best-effort extraction of readable body text."""
        if msg.is_multipart():
            plain_parts: list[str] = []
            html_parts: list[str] = []
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    continue
                content_type = part.get_content_type()
                try:
                    payload = part.get_content()
                except Exception:
                    payload_bytes = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    payload = payload_bytes.decode(charset, errors="replace")
                if not isinstance(payload, str):
                    continue
                if content_type == "text/plain":
                    plain_parts.append(payload)
                elif content_type == "text/html":
                    html_parts.append(payload)
            if plain_parts:
                return "\n\n".join(plain_parts).strip()
            if html_parts:
                return cls._html_to_text("\n\n".join(html_parts)).strip()
            return ""

        try:
            payload = msg.get_content()
        except Exception:
            payload_bytes = msg.get_payload(decode=True) or b""
            charset = msg.get_content_charset() or "utf-8"
            payload = payload_bytes.decode(charset, errors="replace")
        if not isinstance(payload, str):
            return ""
        if msg.get_content_type() == "text/html":
            return cls._html_to_text(payload).strip()
        return payload.strip()

    @staticmethod
    def _html_to_text(raw_html: str) -> str:
        text = re.sub(r"<\s*br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
        text = re.sub(r"<\s*/\s*p\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        return html.unescape(text)

    def _reply_subject(self, base_subject: str) -> str:
        subject = (base_subject or "").strip() or "nanobot reply"
        prefix = self.config.subject_prefix or "Re: "
        if subject.lower().startswith("re:"):
            return subject
        return f"{prefix}{subject}"
