from enum import Enum


class OutreachStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SENT = "SENT"

