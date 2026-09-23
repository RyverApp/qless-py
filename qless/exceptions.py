"""Some exception classes"""


class QlessException(Exception):
    """Any and all qless exceptions"""


class LostLockException(QlessException):
    """Lost lock on a job"""
