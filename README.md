# 基于 Python + OpenCV 的人脸图像预处理及人脸检测系统设计

## 1. 项目简介

本项目是《数字图像处理与机器视觉》课程设计题目 14 的项目交付版本。系统使用 Python、NumPy、OpenCV 和 PyQt6，实现人脸图像预处理、Haar 正面人脸检测、人眼检测、检测参数调节、批量处理以及实验结果保存。

项目同时提供图形界面和命令行入口。图形界面适合课程演示与录屏答辩；命令行适合批量实验、参数对比和复现结果。代码按模块组织，GUI 只负责交互，各项算法由 `src/` 中的模块提供。

## 2. 课程设计题目说明

题目要求搭建人脸检测预处理系统，完成：

- 人脸图像光照均衡；
- 高斯噪声、椒盐噪声等干扰的去除；
- 图像尺寸归一化；
- 基于 Haar 特征分类器的正面人脸检测；
- 在人脸区域内进行人眼检测；
- 调整检测参数，分析复杂背景、轻度侧脸和弱光环境下的检测表现。

Haar 正面分类器对大角度侧脸有模型层面的限制。本项目通过预处理与参数调整改善轻度偏转和弱光图像，但不会把无标注稳定性误写成真实准确率。

## 3. 功能特性

### 3.1 图形界面

- 左侧显示原始图像，右侧显示处理或检测结果；
- 支持打开单张 JPG、JPEG、PNG、BMP、TIF/TIFF 图像；
- 支持灰度化、直方图均衡化、CLAHE、高斯去噪、中值去噪和 Gamma 校正；
- 支持人脸检测、人脸与人眼联合检测；
- 支持“一键完整处理”；
- 支持调节 `scaleFactor`、`minNeighbors`、`minSize` 和 Gamma；
- 显示图像尺寸、当前方法、检测数量、耗时、参数与保存路径；
- 支持保存当前结果以及批量处理文件夹。

### 3.2 命令行

- 单张图像处理与批量目录处理；
- 多种预处理分支自动对比；
- 检测参数传入和预设参数组合搜索；
- 自动生成检测图、对比图、CSV 与 JSON 指标。

## 4. 技术栈

- Python 3.11；
- NumPy：核心预处理算法与数值计算；
- OpenCV 4.11：图像编解码、尺寸缩放、CLAHE 和 Haar 分类器；
- PyQt6：桌面图形界面；
- Pytest：基础测试与回归验证。

## 5. 项目结构

```text
face_detection_course_design/
├─ README.md
├─ requirements.txt
├─ main.py                       命令行入口
├─ gui_app.py                    PyQt6 图形界面入口
├─ src/
│  ├─ __init__.py
│  ├─ config.py                  默认参数、格式与 Haar 路径
│  ├─ image_io.py                中文路径图像读写与目录扫描
│  ├─ preprocess.py              自主预处理算法及组合流程
│  ├─ detector.py                Haar 人脸、人眼检测及参数搜索
│  ├─ evaluator.py               指标统计与 CSV/JSON 保存
│  └─ visualizer.py              画框、拼图和结果保存
├─ data/
│  ├─ raw/                       原始与演示测试图
│  └─ processed/                 预处理结果
├─ results/
│  ├─ detection/                 检测结果图
│  ├─ comparison/                多方法对比图
│  └─ metrics/                   CSV/JSON 指标
├─ docs/                         小组后续报告材料工作区
└─ tests/
   └─ test_basic.py
```

## 6. 环境要求

- 推荐 Windows 10/11；
- 推荐 Miniconda 或 Anaconda；
- 推荐 Python 3.11；
- 屏幕建议分辨率不低于 1366×768。

OpenCV 5.0 的部分预览构建缺少本项目需要的 `CascadeClassifier`，因此项目固定使用经过验证的 `opencv-python==4.11.0.86`。

## 7. 安装依赖

使用 Conda 创建环境：

```powershell
conda create -n face_detection python=3.11 -y
conda activate face_detection
cd "C:\Users\PC\Desktop\数字图像处理课设\face_detection_course_design"
python -m pip install -r requirements.txt
```

如果环境中曾安装 OpenCV 5.0，可强制按项目版本重装：

```powershell
python -m pip install --force-reinstall -r requirements.txt
```

## 8. GUI 运行方式

```powershell
conda activate face_detection
cd "C:\Users\PC\Desktop\数字图像处理课设\face_detection_course_design"
python gui_app.py
```

## 9. 命令行运行方式

查看帮助：

```powershell
python main.py --help
```

处理单张演示图片：

```powershell
python main.py --input data/raw/sample_lena.jpg --output results/detection
```

批量处理：

```powershell
python main.py --batch data/raw --output results/detection
```

批量处理并搜索参数：

```powershell
python main.py --batch data/raw --output results/detection --optimize
```

传入自定义参数：

```powershell
python main.py --input data/raw/sample_lena.jpg --output results/detection --scale-factor 1.1 --min-neighbors 5 --min-size 40 40 --gamma 1.2
```

## 10. GUI 使用说明

1. 点击“打开图像”，选择一张含人脸的图片；
2. 点击灰度化、光照均衡、CLAHE 或滤波按钮观察单项效果；
3. 在右侧参数区调整检测参数和 Gamma；
4. 点击“人脸检测”只显示人脸框，点击“人眼检测”显示人脸与人眼；
5. 点击“一键完整处理”执行尺寸归一化、Gamma、高斯去噪、CLAHE 和联合检测；
6. 点击“保存结果”保存当前画面并同时生成指标；
7. 点击“批量处理”选择文件夹，自动生成所有图片的检测图、对比图和汇总指标。

