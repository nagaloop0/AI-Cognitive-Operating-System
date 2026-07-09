import Quartz
from AppKit import NSWorkspace
from typing import Optional, Tuple
from .base import BaseTracker

class MacTracker(BaseTracker):
    def __init__(self):
        self._check_permissions()

    def _check_permissions(self) -> bool:
        try:
            # Preflight check. If not authorized, request permission (triggers macOS prompt)
            if not Quartz.CGPreflightScreenCaptureAccess():
                print("\n[WARNING] macOS Screen Recording Permission is missing!")
                print("Attempting to request permission...")
                Quartz.CGRequestScreenCaptureAccess()
                return False
            return True
        except AttributeError:
            # Fallback for older macOS versions that don't support preflight checks
            return True

    def get_active_window(self) -> Optional[Tuple[str, str]]:
        try:
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.frontmostApplication()
            if not active_app:
                return None
            
            app_name = active_app.localizedName() or ""
            pid = active_app.processIdentifier()
            
            # Query Quartz for the window name
            options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
            window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
            
            window_title = ""
            if window_list:
                for window in window_list:
                    # Filter by PID of frontmost application
                    if window.get(Quartz.kCGWindowOwnerPID) == pid:
                        # kCGWindowLayer == 0 represents normal application windows
                        if window.get(Quartz.kCGWindowLayer, 0) == 0:
                            # Fallback if kCGWindowName is missing (due to permissions)
                            window_title = window.get(Quartz.kCGWindowName, "")
                            # If we find a valid window name, we take it
                            if window_title:
                                break
                            
            # If we successfully got the app name, but window title is empty and permission is missing, alert
            if not window_title and not Quartz.CGPreflightScreenCaptureAccess():
                # Return empty string but warn in console
                pass

            return app_name, window_title
        except Exception as e:
            # Silent fallback to prevent daemon crashes
            return None
