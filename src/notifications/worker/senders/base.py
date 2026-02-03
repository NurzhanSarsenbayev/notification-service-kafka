from __future__ import annotations
from abc import ABC, abstractmethod


class BaseSender(ABC):
    """Abstract notification sender interface."""

    @abstractmethod
    async def send(self, *, to: str, subject: str, body: str) -> None:
        """Send a message to a specific user."""
        raise NotImplementedError
