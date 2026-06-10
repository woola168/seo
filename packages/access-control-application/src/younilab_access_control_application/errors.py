class AccessControlError(Exception):
    pass


class InvalidCredentials(AccessControlError):
    pass


class InvalidSession(AccessControlError):
    pass


class AccountUnavailable(AccessControlError):
    pass


class ResourceNotFound(AccessControlError):
    pass


class Conflict(AccessControlError):
    pass
