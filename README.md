# Video2Slides

从演讲视频中自动提取 PPT 幻灯片，去重后生成无损 PDF。

## 简介

学术讲座、在线课程、技术分享的视频中，PPT 幻灯片是最核心的信息载体。但手动截图既低效又容易遗漏。Video2Slides 将整个流程自动化：下载视频、识别幻灯片区域、智能去重、可选画质增强，最终输出一份可直接使用的 PDF 文档。

核心特点：

- 一条命令从 B 站 / YouTube 视频提取全部幻灯片
- pHash + dHash 双哈希去重，模板相同的学术 PPT 也不会误删
- Laplacian 方差过滤，自动跳过演讲者特写和转场画面
- 用户红框标注 ROI（纯代码方案，无需多模态模型）
- 可选画质增强（dnn_superres 或 Lanczos + USM）
- img2pdf 无损 PDF 输出，零重编码

## 快速开始

### 安装依赖

```bash
pip install opencv-python imagehash Pillow img2pdf yt-dlp numpy
```

如需 dnn_superres 超分辨率增强（可选）：

```bash
pip install opencv-contrib-python
# 下载 EDSR 模型文件，如 EDSR_x2.pb
```

### 第 1 步：下载视频

```bash
# B 站 — 必须加 --proxy "" 绕过代理
yt-dlp --proxy "" -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" -o "video.mp4" <URL>

# YouTube
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" -o "video.mp4" <URL>
```

### 第 2 步：确定 ROI（如需裁剪）

全屏录屏视频可直接跳过，使用整帧提取。画中画/会议直播需要裁掉非 PPT 区域：

```bash
# A. 提取一帧纯画面，供标注
python scripts/detect_roi.py --extract video.mp4
# → 输出 draw_roi_here.png

# B. 用画图/PS 等工具在 PPT 区域画红框，保存为 annotated.png

# C. 检测红框坐标并裁剪测试
python scripts/detect_roi.py annotated.png --test video.mp4
# → 输出归一化坐标和多帧测试图，确认边界准确后进入下一步
```

### 第 3 步：提取幻灯片

```bash
# 整帧提取（无需裁剪）
python scripts/extract_slides.py video.mp4 --output slides/

# 指定 ROI 区域
python scripts/extract_slides.py video.mp4 --roi 0.085 0.185 0.691 0.788 --output slides/
```

可调参数（默认值对 1080P 学术讲座通用）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--interval` | 1.0 | 采样间隔（秒） |
| `--phash` | 10 | pHash 汉明距离阈值 |
| `--dhash` | 10 | dHash 汉明距离阈值 |
| `--laplacian` | 300 | Laplacian 方差阈值（过滤非 slide 帧） |

### 第 4 步：画质优化（可选）

ROI 裁剪后宽度 >= 1920 通常不需要。如文字模糊：

```bash
# 自动选择最佳方案
python scripts/upscale_slides.py slides/ --output slides_upscaled/

# 手动指定
python scripts/upscale_slides.py slides/ --method lanczos --output slides_upscaled/
python scripts/upscale_slides.py slides/ --method dnn_superres --model EDSR_x2.pb --output slides_upscaled/
```

### 第 5 步：生成 PDF

```bash
python scripts/generate_pdf.py slides/ --output 输出文件名.pdf

# 若做了画质优化
python scripts/generate_pdf.py slides_upscaled/ --output 输出文件名.pdf
```

## 原理说明

### 双哈希去重

两层去重机制确保无重复、无误删：

- **Layer 1（相邻帧检测）**：与上一帧比较，pHash 和 dHash 汉明距离均低于阈值则跳过。过滤同一 slide 的连续帧。
- **Layer 2（全局去重）**：与所有已保存 slide 比较，两者均低于阈值则跳过。处理"讲者回到前面 slide"的情况。

为什么需要双哈希？学术 PPT 常用统一模板，不同内容的 slide 结构高度相似，pHash 单独使用会误判为重复。dHash 对像素级文字变化更敏感，能区分模板相同但文字不同的 slide。两者必须同时判定为重复才跳过。

### Laplacian 方差过滤

Laplacian 方差低于 300 的帧通常是演讲者特写、观众镜头或转场动画，不是 slide，自动排除。

### 无损 PDF

使用 `img2pdf` 将 PNG 原始字节流直接嵌入 PDF，不经过任何重编码。**切勿使用 PIL `Image.save()` 生成 PDF**，即使 `quality=100` 也会重新 JPEG 编码，造成不可逆的文字模糊。

## 踩坑记录

| 问题 | 错误做法 | 正确做法 |
|------|---------|---------|
| B 站下载失败 | 直接 yt-dlp | 加 `--proxy ""` |
| ROI 确定 | CV 边缘检测 / 多模态 LLM | 用户画红框 + HSV 检测（纯代码，无需多模态） |
| Slide 去重 | 仅 SSIM 或仅 pHash | pHash + dHash 双哈希，两者同时判重 |
| 非 slide 帧过滤 | 亮度阈值 | Laplacian 方差阈值 |
| PDF 画质 | PIL `Image.save()` | `img2pdf` 原始字节嵌入 |
| 文字模糊 | 低分辨率直接用 | dnn_superres（优先）→ Lanczos 2x + USM（回退） |

## 目录结构

```
video2slides/
├── SKILL.md              # Skill 定义（触发词、完整 SOP）
├── README.md             # 本文件
├── LICENSE               # MIT 许可证
├── .gitignore
└── scripts/
    ├── detect_roi.py     # ROI 检测（红框 + HSV）
    ├── extract_slides.py # Slide 提取 + 双哈希去重
    ├── upscale_slides.py # 画质优化（dnn_superres / Lanczos+USM）
    └── generate_pdf.py   # 无损 PDF 生成
```

## 许可证

MIT
