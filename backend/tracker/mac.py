import Quartz
from .base import BaseTracker

class MacTracker(BaseTracker):
    def __init__(self):
        self._check_permissions()

    def _check_permissions(self) -> bool:
        try:
            # TODO: Move this permission bootstrap logic out to the application packaging/installation step.
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

    def get_active_window(self) -> tuple[str, str] | None:
        try:
            # Query Quartz directly for the onscreen window list in Z-order (front-to-back)
            options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
            window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
            
            if not window_list:
                return None
                
            for window in window_list:
                # kCGWindowLayer == 0 is the layer for normal application windows
                # We ignore menu bars (layer 24), background items, and dropdowns
                layer = window.get(Quartz.kCGWindowLayer, 0)
                if layer == 0:
                    # Size heuristic: We check if the window width & height is larger than 100px.
                    # This is necessary because macOS apps often create tiny, invisible helper windows
                    # (like autocomplete boxes, background workers, 1x1 overlays) that we must ignore.
                    bounds = window.get(Quartz.kCGWindowBounds, {})
                    if bounds.get('Height', 0) > 100 and bounds.get('Width', 0) > 100:
                        app_name = window.get(Quartz.kCGWindowOwnerName, "")
                        window_title = window.get(Quartz.kCGWindowName, "")
                        
                        # Filter out system UI elements that might report as layer 0
                        if app_name in ["Window Server", "Dock", "Finder"] and not window_title:
                            continue
                            
                        return app_name, window_title
            
            return None
        except Exception as e:
            # Silent fallback to prevent driver crashes
            return None
