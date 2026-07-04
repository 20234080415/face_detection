"""Metric aggregation and JSON/CSV persistence for unlabelled experiments."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np


def build_records(image_name: str, detections: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
    records = []
    for method, result in detections.items():
        records.append(
            {
                "image": image_name,
                "method": method,
                "face_count": len(result["faces"]),
                "eye_count": len(result["eyes"]),
                "elapsed_ms": round(float(result["elapsed_ms"]), 3),
            }
        )
    return records


def stability_summary(records: Iterable[Dict[str, object]]) -> Dict[str, object]:
    rows = list(records)
    counts = [int(row["face_count"]) for row in rows]
    if not counts:
        return {"mode_face_count": 0, "agreement_ratio": 0.0, "face_count_std": 0.0}
    mode_count, frequency = Counter(counts).most_common(1)[0]
    return {
        "mode_face_count": mode_count,
        "agreement_ratio": round(frequency / len(counts), 6),
        "face_count_std": round(float(np.std(counts)), 6),
        "note": "Without labels, agreement only measures consistency; it is not detection accuracy.",
    }


def save_metrics(
    records: List[Dict[str, object]], output_dir: str | Path, stem: str = "metrics", extra: Dict | None = None
) -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    csv_path, json_path = output / f"{stem}.csv", output / f"{stem}.json"
    fields = ["image", "method", "face_count", "eye_count", "elapsed_ms"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    payload = {"records": records, "stability": stability_summary(records)}
    if extra:
        payload.update(extra)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path

