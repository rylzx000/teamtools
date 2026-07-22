from __future__ import annotations


class FpaError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400, stage: str = "validation"):
        super().__init__(message)
        self.status_code = status_code
        self.stage = stage
