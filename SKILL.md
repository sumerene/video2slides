---
name: video2slides
description: 从演讲视频中提取 PPT Slide，去重后生成无损 PDF。当用户提供视频 URL（Bilibili/YouTube）或要求从演示视频中提取幻灯片时触发。
---

# Video to Slides

从演讲视频中自动提取 PPT 幻灯片，去重后拼接为无损 PDF。

## 核心流程

### 1. 视频下载

- 使用 `yt-dlp` 下载视频，默认 1080P 或最高可选分辨率。
- **Bilibili 必须加 `--proxy ""`** 绕过代理，否则连接失败：
  ```
  yt-dlp --proxy "" -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" -o "video.mp4" <URL>
  ```
- 下载后记录分辨率和时长，后续步骤依赖这些信息。

### 2. 确定 ROI（Slide 区域）

**必须向用户提问：** "视频是否需要裁剪 ROI？全屏录屏不需要，画中画/会议直播需要裁掉非 PPT 区域。"

- 若用户说不需要，跳过此步，直接对整帧提取。
- 若用户说需要，采用用户标注红框方案。运行 `detect_roi.py`：

#### 用户标注红框（纯代码方案，无需多模态能力）

本方案全程由代码处理图像文件，模型不需要"看"图片，不依赖多模态能力。

1. 提取纯视频帧供用户标注：
   ```
   python scripts/detect_roi.py --extract video.mp4
   ```
   输出 `draw_roi_here.png`，将路径告知用户，让用户在外部工具（画图、PS 等）中在 PPT 区域画红框并保存。

2. 检测红框坐标并测试：
   ```
   python scripts/detect_roi.py annotated.png --test video.mp4
   ```
   输出归一化 ROI 坐标和多帧裁剪测试图。**必须让用户确认边界准确**后再进入下一步。

**不可靠的方法（不要用）：**
- CV 边缘检测 / 亮度分析 / Sobel 投影：会议装饰（logo、标题栏、分隔线）与 PPT 内容的亮度/边缘特征相似，无法区分。
- 多模态 LLM 识图给坐标：实测坐标偏差较大，仍会包含装饰区域，不可靠。

### 3. Slide 提取与去重

运行 `extract_slides.py`：
```
python scripts/extract_slides.py video.mp4 --roi 0.085 0.185 0.691 0.788 --output slides/
```
不设 `--roi` 则使用整帧，`--roi` 后接4个归一化坐标值。

采用 **pHash + dHash 双哈希** 策略，两层去重：

**Layer 1 — 相邻帧变化检测**：与上一帧比较，pHash 和 dHash 汉明距离都低于阈值则跳过。过滤同一 slide 的连续帧。

**Layer 2 — 全局去重**：与所有已保存 slide 比较，两者都低于阈值则跳过。处理"讲者回到前面 slide"的情况。

**为什么需要双哈希**：
- pHash（感知哈希）：对结构变化敏感，但学术 PPT 常用统一模板，不同内容的 slide 结构相似，pHash 差异很小。
- dHash（差异哈希）：对像素级变化（文字内容）更敏感，能区分模板相同但文字不同的 slide。
- 两者必须同时判定为重复才跳过，避免误删。

**关键参数**：
- `SAMPLE_INTERVAL = 1.0`：采样间隔（秒），1 秒对学术讲座足够
- `PHASH_THRESH = 10`：pHash 汉明距离阈值
- `DHASH_THRESH = 10`：dHash 汉明距离阈值
- `LAPLACIAN_THRESH = 300`：Laplacian 方差阈值，低于此值的帧（演讲者特写、转场画面）不是 slide

### 4. Slide 画质优化

**必须向用户提问：** "提取的 slide 文字是否模糊？需要做画质优化吗？"（若 ROI 裁剪后分辨率 >= 1920 宽度，可提示用户当前分辨率足够，通常不需要。）

若用户确认需要，运行 `upscale_slides.py`：
```
python scripts/upscale_slides.py slides/ --output slides_upscaled/
```
默认自动选择方案（先尝试 dnn_superres，不可用则回退 Lanczos + USM）。
也可手动指定：`--method dnn_superres --model EDSR_x2.pb` 或 `--method lanczos`。

**不推荐的方法**：
- CLAHE 对比度增强：会改变 PPT 原始配色，不适用。
- Real-ESRGAN：Python 3.14 不兼容 basicsr，且需要 GPU，通用性差。

### 5. 生成 PDF

运行 `generate_pdf.py`：
```
python scripts/generate_pdf.py slides/ --output 肺癌免疫治疗生物标志物研究进展.pdf
```
若做了画质优化，则用放大后的目录：
```
python scripts/generate_pdf.py slides_upscaled/ --output 肺癌免疫治疗生物标志物研究进展.pdf
```

脚本使用 `img2pdf` 将 PNG 字节流直接嵌入 PDF，零画质损失。

**绝对不要用 PIL/Pillow 生成 PDF**：`Image.save()` 即使 `quality=100` 也会重新编码，造成不可逆画质损失。用户对此零容忍。

## 依赖

```
pip install opencv-python imagehash Pillow img2pdf yt-dlp numpy
```

## 踩坑记录

| 问题 | 错误做法 | 正确做法 |
|------|---------|---------|
| Bilibili 下载失败 | 直接 yt-dlp | 加 `--proxy ""` |
| ROI 确定 | CV 边缘检测 / 多模态 LLM | 用户画红框，HSV 检测（纯代码，无需多模态） |
| Slide 去重 | 仅 SSIM 或仅 pHash | pHash + dHash 双哈希，两者同时判重 |
| 非slide帧过滤 | 亮度阈值 | Laplacian 方差阈值 |
| PDF 画质 | PIL Image.save | img2pdf 原始字节嵌入 |
| 文字模糊 | 原始分辨率直接用 | dnn_superres（优先）→ Lanczos 2x + USM（回退） |

## 泛化说明

- ROI 是每个视频唯一的，不可硬编码。需 ROI 时走"提取纯帧 → 用户标红框 → HSV 检测 → 用户确认"流程。全屏录屏视频可跳过 ROI。
- 红框方案是纯代码方案，不需要模型具备多模态能力，任何能执行 Python/OpenCV 的环境都可用。
- 双哈希阈值对 1080P 学术 PPT 通用。若视频分辨率差异大，可微调 `LAPLACIAN_THRESH`。
- 采样间隔 1 秒适用于大多数学术讲座（换页速度 ~5-30 秒/页）。若为快速翻页的短视频，可降至 0.5 秒。
- 画质优化步骤可选，若 ROI 裁剪后分辨率 >= 1920 宽度，可跳过。优先尝试 dnn_superres，不可用则回退 Lanczos + USM。
