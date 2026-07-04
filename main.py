"""Command-line entry point for single-image and batch face detection."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.config import DetectorConfig, PreprocessConfig
from src.detector import HaarFaceEyeDetector, search_parameters
from src.evaluator import build_records, save_metrics
from src.image_io import iter_images, read_image, save_image
from src.preprocess import build_variants
from src.visualizer import save_detection_set


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Face preprocessing and Haar face/eye detection system")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="single image path")
    source.add_argument("--batch", type=Path, help="folder containing images")
    parser.add_argument("--output", type=Path, default=Path("results/detection"))
    parser.add_argument("--scale-factor", type=float, default=1.10)
    parser.add_argument("--min-neighbors", type=int, default=5)
    parser.add_argument("--min-size", type=int, nargs=2, metavar=("W", "H"), default=(40, 40))
    parser.add_argument("--target-size", type=int, nargs=2, metavar=("W", "H"), default=(640, 480))
    parser.add_argument("--gamma", type=float, default=1.5)
    parser.add_argument("--optimize", action="store_true", help="search a small predefined parameter grid per image")
    return parser.parse_args()


def run(args: argparse.Namespace) -> int:
    paths = [args.input] if args.input else iter_images(args.batch)
    if not paths:
        print(f"No supported images found in: {args.batch}", file=sys.stderr)
        return 2

    detection_dir = args.output
    results_root = detection_dir.parent
    comparison_dir = results_root / "comparison"
    metrics_dir = results_root / "metrics"
    processed_dir = Path("data/processed")
    for directory in (detection_dir, comparison_dir, metrics_dir, processed_dir):
        directory.mkdir(parents=True, exist_ok=True)

    preprocess_cfg = PreprocessConfig(target_size=tuple(args.target_size), gamma=args.gamma)
    detector_cfg = DetectorConfig(
        scale_factor=args.scale_factor,
        min_neighbors=args.min_neighbors,
        min_size=tuple(args.min_size),
    )
    all_records, searches = [], {}
    for path in paths:
        image = read_image(path)
        variants = build_variants(image, preprocess_cfg)
        save_image(processed_dir / f"{path.stem}_clahe.jpg", variants["clahe"])
        active_cfg = detector_cfg
        if args.optimize:
            active_cfg, trials = search_parameters(variants)
            searches[path.name] = {"selected": _public_config(active_cfg), "trials": trials}
        detections = HaarFaceEyeDetector(active_cfg).detect_variants(variants)
        save_detection_set(path.stem, variants, detections, detection_dir, comparison_dir)
        records = build_records(path.name, detections)
        all_records.extend(records)
        best = max(records, key=lambda row: (row["face_count"] > 0, row["eye_count"], -row["elapsed_ms"]))
        print(
            f"[OK] {path.name}: best={best['method']}, faces={best['face_count']}, "
            f"eyes={best['eye_count']}, time={best['elapsed_ms']} ms"
        )

    stem = "batch_metrics" if args.batch else f"{paths[0].stem}_metrics"
    csv_path, json_path = save_metrics(
        all_records,
        metrics_dir,
        stem,
        extra={"parameter_search": searches, "images_processed": len(paths)},
    )
    print(f"Metrics: {csv_path} and {json_path}")
    return 0


def _public_config(config: DetectorConfig) -> dict:
    return {
        "scale_factor": config.scale_factor,
        "min_neighbors": config.min_neighbors,
        "min_size": list(config.min_size),
    }


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
