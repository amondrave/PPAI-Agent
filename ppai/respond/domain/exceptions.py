class RespondError(Exception):
    pass


class InvalidTransitionError(RespondError):
    pass


class UnauthorizedCallbackError(RespondError):
    pass
