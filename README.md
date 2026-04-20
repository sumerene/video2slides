# Video2Slides

从演讲视频中自动提取 PPT 幻灯片，去重后生成无损 PDF。

## 核心思路

视频 → 采样帧 → 双哈希去重 → Laplacian 过滤非 slide 帧 → 无损 PDF

去重采用 pHash + dHash 双层判定：pHash 对结构敏感，但学术 PPT 模板统一时容易误判；dHash 对文字内容差异更敏感。两者同时判重才跳过，避免误删。

## 快速开始

```bash
pip install opencv-python imagehash Pillow img2pdf yt-dlp numpy
```

**1. 下载视频**

```bash
# B 站 — 必须加 --proxy ""
yt-dlp --proxy "" -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" -o "video.mp4" <URL>

# YouTube
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" -o "video.mp4" <URL>
```

**2. 确定 ROI（可选）**

全屏录屏跳过此步。画中画/会议直播需裁掉非 PPT 区域：

```bash
python scripts/detect_roi.py --extract video.mp4    # 输出 draw_roi_here.png
# 用画图工具在 PPT 区域画红框，保存为 annotated.png
python scripts/detect_roi.py annotated.png --test video.mp4  # 输出坐标 + 测试图
```

**3. 提取幻灯片**

```bash
# 整帧提取
python scripts/extract_slides.py video.mp4 --output slides/

# 指定 ROI
python scripts/extract_slides.py video.mp4 --roi 0.085 0.185 0.691 0.788 --output slides/
```

**4. 画质优化（可选）**

ROI 裁剪后宽度 >= 1920 通常不需要：

```bash
python scripts/upscale_slides.py slides/ --output slides_upscaled/
```

**5. 生成 PDF**

```bash
python scripts/generate_pdf.py slides/ --output output.pdf
```

使用 img2pdf 将 PNG 字节流直接嵌入 PDF，零重编码。不要用 PIL 生成 PDF，即使 quality=100 也会重新 JPEG 编码导致文字模糊。

## 目录结构

```
video2slides/
├── SKILL.md              # Skill 定义（触发词、完整 SOP、踩坑记录）
├── README.md
├── LICENSE
└── scripts/
    ├── detect_roi.py     # ROI 检测（红框标注 + HSV 提取）
    ├── extract_slides.py # Slide 提取 + pHash/dHash 双哈希去重
    ├── upscale_slides.py # 画质优化（dnn_superres / Lanczos+USM）
    └── generate_pdf.py   # img2pdf 无损 PDF 生成
```

## 许可证

MIT
