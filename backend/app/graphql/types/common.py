from enum import Enum

import strawberry


@strawberry.enum
class OperationErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    JOB_CLOSED = "JOB_CLOSED"
    INVALID_FILE = "INVALID_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@strawberry.type
class OperationError:
    code: OperationErrorCode
    message: str
    field: str | None = None


def operation_error(
    code: OperationErrorCode,
    message: str,
    field: str | None = None,
) -> OperationError:
    return OperationError(code=code, message=message, field=field)
