"""
detect_roi.py - 从用户标注红框的图片中检测 ROI 坐标

用法: python detect_roi.py <annotated_image_path> [--test <video_path>]

流程:
  1. 读取用户标注了红框的图片
  2. HSV 颜色检测提取红框像素
  3. 计算归一化坐标 [x1%, y1%, x2%, y2%]
  4. 若提供 --test <video_path>，裁剪多帧测试 ROI 是否准确
"""

import cv2
import sys
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')


def detect_red_box(image_path):
    """检测红框并返回归一化坐标"""
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Cannot read {image_path}")
        sys.exit(1)

    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 红色在 HSV 空间分两段: 0-10 和 160-180
    mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
    mask = mask1 + mask2

    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        print("Error: No red pixels found in the image")
        sys.exit(1)

    x1, x2 = xs.min(), xs.max()
    y1, y2 = ys.min(), ys.max()
    roi_pct = (round(x1 / w, 3), round(y1 / h, 3),
               round(x2 / w, 3), round(y2 / h, 3))

    print(f"Red box pixel range: x=[{x1}, {x2}], y=[{y1}, {y2}]")
    print(f"Normalized ROI: [{roi_pct[0]}, {roi_pct[1]}, {roi_pct[2]}, {roi_pct[3]}]")
    return roi_pct


def test_roi(video_path, roi_pct, num_samples=5):
    """从视频中裁剪多帧测试 ROI"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    h_frame = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w_frame = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    x1 = int(w_frame * roi_pct[0])
    y1 = int(h_frame * roi_pct[1])
    x2 = int(w_frame * roi_pct[2])
    y2 = int(h_frame * roi_pct[3])

    step = duration / (num_samples + 1)
    for i in range(num_samples):
        sec = step * (i + 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps))
        ret, frame = cap.read()
        if not ret:
            continue
        roi = frame[y1:y2, x1:x2]
        out_path = f"roi_test_{i+1}.png"
        cv2.imwrite(out_path, roi)
        print(f"  Test frame {i+1} (t={sec:.0f}s): saved to {out_path}  size={roi.shape[1]}x{roi.shape[0]}")

    cap.release()
    print(f"\nROI test frames saved. Please check if the cropping is accurate.")


def extract_frame(video_path, output_path="draw_roi_here.png"):
    """从视频中提取一帧纯画面，供用户标注红框"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * 10))  # 取第10秒
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Error: Cannot read frame from video")
        return

    cv2.imwrite(output_path, frame)
    print(f"Pure video frame saved to: {output_path}")
    print(f"Please draw a RED box on the PPT area and save the file.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Detect ROI from red box annotation")
    parser.add_argument("annotated_image", nargs="?", help="Path to image with red box annotation")
    parser.add_argument("--test", metavar="VIDEO", help="Video path for ROI test cropping")
    parser.add_argument("--extract", metavar="VIDEO", help="Extract a pure frame from video for annotation")
    args = parser.parse_args()

    if args.extract:
        extract_frame(args.extract)
    elif args.annotated_image:
        roi = detect_red_box(args.annotated_image)
        if args.test:
            print(f"\nTesting ROI on {args.test}...")
            test_roi(args.test, roi)
    else:
        parser.print_help()
