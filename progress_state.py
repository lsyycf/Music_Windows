import threading

class ProgressState:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            self.total = 0
            self.current = 0
            self.desc = ""
            self.is_active = False

    def start(self, total, desc):
        with self.lock:
            self.total = total
            self.current = 0
            self.desc = desc
            self.is_active = True

    def update(self, delta=1):
        with self.lock:
            self.current += delta
            if self.current > self.total:
                self.current = self.total

    def set_current(self, current):
        with self.lock:
            self.current = current

    def finish(self):
        with self.lock:
            self.is_active = False

progress_manager = ProgressState()
