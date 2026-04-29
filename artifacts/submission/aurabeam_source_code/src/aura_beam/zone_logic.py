"""
Module anh xa toa do camera sang luoi LED Matrix 8x8.
"""

from __future__ import annotations


class Matrix8x8Controller:
    """
    Dieu khien vung toi tren ma tran LED 8x8 bang chuoi lenh `BOX:...`.
    """

    def __init__(self, matrix_width: int = 8, matrix_height: int = 8) -> None:
        if matrix_width <= 0 or matrix_height <= 0:
            raise ValueError("matrix dimensions must be > 0")
        self.matrix_width = int(matrix_width)
        self.matrix_height = int(matrix_height)

    def get_dark_box(
        self,
        smooth_x: float,
        smooth_y: float,
        smooth_z: float,
        screen_width: int | float,
        screen_height: int | float,
    ) -> str | None:
        if screen_width <= 0 or screen_height <= 0:
            raise ValueError("screen_width and screen_height must be > 0")

        if smooth_z > 100.0:
            return None

        safe_x = self._clamp_float(float(smooth_x), 0.0, float(screen_width))
        safe_y = self._clamp_float(float(smooth_y), 0.0, float(screen_height))

        col_center = self._clamp(int((safe_x / float(screen_width)) * self.matrix_width), 0, self.matrix_width - 1)
        row_center = self._clamp(int((safe_y / float(screen_height)) * self.matrix_height), 0, self.matrix_height - 1)

        if smooth_z < 30.0:
            expand = 2
        elif smooth_z < 60.0:
            expand = 1
        else:
            expand = 0

        col_start = self._clamp(col_center - expand, 0, self.matrix_width - 1)
        col_end = self._clamp(col_center + expand, 0, self.matrix_width - 1)
        row_start = self._clamp(row_center - expand, 0, self.matrix_height - 1)
        row_end = self._clamp(row_center + expand, 0, self.matrix_height - 1)
        return f"BOX:{col_start}:{col_end}:{row_start}:{row_end}\n"

    @staticmethod
    def _clamp(value: int, minimum: int, maximum: int) -> int:
        return max(minimum, min(value, maximum))

    @staticmethod
    def _clamp_float(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(value, maximum))


class HoldTimeBoxScheduler:
    """
    Giu lenh BOX trong mot so frame de giam flicker khi target dao dong ngan han.
    """

    def __init__(self, hold_time_frames: int = 0) -> None:
        self.hold_time_frames = max(0, int(hold_time_frames))
        self.last_command: str | None = None
        self.last_command_frame: int | None = None

    def apply(self, command: str | None, frame_index: int) -> str | None:
        if command is not None:
            self.last_command = command
            self.last_command_frame = int(frame_index)
            return command

        if self.last_command is None or self.last_command_frame is None:
            return None

        if (int(frame_index) - self.last_command_frame) <= self.hold_time_frames:
            return self.last_command

        self.last_command = None
        self.last_command_frame = None
        return None
