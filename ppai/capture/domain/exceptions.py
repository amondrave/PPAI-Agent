class CaptureError(Exception):
    pass


class InvalidInputError(CaptureError):
    pass


class DuplicateTaskError(CaptureError):
    pass


class TaskLimitReachedError(CaptureError):
    pass
