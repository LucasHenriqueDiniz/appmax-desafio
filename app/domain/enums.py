from enum import StrEnum


class UserType(StrEnum):
    COMMON = "common"
    MERCHANT = "merchant"


class TransferStatus(StrEnum):
    # so existe registro de transferencia quando ela conclui (decisao documentada no README)
    COMPLETED = "completed"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
