"""PyQt6 图形界面：仅负责交互与展示，算法统一调用 src 模块。"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QStatusBar, QVBoxLayout, QWidget,
)

from src.config import DetectorConfig, PreprocessConfig
from src.detector import HaarFaceEyeDetector
from src.evaluator import build_records, save_metrics
from src.image_io import iter_images, read_image, save_image
from src.preprocess import (
    clahe_equalize, gamma_correct, gaussian_filter, histogram_equalize,
    median_filter, normalize_size, to_gray,
)
from src.visualizer import draw_detections, make_comparison, to_bgr


class FaceDetectionWindow(QMainWindow):
    """课程设计系统主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("人脸图像预处理及人脸检测系统")
        self.resize(1380, 850)
        self.original: np.ndarray | None = None
        self.current: np.ndarray | None = None
        self.current_path: Path | None = None
        self.method = "未加载图像"
        self.face_count = 0
        self.eye_count = 0
        self.elapsed_ms = 0.0
        self.saved_path = "尚未保存"
        self._build_ui()
        self._apply_style()
        self._update_info()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        image_layout = QHBoxLayout()
        self.original_label = self._image_panel("原始图像")
        self.result_label = self._image_panel("处理 / 检测结果")
        image_layout.addWidget(self.original_label, 1)
        image_layout.addWidget(self.result_label, 1)
        outer.addLayout(image_layout, 5)

        controls = QHBoxLayout()
        controls.addWidget(self._button_group(), 4)
        controls.addWidget(self._parameter_group(), 1)
        outer.addLayout(controls, 2)

        self.info_label = QLabel()
        self.info_label.setObjectName("infoPanel")
        self.info_label.setWordWrap(True)
        outer.addWidget(self.info_label)
        self.setStatusBar(QStatusBar())

    def _image_panel(self, title: str) -> QLabel:
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(520, 400)
        label.setObjectName("imagePanel")
        label.setScaledContents(False)
        return label

    def _button_group(self) -> QGroupBox:
        box = QGroupBox("功能操作")
        grid = QGridLayout(box)
        actions = [
            ("打开图像", self.open_image), ("灰度化", lambda: self.apply_preprocess("灰度化", to_gray)),
            ("光照均衡", lambda: self.apply_preprocess("直方图均衡化", histogram_equalize)),
            ("CLAHE", lambda: self.apply_preprocess("CLAHE", clahe_equalize)),
            ("高斯去噪", lambda: self.apply_preprocess("高斯去噪", gaussian_filter)),
            ("中值去噪", lambda: self.apply_preprocess("中值去噪", median_filter)),
            ("Gamma 校正", self.apply_gamma), ("人脸检测", lambda: self.detect(include_eyes=False)),
            ("人眼检测", lambda: self.detect(include_eyes=True)), ("一键完整处理", self.full_process),
            ("保存结果", self.save_current), ("批量处理", self.batch_process),
        ]
        for index, (text, callback) in enumerate(actions):
            button = QPushButton(text)
            button.clicked.connect(callback)
            grid.addWidget(button, index // 4, index % 4)
        return box

    def _parameter_group(self) -> QGroupBox:
        box = QGroupBox("检测参数")
        form = QFormLayout(box)
        self.scale_spin = QDoubleSpinBox(); self.scale_spin.setRange(1.01, 1.50); self.scale_spin.setSingleStep(0.01); self.scale_spin.setValue(1.10)
        self.neighbor_spin = QSpinBox(); self.neighbor_spin.setRange(1, 20); self.neighbor_spin.setValue(5)
        self.min_size_spin = QSpinBox(); self.min_size_spin.setRange(20, 300); self.min_size_spin.setValue(40); self.min_size_spin.setSuffix(" px")
        self.gamma_spin = QDoubleSpinBox(); self.gamma_spin.setRange(0.10, 5.00); self.gamma_spin.setSingleStep(0.10); self.gamma_spin.setValue(1.50)
        for widget in (self.scale_spin, self.neighbor_spin, self.min_size_spin, self.gamma_spin):
            widget.valueChanged.connect(self._update_info)
        form.addRow("scaleFactor", self.scale_spin)
        form.addRow("minNeighbors", self.neighbor_spin)
        form.addRow("minSize", self.min_size_spin)
        form.addRow("Gamma", self.gamma_spin)
        return box

    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "打开人脸图像", str(Path("data/raw").resolve()), "图像 (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)")
        if not path:
            return
        try:
            self.current_path = Path(path)
            self.original = read_image(path)
            self.current = self.original.copy()
            self.method, self.face_count, self.eye_count = "原始图像", 0, 0
            self.elapsed_ms, self.saved_path = 0.0, "尚未保存"
            self._show(self.original_label, self.original)
            self._show(self.result_label, self.current)
            self._update_info()
        except Exception as exc:
            self._error(str(exc))

    def apply_preprocess(self, name: str, operation) -> None:
        if not self._require_image():
            return
        try:
            started = perf_counter()
            self.current = operation(self.original)
            self.elapsed_ms = (perf_counter() - started) * 1000
            self.method, self.face_count, self.eye_count = name, 0, 0
            self._show(self.result_label, self.current)
            self._update_info()
        except Exception as exc:
            self._error(str(exc))

    def apply_gamma(self) -> None:
        self.apply_preprocess(f"Gamma 校正 ({self.gamma_spin.value():.2f})", lambda image: gamma_correct(image, self.gamma_spin.value()))

    def detect(self, include_eyes: bool = True) -> None:
        if not self._require_image():
            return
        try:
            detector = HaarFaceEyeDetector(self._detector_config())
            source = self.current if self.current is not None else self.original
            result = detector.detect(source)
            eyes = result["eyes"] if include_eyes else []
            self.current = draw_detections(source, result["faces"], eyes)
            self.face_count, self.eye_count = len(result["faces"]), len(eyes)
            self.elapsed_ms = float(result["elapsed_ms"])
            self.method = "人脸与人眼检测" if include_eyes else "人脸检测"
            self._show(self.result_label, self.current)
            self._update_info()
        except Exception as exc:
            self._error(str(exc))

    def full_process(self) -> None:
        if not self._require_image():
            return
        try:
            started = perf_counter()
            normalized = normalize_size(self.original, (640, 480))
            enhanced = clahe_equalize(gaussian_filter(gamma_correct(to_gray(normalized), self.gamma_spin.value())))
            result = HaarFaceEyeDetector(self._detector_config()).detect(enhanced)
            self.current = draw_detections(enhanced, result["faces"], result["eyes"])
            self.face_count, self.eye_count = len(result["faces"]), len(result["eyes"])
            self.elapsed_ms = (perf_counter() - started) * 1000
            self.method = "Gamma + 高斯去噪 + CLAHE + 人脸/人眼检测"
            self._show(self.result_label, self.current)
            self._update_info()
        except Exception as exc:
            self._error(str(exc))

    def save_current(self) -> None:
        if self.current is None:
            self._error("请先打开并处理图像")
            return
        default = Path("results/detection") / f"{(self.current_path or Path('result')).stem}_gui.jpg"
        path, _ = QFileDialog.getSaveFileName(self, "保存结果", str(default.resolve()), "JPEG (*.jpg);;PNG (*.png)")
        if path:
            self.saved_path = str(save_image(path, self.current))
            self._save_gui_metrics(Path(path).stem)
            self._update_info()
            self.statusBar().showMessage(f"结果已保存：{self.saved_path}", 5000)

    def batch_process(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择批量图片文件夹", str(Path("data/raw").resolve()))
        if not folder:
            return
        try:
            records = []
            detector = HaarFaceEyeDetector(self._detector_config())
            paths = iter_images(folder)
            if not paths:
                raise ValueError("所选文件夹中没有支持的图片")
            for path in paths:
                original = read_image(path)
                processed = clahe_equalize(gaussian_filter(gamma_correct(to_gray(normalize_size(original)), self.gamma_spin.value())))
                result = detector.detect(processed)
                drawn = draw_detections(processed, result["faces"], result["eyes"])
                save_image(Path("results/detection") / f"{path.stem}_gui_batch.jpg", drawn)
                comparison = make_comparison([original, processed, drawn])
                save_image(Path("results/comparison") / f"{path.stem}_gui_batch.jpg", comparison)
                records.extend(build_records(path.name, {"gui_full_process": result}))
            save_metrics(records, "results/metrics", "gui_batch_metrics")
            self.statusBar().showMessage(f"批量处理完成：{len(paths)} 张图像", 8000)
            QMessageBox.information(self, "批量处理完成", f"已处理 {len(paths)} 张图像，结果保存在 results 目录。")
        except Exception as exc:
            self._error(str(exc))

    def _detector_config(self) -> DetectorConfig:
        size = self.min_size_spin.value()
        return DetectorConfig(scale_factor=self.scale_spin.value(), min_neighbors=self.neighbor_spin.value(), min_size=(size, size))

    def _save_gui_metrics(self, stem: str) -> None:
        result = {"faces": [None] * self.face_count, "eyes": [None] * self.eye_count, "elapsed_ms": self.elapsed_ms}
        save_metrics(build_records((self.current_path or Path(stem)).name, {self.method: result}), "results/metrics", f"{stem}_metrics")

    def _show(self, label: QLabel, image: np.ndarray) -> None:
        bgr = to_bgr(image)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        height, width = rgb.shape[:2]
        qimage = QImage(rgb.data, width, height, width * 3, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimage).scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(pixmap)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.original is not None:
            self._show(self.original_label, self.original)
        if self.current is not None:
            self._show(self.result_label, self.current)

    def _update_info(self, *_args) -> None:
        size = "未加载" if self.original is None else f"{self.original.shape[1]} × {self.original.shape[0]}"
        self.info_label.setText(
            f"图像尺寸：{size}　|　当前方法：{self.method}　|　人脸：{self.face_count}　|　人眼：{self.eye_count}\n"
            f"scaleFactor：{self.scale_spin.value():.2f}　 minNeighbors：{self.neighbor_spin.value()}　 minSize：{self.min_size_spin.value()} px　 Gamma：{self.gamma_spin.value():.2f}\n"
            f"运行耗时：{self.elapsed_ms:.2f} ms　|　保存路径：{self.saved_path}"
        )

    def _require_image(self) -> bool:
        if self.original is None:
            self._error("请先点击“打开图像”")
            return False
        return True

    def _error(self, message: str) -> None:
        QMessageBox.warning(self, "提示", message)

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow { background: #f3f6fa; }
            QGroupBox { font-weight: bold; border: 1px solid #c7d2e0; border-radius: 8px; margin-top: 10px; padding: 12px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
            QPushButton { min-height: 34px; border: none; border-radius: 6px; background: #246bfd; color: white; font-weight: bold; }
            QPushButton:hover { background: #174fc0; }
            #imagePanel { border: 2px dashed #a8b6c8; border-radius: 10px; background: #17202b; color: #d7e0ea; font-size: 18px; }
            #infoPanel { border: 1px solid #c7d2e0; border-radius: 8px; padding: 10px; background: white; line-height: 1.5; }
            QSpinBox, QDoubleSpinBox { min-height: 28px; }
        """)


def main() -> int:
    app = QApplication(sys.argv)
    # Windows 中文界面优先加载系统微软雅黑；某些精简 Conda/Qt 环境不会自动发现系统字体。
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyh.ttc"
    font_id = QFontDatabase.addApplicationFont(str(font_path)) if font_path.exists() else -1
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    app.setFont(QFont(families[0] if families else "Microsoft YaHei UI", 10))
    window = FaceDetectionWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
