"""
generate_pdf.py - 将 slide PNG 图片拼接为无损 PDF

用法: python generate_pdf.py <input_dir> [--output FILE]

使用 img2pdf 将 PNG 字节流直接嵌入 PDF，零画质损失。
不要用 PIL/Pillow 生成 PDF，会重新编码造成画质损失。
"""

import img2pdf
import os
import sys
import argparse
import glob

sys.stdout.reconfigure(encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description="Combine slide PNGs into lossless PDF")
    parser.add_argument("input_dir", help="Directory containing slide PNGs")
    parser.add_argument("--output", default=None, help="Output PDF path (default: <input_dir>/output.pdf)")
    args = parser.parse_args()

    pdf_path = args.output
    if not pdf_path:
        pdf_path = os.path.join(args.input_dir, "output.pdf")

    files = sorted(glob.glob(os.path.join(args.input_dir, "slide_*.png")))
    if not files:
        print(f"No slide_*.png found in {args.input_dir}")
        sys.exit(1)
    print(f"Combining {len(files)} slides into PDF...")

    with open(pdf_path, 'wb') as f:
        f.write(img2pdf.convert(files))

    size_mb = os.path.getsize(pdf_path) / 1024 / 1024
    print(f"PDF generated: {pdf_path}")
    print(f"Size: {size_mb:.1f} MB, Pages: {len(files)}")


if __name__ == "__main__":
    main()
