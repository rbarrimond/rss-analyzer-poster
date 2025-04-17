"""Context manager to prevent recursion in a thread-safe manner."""
import threading


class RecursionGuard:
    """Context manager to prevent recursion in a thread-safe manner."""

    def __init__(self, guard: threading.local):
        self.guard = guard

    def __enter__(self):
        if getattr(self.guard, "active", False):
            return False  # Recursion detected
        self.guard.active = True
        return True

    def __exit__(self, exc_type, exc_value, traceback):
        self.guard.active = False
