class ServiceError(Exception):
    """Base for errors services raise; the API layer maps them to HTTP statuses."""


class NotFoundError(ServiceError):
    pass


class InvalidError(ServiceError):
    pass
