class TaskTrackerError(Exception):
    pass


class TaskNotFoundError(TaskTrackerError):
    pass


class DuplicateTaskError(TaskTrackerError):
    pass


class InvalidPatchError(TaskTrackerError):
    pass
