"""图像预处理模块：核心灰度、均衡化和滤波算法采用 NumPy 自主实现。"""
from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Tuple

import cv2
import numpy as np

from .config import PreprocessConfig


def to_gray(image: np.ndarray) -> np.ndarray:
    """按 ITU-R BT.601 权重将 BGR 图像手工转换为灰度图。"""
    if image.ndim == 2:
        return image.copy()
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError("image must be a grayscale or BGR image")
    # OpenCV 图像通道顺序为 B、G、R，因此显式拆分后按亮度公式计算。
    b, g, r = image[..., 0], image[..., 1], image[..., 2]
    gray = 0.114 * b.astype(np.float32) + 0.587 * g.astype(np.float32) + 0.299 * r.astype(np.float32)
    return np.clip(np.rint(gray), 0, 255).astype(np.uint8)


def histogram_equalize(image: np.ndarray) -> np.ndarray:
    """手工统计直方图、计算 CDF，并完成灰度映射。"""
    gray = to_gray(image)
    histogram = np.bincount(gray.ravel(), minlength=256)
    cdf = histogram.cumsum()
    nonzero = np.flatnonzero(cdf)
    if nonzero.size == 0:
        return gray.copy()
    cdf_min = cdf[nonzero[0]]
    denominator = gray.size - cdf_min
    if denominator <= 0:
        return gray.copy()
    mapping = np.clip(np.rint((cdf - cdf_min) * 255.0 / denominator), 0, 255).astype(np.uint8)
    return mapping[gray]


def clahe_equalize(
    image: np.ndarray, clip_limit: float = 2.0, grid_size: Tuple[int, int] = (8, 8)
) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
    return clahe.apply(to_gray(image))


def gaussian_filter(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """自主生成高斯核，并调用自写二维卷积完成去噪。"""
    _validate_odd_kernel(kernel_size)
    kernel = generate_gaussian_kernel(kernel_size)
    return convolve2d(image, kernel)


def median_filter(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """对每个邻域窗口排序取中值，实现椒盐噪声抑制。"""
    _validate_odd_kernel(kernel_size)
    pad = kernel_size // 2
    padded = np.pad(image, ((pad, pad), (pad, pad)) if image.ndim == 2 else ((pad, pad), (pad, pad), (0, 0)), mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, (kernel_size, kernel_size), axis=(0, 1))
    # 对两个窗口维度取中值；彩色图像保留通道维度。
    result = np.median(windows, axis=(-2, -1))
    return np.clip(result, 0, 255).astype(image.dtype)


def gamma_correct(image: np.ndarray, gamma: float = 1.5) -> np.ndarray:
    """手工构造 256 项 Gamma 查找表并按像素索引映射。"""
    if gamma <= 0:
        raise ValueError("gamma must be positive")
    # gamma > 1 brightens dark images in this lookup-table definition.
    table = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)], dtype=np.uint8)
    return table[image]


def generate_gaussian_kernel(kernel_size: int = 5, sigma: float | None = None) -> np.ndarray:
    """根据二维高斯函数自主生成归一化卷积核。"""
    _validate_odd_kernel(kernel_size)
    if sigma is None:
        sigma = 0.3 * ((kernel_size - 1) * 0.5 - 1) + 0.8
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    radius = kernel_size // 2
    coordinates = np.arange(-radius, radius + 1, dtype=np.float64)
    xx, yy = np.meshgrid(coordinates, coordinates)
    kernel = np.exp(-(xx * xx + yy * yy) / (2.0 * sigma * sigma))
    return kernel / kernel.sum()


def convolve2d(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """使用边缘复制填充和滑动窗口实现二维卷积，支持灰度与彩色图。"""
    if kernel.ndim != 2 or kernel.shape[0] != kernel.shape[1] or kernel.shape[0] % 2 == 0:
        raise ValueError("kernel must be a square matrix with odd size")
    pad = kernel.shape[0] // 2
    pad_width = ((pad, pad), (pad, pad)) if image.ndim == 2 else ((pad, pad), (pad, pad), (0, 0))
    padded = np.pad(image.astype(np.float64), pad_width, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, kernel.shape, axis=(0, 1))
    result = np.sum(windows * kernel, axis=(-2, -1))
    return np.clip(np.rint(result), 0, 255).astype(image.dtype)


def normalize_size(
    image: np.ndarray, target_size: Tuple[int, int] = (640, 480), pad_value: int = 0
) -> np.ndarray:
    """Resize with preserved aspect ratio and pad to an exact (width, height)."""
    target_w, target_h = target_size
    if target_w <= 0 or target_h <= 0:
        raise ValueError("target_size values must be positive")
    h, w = image.shape[:2]
    scale = min(target_w / w, target_h / h)
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    resized = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
    if image.ndim == 2:
        canvas = np.full((target_h, target_w), pad_value, dtype=image.dtype)
    else:
        canvas = np.full((target_h, target_w, image.shape[2]), pad_value, dtype=image.dtype)
    x, y = (target_w - new_w) // 2, (target_h - new_h) // 2
    canvas[y : y + new_h, x : x + new_w] = resized
    return canvas


def build_variants(image: np.ndarray, config: PreprocessConfig | None = None) -> Dict[str, np.ndarray]:
    """Build controlled variants used for detection and ablation comparison."""
    cfg = config or PreprocessConfig()
    normalized = normalize_size(image, cfg.target_size)
    gray = to_gray(normalized)
    gamma = gamma_correct(gray, cfg.gamma)
    return OrderedDict(
        original=normalized,
        gray=gray,
        hist_eq=histogram_equalize(gray),
        clahe=clahe_equalize(gray, cfg.clahe_clip_limit, cfg.clahe_grid_size),
        gaussian_clahe=clahe_equalize(
            gaussian_filter(gray, cfg.gaussian_kernel), cfg.clahe_clip_limit, cfg.clahe_grid_size
        ),
        median_clahe=clahe_equalize(
            median_filter(gray, cfg.median_kernel), cfg.clahe_clip_limit, cfg.clahe_grid_size
        ),
        gamma_clahe=clahe_equalize(gamma, cfg.clahe_clip_limit, cfg.clahe_grid_size),
    )


def _validate_odd_kernel(kernel_size: int) -> None:
    if kernel_size <= 1 or kernel_size % 2 == 0:
        raise ValueError("kernel_size must be an odd integer greater than 1")
