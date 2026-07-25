import sys
from .base import BaseTracker

def get_tracker() -> BaseTracker:
    # todo : shld we remve this tracker ..?
    if sys.platform == "darwin":
        # TODO : Need to update here for the cross and move the to the config platform instead of hard coding here.
        from .mac import MacTracker
        return MacTracker()
    else:
        # Cross-platform fallback: Dummy Tracker so the driver runs without crashing on other OSes.
        # In a real setup, we would implement WindowsTracker/LinuxTracker classes here.
        class DummyTracker(BaseTracker):
            def get_active_window(self):
                return "UnsupportedOS", f"Platform {sys.platform} not supported yet"
        return DummyTracker()
