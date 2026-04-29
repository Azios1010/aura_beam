from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_core_package_exists() -> None:
    assert (PROJECT_ROOT / "src" / "aura_beam" / "__init__.py").exists()


def test_runtime_and_evaluation_scripts_exist() -> None:
    assert (PROJECT_ROOT / "scripts" / "runtime" / "main.py").exists()
    assert (PROJECT_ROOT / "scripts" / "evaluation" / "evaluate_metrics.py").exists()
    assert (PROJECT_ROOT / "scripts" / "evaluation" / "run_experiment_suite.py").exists()
    assert (PROJECT_ROOT / "scripts" / "evaluation" / "aggregate_results.py").exists()


def test_firmware_location_exists() -> None:
    assert (PROJECT_ROOT / "firmware" / "arduino_8x8_matrix.ino").exists()


def test_sensor_fusion_contains_2d_kalman() -> None:
    sensor_fusion_path = PROJECT_ROOT / "src" / "aura_beam" / "sensor_fusion.py"
    assert "class KalmanFilter2D" in sensor_fusion_path.read_text(encoding="utf-8")


def test_experiment_suite_config_exists() -> None:
    assert (PROJECT_ROOT / "configs" / "experiment_suite.json").exists()
