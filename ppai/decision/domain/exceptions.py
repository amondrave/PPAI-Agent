class DecisionError(Exception):
    pass


class CycleConflictError(DecisionError):
    """Raised when a duplicate active cycle is detected."""
    pass


class TaskNotInTop3Error(DecisionError):
    """Raised when a callback references a task not in the current Top 3."""
    pass
