"""Detection overlays and comparison-panel composition."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

import cv2
import numpy as np

from .image_io import save_image


def to_bgr(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image.copy()


def draw_detections(
    image: np.ndarray, faces: Iterable[tuple], eyes: Iterable[tuple], label: str | None = None
) -> np.ndarray:
    canvas = to_bgr(image)
    for x, y, w, h in faces:
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (50, 220, 50), 2)
    for x, y, w, h in eyes:
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (30, 80, 255), 2)
    if label:
        cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 32), (20, 20, 20), -1)
        cv2.putText(canvas, label, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1, cv2.LINE_AA)
    return canvas


def make_comparison(panels: List[np.ndarray], columns: int = 3, panel_size=(420, 315)) -> np.ndarray:
    if not panels:
        raise ValueError("At least one panel is required")
    resized = [cv2.resize(to_bgr(p), panel_size, interpolation=cv2.INTER_AREA) for p in panels]
    blank = np.full_like(resized[0], 245)
    while len(resized) % columns:
        resized.append(blank.copy())
    rows = [cv2.hconcat(resized[i : i + columns]) for i in range(0, len(resized), columns)]
    return cv2.vconcat(rows)


def save_detection_set(
    stem: str,
    variants: Dict[str, np.ndarray],
    detections: Dict[str, Dict[str, object]],
    detection_dir: str | Path,
    comparison_dir: str | Path,
) -> tuple[List[Path], Path]:
    saved, panels = [], []
    for method, image in variants.items():
        result = detections[method]
        label = f"{method} | faces={len(result['faces'])} eyes={len(result['eyes'])} {result['elapsed_ms']:.1f}ms"
        drawn = draw_detections(image, result["faces"], result["eyes"], label)
        path = save_image(Path(detection_dir) / f"{stem}_{method}.jpg", drawn)
        saved.append(path)
        panels.append(drawn)
    comparison = make_comparison(panels)
    comparison_path = save_image(Path(comparison_dir) / f"{stem}_comparison.jpg", comparison)
    return saved, comparison_path
