"""
Module sensor fusion cho AuraBeam HIL Simulation.

Lõi của module là bộ lọc Kalman 3D với state:
    [x, y, z, vx, vy, vz]

Thiết kế mới ưu tiên:
- X, Y đến từ AI camera nên nhiễu cao.
- Z đến từ pseudo-radar nên tin cậy hơn, nhiễu thấp hơn rõ rệt.
- Khi AI mất box, hệ thống vẫn tiếp tục cập nhật bằng Z_radar và mô hình vật lý,
  nhờ đó quỹ đạo X, Y không bị đứt gãy ngay lập tức.
"""

from __future__ import annotations

import numpy as np


class KalmanFilter2D:
    """
    Bộ lọc Kalman 2D cho baseline chỉ làm mượt tọa độ ảnh.

    State:
        [x, y, vx, vy]
    """

    def __init__(self, dt: float = 1.0) -> None:
        self.dt = float(dt)
        self.x = np.zeros((4, 1), dtype=np.float64)

        self.F = np.array(
            [
                [1.0, 0.0, self.dt, 0.0],
                [0.0, 1.0, 0.0, self.dt],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

        self.P = np.diag([250.0, 250.0, 120.0, 120.0]).astype(np.float64)
        self.Q = np.diag([0.08, 0.08, 0.03, 0.03]).astype(np.float64)
        self.R = np.diag([30.0, 30.0]).astype(np.float64)
        self.H = np.array(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
            ],
            dtype=np.float64,
        )
        self.identity = np.eye(4, dtype=np.float64)

    def initialize(self, x: float, y: float) -> None:
        self.x[0, 0] = float(x)
        self.x[1, 0] = float(y)

    def predict(self) -> tuple[float, float]:
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        return self.get_state()

    def update(
        self,
        meas_x: float | None,
        meas_y: float | None,
        predict_first: bool = True,
    ) -> tuple[float, float]:
        if predict_first:
            self.predict()

        if meas_x is None or meas_y is None:
            return self.get_state()

        measurement = np.array([[meas_x], [meas_y]], dtype=np.float64)
        innovation = measurement - np.dot(self.H, self.x)
        innovation_covariance = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        kalman_gain = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(innovation_covariance))

        self.x = self.x + np.dot(kalman_gain, innovation)
        self.P = np.dot(self.identity - np.dot(kalman_gain, self.H), self.P)
        return self.get_state()

    def get_state(self) -> tuple[float, float]:
        return float(self.x[0, 0]), float(self.x[1, 0])


