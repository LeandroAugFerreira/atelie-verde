import time


class Budget:
    def __init__(self, seconds=10, started_at=None):
        self.deadline = (started_at or time.monotonic()) + min(30, max(0.05, seconds))

    def remaining(self):
        return max(0, self.deadline - time.monotonic())
