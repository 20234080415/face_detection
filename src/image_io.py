"""Unicode-safe image loading, saving and batch discovery."""
from __future__ import annotations

from pathlib import Path
from typing import List

import cv2
import numpy as np

from .config import SUPPORTED_EXTENSIONS


def read_image(path: str | Path, flags: int = cv2.IMREAD_COLOR) -> np.ndarray:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Image does not exist: {path}")
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, flags)
    if image is None:
        raise ValueError(f"OpenCV cannot decode image: {path}")
    return image


def save_image(path: str | Path, image: np.ndarray, quality: int = 95) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower() or ".jpg"
    if not path.suffix:
        path = path.with_suffix(suffix)
    params = [cv2.IMWRITE_JPEG_QUALITY, quality] if suffix in {".jpg", ".jpeg"} else []
    ok, encoded = cv2.imencode(suffix, image, params)
    if not ok:
        raise ValueError(f"OpenCV cannot encode image as {suffix}")
    encoded.tofile(str(path))
    return path


def iter_images(folder: str | Path) -> List[Path]:
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"Batch directory does not exist: {folder}")
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)


def show_image(title: str, image: np.ndarray, wait_ms: int = 0) -> None:
    cv2.imshow(title, image)
    cv2.waitKey(wait_ms)
    cv2.destroyAllWindows()