class KalmanFilter3D:
    """
    Bộ lọc Kalman 3D cho trạng thái vị trí - vận tốc.
    """

    def __init__(self, dt: float = 1.0) -> None:
        """
        Khởi tạo bộ lọc Kalman.

        Args:
            dt (float): Chu kỳ lấy mẫu giữa hai frame liên tiếp.
        """
        self.dt = float(dt)
        self.x = np.zeros((6, 1), dtype=np.float64)

        # F - Ma trận chuyển trạng thái:
        # Mô hình chuyển động thẳng đều trong không gian 3D.
        # x(k+1) = x(k) + vx * dt
        # y(k+1) = y(k) + vy * dt
        # z(k+1) = z(k) + vz * dt
        # vận tốc được giữ theo quán tính nếu chưa có lực/đo mới tác động.
        self.F = np.array(
            [
                [1.0, 0.0, 0.0, self.dt, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0, self.dt, 0.0],
                [0.0, 0.0, 1.0, 0.0, 0.0, self.dt],
                [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

        # P - Ma trận hiệp phương sai sai số trạng thái:
        # Khởi tạo cao vì ban đầu chưa biết chính xác cả vị trí lẫn vận tốc.
        self.P = np.diag([250.0, 250.0, 40.0, 120.0, 120.0, 25.0]).astype(np.float64)

        # Q - Ma trận nhiễu hệ thống:
        # Đặt thấp để giữ quán tính mạnh, giúp state không bị giật theo nhiễu ảnh.
        self.Q = np.diag([0.08, 0.08, 0.03, 0.03, 0.03, 0.02]).astype(np.float64)

        # R_full - Nhiễu đo lường khi có đủ AI + Radar:
        # X, Y nhiễu cao vì bounding box camera rung.
        # Z_radar nhiễu thấp vì radar ổn định hơn ảnh.
        self.R_full = np.diag([30.0, 30.0, 0.5]).astype(np.float64)

        # H_full - Ma trận quan sát khi có đủ X, Y từ AI và Z từ radar.
        self.H_full = np.array(
            [
                [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            ],
            dtype=np.float64,
        )

        # R_z_only - Nhiễu đo lường khi AI mất box, chỉ còn radar Z.
        self.R_z_only = np.array([[0.5]], dtype=np.float64)

        # H_z_only - Chỉ đo trục Z, còn X/Y tiếp tục đi theo mô hình vật lý F.
        self.H_z_only = np.array([[0.0, 0.0, 1.0, 0.0, 0.0, 0.0]], dtype=np.float64)

        self.identity = np.eye(6, dtype=np.float64)

    def initialize(self, x: float, y: float, z: float) -> None:
        """
        Khởi tạo state ban đầu khi vừa bắt được mục tiêu lần đầu.
        """
        self.x[0, 0] = float(x)
        self.x[1, 0] = float(y)
        self.x[2, 0] = float(z)

    def predict(self) -> tuple[float, float, float]:
        """
        Dự đoán trạng thái kế tiếp theo mô hình vật lý.
        """
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        return self.get_state()

    def update(
        self,
        meas_x: float | None,
        meas_y: float | None,
        meas_z_radar: float,
        predict_first: bool = True,
    ) -> tuple[float, float, float]:
        """
        Cập nhật bộ lọc bằng AI + Radar hoặc chỉ Radar.

        Trường hợp 1:
        - Nếu AI còn box, dùng cả X, Y từ camera và Z từ radar.

        Trường hợp 2:
        - Nếu AI mất box, chỉ dùng Z_radar để hiệu chỉnh chiều sâu.
        - X, Y sẽ tiếp tục được duy trì bởi mô hình động học F,
          đây chính là cơ chế điền khuyết quỹ đạo ngắn hạn.
        """
        if predict_first:
            self.predict()

        if meas_x is not None and meas_y is not None:
            measurement = np.array([[meas_x], [meas_y], [meas_z_radar]], dtype=np.float64)
            return self._apply_measurement(
                measurement=measurement,
                H=self.H_full,
                R=self.R_full,
            )

        measurement = np.array([[meas_z_radar]], dtype=np.float64)
        return self._apply_measurement(
            measurement=measurement,
            H=self.H_z_only,
            R=self.R_z_only,
        )

    def _apply_measurement(
        self,
        measurement: np.ndarray,
        H: np.ndarray,
        R: np.ndarray,
    ) -> tuple[float, float, float]:
        """
        Áp dụng một phép đo bất kỳ vào state hiện tại.

        Hàm này dùng chung cho hai chế độ:
        - Đo đầy đủ [x, y, z]
        - Đo riêng [z]
        """
        innovation = measurement - np.dot(H, self.x)
        innovation_covariance = np.dot(np.dot(H, self.P), H.T) + R
        kalman_gain = np.dot(np.dot(self.P, H.T), np.linalg.inv(innovation_covariance))

        self.x = self.x + np.dot(kalman_gain, innovation)
        self.P = np.dot(self.identity - np.dot(kalman_gain, H), self.P)
        return self.get_state()

    def get_state(self) -> tuple[float, float, float]:
        """
        Trả về vị trí đã được làm mượt.
        """
        return float(self.x[0, 0]), float(self.x[1, 0]), float(self.x[2, 0])
