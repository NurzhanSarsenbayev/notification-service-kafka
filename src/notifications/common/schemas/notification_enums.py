try:
    from enum import StrEnum  # Python 3.11+
except ImportError:  # Python 3.10
    from strenum import StrEnum


class NotificationStatus(StrEnum):
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    EXPIRED = "EXPIRED"


class NotificationChannel(StrEnum):
    EMAIL = "email"
    PUSH = "push"
    WS = "ws"
    SMS = "sms"  # reserved


class NotificationPriority(StrEnum):
    NORMAL = "normal"
    HIGH = "high"
