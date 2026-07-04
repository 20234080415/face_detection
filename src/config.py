"""Central configuration objects for preprocessing and Haar detection."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

import cv2


@dataclass(frozen=True)
class PreprocessConfig:
    target_size: Tuple[int, int] = (640, 480)
    gaussian_kernel: int = 5
    median_kernel: int = 5
    clahe_clip_limit: float = 2.0
    clahe_grid_size: Tuple[int, int] = (8, 8)
    gamma: float = 1.5


@dataclass(frozen=True)
class DetectorConfig:
    scale_factor: float = 1.1
    min_neighbors: int = 5
    min_size: Tuple[int, int] = (40, 40)
    eye_scale_factor: float = 1.1
    eye_min_neighbors: int = 5
    eye_min_size: Tuple[int, int] = (12, 12)
    face_cascade_path: Path = field(
        default_factory=lambda: Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    )
    eye_cascade_path: Path = field(
        default_factory=lambda: Path(cv2.data.haarcascades) / "haarcascade_eye_tree_eyeglasses.xml"
    )


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

