"""
Module giao tiếp Serial giữa PC Python và Arduino.

Giao thức điều khiển:
    BOX:col_start:col_end:row_start:row_end\n

Module này chỉ gửi lệnh mới khi box thay đổi để tránh tràn bộ đệm Serial.
"""

from __future__ import annotations

import serial
from serial import SerialException


CLEAR_BOX_COMMAND = "BOX:-1:-1:-1:-1\n"


class SerialController:
    """
    Điều khiển kết nối Serial tới Arduino/MAX7219.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.1) -> None:
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout = float(timeout)
        self.ser: serial.Serial | None = None
        self.last_command: str | None = None

        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            print(f"[Serial] Connected to {self.port} @ {self.baudrate} baud.")
        except (SerialException, OSError) as exc:
            self.ser = None
            print(f"[Serial] Cannot open port {self.port}: {exc}")

    def send_command(self, box_string: str | None) -> bool:
        """
        Gửi lệnh BOX xuống Arduino.

        Args:
            box_string (str | None):
                - Chuỗi `BOX:col_start:col_end:row_start:row_end\n`
                - `None` để gửi lệnh clear toàn bộ vùng tối

        Returns:
            bool:
                - True nếu gửi thành công
                - False nếu lệnh trùng, Serial chưa mở, hoặc lỗi ghi dữ liệu
        """
        command = CLEAR_BOX_COMMAND if box_string is None else box_string

        if not command.endswith("\n"):
            command = f"{command}\n"

        if command == self.last_command:
            return False

        if self.ser is None or not self.ser.is_open:
            return False

        try:
            self.ser.write(command.encode("utf-8"))
            self.last_command = command
            return True
        except (SerialException, OSError) as exc:
            print(f"[Serial] Write failed on {self.port}: {exc}")
            return False

    def close(self) -> None:
        """
        Đóng cổng Serial an toàn.
        """
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
            print(f"[Serial] Closed port {self.port}.")
