"""Core package for the AuraBeam research prototype."""

from .detector_ensemble import EnsembleDetector
from .pseudo_radar import VirtualRadar
from .sensor_fusion import KalmanFilter2D
from .sensor_fusion import KalmanFilter3D
from .serial_manager import SerialController
from .zone_logic import HoldTimeBoxScheduler
from .zone_logic import Matrix8x8Controller

__all__ = [
    "EnsembleDetector",
    "VirtualRadar",
    "KalmanFilter2D",
    "KalmanFilter3D",
    "SerialController",
    "HoldTimeBoxScheduler",
    "Matrix8x8Controller",
]
