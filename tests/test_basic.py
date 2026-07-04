from pathlib import Path
import subprocess
import sys

import numpy as np

from src.config import DetectorConfig, PreprocessConfig
from src.detector import HaarFaceEyeDetector
from src.evaluator import build_records, save_metrics, stability_summary
from src.image_io import read_image, save_image
from src.preprocess import (
    build_variants,
    convolve2d,
    gamma_correct,
    generate_gaussian_kernel,
    histogram_equalize,
    median_filter,
    to_gray,
)
from src.visualizer import draw_detections, make_comparison


def test_preprocessing_shapes_and_ranges():
    image = np.full((120, 80, 3), 40, dtype=np.uint8)
    variants = build_variants(image, PreprocessConfig(target_size=(160, 120)))
    assert set(variants) == {
        "original", "gray", "hist_eq", "clahe", "gaussian_clahe", "median_clahe", "gamma_clahe"
    }
    assert all(value.shape[:2] == (120, 160) for value in variants.values())
    assert gamma_correct(image, 2.0).mean() > image.mean()


def test_manual_preprocessing_algorithms():
    color = np.array([[[10, 20, 30], [30, 40, 50]]], dtype=np.uint8)
    expected = np.rint(0.114 * color[..., 0] + 0.587 * color[..., 1] + 0.299 * color[..., 2]).astype(np.uint8)
    assert np.array_equal(to_gray(color), expected)

    gradient = np.arange(256, dtype=np.uint8).reshape(16, 16)
    assert np.array_equal(histogram_equalize(gradient), gradient)

    kernel = generate_gaussian_kernel(5)
    assert kernel.shape == (5, 5)
    assert np.isclose(kernel.sum(), 1.0)
    assert convolve2d(np.full((8, 8), 77, dtype=np.uint8), kernel).mean() == 77

    impulse = np.full((7, 7), 100, dtype=np.uint8)
    impulse[3, 3] = 255
    assert median_filter(impulse, 3)[3, 3] == 100


def test_gui_module_imports():
    import gui_app

    assert hasattr(gui_app, "FaceDetectionWindow")


def test_unicode_image_io(tmp_path):
    path = tmp_path / "测试图像.png"
    image = np.zeros((20, 30, 3), dtype=np.uint8)
    save_image(path, image)
    loaded = read_image(path)
    assert loaded.shape == image.shape


def test_detector_and_visualizer_smoke():
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    result = HaarFaceEyeDetector(DetectorConfig(min_size=(20, 20))).detect(image)
    assert {"faces", "eyes", "elapsed_ms"} <= result.keys()
    overlay = draw_detections(image, result["faces"], result["eyes"], "smoke")
    comparison = make_comparison([image, overlay], columns=2, panel_size=(160, 120))
    assert comparison.shape == (120, 320, 3)


def test_metrics_export(tmp_path):
    detections = {"gray": {"faces": [], "eyes": [], "elapsed_ms": 1.2345}}
    records = build_records("demo.jpg", detections)
    csv_path, json_path = save_metrics(records, tmp_path)
    assert csv_path.exists() and json_path.exists()
    assert stability_summary(records)["agreement_ratio"] == 1.0


def test_main_help_starts():
    project_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "main.py", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0
    assert "--input" in completed.stdout and "--batch" in completed.stdout
