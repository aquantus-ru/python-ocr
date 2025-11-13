#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import os
import shutil
import tempfile
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import cv2

def is_tesseract_installed():
    """Check if Tesseract is installed."""
    return shutil.which("tesseract") is not None

def preprocess_image(image_source, grayscale=False, threshold=None, resize_factor=None):
    """Preprocess the image before OCR. Can accept a file path or a PIL Image object."""
    if isinstance(image_source, str):
        image = Image.open(image_source)
    else:
        image = image_source

    if grayscale:
        image = image.convert('L')

    if threshold is not None:
        image = image.point(lambda p: p > threshold and 255)

    if resize_factor is not None:
        width, height = image.size
        new_size = (int(width * resize_factor), int(height * resize_factor))
        image = image.resize(new_size, Image.LANCZOS)

    return image

def ocr_image(image, lang='eng'):
    """Perform OCR on the given image."""
    return pytesseract.image_to_string(image, lang=lang)

def process_image(file_path, args):
    """Process a single image file."""
    image = preprocess_image(file_path, args.grayscale, args.threshold, args.resize)
    return ocr_image(image, args.lang)

def process_pdf(file_path, args):
    """Process a PDF file."""
    images = convert_from_path(file_path)
    text = ""
    for image_obj in images:
        processed_image = preprocess_image(image_obj, args.grayscale, args.threshold, args.resize)
        text += ocr_image(processed_image, args.lang) + "\n\n"
    return text

def process_video(file_path, args):
    """Process a video file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        vidcap = cv2.VideoCapture(file_path)
        fps = int(vidcap.get(cv2.CAP_PROP_FPS))
        frame_interval = args.interval * fps

        count = 0
        text = ""
        while True:
            success, image = vidcap.read()
            if not success:
                break

            if count % frame_interval == 0:
                if args.resolution:
                    width, height = map(int, args.resolution.split('x'))
                    image = cv2.resize(image, (width, height))

                frame_path = os.path.join(temp_dir, f"frame{count}.jpg")
                cv2.imwrite(frame_path, image)
                processed_image = preprocess_image(frame_path, args.grayscale, args.threshold, args.resize)
                text += ocr_image(processed_image, args.lang) + "\n\n"
            count += 1
        return text

def process_file(file_path, args):
    """Process a single file."""
    basename = os.path.basename(file_path)
    filename, extension = os.path.splitext(basename)
    output_path = os.path.join(args.output, f"{filename}.txt")

    if os.path.exists(output_path) and not args.overwrite:
        overwrite = input(f"File '{output_path}' already exists. Overwrite? (y/n): ")
        if overwrite.lower() != 'y':
            return

    text = ""
    if extension.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        text = process_image(file_path, args)
    elif extension.lower() == '.pdf':
        text = process_pdf(file_path, args)
    elif extension.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
        text = process_video(file_path, args)
    else:
        print(f"Unsupported file type: {extension}")
        return

    with open(output_path, 'w') as f:
        f.write(text)

def main():
    """Main function"""
    if not is_tesseract_installed():
        print("Error: Tesseract is not installed or not in your PATH.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="OCR Scanner")
    parser.add_argument("-i", "--input", required=True, help="Path to the source file or directory")
    parser.add_argument("-o", "--output", required=True, help="Directory where the text files will be saved")
    parser.add_argument("-ow", "--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument("-l", "--lang", default="eng", help="Language for Tesseract OCR")

    # Video-specific options
    parser.add_argument("--interval", type=int, default=1, help="Time in seconds between each screenshot from a video")
    parser.add_argument("--resolution", type=str, help="Resolution for the video screenshots (e.g., 1920x1080)")

    # Image preprocessing options
    parser.add_argument("--grayscale", action="store_true", help="Convert images to grayscale before OCR")
    parser.add_argument("--threshold", type=int, help="Threshold value for black-and-white filter")
    parser.add_argument("--resize", type=float, help="Resize factor for images")

    args = parser.parse_args()

    if not os.path.exists(args.output):
        os.makedirs(args.output)

    if os.path.isdir(args.input):
        for filename in os.listdir(args.input):
            file_path = os.path.join(args.input, filename)
            process_file(file_path, args)
    else:
        process_file(args.input, args)

if __name__ == '__main__':
    main()
