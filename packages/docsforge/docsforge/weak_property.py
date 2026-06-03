"""weak_property descriptor - same as read-only property but allows overwriting."""

from __future__ import annotations


class weak_property:
    """Same as a read-only property, but allows overwriting the field for good."""

    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self.func(instance)
