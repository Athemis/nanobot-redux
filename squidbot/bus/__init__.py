"""Message bus module for decoupled channel-agent communication."""

from squidbot.bus.events import InboundMessage, OutboundMessage
from squidbot.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
