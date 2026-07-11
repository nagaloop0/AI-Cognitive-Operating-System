from abc import ABC, abstractmethod

class BaseTracker(ABC):
    @abstractmethod
    def get_active_window(self) -> tuple[str, str] | None:
        """
        Returns a tuple of (app_name, window_title) for the currently active/frontmost window.
        Returns None if no active window can be detected.
        """
        pass
