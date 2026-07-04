"""Haar cascade face/eye detection and lightweight parameter search."""
from __future__ import annotations

from dataclasses import replace
from time import perf_counter
from typing import Dict, Iterable, List, Tuple

import cv2
import numpy as np

from .config import DetectorConfig
from .preprocess import to_gray

Box = Tuple[int, int, int, int]


class HaarFaceEyeDetector:
    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()
        self.face_cascade = cv2.CascadeClassifier(str(self.config.face_cascade_path))
        self.eye_cascade = cv2.CascadeClassifier(str(self.config.eye_cascade_path))
        if self.face_cascade.empty():
            raise FileNotFoundError(f"Cannot load face cascade: {self.config.face_cascade_path}")
        if self.eye_cascade.empty():
            raise FileNotFoundError(f"Cannot load eye cascade: {self.config.eye_cascade_path}")

    def detect(self, image: np.ndarray) -> Dict[str, object]:
        gray = to_gray(image)
        started = perf_counter()
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=self.config.scale_factor,
            minNeighbors=self.config.min_neighbors,
            minSize=self.config.min_size,
        )
        face_boxes: List[Box] = [tuple(map(int, face)) for face in faces]
        eye_boxes: List[Box] = []
        for x, y, w, h in face_boxes:
            # Eyes are expected in the upper 65% of a frontal face.
            roi = gray[y : y + int(h * 0.65), x : x + w]
            eyes = self.eye_cascade.detectMultiScale(
                roi,
                scaleFactor=self.config.eye_scale_factor,
                minNeighbors=self.config.eye_min_neighbors,
                minSize=self.config.eye_min_size,
            )
            candidates = [tuple(map(int, eye)) for eye in eyes]
            candidates.sort(key=lambda b: b[2] * b[3], reverse=True)
            for ex, ey, ew, eh in candidates[:2]:
                eye_boxes.append((x + ex, y + ey, ew, eh))
        elapsed_ms = (perf_counter() - started) * 1000.0
        return {"faces": face_boxes, "eyes": eye_boxes, "elapsed_ms": elapsed_ms}

    def detect_variants(self, variants: Dict[str, np.ndarray]) -> Dict[str, Dict[str, object]]:
        return {name: self.detect(image) for name, image in variants.items()}


def search_parameters(
    variants: Dict[str, np.ndarray], candidates: Iterable[DetectorConfig] | None = None
) -> Tuple[DetectorConfig, List[Dict[str, object]]]:
    """Choose stable parameters without ground truth using count consistency and eyes."""
    candidates = list(candidates or default_parameter_candidates())
    trials: List[Dict[str, object]] = []
    for cfg in candidates:
        outputs = HaarFaceEyeDetector(cfg).detect_variants(variants)
        face_counts = np.array([len(v["faces"]) for v in outputs.values()], dtype=float)
        eye_counts = np.array([len(v["eyes"]) for v in outputs.values()], dtype=float)
        nonzero_ratio = float(np.mean(face_counts > 0))
        stability = 1.0 / (1.0 + float(np.std(face_counts)))
        plausible_eyes = float(np.mean(np.minimum(eye_counts, 2 * face_counts)))
        mean_ms = float(np.mean([v["elapsed_ms"] for v in outputs.values()]))
        # Proxy score: reward detection across variants and plausible eye evidence;
        # mildly penalize unstable counts and slower settings.
        score = 3.0 * nonzero_ratio + 2.0 * stability + 0.3 * plausible_eyes - 0.001 * mean_ms
        trials.append(
            {
                "scale_factor": cfg.scale_factor,
                "min_neighbors": cfg.min_neighbors,
                "min_size": list(cfg.min_size),
                "score": round(score, 6),
                "nonzero_ratio": round(nonzero_ratio, 6),
                "stability": round(stability, 6),
                "mean_ms": round(mean_ms, 3),
            }
        )
    best_index = max(range(len(trials)), key=lambda i: trials[i]["score"])
    return candidates[best_index], trials


def default_parameter_candidates() -> List[DetectorConfig]:
    base = DetectorConfig()
    return [
        replace(base, scale_factor=1.05, min_neighbors=4, min_size=(30, 30)),
        replace(base, scale_factor=1.08, min_neighbors=5, min_size=(35, 35)),
        replace(base, scale_factor=1.10, min_neighbors=5, min_size=(40, 40)),
        replace(base, scale_factor=1.15, min_neighbors=4, min_size=(40, 40)),
        replace(base, scale_factor=1.20, min_neighbors=6, min_size=(50, 50)),
    ]
