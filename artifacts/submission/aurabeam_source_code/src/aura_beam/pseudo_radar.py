"""
Module cảm biến radar ảo cho mô phỏng HIL AuraBeam.

Radar ảo này tạo ra khoảng cách Z theo quy luật chuyển động thẳng đều:
    Z = initial_z - target_speed * time

Sau đó cộng thêm nhiễu trắng nhỏ để mô phỏng rung cảm biến thực tế.
"""

from __future__ import annotations

import numpy as np


class VirtualRadar:
    """
    Cảm biến radar ảo sinh dữ liệu khoảng cách theo từng frame.
    """

    def __init__(self, fps: float, initial_z: float = 100.0, target_speed: float = 15.0) -> None:
        """
        Khởi tạo radar ảo.

        Args:
            fps (float): Tốc độ khung hình của video.
            initial_z (float): Khoảng cách ban đầu từ xe ego tới mục tiêu, đơn vị mét.
            target_speed (float): Tốc độ tiến lại gần, đơn vị m/s.
        """
        if fps <= 0:
            raise ValueError("fps must be > 0")

        self.fps = float(fps)
        self.initial_z = float(initial_z)
        self.target_speed = float(target_speed)

    def get_distance(self, frame_id: int) -> float:
        """
        Tính khoảng cách mục tiêu tại một frame cụ thể.

        Công thức vật lý:
            Z = initial_z - (target_speed * frame_id / fps)

        Sau đó thêm nhiễu trắng nhỏ N(0, 0.2) để giả lập độ rung cảm biến.
        """
        elapsed_time = float(frame_id) / self.fps
        ideal_distance = self.initial_z - (self.target_speed * elapsed_time)
        noisy_distance = ideal_distance + np.random.normal(0.0, 0.2)

        # Chặn dưới để tránh khoảng cách âm khi video chạy quá lâu.
        return max(0.0, float(noisy_distance))
