"""Public failure categories with stable machine-readable codes."""


class ETLError(ValueError):
    code = "ETL_ERROR"


class SourceError(ETLError):
    code = "SOURCE_INVALID"


class ApprovalError(ETLError):
    code = "APPROVAL_INVALID"


class LoadConflict(ETLError):
    code = "ORDER_CONFLICT"


class InjectedFailure(ETLError):
    code = "INJECTED_FAILURE"


class StorageError(ETLError):
    code = "STORAGE_ERROR"
