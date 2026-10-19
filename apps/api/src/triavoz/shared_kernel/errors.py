"""Domain-level errors. Interfaces translate them to HTTP; the domain never imports HTTP."""


class DomainError(Exception):
    code = "domain_error"


class NotFound(DomainError):
    """Also used for 'exists but belongs to someone else' — we never reveal existence."""

    code = "not_found"


class SlotTaken(DomainError):
    code = "slot_taken"


class SlotUnavailable(DomainError):
    """The requested time is not a free slot (outside hours, past, or not offered)."""

    code = "slot_unavailable"


class InvalidRequest(DomainError):
    code = "invalid_request"


class AuthenticationError(DomainError):
    """Use one generic code for bad credentials; do not reveal which factor failed."""

    code = "invalid_credentials"


class TooManyAttempts(DomainError):
    code = "too_many_attempts"


class Forbidden(DomainError):
    code = "forbidden"


class Conflict(DomainError):
    code = "conflict"


class ServiceUnavailable(DomainError):
    code = "service_unavailable"
