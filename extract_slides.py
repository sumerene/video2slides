"""
extract_slides.py - 从视频中提取 PPT Slide，双哈希去重

用法: python extract_slides.py <video_path> [--roi x1 y1 x2 y2] [--output DIR]

参数:
  video_path        视频文件路径
  --roi x1 y1 x2 y2  ROI 归一化坐标 (0~1)，不设则使用整帧
  --output DIR       输出目录，默认 slides/
  --interval SEC     采样间隔(秒)，默认 1.0
  --phash N          pHash 汉明距离阈值，默认 10
  --dhash N          dHash 汉明距离阈值，默认 10
  --laplacian N      Laplacian 方差阈值，默认 300
"""

import cv2
import os
import sys
import argparse
import numpy as np
from PIL import Image
import imagehash
from datetime import timedelta

sys.stdout.reconfigure(encoding='utf-8')


def crop_roi(frame, roi_pct):
    h, w = frame.shape[:2]
    x1 = int(w * roi_pct[0])
    y1 = int(h * roi_pct[1])
    x2 = int(w * roi_pct[2])
    y2 = int(h * roi_pct[3])
    return frame[y1:y2, x1:x2]


def compute_hashes(roi_bgr):
    roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(roi_rgb)
    ph = imagehash.phash(pil_img)
    dh = imagehash.dhash(pil_img)
    return ph, dh


def is_duplicate(ph, dh, saved_hashes, p_thresh, d_thresh):
    for sp, sd in saved_hashes:
        if (ph - sp) < p_thresh and (dh - sd) < d_thresh:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Extract slides from video with dual-hash dedup")
    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument("--roi", nargs=4, type=float, metavar=("X1", "Y1", "X2", "Y2"),
                        help="ROI normalized coordinates (0~1)")
    parser.add_argument("--output", default="slides", help="Output directory (default: slides/)")
    parser.add_argument("--interval", type=float, default=1.0, help="Sample interval in seconds (default: 1.0)")
    parser.add_argument("--phash", type=int, default=10, help="pHash hamming distance threshold (default: 10)")
    parser.add_argument("--dhash", type=int, default=10, help="dHash hamming distance threshold (default: 10)")
    parser.add_argument("--laplacian", type=int, default=300, help="Laplacian variance threshold (default: 300)")
    parser.add_argument("--start", type=float, default=0.0, help="Start time in seconds (default: 0.0)")
    args = parser.parse_args()

    roi_pct = tuple(args.roi) if args.roi else None
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    # Clean old files
    for f in os.listdir(output_dir):
        if f.endswith('.png'):
            os.remove(os.path.join(output_dir, f))

    cap = cv2.VideoCapture(args.video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open {args.video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    print(f"Video: {duration:.0f}s, {fps:.0f}fps, {total_frames} frames")
    if roi_pct:
        print(f"ROI: [{roi_pct[0]}, {roi_pct[1]}, {roi_pct[2]}, {roi_pct[3]}]")
    else:
        print("ROI: full frame (no crop)")

    saved_hashes = []
    prev_ph = None
    prev_dh = None
    slide_count = 0

    sec = args.start
    while sec < duration:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps))
        ret, frame = cap.read()
        if not ret:
            break

        roi = crop_roi(frame, roi_pct) if roi_pct else frame

        # Filter non-slide frames by Laplacian variance
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if lap_var < args.laplacian:
            sec += args.interval
            continue

        ph, dh = compute_hashes(roi)

        # Layer 1: skip if similar to previous frame
        if prev_ph is not None:
            if (ph - prev_ph) < args.phash and (dh - prev_dh) < args.dhash:
                sec += args.interval
                continue

        # Layer 2: global dedup
        if is_duplicate(ph, dh, saved_hashes, args.phash, args.dhash):
            prev_ph, prev_dh = ph, dh
            sec += args.interval
            continue

        slide_count += 1
        ts = str(timedelta(seconds=int(sec))).replace(":", "-")
        filename = f"slide_{slide_count:03d}_{ts}.png"
        cv2.imwrite(os.path.join(output_dir, filename), roi)
        print(f"[{slide_count}] {filename}  (t={sec:.0f}s)")

        saved_hashes.append((ph, dh))
        prev_ph, prev_dh = ph, dh
        sec += args.interval

    cap.release()
    print(f"\nDone. {slide_count} slides saved to {output_dir}")


if __name__ == "__main__":
    main()