绿色矩形代表人脸，红色矩形代表人眼。参数调整建议：

- `scaleFactor` 越接近 1，尺度搜索越细，但速度越慢；
- `minNeighbors` 越小越容易检出弱目标，同时可能增加误检；
- `minSize` 应根据图中最小人脸大小调整；
- 本项目定义中 Gamma 大于 1 用于提亮暗部。

## 11. 测试图片说明

项目保留三张可复现实验图片：

- `sample_lena.jpg`：来自 [OpenCV 官方示例仓库](https://github.com/opencv/opencv/blob/4.x/samples/data/lena.jpg)，用于正常光照演示；
- `sample_lowlight.jpg`：由官方示例图降低亮度生成；
- `sample_noise.jpg`：由官方示例图加入可复现高斯噪声生成。

课程最终实验建议补充自行拍摄或已获授权的正常光照、弱光、复杂背景、多人和轻度侧脸图片，并注明来源。不要提交来源不明的人像图片。

## 12. 输出结果说明

- `data/processed/`：命令行流程保存的 CLAHE 预处理结果；
- `results/detection/`：每个预处理分支或 GUI 批处理的画框结果；
- `results/comparison/`：原图、预处理图和检测图的拼接对比；
- `results/metrics/`：逐图逐方法的 CSV、JSON 指标和参数搜索详情。

指标包括人脸数、人眼数、检测耗时和跨分支稳定性。没有真实标注框时，稳定性只表示不同处理结果是否一致，不等于准确率。

## 13. 核心模块说明

- `preprocess.py`：实现灰度化、Gamma、直方图均衡、高斯核、自定义卷积、高斯滤波和中值滤波；封装 CLAHE 和尺寸归一化；
- `detector.py`：加载 OpenCV Haar XML，在灰度图上检测正面人脸，并在人脸上部区域检测眼睛；
- `evaluator.py`：记录检测数量、耗时和稳定性，输出 UTF-8 CSV 与 JSON；
- `visualizer.py`：绘制人脸框和人眼框，生成多宫格对比图；
- `gui_app.py`：只负责界面交互，通过上述模块完成处理，不重复实现算法。

## 14. 核心算法说明

### 14.1 灰度化

自主按 `Gray = 0.299R + 0.587G + 0.114B` 计算，不直接调用 OpenCV 灰度转换函数。

### 14.2 直方图均衡化

自主使用 `numpy.bincount` 统计 256 级灰度直方图，计算累计分布函数 CDF，再构造灰度映射表完成均衡化。

### 14.3 Gamma 校正

自主计算 256 项幂律查找表，再通过数组索引逐像素映射。Gamma 大于 1 时抬升暗部。

### 14.4 高斯滤波

自主根据二维高斯函数生成归一化高斯核，使用边缘复制填充和滑动窗口实现二维卷积。

### 14.5 中值滤波

自主构造邻域窗口，对窗口像素排序取中位数，适合抑制椒盐噪声。

### 14.6 Haar 检测

OpenCV 提供训练好的 Haar cascade XML 和滑动窗口检测接口。本项目完成模型加载、参数配置、人脸 ROI 内眼睛搜索、结果筛选和系统集成，不从零训练 Haar 分类器。

## 15. 自主实现说明

本项目自主实现了灰度化、Gamma 校正、直方图均衡化、高斯核生成、自定义二维卷积、高斯滤波和中值滤波等核心预处理算法。OpenCV 主要用于图像编解码、基础尺寸缩放、CLAHE 封装、可视化辅助以及 Haar 分类器加载与检测。`cv2.resize` 属于课程允许使用的基础图像操作。

## 16. 测试方法

```powershell
python -m pytest -q
```

测试覆盖模块导入、核心预处理算法、中文路径读写、Haar 路径加载、可视化、指标保存以及命令行帮助启动。

## 17. 常见问题

### 找不到 Haar XML 文件

确认安装的是 `opencv-python==4.11.0.86`，并执行：

```powershell
python -c "import cv2; print(cv2.data.haarcascades)"
```

### 出现 `cv2 has no attribute CascadeClassifier`

通常是安装了 OpenCV 5.0 预览构建。执行 `python -m pip install --force-reinstall -r requirements.txt`。

### 图片打不开

确认格式属于 JPG、JPEG、PNG、BMP、TIF 或 TIFF，并检查文件是否损坏。项目读写模块支持中文路径。

### GUI 启动失败

确认已经激活 `face_detection` 环境并安装 PyQt6。可执行 `python -c "import PyQt6; print('PyQt6 OK')"` 检查。

### 检测不到人脸

优先使用正面、清晰且人脸尺寸较大的图片；尝试降低 `minNeighbors`、减小 `minSize`，或先执行 Gamma/CLAHE。大角度侧脸超出正面 Haar 模型的主要适用范围。

### PyQt6 下载或安装失败

先升级 pip：`python -m pip install -U pip`。若镜像缺包，可临时指定官方源：`python -m pip install PyQt6 -i https://pypi.org/simple`。

## 18. 后续可扩展方向

- 摄像头实时人脸检测；
- 人脸关键点与姿态估计；
- DNN 或深度学习人脸检测；
- 制作人工标注集并计算 Precision、Recall、F1 与 IoU；
- 自动生成实验统计图与课程设计报告；
- 增加双边滤波、Retinex 等增强方法。

## 19. 小组分工说明

当前仓库主要完成课程设计项目代码、GUI、README、测试图片、运行结果与可复现实验流程。课程设计报告、答辩 PPT 和答辩视频由小组其他成员后续基于本项目继续完善。报告撰写时可直接引用 `results/metrics/` 中的真实运行数据，并从 `results/comparison/` 选择对比图。
