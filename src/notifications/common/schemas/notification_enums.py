from enum import StrEnum


class NotificationStatus(StrEnum):
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
