import threading
from pynput import keyboard, mouse

class InputTracker:
    # used the constructor to initialize variables 
    def __init__(self):
        self.keystroke_count = 0
        self.mouse_click_count = 0
        self.lock = threading.Lock()
        
        self.keyboard_listener = None
        self.mouse_listener = None

    def start(self):
        # Callback for keypresses - only increment count, discard key data (Privacy Rule #1)
        def on_press(key):
            with self.lock:
                self.keystroke_count += 1

        # Callback for mouse clicks - only increment count, discard coordinates (Privacy Rule #1)
        def on_click(x, y, button, pressed):
            if pressed:
                with self.lock:
                    self.mouse_click_count += 1

        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.mouse_listener = mouse.Listener(on_click=on_click)

        self.keyboard_listener.start()
        self.mouse_listener.start()

    def stop(self):
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()

    def get_and_reset_counts(self) -> tuple[int, int]:
        with self.lock:
            counts = (self.keystroke_count, self.mouse_click_count)
            self.keystroke_count = 0
            self.mouse_click_count = 0
            return counts
