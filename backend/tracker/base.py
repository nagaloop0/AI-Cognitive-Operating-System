from abc import ABC, abstractmethod
from typing import Optional, Tuple

class BaseTracker(ABC):
    @abstractmethod
    def get_active_window(self) -> Optional[Tuple[str, str]]:
        """
        Returns a tuple of (app_name, window_title) for the currently active/frontmost window.
        Returns None if no active window can be detected.
        """
        pass
