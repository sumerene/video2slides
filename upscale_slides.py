"""
upscale_slides.py - Slide 画质优化

用法: python upscale_slides.py <input_dir> [--output DIR] [--method auto|dnn_superres|lanczos]

按优先级自动选择方案:
  1. dnn_superres (效果最好，需 opencv-contrib-python 含 dnn_superres 模块 + 模型文件)
  2. Lanczos 2x + USM 锐化 (通用回退方案)
"""

import cv2
import os
import sys
import argparse
import glob

sys.stdout.reconfigure(encoding='utf-8')


def upscale_lanczos_usm(img):
    """Lanczos 2x 放大 + USM 锐化"""
    h, w = img.shape[:2]
    up = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_LANCZOS4)
    blurred = cv2.GaussianBlur(up, (0, 0), 1.5)
    sharpened = cv2.addWeighted(up, 2.0, blurred, -1.0, 0)
    return sharpened


def upscale_dnn_superres(img, model_path, scale=2):
    """OpenCV dnn_superres 超分辨率放大"""
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(model_path)
    sr.setModel("edsr", scale)
    result = sr.upsample(img)
    return result


def check_dnn_superres_available():
    """检查 dnn_superres 模块是否可用"""
    try:
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        return True
    except AttributeError:
        return False


def main():
    parser = argparse.ArgumentParser(description="Upscale slides for better text clarity")
    parser.add_argument("input_dir", help="Directory containing slide PNGs")
    parser.add_argument("--output", default=None, help="Output directory (default: <input_dir>_upscaled)")
    parser.add_argument("--method", choices=["auto", "dnn_superres", "lanczos"], default="auto",
                        help="Upscale method (default: auto)")
    parser.add_argument("--model", default=None, help="Path to dnn_superres model file (e.g. EDSR_x2.pb)")
    args = parser.parse_args()

    output_dir = args.output or (args.input_dir.rstrip("/\\") + "_upscaled")
    os.makedirs(output_dir, exist_ok=True)

    # Clean output dir
    for f in os.listdir(output_dir):
        if f.endswith('.png'):
            os.remove(os.path.join(output_dir, f))

    # Determine method
    use_dnn = False
    if args.method == "dnn_superres":
        if not check_dnn_superres_available():
            print("Error: dnn_superres module not available in opencv-contrib-python")
            sys.exit(1)
        if not args.model or not os.path.isfile(args.model):
            print("Error: --model path required for dnn_superres method")
            sys.exit(1)
        use_dnn = True
    elif args.method == "auto":
        if check_dnn_superres_available() and args.model and os.path.isfile(args.model):
            use_dnn = True
            print("Auto: dnn_superres available, using it")
        else:
            print("Auto: dnn_superres not available, falling back to Lanczos + USM")

    files = sorted(glob.glob(os.path.join(args.input_dir, "slide_*.png")))
    if not files:
        print(f"No slide_*.png found in {args.input_dir}")
        sys.exit(1)
    print(f"Found {len(files)} slides")

    for i, fpath in enumerate(files):
        img = cv2.imread(fpath)
        if img is None:
            print(f"  Skip: {fpath} (cannot read)")
            continue

        if use_dnn:
            result = upscale_dnn_superres(img, args.model)
        else:
            result = upscale_lanczos_usm(img)

        fname = os.path.basename(fpath)
        cv2.imwrite(os.path.join(output_dir, fname), result)

        if (i + 1) % 10 == 0 or i == 0 or i == len(files) - 1:
            print(f"  [{i+1}/{len(files)}] {fname} {img.shape[1]}x{img.shape[0]} -> {result.shape[1]}x{result.shape[0]}")

    print(f"\nDone. {len(files)} slides upscaled to {output_dir}")


if __name__ == "__main__":
    main()
