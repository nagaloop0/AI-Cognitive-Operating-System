import time
from backend.tracker import get_tracker

def test_active_window():
    tracker = get_tracker()
    print('getting tracker', tracker)
    print("Starting macOS Window Tracker verification (Ctrl+C to stop)...")
    print("Please switch applications to verify it catches title changes.")
    print("-" * 50)
    
    last_window = None
    try:
        # Run for 10 iterations (20 seconds) so it exits automatically during test
        for i in range(10):
            result = tracker.get_active_window()
            print('getting active window', result)
            if result:
                app_name, window_title = result
                current = (app_name, window_title)
                if current != last_window:
                    print(f"[SWITCH] App: {app_name} | Title: {window_title}")
                    last_window = current
            else:
                pass
            time.sleep(2)
        print("\nVerification completed.")
    except KeyboardInterrupt:
        print("\nVerification stopped by user.")

if __name__ == "__main__":
    test_active_window()
