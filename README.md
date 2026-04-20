# Video2Slides

Extract presentation slides from lecture videos, deduplicate, and produce lossless PDF — automatically.

## Features

- One-command slide extraction from Bilibili / YouTube videos
- Dual-hash deduplication (pHash + dHash) — handles repeated slides and template-heavy academic PPTs
- Laplacian variance filter — skips speaker close-ups and transition frames
- User-annotated ROI detection (red box + HSV, no multimodal model needed)
- Optional upscaling (dnn_superres or Lanczos + USM) for blurry text
- Lossless PDF output via `img2pdf` — zero re-encoding

## Quick Start

### Install dependencies

```bash
pip install opencv-python imagehash Pillow img2pdf yt-dlp numpy
```

For dnn_superres upscaling (optional):

```bash
pip install opencv-contrib-python
# Download an EDSR model, e.g. EDSR_x2.pb
```

### 1. Download video

```bash
# Bilibili — MUST use --proxy ""
yt-dlp --proxy "" -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" -o "video.mp4" <URL>

# YouTube
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" -o "video.mp4" <URL>
```

### 2. Determine ROI (if needed)

For full-screen recordings — skip this step and use the whole frame.

For picture-in-picture / conference recordings:

```bash
# Step A: extract a clean frame for annotation
python detect_roi.py --extract video.mp4
# → saves draw_roi_here.png

# Step B: draw a RED box around the PPT area in any image editor, save as annotated.png

# Step C: detect ROI and test cropping
python detect_roi.py annotated.png --test video.mp4
# → prints normalized coordinates and saves test crops
```

### 3. Extract slides

```bash
# Full frame (no crop)
python extract_slides.py video.mp4 --output slides/

# With ROI
python extract_slides.py video.mp4 --roi 0.085 0.185 0.691 0.788 --output slides/
```

Key parameters (defaults work well for 1080p academic talks):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--interval` | 1.0 | Sampling interval in seconds |
| `--phash` | 10 | pHash hamming distance threshold |
| `--dhash` | 10 | dHash hamming distance threshold |
| `--laplacian` | 300 | Laplacian variance threshold (filters non-slide frames) |

### 4. Upscale (optional)

If text appears blurry after ROI cropping:

```bash
# Auto-select best available method
python upscale_slides.py slides/ --output slides_upscaled/

# Explicit method
python upscale_slides.py slides/ --method lanczos --output slides_upscaled/
python upscale_slides.py slides/ --method dnn_superres --model EDSR_x2.pb --output slides_upscaled/
```

### 5. Generate PDF

```bash
python generate_pdf.py slides/ --output presentation.pdf

# If upscaled
python generate_pdf.py slides_upscaled/ --output presentation.pdf
```

## How It Works

### Dual-hash deduplication

Two layers ensure no duplicates and no false deletions:

- **Layer 1 (adjacent frame)**: Compares each frame to the previous one. If both pHash and dHash distances are below threshold, the frame is skipped. Filters consecutive frames of the same slide.
- **Layer 2 (global)**: Compares against all saved slides. Handles the case where a speaker returns to an earlier slide.

Why both hashes? Academic PPTs often share the same template — pHash alone misses content differences on structurally similar slides. dHash catches pixel-level text changes. Both must agree a frame is duplicate to skip it.

### Laplacian variance filter

Frames with Laplacian variance below 300 are typically speaker close-ups, audience shots, or transition animations — not slides. These are automatically excluded.

### Lossless PDF

`img2pdf` embeds raw PNG byte streams into PDF. No re-encoding, no quality loss. Do NOT use PIL `Image.save()` — even at `quality=100` it re-encodes and degrades text.

## Pitfall Reference

| Problem | Wrong approach | Correct approach |
|---------|---------------|-----------------|
| Bilibili download fails | `yt-dlp` directly | Add `--proxy ""` |
| ROI detection | CV edge detection / multimodal LLM | User red box + HSV detection |
| Slide deduplication | SSIM alone or pHash alone | pHash + dHash dual-hash |
| Non-slide frame filtering | Brightness threshold | Laplacian variance threshold |
| PDF quality | PIL `Image.save()` | `img2pdf` raw byte embedding |
| Blurry text | Use low-res as-is | dnn_superres (preferred) → Lanczos 2x + USM (fallback) |

## File Overview

```
video2slides/
├── SKILL.md            # Skill definition (trigger words, full SOP)
├── README.md           # This file
├── LICENSE             # MIT License
├── detect_roi.py       # ROI detection via red box + HSV
├── extract_slides.py   # Slide extraction with dual-hash dedup
├── upscale_slides.py   # Optional upscaling (dnn_superres / Lanczos+USM)
└── generate_pdf.py     # Lossless PDF generation
```

## License

MIT
